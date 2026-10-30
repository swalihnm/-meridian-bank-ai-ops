"""Lexical retrieval: tokenizer, hit type and BM25 index.

No torch here, so the API and the scenario suite can run from a slim image. The dense
and reranker code stays in retrieval.py.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

import numpy as np
from rank_bm25 import BM25Okapi

from services.assistant.rag.chunking import Chunk

# Unicode word characters, so Arabic words are tokens. English tokenization is unchanged for
# ASCII text (letters, digits, and the same splits at punctuation).
TOKEN = re.compile(r"\w+")


def tokenize(text: str) -> list[str]:
    return TOKEN.findall(text.lower())


@dataclass(frozen=True)
class Hit:
    chunk: Chunk
    score: float


class BM25Index:
    """Lexical-only index. No model download, so it is deterministic and fast for CI gates."""

    def __init__(self, chunks: list[Chunk]) -> None:
        self.chunks = chunks
        self.bm25 = BM25Okapi([tokenize(c.text) for c in chunks])

    def search(self, query: str, k: int = 5) -> list[Hit]:
        scores = self.bm25.get_scores(tokenize(query))
        order = np.argsort(-scores)[:k]
        return [Hit(self.chunks[int(i)], float(scores[int(i)])) for i in order]
