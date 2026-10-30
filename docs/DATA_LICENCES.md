# Data and model licences

Every dataset and model is recorded here **before** it is used. Verify each licence at the source and record the date checked.

| Asset | Used for | Source | Licence (as found) | Checked on | Notes |
|---|---|---|---|---|---|
| Banking77 (original) | Intent classification | `PolyAI/banking77` on Hugging Face | CC BY 4.0 (licence tag on the Hub) | 2026-10-29 (Hub API) | The original repo ships only a loading script, which the `datasets` library no longer runs |
| Banking77 (mirror, used) | Intent classification (Week 2 to 3) | `legacy-datasets/banking77` (Parquet) | CC BY 4.0 (licence tag on the Hub) | 2026-10-29 (Hub API) | Used because it loads without a script. Split sizes checked: 9,002 train, 1,001 validation (from official train), 3,080 test, 77 labels |
| CFPB Consumer Complaint Database | Complaint text and routing (planned) | US CFPB | To verify (US federal government data) | Not checked | **Not used.** The download returns 403 from this machine; no data loaded |
| Synthetic generator | Customers, accounts, transactions, tickets | Written in this repo | Repo licence (TBD) | n/a | Seeded and reproducible |
| Synthetic policy documents (English) | RAG | Written in this repo | Repo licence (TBD) | n/a | Fictional bank policies |
| Synthetic policy documents (Arabic, five) | RAG (Week 10) | Translated in this repo by the project | Repo licence (TBD) | n/a | **Machine-written translations, not reviewed by a native speaker** |
| Synthetic golden sets (retrieval, scenarios, Arabic, red team) | Evaluation | Written in this repo | Repo licence (TBD) | n/a | Small, hand-written; some written after seeing failures |

## Models
| Model | Use | Licence | Checked on |
|---|---|---|---|
| distilbert-base-uncased | Intent model (fine-tuned) | Apache 2.0 (Hub tag) | 2026-10-29 (Hub API) |
| sentence-transformers/all-MiniLM-L6-v2 | Dense retrieval | Apache 2.0 (Hub tag) | 2026-10-29 (Hub API) |
| cross-encoder/ms-marco-MiniLM-L-6-v2 | Reranker (not enabled by default) | Apache 2.0 (Hub tag) | 2026-10-29 (Hub API) |
| Small open LLM for LoRA (Week 8) | Not done | n/a | n/a |

## Rules
- No asset is used before its row is completed.
- **Breach, recorded 2026-10-29:** Banking77 and the three models were used before their licences were checked. The licences are now checked from the Hub's licence tags (not the full licence text), so the breach is closed for those entries. Full licence text still needs reading before publication of weights.
- The CFPB dataset is still not checked (download blocked).
- If a licence forbids publication of derived weights, the model is not published and the README says so.
