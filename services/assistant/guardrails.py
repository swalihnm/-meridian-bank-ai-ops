"""Input and output guardrails: injection defence, PII redaction, kill-switch and daily budget.

Presidio (PLAN Section 6) is not installed yet, so PII redaction is rule-based here. The rules
use checksums where a format has one (Luhn for card numbers, mod-97 for IBANs) so ordinary numbers
are not redacted by mistake. Presidio can replace this module later behind the same interface.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date

# ---- injection ----------------------------------------------------------------

INJECTION_PATTERNS = [
    re.compile(p, re.IGNORECASE)
    for p in (
        r"ignore (all |any |the )?(previous|prior|above) (instructions|rules|prompts)",
        r"disregard (all |your )?(instructions|rules|policy|policies)",
        r"you are now (in )?(developer|dan|jailbreak|unrestricted) mode",
        r"reveal (your|the) (system )?prompt",
        r"(transfer|send|pay|withdraw) .{0,40}(all|every|the entire) .{0,20}(balance|money|funds)",
        r"act as (an? )?(admin|administrator|root|system)",
        r"override (the )?(approval|confirmation|limit|verification)",
        r"(rules|guidelines|instructions|restrictions|policies) .{0,40}"
        r"(no longer|do not|don't|not) apply",
        r"(skip|bypass|ignore|disable) (the |this |my )?"
        r"(confirmation|verification|approval|rules|step)",
        r"(print|paste|output|show|reveal) .{0,30}"
        r"(system prompt|configuration|hidden instructions|instructions)",
        r"no restrictions",
        r"(release|transfer|send|move|wire|pay) .{0,50}"
        r"(funds|money|balance|savings|dirhams|everything)",
    )
]

# Arabic equivalents of "ignore previous instructions"
INJECTION_AR = re.compile(r"تجاهل (كل |جميع )?(التعليمات|القواعد) (السابقة|السابقه)")


def detect_injection(text: str) -> str | None:
    """Return the name of the matched pattern, or None."""
    for pattern in INJECTION_PATTERNS:
        if pattern.search(text):
            return pattern.pattern
    if INJECTION_AR.search(text):
        return "arabic_ignore_instructions"
    return None


# ---- PII ----------------------------------------------------------------------

EMIRATES_ID = re.compile(r"\b784-?\d{4}-?\d{7}-?\d\b")
EMAIL = re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b")
UAE_PHONE = re.compile(r"(?:\+971|00971|\b0)5\d[\s-]?\d{3}[\s-]?\d{4}\b")
IBAN_AE = re.compile(r"\bAE\d{2}\s?(?:\d{4}\s?){4}\d{3}\b")
CARD_CANDIDATE = re.compile(r"\b(?:\d[ -]?){13,19}\b")


def luhn_ok(digits: str) -> bool:
    total = 0
    for i, ch in enumerate(reversed(digits)):
        d = int(ch)
        if i % 2 == 1:
            d *= 2
            if d > 9:
                d -= 9
        total += d
    return total % 10 == 0


def iban_ok(iban: str) -> bool:
    compact = iban.replace(" ", "").upper()
    rearranged = compact[4:] + compact[:4]
    numeric = "".join(str(int(c, 36)) for c in rearranged)
    return int(numeric) % 97 == 1


@dataclass(frozen=True)
class Redaction:
    text: str
    kinds: tuple[str, ...]


def redact_pii(text: str) -> Redaction:
    kinds: list[str] = []

    def sub(pattern: re.Pattern[str], label: str, src: str, valid: object = None) -> str:
        def repl(m: re.Match[str]) -> str:
            if valid is not None and not valid(m.group(0)):  # type: ignore[operator]
                return m.group(0)
            kinds.append(label)
            return f"[{label}]"

        return pattern.sub(repl, src)

    out = sub(EMIRATES_ID, "EMIRATES_ID", text)
    out = sub(IBAN_AE, "IBAN", out, iban_ok)
    out = sub(CARD_CANDIDATE, "CARD_NUMBER", out, lambda s: _digits_luhn(s))
    out = sub(EMAIL, "EMAIL", out)
    out = sub(UAE_PHONE, "PHONE", out)
    return Redaction(out, tuple(kinds))


def _digits_luhn(candidate: str) -> bool:
    digits = re.sub(r"\D", "", candidate)
    return 13 <= len(digits) <= 19 and luhn_ok(digits)


# ---- kill-switch and budget -----------------------------------------------------


@dataclass
class KillSwitch:
    enabled: bool = False
    reason: str = ""

    def trip(self, reason: str) -> None:
        self.enabled, self.reason = True, reason

    def reset(self) -> None:
        self.enabled, self.reason = False, ""


@dataclass
class DailyBudget:
    """Cap on spend per day, in USD cents. Spend is recorded per call and refused when over."""

    limit_cents: int
    day: date = field(default_factory=date.today)
    spent_cents: int = 0

    def _roll(self, today: date) -> None:
        if today != self.day:
            self.day, self.spent_cents = today, 0

    def can_spend(self, cents: int, today: date | None = None) -> bool:
        self._roll(today or date.today())
        return self.spent_cents + cents <= self.limit_cents

    def record(self, cents: int, today: date | None = None) -> None:
        self._roll(today or date.today())
        self.spent_cents += cents
