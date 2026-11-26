# E001-E008: step-by-step experiment guide

This is the main execution path for the research experiments. Follow it in order:
**E001 -> E002 -> E002b -> E003 -> E004 -> E005 -> E006 -> E007 -> E008**.
The linked learning notes explain the implementation; preregistrations define the
complete hypotheses, parameters, gates, and decision rules.

## Experiment map

| Step | Experiment | Change under study |
| --- | --- | --- |
| 1 | E001 | Frozen BM25 lexical baseline |
| 2 | E002 | Explicit query normalization |
| 3 | E002b | Context-aware alias eligibility |
| 4 | E003 | Field-aware scoring and temporal reranking, separately and combined |
| 5 | E004 | Fixed synonym expansion |
| 6 | E005 | Structured benchmark v2, recipient/subject routing, date ranges |
| 7 | E006 | Semantic dense retrieval alone |
| 8 | E007 | Hybrid lexical/dense reciprocal-rank fusion |
| 9 | E008 | Cross-encoder reranking |

**Do not confuse config numbers with experiment IDs.** The original Milestone 1
configs `002_dense.yaml`, `003_hybrid.yaml`, and `004_hybrid_reranker.yaml` are
dependency-light demos, not research E002, E003, and E004. Research E002 uses
config `005`, E002b uses `006`, and research E003-E008 use configs `000` and
`007`-`014` as shown below.

## Step 0 - Set up and freeze the dataset

Run all commands from the repository root. Commands use PowerShell and Windows
paths. Python 3.11 or newer is required.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
python -m pytest -q
```

If script activation is unavailable, use `.\.venv\Scripts\python.exe` in place of
`python` throughout, including the installation command.

For a fresh workspace, generate the deterministic baseline dataset once:

```powershell
python scripts\generate_dataset.py --emails 2000 --queries 200 --seed 42 --output datasets
```

If the frozen dataset is already present, reuse it. Keep the corpus, original
200 queries, qrels, tokenizer, BM25 parameters, and metric definitions unchanged
throughout the sequence. Do not regenerate or replace them between experiments.

Before each treatment, read its preregistration. After each comparison, record
the decision before moving to the next experiment. A null result is a valid
decision, not permission to tune parameters under the same experiment ID.

## Step 1 - E001: establish the BM25 baseline

```powershell
python scripts\run_experiment.py --config experiments\configs\001_bm25.yaml
python scripts\analyze_e001.py `
  --report experiments\results\e001-bm25-baseline.json `
  --dataset datasets `
  --output experiments\results\e001-bm25-analysis-v2.json
```

**Inspect:** `experiments\results\e001-bm25-baseline.json` and the JSON/Markdown
analysis. Review overall and scenario metrics, difficulty groups, worst queries,
Recall@50 versus NDCG@10, and the failure taxonomy.

**Checkpoint:** retain the per-query baseline and freeze E001. Later experiments
must not silently add normalization, fields, time, or semantics to its algorithm.

**Read:** [E001 plan](e001-bm25.md),
[running and analyzing E001](../learning/08-running-and-analyzing-e001.md),
and [BM25 implementation guide](../implementation/e001-bm25-code-guide.md).

## Step 2 - E002: normalize lexical surface forms

```powershell
python scripts\run_experiment.py --config experiments\configs\005_query_normalized_bm25.yaml
python scripts\compare_experiments.py `
  --control experiments\results\e001-bm25-baseline.json `
  --treatment experiments\results\e002-query-normalized-bm25.json `
  --output experiments\results\e001-vs-e002-comparison.json
```

**Inspect:** the comparison JSON and Markdown, including aliases, initials,
hyphenation, misspellings, untouched queries, and scenario regressions.

**Checkpoint:** targeted Recall@50 must improve; targeted NDCG@10 must not
decrease. Untouched-query NDCG@10 and Recall@50 deltas must each be at least
-0.01. Record the decision and preserve the E002 report for E002b.

**Read:** [E002 hypotheses and gates](e002-query-normalized-bm25.md),
[normalization guide](../learning/09-query-normalization-and-e002.md),
and [paired comparison guide](../learning/10-comparing-e001-e002.md).

## Step 3 - E002b: prevent harmful alias expansion

The implementation is already integrated; no package-copy or runner-registration
step is needed.

```powershell
python scripts\run_experiment.py --config experiments\configs\006_context_aware_query_normalized_bm25.yaml
python scripts\compare_e002b.py `
  --e002 experiments\results\e002-query-normalized-bm25.json `
  --e002b experiments\results\e002b-context-aware-bm25.json `
  --output experiments\results\e002b-vs-e002-comparison.json `
  --diagnostic-query-id query-0056 `
  --diagnostic-query-id query-0186
```

The diagnostic IDs refer to the frozen benchmark's two `Fatima Ali` queries.
Check normalized terms, cohorts, and suppressed aliases as well as rankings.

