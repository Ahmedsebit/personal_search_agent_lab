# E003 preregistration — field-aware and temporal lexical retrieval

**Status:** PREREGISTERED. Frozen before any E003 treatment run.
**Date:** 2026-11-24
**Arms:** E003-F, E003-T, E003-FT
**Control:** frozen E002b
**Benchmark:** frozen 200-query benchmark, unchanged
**Cohort file:** `e003-query-annotations.csv`, SHA-256 `ca0acd5db4dbed7a232f88ed664bce4cb9a5e5e6fb9cc7f26e3e29f5daff6d49`
**Parameter file:** `e003-preregistered-parameters.yaml`
**Evidence base:** `e003-benchmark-coverage-audit.md`

## 0. Freeze rules

1. The hypotheses, cohorts, parameters, gates and decision rules in this document and its parameter file are fixed. They must not change after any treatment output is seen.
2. Parameters are set from principle, not tuning. No E003 arm is run on the benchmark more than once for gate evaluation.
3. Any change after a run is a new experiment ID (for example, E003-F2), with its own preregistration. Re-running a frozen arm with altered parameters and reporting it under the same ID is not allowed.
4. Frozen components that E003 must not modify: E001 BM25 core (k1, b, tokenizer, stopwords), E002 normalizer, E002b context-aware alias logic, the benchmark queries, the qrels and the metric implementations.
5. **Gate 0** (corpus audit) must run and pass for an arm's scope before that arm's treatment run.

## 1. Experimental design

| Arm | Field-aware scoring | Temporal handling | Compared with |
| --- | --- | --- | --- |
| Control | No | No | — (frozen E002b) |
| **E003-F** | Yes | No | Control |
| **E003-T** | No | Yes | Control |
| **E003-FT** | Yes | Yes | Control, E003-F and E003-T |

All arms share E002b query normalization. The pipeline order is fixed:

```text
query
  → E002b normalization (frozen)
  → [T] temporal-intent detection and stripping
  → [F] cue routing + field-weighted lexical scoring   |  control lexical scoring
  → top-50 candidates
  → [T] recency re-rank (temporal queries only)
  → ranked list
```

## 2. Treatments (frozen specification)

### 2.1 E003-F — field-aware lexical retrieval

**F.a: field-weighted BM25 (BM25F style).** Each document is indexed as the fields `sender`, `recipients` (to + cc), `subject`, `body` and `attachment_names`. Per-field term frequency is length-normalized with the frozen E001 `b`, weighted and summed. A single saturation with the frozen E001 `k1` follows, using corpus-level IDF.

| Field | Weight | Rationale |
| --- | --- | --- |
| sender | 3.0 | Strongest structured signal; 75 queries carry a sender cue |
| subject | 2.0 | Short, high-precision summary field |
| attachment_names | 2.0 | Short, high-precision; target of attachment queries |
| recipients | 1.0 | Neutral; untestable on this benchmark (0 recipient queries) |
| body | 1.0 | Reference weight |

**F.b: deterministic cue routing.** Routing applies only when a cue is detected:

- `from <person span>`: the span is the E002b identity span after alias handling. Its terms are scored against `sender` only, with weight 3.0. Remaining query terms use the F.a weights.
- `attachment(s) about <topic>`: topic terms use `attachment_names` 4.0, `subject` 2.0, `body` 1.0, `sender` 0, `recipients` 0.
- The cue tokens `emails`, `messages`, `from`, `attachment`, `attachments` and `about` are structural when their cue fires. They are excluded from lexical scoring; if already stop-worded, nothing changes.
- With no cue, scoring is F.a only.

### 2.2 E003-T — temporal lexical retrieval

- **Detector:** a closed lexicon of `latest`, `newest`, `most recent` and `recent`, as whole tokens at any position. Only `latest` occurs in the benchmark; the others are included for robustness and are untested.
- **Out of scope:** range or relative expressions (`last week`, `yesterday`, `today`, dates). They are not detected and are left unchanged.
- **Stripping:** the matched temporal tokens are removed from the lexical query.
- **Candidates:** the top 50 from control lexical scoring on the stripped query.
- **Re-rank:** temporal queries only.
  - `lex_norm` = min–max normalized lexical score within the top 50.
  - `rec` = 1 − (time_rank − 1) ÷ (n − 1), where time_rank 1 is the newest candidate. It is rank-based, so there is no reference-time or decay parameter.
  - `score = (1 − λ) · lex_norm + λ · rec`, with **λ = 0.30**.
  - Ties break by lexical score, then document ID.
