# Amendment U1–U3 to the E004–E008 preregistrations

**Status:** PREREGISTERED 2026-11-27, before any E004–E008 run.
**Applies to:** E004, E005, E006, E007, E008 (E003 is unchanged).
**Why it is allowed now:** no E004–E008 run file exists yet. The original hypotheses, cohorts and gates are unchanged; this amendment only **adds** gates, one benchmark and one precondition. After the first run of an experiment, changing any of this needs a new experiment ID.

| Upgrade | Problem it addresses | What changes |
| --- | --- | --- |
| **U1 Paraphrase robustness** | Reworded topics average NDCG@10 0.24 against 0.93 for canonical wording; all 28 zero-score queries are reworded. Averages hide whether a system is *consistent*. | New paraphrase-twin benchmark `pt`; family-level gates in E006–E008; informational in E004. |
| **U2 Latency and cost** | Quality-only gates would adopt a much slower stage for a tiny gain. | Every run is timed on CPU; latency and gain-per-latency gates; new verdicts `HOLD_COST` and `HOLD_COST_UNVERIFIED`. |
| **U3 Silver-label check** | E005's v2 relevance labels are generated from metadata and have never been checked by a person. | Blind human labelling of a sample; agreement thresholds; v2 gates for an unvalidated scenario become NOT EVALUABLE. Optional LLM judge measured against the same human labels. |

## U1 — Paraphrase robustness

### Benchmark `pt` (paraphrase twins)

Built by `scripts/build_paraphrase_twins.py` from the frozen v1 queries and gold qrels.

- Every unique v1 query containing a term from the frozen E004 lexicon (either side) becomes a **family** of two queries: the canonical wording and the reworded wording. Only that term changes.
- Both variants inherit the **source query's gold qrels**. A score difference within a family is therefore caused by wording alone.
- On the frozen v1 file this gives **117 families** (43 from canonical originals, 74 from reworded originals). Freeze the printed SHA-256 into `shared_data.yaml → benchmarks.pt.annotations_sha256`.
- **Stated assumption:** swapping a lexicon pair does not change the information need.
- **Stated limitation:** the lexicon is benchmark-derived. E004 closes the gap by construction on `pt`, so E004's `pt` gates are informational only.

### Family statistics (`packages/eval/robustness.py`)

| Statistic | Definition | Better |
| --- | --- | --- |
| `abs_gap` | \|NDCG@10(canonical) − NDCG@10(paraphrase)\| | lower |
| `worst` | min NDCG@10 over the two variants | higher |
| `para` | NDCG@10 of the reworded variant | higher |
| `overlap` | Jaccard overlap of the two top-10 sets | higher |

Gate kinds `family_gt0` (improvement) and `family_guard` (≥ −ε) test the mean family delta, oriented so positive = better, with a 10,000-resample bootstrap CI over families. Minimum 30 families.

**Why two gates, not one:** a narrower gap can come from the canonical wording getting *worse* ("levelling down"). Requiring `worst` to improve as well blocks that.

### Gates added

| Exp | Gate | Requirement | Role |
| --- | --- | --- | --- |
| E004 | P-1, P-2 | `abs_gap`, `worst` improve | informational (oracle lexicon) |
| E006 | P-A, P-B | `abs_gap` and `worst` improve | improvement gates |
| E006 | P-C | `overlap` improves | informational |
| E007 | P-A, P-B | `abs_gap` and `worst` improve | improvement gates |
| E007 | P-C | `overlap` not worse by > ε | guardrail |
| E008 | P-A | `worst` not worse by > ε | guardrail |
| E008 | P-B | `abs_gap` improves | informational (exploratory) |

## U2 — Latency and cost

### Measurement (`scripts/run_pipeline.py`)

- CPU only: `CUDA_VISIBLE_DEVICES=""` is set unless you set it yourself, and it is recorded.
- Warm-up: the first 5 queries run untimed (loads models, fills caches). Build + warm-up time is recorded separately.
- Each query is run 3 times; the **median** is its latency.
- A machine fingerprint (OS, CPU, core count, Python, hashed host name) is stored. **Latency gates are NOT EVALUABLE if control and treatment were timed on different machines.** Run both arms back to back on the same idle machine.

### Gates added (cohort: all v1 queries)

