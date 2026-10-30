"""Parse POLICIES.md into policy chunks.

Each policy (## POL-xxx heading) is split into sentence windows. Windows keep the policy ID
so a citation always points at a real policy. Window size and overlap are parameters so
the chunking experiment in Week 4 can be repeated.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

HEADING = re.compile(r"^## (POL-\d{3}) (.+)$", re.MULTILINE)
SENTENCE_END = re.compile(r"(?<=[.!?])\s+")


@dataclass(frozen=True)
class Chunk:
    chunk_id: str
    policy_id: str
    title: str
    text: str


def parse_policies(markdown: str) -> dict[str, tuple[str, str]]:
    """Return {policy_id: (title, body)} in document order."""
    matches = list(HEADING.finditer(markdown))
    policies: dict[str, tuple[str, str]] = {}
    for i, m in enumerate(matches):
        end = matches[i + 1].start() if i + 1 < len(matches) else len(markdown)
        body = markdown[m.end() : end].strip()
        policies[m.group(1)] = (m.group(2).strip(), body)
    return policies


def split_sentences(text: str) -> list[str]:
    return [s.strip() for s in SENTENCE_END.split(text) if s.strip()]


def chunk_policies(
    policies: dict[str, tuple[str, str]], window: int = 2, overlap: int = 1
) -> list[Chunk]:
    if window < 1 or overlap < 0 or overlap >= window:
        raise ValueError("need window >= 1 and 0 <= overlap < window")
    step = window - overlap
    chunks: list[Chunk] = []
    for policy_id, (title, body) in policies.items():
        sentences = split_sentences(body)
        starts = range(0, max(len(sentences) - overlap, 1), step)
        for n, start in enumerate(starts):
            text = " ".join(sentences[start : start + window])
            chunks.append(Chunk(f"{policy_id}-{n}", policy_id, title, text))
    return chunks


def load_chunks(path: Path, window: int = 2, overlap: int = 1) -> list[Chunk]:
    return chunk_policies(parse_policies(path.read_text(encoding="utf-8")), window, overlap)