- **Non-temporal queries bypass E003-T entirely.**

### 2.3 E003-FT — combined

E003-F scoring produces the candidates, and the E003-T re-rank is then applied with the same λ. No parameter is re-set for the combination.

## 3. Cohorts (frozen from the annotation file)

| Cohort | Definition | Queries | Unique |
| --- | --- | --- | --- |
| field_only | Field cue, no temporal cue (person, person_topic, attachment) | 75 | 49 |
| temporal_only | Temporal cue, no field cue (recency) | 25 | 22 |
| field_and_temporal | Both cues (mixed) | 25 | 25 |
| neither | No cue (status, thread, topic) | 75 | 59 |
| attachment | `field_attachment_cue = 1` | 25 | 6 |
| person_all | person ∪ person_topic | 50 | 43 |
| temporal_all | `temporal_explicit = 1` | 50 | 47 |
| non_temporal | `temporal_explicit = 0` | 150 | 108 |
| **sub_f_ordering** | field_only ∩ ordering class | 20 | — |
| **sub_t_ordering** | temporal ∩ ordering class | 13 | — |
| sub_paraphrase_recall_limited | paraphrase ∩ (recall_limited ∪ zero_recall) | 60 | — |
| e002b_diagnostic | query-0056 `emails from Fatima Ali`, query-0186 `rollout from Fatima Ali` | 2 | — |

## 4. Metrics and statistics

- **Primary metric:** NDCG@10. **Secondary metrics:** Recall@50, MRR, Precision@10, Recall@10, DCG@10. All use the frozen metric code.
- **Delta:** treatment − control, per query, then the cohort mean.
- **Primary weighting:** query-weighted, consistent with E002 and E002b.
- **Sensitivity weighting:** de-duplicated, with each unique query string weighted once.
- **Uncertainty:** paired bootstrap 95% CI on every cohort delta (10,000 resamples, seed 20261124), reported alongside the gates. The CI is descriptive and not itself a gate.
- **Counts:** improved, regressed and unchanged per cohort, with |Δ NDCG@10| > 1e-9 counting as changed.
- **Fragility flag:** a gate that passes query-weighted but whose de-duplicated delta fails the same threshold is reported as **PASS (fragile)**. A fragile pass counts as a pass for that gate, but an arm cannot be adopted if one of its improvement gates is fragile.
- **Guardrail tolerance:** ε = 0.01, the same as E002 and E002b.

## 5. Hypotheses and acceptance gates

### Gate 0 — validity preconditions (before any treatment run)

Run `scripts/audit_e003_corpus.py`. E003-F needs G0-2, G0-3, G0-5 and G0-6. E003-T needs G0-1, G0-4 and G0-6. E003-FT needs all of them. If an arm's Gate 0 fails, that arm is recorded as **NOT EVALUABLE on this benchmark**, not as failed, and is not run.

### E003-F (vs control)

| Hypothesis | Gate | Requirement |
| --- | --- | --- |
| H1-F field cues help | **F-A** | field_only mean ΔNDCG@10 **> 0** |
| | F-B | field_only ΔRecall@50 ≥ −0.01 |
| H2-F attachment holds or improves | F-C | attachment ΔNDCG@10 ≥ −0.01 **and** ΔRecall@50 ≥ −0.01 |
| H3-F person does not regress | F-D | person_all ΔNDCG@10 ≥ −0.01 **and** ΔRecall@50 ≥ −0.01 |
| H4-F no-cue queries are safe | F-E | neither ΔNDCG@10 ≥ −0.01 **and** ΔRecall@50 ≥ −0.01 |
| | F-F | temporal_only ΔNDCG@10 ≥ −0.01 |
| E002b wins retained | F-G | each e002b_diagnostic query has NDCG@10 ≥ control − 0.01 |

**Mechanism predictions (reported, not gated):**

- sub_f_ordering ΔNDCG@10 > 0.
- person scenario ΔRecall@50 ≈ 0, because 22 of 25 queries are at the Recall@50 cap.
- sub_paraphrase_recall_limited |ΔNDCG@10| small.