| Exp | C-1 latency budget (p95) | C-2 gain per +100 ms of median latency |
| --- | --- | --- |
| E004 | added ≤ 20 ms | — |
| E005 | added ≤ 20 ms | — |
| E006 | ≤ 150 ms | ≥ 0.01 NDCG@10 |
| E007 | ≤ 200 ms | ≥ 0.01 NDCG@10 |
| E008 | ≤ 600 ms | ≥ 0.01 NDCG@10 |

C-2 is automatically passed when the treatment is not slower (≤ 1 ms added at the median).

The budgets describe an interactive search on a laptop CPU. They are fixed now, before any timing is seen.

### Verdicts

Cost gates never decide adoption on quality. They can only hold back a stage that passed every quality gate:

| Verdict | Meaning | Action |
| --- | --- | --- |
| `HOLD_COST` | Quality gates pass; a latency or cost-benefit gate fails | Don't adopt. Record a targeted follow-up (e.g. smaller model, shallower depth) as a new ID |
| `HOLD_COST_UNVERIFIED` | Quality gates pass; timing missing or from different machines | Re-time both arms on one machine; don't adopt until then |

## U3 — Silver-label check for E005

### Procedure

1. `scripts/make_label_sheet.py` samples 8 v2 queries per scenario (seed 20261124). For each, it pools the top 5 of the control and treatment runs, up to 3 silver-relevant emails the runs missed, and 3 random non-relevant emails. **The sheet never shows the silver grade**; that goes in a separate key file.
2. You fill `human_grade` with 0 (not relevant), 1 (partly) or 2 (clearly relevant). Don't open the key file while labelling.
3. *(Optional)* `scripts/llm_label.py` grades the same pairs with an LLM judge. Each email is analysed once and the analysis is reused for every judgment, and token use is measured against the no-sharing baseline. **Synthetic lab data only.**
4. `scripts/label_agreement.py` writes `label_audit.json` and `label_audit.md`.

### Thresholds (per scenario)

| ID | Requirement |
| --- | --- |
| LA-1 | ≥ 30 labelled pairs, else NOT EVALUABLE |
| LA-3 | Cohen's κ (relevant vs not) between silver and human ≥ 0.60 |
| LA-4 | Silver precision ≥ 0.80 (of the pairs silver calls relevant, a person agrees on at least 80%) |
| LA-2 | Overall κ — reported only |
| LJ-1 | LLM vs human κ ≥ 0.70 — informational: decides whether an LLM judge may label future benchmarks |

A scenario is **VALIDATED** only if LA-1, LA-3 and LA-4 all pass. Each scenario is judged on its own, so a bad scenario does not block a good one.

### Effect on E005

`e005-gates.yaml → evaluations.v2.label_audit` points at `label_audit.json`. When evaluating:

- If the file is missing, or was made for a different `queries_v2.csv` (hash check), **every v2 gate is NOT EVALUABLE**.
- Otherwise, gates whose scenario is not VALIDATED are NOT EVALUABLE. A component whose gates are all NOT EVALUABLE gets the verdict NOT_EVALUABLE.

**Known limitation:** one labeller. If a second person can label 20% of the sheet, report their κ with the first labeller next to the results.

## Engine change that applies to all experiments

If **every improvement gate** in a verdict is NOT EVALUABLE, the verdict is now `NOT_EVALUABLE`. Before, the remaining guardrail gates alone could yield ADOPT_CANDIDATE. The U3 end-to-end test exposed this.

## Decision on the U2 limits (2026-11-27)

Ahmed asked for a best-judgement call. **The limits are kept unchanged and are now frozen.** Reasoning:

- **E006 (150 ms) and E007 (200 ms):** encoding one query with a small sentence model on CPU, plus an exact search over a few thousand emails, normally takes well under 50 ms. The limit leaves room for a slower laptop without letting a pathological setup pass.
- **E008 (600 ms):** this is the limit most likely to bind. Scoring 50 email–query pairs at up to 512 tokens on CPU can approach it. That is deliberate. If E008 improves quality but misses the limit, the verdict is HOLD_COST, and the follow-up is a cheaper variant under a new ID (e.g. E008b: re-rank the top 20, or cut emails to 256 tokens). The limit is not loosened after the fact.
- **E004/E005 (+20 ms):** query rewriting and a date filter should add almost nothing. 20 ms catches an accidental slow path, such as re-scanning the whole corpus per query.
- **Gain per +100 ms ≥ 0.01 NDCG@10:** e.g. E008 adding 300 ms must gain at least 0.03 NDCG@10 overall.

All limits are per query for the full pipeline, measured after warm-up, so one-time model loading is excluded (and reported separately).
