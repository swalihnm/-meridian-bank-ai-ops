# 0007: One policy index for English and Arabic

**Status:** Accepted, 2026-10-29 (EXP-003).

## Context
The English-only index answers Arabic questions poorly (recall 0.40, citation 0.00 on the Arabic set). Arabic tickets were all sent to humans.

## Decision
A single BM25 index holds the English and Arabic policy chunks. The tokenizer uses Unicode word characters, and Arabic function words are in the stopword list.

## Consequences
- Arabic answers are possible, but the Arabic policies cover only five of the thirty, and the translations are not native-speaker reviewed.
- English retrieval was checked on the full 60-question set and did not regress.
- Lexical only: Arabic inflection (no stemming) limits recall.
