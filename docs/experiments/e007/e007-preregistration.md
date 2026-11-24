# E007 preregistration — hybrid lexical + dense

**Status:** PREREGISTERED 2026-11-24, provisional control
**Gates:** `e007-gates.yaml`
**Config:** `013_e007_hybrid.yaml`

## Treatment

Reciprocal-rank fusion of the frozen control (lexical, with every adopted stage) and the E006 dense retriever: `score = Σ 1/(60 + rank)`. Each list contributes its top 100, the weights are equal, and ties break by document ID. A `dense_only` arm is run in the same harness for gate H-D.

## Gates

| Gate | Hypothesis | Cohort | Requirement |
| --- | --- | --- | --- |
| **H-A** | Hybrid beats control | all (200) | ΔNDCG@10 > 0 |
| **H-B** | Hybrid improves paraphrase | paraphrase | ΔNDCG@10 > 0 |
| **H-C** | Hybrid recall above control | all | ΔRecall@50 > 0 |
| **H-D** | Hybrid beats dense alone | all | ΔNDCG@10 > 0 vs dense_only |
| H-E | Canonical not harmed | canonical | ΔNDCG@10 ≥ −0.01 |
| H-F | People not harmed | person + person_topic | ΔNDCG@10 ≥ −0.01 |
| H-G | Temporal not harmed | temporal_all | ΔNDCG@10 ≥ −0.01 |
| H-H | E002b wins retained | 2 diagnostics | Each ≥ control − 0.01 |
| H-V2 | v2 structure not harmed (if v2 is frozen) | v2 all | ΔNDCG@10 ≥ −0.01 |

## Risk to watch

Fusing ranks can wash out an E003-T recency order or an E005 range filter, because dense retrieval ignores time. H-G and H-V2 exist for this reason.

## Exploratory, not gated

`exploratory_k20`: RRF with k = 20.
