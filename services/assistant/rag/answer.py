"""Answer composition and citation verification for policy questions.

No hosted LLM is wired in yet, so answers are EXTRACTIVE: the best-matching sentences from the
top retrieved policy. Extractive answers are supported by construction; the citation check
matters once a generator is added (Week 5 onward), and it is tested here with deliberately
unsupported sentences so the blocking logic is proven, not assumed.

An answer is blocked (the assistant abstains and offers a human, POL-028) when:
- no retrieved policy shares enough content words with the question, or
- a composed sentence is not supported by the policy it cites.
"""

from __future__ import annotations

from dataclasses import dataclass

from services.assistant.rag.chunking import split_sentences
from services.assistant.rag.lexical import Hit, tokenize

STOPWORDS = frozenset(
    [
        "a",
        "an",
        "and",
        "are",
        "as",
        "at",
        "be",
        "by",
        "can",
        "do",
        "does",
        "for",
        "from",
        "has",
        "have",
        "how",
        "i",
        "if",
        "in",
        "is",
        "it",
        "its",
        "my",
        "of",
        "on",
        "or",
        "the",
        "to",
        "what",
        "when",
        "where",
        "which",
        "who",
        "why",
        "will",
        "with",
        "you",
        "your",
        "me",
        "we",
        "our",
        "there",
        "this",
        "that",
        "about",
        "tell",
        "please",
        "write",
        "give",
        "say",
        "need",
        "want",
        "get",
        # Arabic function words, so they do not count as content in the abstain rule.
        "ما",
        "هي",
        "هو",
        "هل",
        "كم",
        "متى",
        "كيف",
        "على",
        "في",
        "من",
        "إلى",
        "عن",
        "أن",
        "و",
        "أو",
        "لا",
        "هذا",
        "هذه",
        "التي",
        "الذي",
        "أريد",
        "فضلك",
    ]
)
SUPPORT_THRESHOLD = 0.6
MIN_QUERY_MATCHES = 2
MIN_QUERY_SHARE = 0.5


@dataclass(frozen=True)
class Citation:
    policy_id: str
    title: str


@dataclass(frozen=True)
class Answer:
    text: str | None
    citations: list[Citation]
    blocked_reason: str | None

    @property
    def answered(self) -> bool:
        return self.text is not None


def content_words(text: str) -> set[str]:
    return {t for t in tokenize(text) if t not in STOPWORDS}


def support_ratio(sentence: str, source: str) -> float:
    """Share of the sentence's content words that appear in the source text."""
    words = content_words(sentence)
    if not words:
        return 1.0
    return len(words & content_words(source)) / len(words)


def is_supported(sentence: str, source: str) -> bool:
    return support_ratio(sentence, source) >= SUPPORT_THRESHOLD


def verify_citations(sentences: list[str], source: str) -> list[str]:
    """Return the sentences that are NOT supported by the cited source."""
    return [s for s in sentences if not is_supported(s, source)]


def compose_answer(
    question: str,
    hits: list[Hit],
    max_sentences: int = 2,
    min_matches: int = MIN_QUERY_MATCHES,
    min_share: float = MIN_QUERY_SHARE,
) -> Answer:
    if not hits:
        return Answer(None, [], "no_policy_retrieved")
    top = hits[0].chunk
    query_words = content_words(question)
    if not query_words:
        return Answer(None, [], "no_content_in_question")
    matched = len(query_words & content_words(top.text))
    # One shared generic word is not evidence: require two matches, or half the question.
    if matched < min_matches and matched / len(query_words) < min_share:
        return Answer(None, [], "low_query_overlap")

    candidates = split_sentences(top.text)
    ranked = sorted(
        candidates,
        key=lambda s: -len(content_words(question) & content_words(s)),
    )
    chosen = [s for s in ranked[:max_sentences] if s]
    unsupported = verify_citations(chosen, top.text)
    if unsupported or not chosen:
        return Answer(None, [], "citation_check_failed")
    citation = Citation(top.policy_id, top.title)
    return Answer(" ".join(chosen), [citation], None)
