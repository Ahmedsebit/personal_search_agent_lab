# E008 preregistration — cross-encoder re-ranking

**Status:** PREREGISTERED 2026-11-24, provisional control
**Gates:** `e008-gates.yaml`
**Config:** `014_e008_rerank.yaml`

## Treatment

- **Model:** `cross-encoder/ms-marco-MiniLM-L-6-v2` on CPU, maximum length 512, batch size 32.
- **Scope:** re-scores the frozen control's top 50 using the same document text as E006.
- **Ties:** keep the control's order.
- **Items below 50:** keep their order.

Because the top 50 is only re-ordered, Recall@50 is identical by construction. Gate K-B checks this as a harness invariant.

## Gates

| Gate | Hypothesis | Cohort | Requirement |
| --- | --- | --- | --- |
| **K-A** | Re-ranking improves ranking | all (200) | ΔNDCG@10 > 0 |
| K-B | Recall@50 unchanged | all | ΔRecall@50 = 0 |
| K-C | People not harmed | person + person_topic | ΔNDCG@10 ≥ −0.01 |
| K-D | Recency order not undone | temporal_all | ΔNDCG@10 ≥ −0.01 |
| K-E | Mixed field+time not harmed | field_and_temporal | ΔNDCG@10 ≥ −0.01 |
| K-F | E002b wins retained | 2 diagnostics | Each ≥ control − 0.01 |
| K-V2 | v2 structure not harmed (if v2 is frozen) | v2 all | ΔNDCG@10 ≥ −0.01 |

## Reported, not gated

Latency p50 and p95 per query on CPU, compared with the control. The re-ranker adds the most cost of any stage in the roadmap.

## Main risk

The cross-encoder has no notion of time or sender. K-D and K-C protect the E003 gains.
