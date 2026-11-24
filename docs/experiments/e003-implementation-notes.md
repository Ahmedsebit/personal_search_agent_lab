# E003 implementation notes

**Date:** 2026-11-24. **Written after preregistration and before any treatment run.** These notes record how the frozen specification is implemented. They change no preregistered parameter.

## Specification → code

| Preregistered item | Implementation |
| --- | --- |
| BM25F with frozen k1, b and IDF | `FieldAwareBM25`. k1 and b are read from the frozen retriever when it exposes them; the source is recorded in every run file. IDF defaults to `ln(1 + (N − df + 0.5)/(df + 0.5))` and can be swapped for E001's function. |
| Field weights 3/2/2/1/1 | `DEFAULT_FIELD_WEIGHTS` in `field_cues.py` and the config `params.field_weights` |
| Sender cue → E002b identity span on sender only | Terms after `from` in the **E002b-normalized** query, so alias expansions and E002b suppression are inherited, are scored on `sender` only with weight 3.0 |
| Attachment cue | Topic terms after `attachment(s) about` use attachment 4 / subject 2 / body 1 |
| Structural tokens excluded when a cue fires | `STRUCTURAL_TOKENS` |
| Temporal lexicon, stripping | `temporal_intent.py`. `most recent` is matched before `recent`. |
| Re-rank formula, λ = 0.30, ties | `temporal_rerank.py` |
| Non-temporal queries bypass E003-T | `E003Retriever.search` returns the control result unchanged. Gate T-A verifies this on all 150 queries. |
| E003-FT order | F scoring on the stripped query, then the T re-rank |
| Gates, de-duplication, bootstrap (10,000 resamples, seed 20261124), fragility, decision rules | `e003_comparison.py` |

## Properties to keep in mind when reading results

1. **Min–max normalization on small candidate sets.** With very few candidates, lexical scores are stretched to 0 and 1. With two candidates, the top lexical item always wins at λ = 0.30. This is the preregistered behavior. It matters only when a query returns very few matches.
2. **E003-F does not strip `latest`.** In the F arm, temporal words remain ordinary query terms, as preregistered. Only T and FT strip them.
3. **The field arms build a separate index.** E003-F does not modify the frozen BM25 index. It builds a parallel field index from the same emails, so the control is untouched.
4. **Metric gain mode.** The control run tries linear gain first, then `2^grade − 1`, and keeps whichever reproduces the frozen E002b values exactly. All arms then reuse that mode.

## Verification done before handover

- 37 unit and integration tests pass. They cover:
  - an exact BM25 reduction for a single field;
  - Gate T-0 checked against the real 200 annotated queries;
  - routing, including the Fatima Ali and E002b-expansion cases;
  - re-rank determinism;
  - the gate logic, including fragile, guardrail-failure and decision paths.
- An end-to-end smoke run worked on a **synthetic** corpus with a stand-in E002b retriever. All four arms ran, the comparison produced every gate, and Gate 0 ran. The smoke numbers are not evidence and are not reported.
