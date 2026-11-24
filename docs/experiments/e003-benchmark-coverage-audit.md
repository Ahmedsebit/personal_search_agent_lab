# E003 benchmark coverage audit — field and temporal

**Status:** Complete for the query side; corpus/qrels side pending Gate 0
**Date:** 2026-11-24
**Control for E003:** frozen E002b (context-aware alias normalization over frozen E001 BM25)
**Benchmark:** the frozen 200-query benchmark used for E001, E002 and E002b

## 1. Scope and sources

The audit asks one question: **can this benchmark actually measure a field-aware or temporal retrieval effect, and where?**

| Source | Used for |
| --- | --- |
| `e001-vs-e002-comparison.json` | Query text, scenario label, E002 per-query metrics |
| `e002b-vs-e002-comparison.json` | E002b per-query deltas, so control metrics = E002 + E002b delta |
| Rule-based query annotation (this audit) | Field cues, temporal cues, lexical form, headroom class |

**Not audited here:** the email corpus and qrels. These were not available on the audit side. The audit therefore cannot confirm field population, timestamp quality or whether the qrels reward recency. Those checks are preregistered as **Gate 0**, run on the repository side with `scripts/audit_e003_corpus.py`, before any E003 treatment run.

Every query-level number below is reproducible from `e003-query-annotations.csv`.

## 2. Control baseline (E002b), all 200 queries

| Metric | Mean |
| --- | --- |
| NDCG@10 | 0.6116 |
| Recall@50 | 0.7031 |

## 3. Field coverage

| Field cue | Queries | Pattern | Scenarios |
| --- | --- | --- | --- |
| Sender (`from <person>`) | **75** | `emails from X`, `<topic> from X`, `latest … from X` | person, person_topic, mixed |
| Attachment (`attachment about …`) | **25** | `attachment about <entity> <topic>` | attachment |
| Recipient (`to`, `cc`) | **0** | — | — |
| Subject (`subject`, `titled`) | **0** | — | — |

**Finding F1 — only two fields are testable.** The benchmark exercises sender and attachment-name matching. It has no recipient or subject-cue queries. E003-F may index recipients and subject, but **no claim about recipient or subject weighting can be supported by this benchmark.**

**Finding F2 — the attachment cohort is effectively six queries.** The 25 attachment queries contain only **6 unique strings**; `attachment about Cedar move-over` appears **14 times** and `attachment about Cedar migration` 7 times. Any attachment result is dominated by two query strings and must be reported de-duplicated as well.

**Finding F3 — person queries have almost no NDCG headroom, and their Recall@50 gap is mostly structural.** 22 of 25 person queries already have NDCG@10 = 1.0. Their mean Recall@50 is 0.7094, but the inferred relevant-set sizes are 50–83 documents per sender, so **22 of 25 are already at the maximum achievable Recall@50** (50 ÷ relevant count). Only the alias queries (`emails from OH` ×2, `emails from Ali`) sit below the cap, and those are E002/E002b territory. Field-aware sender matching cannot be expected to move the person scenario.

> Inference method: relevant count = (Precision@10 × 10) ÷ Recall@10. It assumes a binary relevance threshold for P@10 and R@10. Gate 0 confirms it against the qrels.

## 4. Temporal coverage

| Temporal property | Count |
| --- | --- |
| Queries with a temporal expression | **50** (25 recency + 25 mixed) |
| Operators present | **`latest` only** |
| `newest`, `recent`, `last week`, `yesterday`, `today` | 0 |
| Explicit dates or ranges | 0 |

**Finding T1 — temporal coverage is a single superlative operator.** E003-T can test "rank the newest relevant item first". It **cannot** test range filtering (`last week`), relative dates (`yesterday`) or absolute dates. Those are out of E003 scope and would need new queries and qrels (candidate: E003-T2).

**Finding T2 — mixed queries each have exactly one relevant document (inferred).** 21 of 25 already rank it first (NDCG@10 = 1.0). Only 4 have room to improve (target at rank 2 or 3). The mixed scenario is a clean but small temporal + field interaction test.

**Finding T3 — temporal headroom splits cleanly in two.**

| Recency sub-group | Queries | NDCG@10 | Recall@50 | MRR | What limits it |
| --- | --- | --- | --- | --- | --- |
| Canonical topic term | 9 | 0.5875 | 1.0 | 1.0 | **Ordering** — every relevant item is retrieved; the order is wrong |
| Paraphrased topic term | 16 | 0.0500 | 0.2304 | 0.3043 | **Recall** — most relevant items are never retrieved |

A recency re-rank can only help the first group. It cannot recover documents that lexical retrieval never returns.

## 5. The dominant failure is vocabulary mismatch, not field or time

Each query was tagged by its topic term: **canonical** (incident, latency, deployment, authentication, evaluation, budget, ranking, migration, design, privacy), **paraphrase** (service disruption, response time, rollout, sign-in security, quality measurement, spend plan, result ordering, move-over, architecture, data protection), or **none** (person and status queries).