**Checkpoint:** all seven preregistered gates must pass: collision ranking
improves, collision recall does not regress, safe-alias and untouched cohorts
stay within tolerance, and both diagnostic queries improve in NDCG@10 without
losing Recall@50. Retain the report for the E003 control-parity check.

The repository's [frozen control](../../experiments/frozen/frozen_control.yaml)
already records E002b as adopted. Reproducing the early steps does not authorize
overwriting that history or the frozen annotation metrics.

**Read:** [E002b specification](e002b-context-aware-alias-normalization.md)
and [validation details](../learning/12-running-and-validating-e002b.md).

## Step 4 - E003: isolate field and temporal effects

Run Gate 0 before any treatment:

```powershell
python scripts\audit_e003_corpus.py `
  --emails datasets\synthetic\emails.jsonl `
  --qrels datasets\benchmarks\judgments.jsonl `
  --annotations docs\experiments\e003\e003-query-annotations.csv `
  --out runs\e003\gate0-corpus-audit.json

python scripts\run_e003.py --config experiments\configs\000_e003_control.yaml
```

**Stop unless control parity passes for all 200 queries.** Only run the arms
whose Gate 0 requirements pass: F needs G0-2/3/5/6, T needs G0-1/4/6, and FT
needs all six.

```powershell
# Run each eligible arm once; skip arms that Gate 0 cannot evaluate.
python scripts\run_e003.py --config experiments\configs\007_e003_f.yaml
python scripts\run_e003.py --config experiments\configs\008_e003_t.yaml
python scripts\run_e003.py --config experiments\configs\009_e003_ft.yaml
python scripts\compare_e003.py --runs runs\e003 --out docs\experiments\e003\results
```

**Inspect:** `docs\experiments\e003\results\e003-results.md`, the per-arm
comparisons, interaction analysis, guardrails, and de-duplicated sensitivity
checks. An improvement that passes only with duplicate queries counted
repeatedly is fragile and cannot justify adoption.

**Checkpoint:** record the decision. Set `current.e003_arm` in
`experiments\frozen\frozen_control.yaml` to the adopted arm (`e003_f`, `e003_t`,
or `e003_ft`), or retain `control` if none is adopted. Update the control ID to
identify the adopted configuration and append a dated history entry. If arms
were skipped, explicitly record their not-evaluable status; the comparison
script emits a combined decision only when all three treatment runs exist.

**Read:** [E003 preregistration](e003/e003-preregistration.md),
[integration reference](../../E003_INTEGRATION.md),
and [E003 learning notes](../learning/13-running-and-validating-e003.md).

## Shared procedure for E004-E008

Each experiment compares against the control frozen **after the previous
decision**, including only adopted stages. Do not run all experiments against a
stale control and stack the winners later.

Arm outputs go to `runs\e00N\v1\<arm>.json` (or `v2`). Gate evaluation writes
`docs\experiments\e00N\results\e00N-results.json` and `.md`.

Record each verdict and its evidence before editing the frozen control. Adopt
only candidates allowed by the preregistered decision rules, copy the exact
stage spec from the experiment config, update the control ID, and append a
dated history entry. Do not adopt fragile, failed, null, or not-evaluable
results. Keep paired runs from the same frozen control together; preserve
earlier evidence before reusing output paths.

## Step 5 - E004: test fixed synonym expansion

```powershell
python scripts\run_pipeline.py --config experiments\configs\010_e004_synonyms.yaml --arm control
python scripts\run_pipeline.py --config experiments\configs\010_e004_synonyms.yaml --arm treatment
python scripts\evaluate_prereg.py --prereg docs\experiments\e004\e004-gates.yaml
```

**Checkpoint:** inspect the verdict and all guardrails, not just aggregate
improvement. If adopted, append
`{type: synonym_expansion, bidirectional: true, mode: append}` to
`current.adopted_stages`.

This frozen, benchmark-derived lexicon tests a vocabulary-bridging upper bound,
not general synonym quality. Exploratory arms are not the gated treatment.

**Read:** [E004 preregistration](e004/e004-preregistration.md).

## Step 6 - E005: freeze benchmark v2 and test structure

Build v2 before treatment runs:

```powershell
python scripts\build_benchmark_v2.py --emails datasets\synthetic\emails.jsonl --out data\benchmark_v2
```

Read `data\benchmark_v2\BENCHMARK_V2_CARD.md`. Paste its printed query-file
SHA-256 into `benchmarks.v2.annotations_sha256` in
`experiments\configs\shared_data.yaml`. Keep v1 unchanged. Each v2 scenario
needs at least 15 queries to be evaluable; its qrels are metadata-derived silver
judgments, not human relevance labels.

```powershell
python scripts\run_pipeline.py --config experiments\configs\011_e005_structure_ranges.yaml --arm control --benchmark v1
python scripts\run_pipeline.py --config experiments\configs\011_e005_structure_ranges.yaml --arm treatment --benchmark v1
python scripts\run_pipeline.py --config experiments\configs\011_e005_structure_ranges.yaml --arm control --benchmark v2
python scripts\run_pipeline.py --config experiments\configs\011_e005_structure_ranges.yaml --arm treatment --benchmark v2
python scripts\evaluate_prereg.py --prereg docs\experiments\e005\e005-gates.yaml
```

