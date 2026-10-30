"""LLM evaluation on the policy golden set (Week 6 judge, Week 8 strong-model path).

Two parts, both using the hosted model via services/assistant/llm/ollama_client.py:

1. Judge agreement. For each in-scope question, the extractive answer and its cited policy are shown
   to the model, which answers SUPPORTED or NOT_SUPPORTED. The reference label is programmatic: the
   cited policy is the expected one. This is NOT human labelling, so the kappa measures agreement
   with a rule, not with people. The plan's human-labelled kappa is still open.

2. Generated answers. The model answers from the top retrieved policies and must cite a policy ID.
   The same citation check as the extractive path measures unsupported sentences. Out-of-scope
   questions should get NO_ANSWER.

Requires OLLAMA_API_KEY in the environment. Writes ml/eval/results/llm_eval.json.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from ml.eval.retrieval_eval import GOLDEN_PATH, POLICY_PATH, Case, load_golden
from services.assistant.llm.ollama_client import OllamaClient
from services.assistant.rag.answer import compose_answer, is_supported
from services.assistant.rag.chunking import load_chunks, split_sentences
from services.assistant.rag.lexical import BM25Index
from services.experiments.stats import wilson_interval

RESULTS = Path("ml/eval/results/llm_eval.json")
K = 3
JUDGE_SYSTEM = (
    "You check bank assistant answers. Reply with exactly one word: SUPPORTED if the answer is "
    "correct according to the cited policy text, otherwise NOT_SUPPORTED."
)
GEN_SYSTEM = (
    "You answer customer questions about Meridian Bank using ONLY the policy excerpts given.\n"
    "Rules:\n"
    "1. Use at most two sentences. Each sentence must copy a fact that appears word for word in "
    "the excerpt you cite. Do not add numbers, names or conditions that are not in the excerpt.\n"
    "2. End with the single policy ID you used, as (source: POL-xxx).\n"
    "3. If no excerpt answers the question, reply exactly NO_ANSWER.\n"
)


def cohen_kappa(a: list[bool], b: list[bool]) -> float:
    n = len(a)
    agree = sum(x == y for x, y in zip(a, b, strict=True)) / n
    pa, pb = sum(a) / n, sum(b) / n
    expected = pa * pb + (1 - pa) * (1 - pb)
    return 1.0 if expected == 1.0 else (agree - expected) / (1 - expected)


def judge_part(
    client: OllamaClient, index: BM25Index, cases: list[Case], policy_text: dict[str, str]
) -> dict[str, Any]:
    reference: list[bool] = []
    judged: list[bool] = []
    rows = []
    for case in cases:
        hits = index.search(case.question, k=5)
        answer = compose_answer(case.question, hits)
        if not answer.answered:
            continue
        cited = answer.citations[0].policy_id
        prompt = (
            f"Question: {case.question}\n"
            f"Answer: {answer.text}\n"
            f"Cited policy {cited}:\n{policy_text[cited]}"
        )
        verdict = client.chat(JUDGE_SYSTEM, prompt).text.upper()
        says_ok = verdict.startswith("SUPPORTED")
        is_ok = cited == case.expected_policy
        reference.append(is_ok)
        judged.append(says_ok)
        rows.append(
            {"id": case.id, "cited": cited, "expected": case.expected_policy, "judge": verdict[:30]}
        )
    agree = sum(r == j for r, j in zip(reference, judged, strict=True)) / len(reference)
    return {
        "n_judged": len(reference),
        "agreement_with_programmatic_label": round(agree, 3),
        "agreement_ci95": [
            round(v, 3)
            for v in wilson_interval(
                sum(r == j for r, j in zip(reference, judged, strict=True)), len(reference)
            )
        ],
        "cohen_kappa_vs_programmatic_label": round(cohen_kappa(reference, judged), 3),
        "judge_says_supported": sum(judged),
        "reference_correct": sum(reference),
        "rows": rows,
    }


def generation_part(
    client: OllamaClient, index: BM25Index, cases: list[Case], policy_text: dict[str, str]
) -> dict[str, Any]:
    answered = correct = unsupported_sentences = total_sentences = 0
    refused_oos = oos_total = oos_answered = 0
    rows = []
    for case in cases:
        hits = index.search(case.question, k=K)
        excerpts = "\n\n".join(f"[{h.chunk.policy_id}] {h.chunk.text}" for h in hits)
        out = client.chat(GEN_SYSTEM, f"Excerpts:\n{excerpts}\n\nQuestion: {case.question}").text
        if case.expected_policy is None:
            oos_total += 1
            if "NO_ANSWER" in out.upper():
                refused_oos += 1
            else:
                oos_answered += 1
            continue
        match = re.search(r"POL-\d{3}", out)
        cited = match.group(0) if match else None
        body = re.sub(r"\(source:[^)]*\)", "", out).strip()
        if "NO_ANSWER" in out.upper() or cited is None:
            rows.append({"id": case.id, "cited": cited, "refused": True})
            continue
        answered += 1
        if cited == case.expected_policy:
            correct += 1
        source = policy_text.get(cited, "")
        for sentence in split_sentences(body):
            total_sentences += 1
            if not is_supported(sentence, source):
                unsupported_sentences += 1
        rows.append(
            {"id": case.id, "cited": cited, "expected": case.expected_policy, "answer": body[:300]}
        )
    n_in = sum(1 for c in cases if c.expected_policy is not None)
    return {
        "in_scope_n": n_in,
        "answered": answered,
        "citation_correct": correct,
        "citation_correct_rate": round(correct / n_in, 3) if n_in else None,
        "unsupported_sentence_rate": round(unsupported_sentences / total_sentences, 3)
        if total_sentences
        else None,
        "out_of_scope_n": oos_total,
        "out_of_scope_refused": refused_oos,
        "out_of_scope_answered": oos_answered,
        "rows": rows,
    }


def main() -> None:
    client = OllamaClient()
    chunks = load_chunks(POLICY_PATH, window=2, overlap=1)
    index = BM25Index(chunks)
    policy_text: dict[str, str] = {}
    for c in chunks:
        policy_text[c.policy_id] = policy_text.get(c.policy_id, "") + " " + c.text
    cases = load_golden(GOLDEN_PATH)
    in_scope = [c for c in cases if c.expected_policy is not None]

    result: dict[str, Any] = {
        "model": client.model,
        "judge": judge_part(client, index, in_scope, policy_text),
        "generation": generation_part(client, index, cases, policy_text),
        "caveat": (
            "Judge reference label is programmatic (cited == expected), not human. "
            "Generated answers use the same citation check as the extractive path."
        ),
    }
    RESULTS.parent.mkdir(parents=True, exist_ok=True)
    RESULTS.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    summary = {
        "judge_agreement": result["judge"]["agreement_with_programmatic_label"],
        "judge_kappa": result["judge"]["cohen_kappa_vs_programmatic_label"],
        "generation_citation_correct_rate": result["generation"]["citation_correct_rate"],
        "generation_unsupported_sentence_rate": result["generation"]["unsupported_sentence_rate"],
        "generation_oos_answered": result["generation"]["out_of_scope_answered"],
    }
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
