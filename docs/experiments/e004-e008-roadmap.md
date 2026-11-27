# E004–E009 roadmap

E004-E008 were preregistered on 2026-11-24 with a provisional control.
E009 and the U1-U3 amendment were preregistered on 2026-11-27.
For execution order, follow the
[E001-E009 step-by-step guide](step-by-step-e001-e008.md).

| ID | Experiment | Mechanism | Target cohort (v1 unless stated) | Primary improvement gate |
| --- | --- | --- | --- | --- |
| E004 | Fixed synonym lexicon | Query rewrite: append counterpart terms from a frozen 10-pair lexicon | 96 paraphrase queries | Paraphrase ΔNDCG@10 > 0 and ΔRecall@50 > 0 |
| E005 | Benchmark extension + structure | New v2 queries (recipient, subject, date range) with silver qrels; recipient/subject routing; date-range filter | v2 scenarios | Per-scenario ΔNDCG@10 > 0 |
| E006 | Dense retrieval alone | CPU-only sentence embedding, exact cosine | Paraphrase and recall-limited | Paraphrase ΔNDCG@10 > 0, recall-limited ΔRecall@50 > 0 |
| E007 | Hybrid | Reciprocal-rank fusion of the frozen control and dense (k = 60, depth 100) | All 200 | All ΔNDCG@10 > 0 vs control **and** vs dense alone |
| E008 | Re-ranking | Cross-encoder re-scores the frozen control's top 50 | All 200 | All ΔNDCG@10 > 0; Recall@50 unchanged by construction |
| E009 | Grounded answers + layered judges | Extractive answer from the top 5; 7 judges in 3 layers (safety stops first) | v3: clean, planted-failure and real answers | Planted safety failures caught ≥ 90%, ≤ 5% false safety alarms; see `e009/e009-preregistration.md` |


Automatic query expansion (pseudo-relevance feedback) was considered and dropped by decision on 2026-11-24.

**Benchmark v3** (`benchmark-v3/benchmark-v3-plan.md`) is the main benchmark from E009 on. It is cleaned (155 unique gold queries) and extended with human-checked silver scenarios: recipient, subject, date range, attachment files, newest and oldest. E003–E008 stay on v1.

## Rules that apply to every experiment

1. **The control is whatever is frozen at run time.** `experiments/frozen/frozen_control.yaml` is the single source of truth. Every run file records it. It is updated only after an experiment's decision is written, and each change is appended to its history.
2. **Hypotheses, cohorts, gates and parameters are fixed now.** They live in `docs/experiments/e00N/e00N-gates.yaml` and the configs. Only the control slot is filled in later.
3. **Each experiment runs after its predecessor's decision.** E004 runs after the E003 decision, E005 after E004, and so on. Running two experiments against the same stale control and then stacking them is not allowed.
4. **Same guardrail tolerance, de-duplication, fragility rule and bootstrap as E003** (ε = 0.01; 10,000 resamples; seed 20261124). An improvement gate needs a delta greater than 1e-9, so floating-point noise doesn't count.
5. **Decision rules** (from `verdict` in `prereg_gates.py`):

| Verdict | Meaning | Action |
| --- | --- | --- |
| ADOPT_CANDIDATE | All gates pass, no fragile improvement | Append the stage to `frozen_control.yaml` |
| NOT_ADOPTED_FRAGILE | Improvement holds only with duplicate queries counted each time | Don't adopt |
| NOT_ADOPTED_GUARDRAIL_FAILURE | A protection gate failed | Don't adopt; analyse the regressions first |
| NULL_RESULT | Nothing broke, target didn't improve | Record it; don't adopt |
| NOT_EVALUABLE | The cohort is too small or missing, or every improvement gate was blocked | Record it; extend or validate the benchmark |
| HOLD_COST | Quality passes, latency or cost-benefit fails (U2) | Don't adopt; plan a cheaper variant under a new ID |
| HOLD_COST_UNVERIFIED | Quality passes, timing missing or from different machines (U2) | Re-time both arms on one machine |

Informational gates are reported but never affect a verdict.

6. Re-running with changed parameters requires a new ID (for example, E004b).

## Amendment U1–U3 (2026-11-27, before any run)

See `u1-u3-amendment-preregistration.md`. It adds paraphrase-robustness gates on a new twin benchmark (`pt`), latency and cost-benefit gates, and a human check of E005's silver labels. No existing gate was changed.

## Known limitations, stated up front

- **E004 is an oracle-lexicon upper bound.** The 10 pairs came from the benchmark's own vocabulary in the E003 audit. A positive E004 result shows that vocabulary bridging works on this benchmark. It does not show that a general synonym resource would. E006 and E007 are the general test.
- **E005 qrels are silver.** They are derived from metadata: recipient list membership, subject match, and date range plus topic word. They test whether retrieval honours structure, not human relevance.
- **E006–E008 need `sentence-transformers` installed.** The preregistered models are `sentence-transformers/all-MiniLM-L6-v2` (dense) and `cross-encoder/ms-marco-MiniLM-L-6-v2` (re-ranker), both run on CPU. They were tested here only with deterministic stand-ins.