**Checkpoint:** v1 top-50 lists must remain identical (R-0). Judge `field_v2`
and `range_filter` separately using their component verdicts plus R-0.
Append only adopted components, in config order:
`{type: field_v2}` and
`{type: range_filter, reference_time: corpus_max, depth: 1000}`.
Record rejected or not-evaluable components too.

**Read:** [E005 preregistration](e005/e005-preregistration.md)
and [benchmark v2 design](../design/benchmark-v2.md).

## Step 7 - E006: measure semantic dense retrieval

Real E006-E008 runs require model dependencies and downloads. Lexical runs and
unit tests do not.

```powershell
python -m pip install -e ".[models]"
python scripts\run_pipeline.py --config experiments\configs\012_e006_dense.yaml --arm control
python scripts\run_pipeline.py --config experiments\configs\012_e006_dense.yaml --arm treatment
python scripts\evaluate_prereg.py --prereg docs\experiments\e006\e006-gates.yaml
```

The treatment uses `sentence-transformers/all-MiniLM-L6-v2` on CPU, not the
original hashing-based dense demo. Embeddings are cached in `runs\cache`.

**Checkpoint:** record the diagnostic result. E007 proceeds only if D-A
(paraphrase ranking) or D-B (recall-limited paraphrase recall) passes. If neither
passes, stop the sequence and record why. A dense signal can justify hybrid
testing even if dense alone fails a guardrail. Do not automatically append dense
to the lexical control: dense alone is eligible to become the control only if
every preregistered gate passes.

**Read:** [E006 preregistration](e006/e006-preregistration.md).

## Step 8 - E007: fuse lexical and dense rankings

```powershell
python scripts\run_pipeline.py --config experiments\configs\013_e007_hybrid.yaml --arm control
python scripts\run_pipeline.py --config experiments\configs\013_e007_hybrid.yaml --arm treatment
python scripts\run_pipeline.py --config experiments\configs\013_e007_hybrid.yaml --arm dense_only
```

If benchmark v2 was frozen in E005, also run its protection check before
evaluating:

```powershell
python scripts\run_pipeline.py --config experiments\configs\013_e007_hybrid.yaml --arm control --benchmark v2
python scripts\run_pipeline.py --config experiments\configs\013_e007_hybrid.yaml --arm treatment --benchmark v2
```

```powershell
python scripts\evaluate_prereg.py --prereg docs\experiments\e007\e007-gates.yaml
```

**Checkpoint:** hybrid must beat both control and dense alone while preserving
the protected cohorts. If adopted, append
`{type: hybrid_rrf, k: 60, depth: 100, encoder: sentence_transformer}`.
Record the E007 decision before E008, even if hybrid is not adopted.

**Read:** [E007 preregistration](e007/e007-preregistration.md).

## Step 9 - E008: rerank the frozen control's top 50

```powershell
python scripts\run_pipeline.py --config experiments\configs\014_e008_rerank.yaml --arm control
python scripts\run_pipeline.py --config experiments\configs\014_e008_rerank.yaml --arm treatment
```

If v2 is frozen, include its protection check:

```powershell
python scripts\run_pipeline.py --config experiments\configs\014_e008_rerank.yaml --arm control --benchmark v2
python scripts\run_pipeline.py --config experiments\configs\014_e008_rerank.yaml --arm treatment --benchmark v2
```

```powershell
python scripts\evaluate_prereg.py --prereg docs\experiments\e008\e008-gates.yaml
```

The CPU scorer is `cross-encoder/ms-marco-MiniLM-L-6-v2`.

**Checkpoint:** NDCG@10 must improve, Recall@50 must remain unchanged, and all
protected cohorts must pass. Report latency alongside quality. If adopted,
append `{type: rerank, scorer: cross_encoder, depth: 50}`. Record the final
decision and frozen configuration even if the reranker is not adopted.

**Read:** [E008 preregistration](e008/e008-preregistration.md).

## Evidence safeguards and further reading

Control parity, annotation hashes, provenance, de-duplication, and guardrails
are required evidence checks, not optional troubleshooting steps. Never replace
the preregistered models with hashing encoders or overlap scorers in evidence
runs. If `E003_SMOKE` is set to `1`, outputs are smoke-only and cannot support
adoption; clear it with `Remove-Item Env:E003_SMOKE` before evidence runs.

The older guides and checked-in results remain supporting references, not proof
that a new run passed. Keep synthetic-benchmark conclusions separate from claims
about real email search.

- [Learning path](../learning/README.md): implementation exercises and explanations.
- [Experiment methodology](../experiment-methodology.md): evidence discipline.
- [E004-E008 roadmap](e004-e008-roadmap.md): shared rules and limitations.
- [Composable pipeline guide](../learning/14-composable-pipeline-e004-e008.md): stage design.
- [Documentation index](../index.md): architecture, design, operations, and background.