### E003-T (vs control)

| Hypothesis | Gate | Requirement |
| --- | --- | --- |
| Detector is exact | **T-0** | Fires on exactly the 50 annotated temporal queries; 0 false positives on the other 150 |
| H4-T non-temporal invariance | **T-A** | All 150 non-temporal queries return a top-50 list identical to control (same IDs, same order) |
| H1-T temporal ordering improves | **T-B** | temporal_only mean ΔNDCG@10 **> 0** |
| H2-T first result does not get worse | T-C | temporal_only ΔMRR ≥ −0.01 |
| H3-T candidates are stable | T-D | temporal_all ΔRecall@50 ≥ −0.01 |
| Mixed queries are safe | T-E | field_and_temporal ΔNDCG@10 ≥ −0.01 |

**Mechanism predictions (reported, not gated):**

- sub_t_ordering ΔNDCG@10 > 0.
- The 16 paraphrase recency queries change little, because they are recall-limited.

### E003-FT (vs control and vs single arms)

| Hypothesis | Gate | Requirement |
| --- | --- | --- |
| H1-FT combined system helps | **FT-A** | All 200 queries: mean ΔNDCG@10 vs control **> 0** |
| H2-FT no destructive interference | FT-B | field_only NDCG@10(FT) ≥ NDCG@10(F) − 0.01 **and** temporal_only NDCG@10(FT) ≥ NDCG@10(T) − 0.01 |
| H3-FT mixed queries hold | FT-C | field_and_temporal ΔNDCG@10 ≥ −0.01 **and** ΔRecall@50 ≥ −0.01 vs control |
| H4-FT guardrail | FT-D | neither ΔNDCG@10 ≥ −0.01 **and** ΔRecall@50 ≥ −0.01 vs control |
| E002b wins retained | FT-E | As F-G |

**Interaction (descriptive):** for each cohort, I = (FT − C) − [(F − C) + (T − C)] on NDCG@10, labelled as follows.

| I value | Label |
| --- | --- |
| I > +0.01 | Synergy |
| I < −0.01 | Interference |
| Otherwise | Additive |

## 6. Decision rules

| Outcome | Decision |
| --- | --- |
| F passes all gates, with F-A not fragile | Adopt F as a candidate component |
| T passes all gates, with T-B not fragile | Adopt T as a candidate component |
| FT passes all gates, and F and T both adopted | **FT becomes the new frozen control (E003 final)** |
| FT passes, but only one of F or T adopted | Freeze the adopted single arm as control; record FT as exploratory |
| An arm fails a guardrail gate | Do not adopt; do a failure analysis on the regressed queries before any follow-up ID |
| An arm fails only its improvement gate | Record as a null result; the audit predicted limited headroom |
| Gate 0 fails for an arm | Record as NOT EVALUABLE; propose a benchmark extension, not a tuning pass |

## 7. Preregistered expectations

These expectations come from the audit:

- Any overall NDCG@10 gain will be **modest**. The upper bound from the ordering-class queries is +0.1064, and realistic gains are well below it.
- The attachment result is dominated by 2 query strings. A large query-weighted attachment gain with a small de-duplicated gain is expected, and it will be labelled.
- The 60 paraphrase-limited queries will stay low across all arms. This is the target for **E004 (vocabulary mismatch)**.

## 8. Exploratory analyses (not gated, labelled exploratory)

1. **F.a-only ablation:** field weights without cue routing.
2. **λ sensitivity** for E003-T: 0.15, 0.30 and 0.50. Reported only; λ stays frozen at 0.30 for the gates.
3. **Per-entity breakdown** for Atlas/Atlassian, Falcon/Falcone and Orion/OrionX.
4. **Latency** p50 and p95 per arm.

## 9. Required outputs

- `e003-gate0-corpus-audit.json`
- `e003-f-vs-e002b-comparison.{json,md}`
- `e003-t-vs-e002b-comparison.{json,md}`
- `e003-ft-vs-e002b-comparison.{json,md}`
- `e003-ft-vs-f-and-t.{json,md}`, including the interaction table
- `e003-results.md`, with the gate table showing query-weighted value, de-duplicated value, CI and pass/fail per gate
