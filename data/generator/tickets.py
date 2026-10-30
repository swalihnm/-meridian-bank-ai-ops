"""Synthetic customer tickets with intent labels.

Templates are hand-written and paraphrased. Light character noise (typos, casing, dropped
punctuation) is added so a model cannot score perfectly by memorising template strings.
These tickets are SYNTHETIC. Report results on them as such; the public Banking77 set is the
real-text benchmark.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

TICKET_INTENTS = (
    "card_freeze",
    "card_dispute",
    "fee_question",
    "limit_question",
    "address_change",
    "account_closure",
    "complaint",
    "other",
)

TEMPLATES_EN: dict[str, tuple[str, ...]] = {
    "card_freeze": (
        "Please freeze my card, I think I lost it",
        "I want to block my debit card right now",
        "my card was stolen, stop it immediately",
        "can you temporarily lock my card ending {last4}",
    ),
    "card_dispute": (
        "I see a charge of {amount} that I did not make, I want to dispute it",
        "there is a transaction I don't recognise, please open a dispute",
        "I was charged twice for the same purchase, I want my money back",
        "wrong amount charged at a shop, how do I raise a chargeback",
    ),
    "fee_question": (
        "why was I charged a fee on my account this month",
        "what is the fee for a foreign currency transaction",
        "how much is the ATM withdrawal fee abroad",
        "explain the monthly maintenance charge on my statement",
    ),
    "limit_question": (
        "what is my daily spending limit on the card",
        "can I increase my ATM withdrawal limit",
        "what is the maximum I can transfer per day",
        "how do I raise my online payment limit",
    ),
    "address_change": (
        "I moved house, how do I update my address",
        "please change the postal address on my account",
        "my new address is different, where do I update it",
    ),
    "account_closure": (
        "I want to close my account and move to another bank",
        "how do I cancel my savings account",
        "please terminate my current account",
    ),
    "complaint": (
        "this is the third time I've had a problem, I am very unhappy with your service",
        "I want to complain about how my case was handled",
        "your agent was rude to me, I want to file a formal complaint",
    ),
    "other": (
        "what are your opening hours for the branch",
        "do you have an app for tablets",
        "hello, I have a general question",
    ),
}

TEMPLATES_AR: dict[str, tuple[str, ...]] = {
    "card_freeze": ("من فضلك أوقف بطاقتي فقد ضاعت",),
    "card_dispute": ("هناك عملية لم أقم بها أريد الاعتراض عليها",),
    "fee_question": ("لماذا تم خصم رسوم من حسابي هذا الشهر",),
    "limit_question": ("ما هو الحد اليومي للسحب من البطاقة",),
    "address_change": ("انتقلت إلى منزل جديد كيف أغير عنواني",),
    "account_closure": ("أريد إغلاق حسابي",),
    "complaint": ("أنا غير راضٍ عن الخدمة وأريد تقديم شكوى",),
    "other": ("ما هي ساعات عمل الفرع",),
}


def _add_noise(text: str, rng: np.random.Generator) -> str:
    chars = list(text)
    if len(chars) > 8 and rng.random() < 0.3:
        i = int(rng.integers(1, len(chars) - 1))
        chars[i], chars[i - 1] = chars[i - 1], chars[i]  # swap two adjacent letters
    out = "".join(chars)
    if rng.random() < 0.3:
        out = out.lower()
    if rng.random() < 0.3:
        out = out.rstrip(".!?")
    return out


def generate_tickets(
    customer_ids: list[str], n_tickets: int, seed: int, start: str = "2025-01-01"
) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    intents = rng.choice(TICKET_INTENTS, size=n_tickets)
    rows: list[dict[str, object]] = []
    for i, intent in enumerate(intents):
        use_ar = rng.random() < 0.15 and TEMPLATES_AR.get(str(intent))
        pool = TEMPLATES_AR[str(intent)] if use_ar else TEMPLATES_EN[str(intent)]
        template = pool[int(rng.integers(0, len(pool)))]
        text = template.format(
            last4=f"{int(rng.integers(0, 10_000)):04d}",
            amount=f"AED {int(rng.integers(20, 5_000))}",
        )
        rows.append(
            {
                "ticket_id": f"TK{i + 1:07d}",
                "customer_id": customer_ids[int(rng.integers(0, len(customer_ids)))],
                "channel": str(
                    rng.choice(["app", "email", "chat", "complaint"], p=[0.5, 0.2, 0.2, 0.1])
                ),
                "language": "ar" if use_ar else "en",
                "text": _add_noise(text, rng) if not use_ar else text,
                "intent": str(intent),
            }
        )
    frame = pd.DataFrame(rows)
    frame["created_at"] = pd.Timestamp(start) + pd.to_timedelta(
        rng.integers(0, 365 * 24 * 60, len(frame)), unit="m"
    )
    return frame
