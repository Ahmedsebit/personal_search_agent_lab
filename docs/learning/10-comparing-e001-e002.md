# Comparing E001 and E002

The comparison layer is fixed before the full E002 run. Its purpose is to prevent selective interpretation after treatment results are available.

## Join by query ID

`compare_reports()` joins E001 and E002 per-query records by `query_id`, verifies the query sets and query text match, then calculates:

```text
delta = E002 - E001
```

for Precision@10, Recall@10, Recall@50, MRR, DCG@10, and NDCG@10.

## Outcomes

Each query is labeled:

- `improved` when NDCG@10 or Recall@50 has a positive delta and neither rule is overridden by a negative-only outcome;
- `regressed` when either key metric decreases and neither improves;
- `unchanged` when both are effectively identical.

The actual numeric deltas remain the evidence; the outcome label is only a convenience for inspection.

## Cohorts

Cohorts are recomputed from the frozen normalizer using the original query text. Reports include individual transformation labels plus:

- `targeted` for any E002 transformation;
- `multiple` when more than one family fires;
- `none` when the query is untouched.

The report averages metric deltas within each cohort, counts improved/regressed/unchanged queries, and separately reports scenario-level deltas.

## Acceptance gates

The comparison tool encodes the preregistered quality gates:

- targeted Recall@50 delta must be positive;
- targeted NDCG@10 must not decrease;
- `none` NDCG@10 delta must be at least -0.01;
- `none` Recall@50 delta must be at least -0.01.

Latency deltas are reported separately because no hard latency threshold was preregistered.

## CLI

After an E002 report exists:

```bash
python scripts/compare_experiments.py \
  --control experiments/results/e001-bm25-baseline.json \
  --treatment experiments/results/e002-query-normalized-bm25.json \
  --output experiments/results/e001-vs-e002-comparison.json
```

The command writes both JSON and Markdown.

## Why build this before running E002?

It freezes the questions we will ask of the treatment: overall deltas, targeted-cohort behavior, untouched-query regressions, scenario movement, latency changes, and the most changed individual queries. We should not redesign the comparison because we dislike the eventual result.
