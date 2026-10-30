"""Property-based tests (Hypothesis) for the guardrails and the policy answer rules."""

from __future__ import annotations

import re

from hypothesis import given, settings
from hypothesis import strategies as st

from services.assistant.guardrails import detect_injection, luhn_ok, redact_pii
from services.assistant.rag.answer import content_words, support_ratio


def _luhn_check_digit(payload: str) -> str:
    for digit in "0123456789":
        if luhn_ok(payload + digit):
            return digit
    raise AssertionError("unreachable: every payload has one valid check digit")


@given(st.text(alphabet="0123456789", min_size=12, max_size=18))
@settings(max_examples=300, deadline=None)
def test_valid_card_numbers_are_always_redacted(payload: str) -> None:
    card = payload + _luhn_check_digit(payload)
    if not 13 <= len(card) <= 19:
        return
    text = f"my card is {card} please"
    out = redact_pii(text).text
    assert card not in out
    assert "[CARD_NUMBER]" in out


@given(st.text(alphabet="0123456789", min_size=13, max_size=19))
@settings(max_examples=300, deadline=None)
def test_luhn_matches_the_reference_definition(digits: str) -> None:
    total = 0
    for i, ch in enumerate(reversed(digits)):
        d = int(ch)
        if i % 2 == 1:
            d *= 2
            if d > 9:
                d -= 9
        total += d
    assert luhn_ok(digits) == (total % 10 == 0)


@given(st.text(max_size=300))
@settings(max_examples=300, deadline=None)
def test_redaction_never_crashes_and_is_idempotent(text: str) -> None:
    once = redact_pii(text).text
    twice = redact_pii(once).text
    assert twice == once


@given(st.from_regex(r"[a-z]{3,8}( [a-z]{3,8}){2,6}", fullmatch=True))
@settings(max_examples=200, deadline=None)
def test_ordinary_english_questions_are_not_flagged_as_injection(question: str) -> None:
    # Random lowercase words. None of them should match an injection pattern by chance.
    assert detect_injection(question) is None


@given(st.text(max_size=200), st.text(max_size=200))
@settings(max_examples=300, deadline=None)
def test_support_ratio_is_a_fraction(sentence: str, source: str) -> None:
    ratio = support_ratio(sentence, source)
    assert 0.0 <= ratio <= 1.0


@given(st.text(max_size=200))
@settings(max_examples=200, deadline=None)
def test_a_sentence_supports_itself(sentence: str) -> None:
    if content_words(sentence):
        assert support_ratio(sentence, sentence) == 1.0


def test_hypothesis_regex_fixture_is_valid() -> None:
    # Guards the pattern used above, so a typo fails here rather than silently testing nothing.
    assert re.fullmatch(r"[a-z]{3,8}( [a-z]{3,8}){2,6}", "alpha beta gamma")
