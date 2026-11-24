# E004 preregistration — fixed synonym lexicon

**Status:** PREREGISTERED 2026-11-24, provisional control
**Control:** `frozen_control.yaml` at run time (after the E003 decision)
**Gates:** `e004-gates.yaml`
**Config:** `experiments/configs/010_e004_synonyms.yaml`

## Motivation

The E003 audit found that all 28 zero-NDCG queries, and 80 of the 83 queries below 0.5, use a paraphrased topic word. Paraphrased queries average NDCG@10 0.2424, against 0.9313 for canonical ones.

## Treatment

`packages/search/query/synonym_expansion.py`: a frozen 10-pair lexicon applied as a query rewrite before the frozen control.

- **Bidirectional:** paraphrase → canonical and canonical → paraphrase.
- **Longest match first**, matching whole phrases (hyphens count as part of a word).
- **Append mode:** the original query is kept and the counterpart terms are added once each.
- **Queries with no match** go to the control unchanged.

| Paraphrase | Canonical |
| --- | --- |
| service disruption | incident |
| response time | latency |
| rollout | deployment |
| sign-in security | authentication |
| quality measurement | evaluation |
| spend plan | budget |
| result ordering | ranking |
| move-over | migration |
| architecture | design |
| data protection | privacy |

## Hypotheses and gates

| Gate | Hypothesis | Cohort | Requirement |
| --- | --- | --- | --- |
| **S-A** | H1 paraphrase ranking improves | paraphrase (96) | ΔNDCG@10 > 0 |
| **S-B** | H2 paraphrase recall improves | paraphrase (96) | ΔRecall@50 > 0 |
| **S-C** | H2 recall-limited paraphrase recall improves | recall-limited paraphrase (60) | ΔRecall@50 > 0 |
| S-D | H3 canonical ranking not harmed | canonical (54) | ΔNDCG@10 ≥ −0.01 |
| S-E | H3 canonical recall not harmed | canonical (54) | ΔRecall@50 ≥ −0.01 |
| S-F | H4 unexpanded queries identical | queries with no lexicon match | Identical top 50 |
| S-G | E002b wins retained | query-0056, query-0186 | Each ≥ control − 0.01 |
| S-H | Temporal behaviour not harmed | temporal_all (50) | ΔNDCG@10 ≥ −0.01 |
| S-I | Field behaviour not harmed | field_only (75) | ΔNDCG@10 ≥ −0.01 |

## Exploratory, not gated

- Forward-only expansion: `exploratory_forward_only`.
- Replace instead of append: `exploratory_replace`.

## Expectation

S-D carries the main risk. Adding a paraphrase to an already-perfect canonical query could dilute it.
