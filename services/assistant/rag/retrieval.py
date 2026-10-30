"""Hybrid retrieval: BM25 + dense embeddings, fused with reciprocal rank fusion (RRF).

Optional cross-encoder reranker on the fused top-k. The dense index is held in memory with numpy.
pgvector is the production target (PLAN Section 5); it is deferred until the Postgres
container is part of the stack (see docs/LOG.md).
"""

from __future__ import annotations

from typing import Protocol

import numpy as np
import numpy.typing as npt
import torch
from rank_bm25 import BM25Okapi
from transformers import AutoModel, AutoModelForSequenceClassification, AutoTokenizer

from services.assistant.rag.chunking import Chunk
from services.assistant.rag.lexical import Hit, tokenize

EMBED_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
RERANK_MODEL = "cross-encoder/ms-marco-MiniLM-L-6-v2"
RRF_K = 60


class Embedder(Protocol):
    def encode(self, texts: list[str]) -> npt.NDArray[np.float32]: ...


class TransformerEmbedder:
    """Mean-pooled, L2-normalised sentence embeddings."""

    def __init__(self, model_id: str = EMBED_MODEL) -> None:
        self.tokenizer = AutoTokenizer.from_pretrained(model_id)
        self.model = AutoModel.from_pretrained(model_id).eval()

    @torch.no_grad()
    def encode(self, texts: list[str]) -> npt.NDArray[np.float32]:
        enc = self.tokenizer(
            texts, padding=True, truncation=True, max_length=256, return_tensors="pt"
        )
        out = self.model(**enc).last_hidden_state
        mask = enc["attention_mask"].unsqueeze(-1).float()
        pooled = (out * mask).sum(dim=1) / mask.sum(dim=1).clamp(min=1e-9)
        normed = torch.nn.functional.normalize(pooled, p=2, dim=1)
        return normed.cpu().numpy().astype(np.float32)


class HybridIndex:
    def __init__(self, chunks: list[Chunk], embedder: Embedder) -> None:
        self.chunks = chunks
        self.embedder = embedder
        self.bm25 = BM25Okapi([tokenize(c.text) for c in chunks])
        self.vectors = embedder.encode([c.text for c in chunks])

    def bm25_ranks(self, query: str) -> list[int]:
        scores = self.bm25.get_scores(tokenize(query))
        return list(np.argsort(-scores))

    def dense_ranks(self, query: str) -> list[int]:
        q = self.embedder.encode([query])[0]
        return list(np.argsort(-(self.vectors @ q)))

    def search(
        self, query: str, k: int = 5, use_dense: bool = True, use_bm25: bool = True
    ) -> list[Hit]:
        """Fuse the enabled rankers with RRF and return the top k chunks."""
        rankings: list[list[int]] = []
        if use_bm25:
            rankings.append(self.bm25_ranks(query))
        if use_dense:
            rankings.append(self.dense_ranks(query))
        if not rankings:
            raise ValueError("at least one ranker must be enabled")
        fused: dict[int, float] = {}
        for ranking in rankings:
            for rank, idx in enumerate(ranking):
                fused[int(idx)] = fused.get(int(idx), 0.0) + 1.0 / (RRF_K + rank + 1)
        top = sorted(fused.items(), key=lambda kv: -kv[1])[:k]
        return [Hit(self.chunks[i], score) for i, score in top]


class CrossEncoderReranker:
    def __init__(self, model_id: str = RERANK_MODEL) -> None:
        self.tokenizer = AutoTokenizer.from_pretrained(model_id)
        self.model = AutoModelForSequenceClassification.from_pretrained(model_id).eval()

    @torch.no_grad()
    def rerank(self, query: str, hits: list[Hit]) -> list[Hit]:
        if not hits:
            return hits
        enc = self.tokenizer(
            [query] * len(hits),
            [h.chunk.text for h in hits],
            padding=True,
            truncation=True,
            max_length=256,
            return_tensors="pt",
        )
        scores = self.model(**enc).logits.squeeze(-1).cpu().numpy()
        order = np.argsort(-scores)
        return [Hit(hits[i].chunk, float(scores[i])) for i in order]