| Lexical form | Queries | Unique | NDCG@10 | Recall@50 | MRR |
| --- | --- | --- | --- | --- | --- |
| canonical | 54 | 43 | 0.9313 | 0.8741 | 1.0000 |
| none | 50 | 38 | 0.9754 | 0.8509 | 1.0000 |
| **paraphrase** | **96** | 74 | **0.2424** | **0.5300** | **0.3948** |

- **All 28** queries with NDCG@10 = 0 use a paraphrased topic term.
- **80 of the 83** queries with NDCG@10 < 0.5 use a paraphrased topic term.
- In the topic scenario, the 9 canonical queries all score NDCG@10 = 1.0 and the 16 paraphrased ones all score 0.0.

**Finding V1 — most residual error lies outside E003's mechanism.** Field weighting and recency ordering re-score terms that already match. They do not bridge `rollout` → `deployment` or `spend plan` → `budget`. **E003 should be expected to produce a modest aggregate gain, and a null result on paraphrase-limited queries is the predicted outcome, not a failure.** This is the strongest evidence for an E004 on vocabulary mismatch (synonym or semantic expansion).

## 6. Headroom E003 can actually reach

Each query was classed by its control result:

| Class | Definition | Count |
| --- | --- | --- |
| ceiling | NDCG@10 = 1.0 | 104 |
| ordering | NDCG@10 < 1.0 and Recall@50 = 1.0 | 33 |
| recall_limited | NDCG@10 < 1.0 and 0 < Recall@50 < 1.0 | 47 |
| zero_recall | Recall@50 = 0 | 16 |

| E003 cohort | Queries | Unique | NDCG@10 | Recall@50 | Ceiling | Ordering | Recall-limited | Zero-recall |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| field_only (person, person_topic, attachment) | 75 | 49 | 0.6371 | 0.8403 | 40 | 20 | 15 | 0 |
| temporal_only (recency) | 25 | 22 | 0.2435 | 0.5075 | 0 | 9 | 16 | 0 |
| field_and_temporal (mixed) | 25 | 25 | 0.9305 | 1.0000 | 21 | 4 | 0 | 0 |
| neither (status, thread, topic) | 75 | 59 | 0.6026 | 0.5322 | 43 | 0 | 16 | 16 |

- **Total NDCG@10 headroom** over all 200 queries is 0.3884. The ordering-class queries hold 0.1064 of it, or **about 27%**.
- If E003 made every ordering-class query perfect, overall NDCG@10 would rise by at most **+0.1064**. Realistic gains will be well below this.
- The ordering class splits as follows: **20 field** queries (16 attachment, 4 person_topic) and **13 temporal** queries (9 recency, 4 mixed). These become the preregistered mechanism sub-cohorts.
- The `neither` cohort has **no ordering-class queries**. It is a pure guardrail.

## 7. Other confounds

| Confound | Evidence | Handling in preregistration |
| --- | --- | --- |
| Duplicate queries | 155 unique strings out of 200 | Every gate is reported query-weighted (primary) and de-duplicated (sensitivity) |
| Near-name entities | Atlas/Atlassian, Falcon/Falcone, Orion/OrionX occur across scenarios | Not targeted by E003; watched in the per-query regression list |
| Ceiling saturation | status 25/25 and mixed 21/25 at NDCG@10 = 1.0 | Treated as guardrails; improvement gates use only cohorts with headroom |
| E002b wins at risk | `emails from Fatima Ali` 1.0000, `rollout from Fatima Ali` 0.3622 | Explicit per-query retention gate |

## 8. Pending corpus-side checks (Gate 0)

`scripts/audit_e003_corpus.py` checks the following and writes `e003-gate0-corpus-audit.json`:

| Check | Threshold | Blocks |
| --- | --- | --- |
| G0-1 Every document has a parseable timestamp | 100% | E003-T, E003-FT |
| G0-2 Sender field populated | ≥ 99% | E003-F, E003-FT |
| G0-3 Relevant docs of attachment queries carry an attachment name | ≥ 90% | E003-F, E003-FT |
| G0-4 For temporal queries, the newest relevant doc holds the top relevance grade | ≥ 80% of multi-relevant temporal queries | E003-T, E003-FT |
| G0-5 Relevant docs of full-name sender queries have that sender | ≥ 90% | E003-F, E003-FT |
| G0-6 All 200 annotated queries have qrels | 100% | All |

G0-4 is the critical check. If the qrels do not reward recency, a recency re-rank cannot improve NDCG and E003-T is not a valid experiment on this benchmark.

## 9. Audit conclusions

1. E003 is **measurable** on this benchmark for **sender**, **attachment-name** and **`latest`** behaviour only.
2. The reachable signal is concentrated in **33 ordering-class queries**: 20 field and 13 temporal.
3. Person queries are near their maximum, the mixed queries have 4 open cases and the attachment cohort is effectively 6 queries. Effects will be **small and fragile**, so de-duplicated reporting is mandatory.
4. **Vocabulary mismatch drives most of the remaining error.** E003 cannot fix it, and E004 should target it.
