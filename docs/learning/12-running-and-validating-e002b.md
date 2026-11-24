# Running and Validating E002b

## Goal

Run E002b as a paired experiment against frozen E002, while retaining E001 as the original lexical baseline. E002b changes only alias-expansion eligibility and must use the original frozen E001 BM25 implementation.

## 1. Merge the package

Copy these files into the complete Personal Search & Agent Lab repository:

- `packages/search/query/context_aware_normalization.py`
- `packages/search/retrieval/context_aware_bm25.py`
- `packages/search/retrieval/e001_adapter.py`
- `packages/eval/e002b_runner_support.py`
- `packages/eval/e002b_comparison.py`
- `experiments/configs/006_context_aware_query_normalized_bm25.yaml`
- corresponding tests and docs

The integrated `e001_adapter.py` wraps the repository's E001 BM25 implementation, translating text mappings into indexed emails and normalized terms into queries. `simple_bm25.py` remains a standalone test double, not a runtime fallback.

## 2. Register the retriever

`scripts/run_experiment.py` handles `retrieval.type: context_aware_normalized_bm25` directly. Config 006 uses the same `name`, `dataset.root`, and `report.output_dir` schema as E001 and E002.

The runner reuses E002's explicit alias, misspelling, and hyphenation rules. Known full names come from corpus sender and recipient identities, not query intents or relevance judgments. No external alias or identity files are required.

## 3. Persist E002b metadata

For every query result, preserve the ordinary metrics plus:

- `source`
- `normalized_terms`
- `cohorts`
- `suppressed_aliases`

The shared evaluation runner stores these fields automatically for E002b, alongside the ordinary metrics, rankings, and latency. E001 and E002 retain their existing report schemas.

## 4. Run tests first

From the repository root:

```bash
PYTHONPATH=. python -m pytest -q
```

Do not run the benchmark unless all normalization, retrieval-integration, runner-support, and comparison tests pass.

## 5. Smoke-test individual queries

Run or inspect at least:

```text
emails from Ali
spend plan from Ally
architecture from O.H.
emails from Fatima Ali
rollout from Fatima Ali
latest Atlas ranking
```

Expected checks:

- standalone aliases still expand;
- `Fatima Ali` creates `alias_collision` metadata and suppresses `Alice Morgan` terms;
- initials retain E002 behavior;
- `none` queries retain identical rankings;
- result source is `context-aware-query-normalized-bm25`;
- top-k remains 50 by default.

## 6. Run the full E002b experiment

Use the same experiment runner used for E001 and E002, pointing to:

```text
experiments/configs/006_context_aware_query_normalized_bm25.yaml
```

For example, if the existing runner accepts `--config`:

```bash
PYTHONPATH=. python scripts/run_experiment.py \
  --config experiments/configs/006_context_aware_query_normalized_bm25.yaml
```

Expected result artifact:

```text
experiments/results/e002b-context-aware-bm25.json
```

If the repository's runner uses a different command, preserve its existing interface and only add the E002b retriever type and metadata fields.

## 7. Compare E002b with E002

Use the E002 result that produced the accepted E002 comparison. Then run:

```bash
PYTHONPATH=. python scripts/compare_e002b.py \
  --e002 experiments/results/e002-query-normalized-bm25.json \
  --e002b experiments/results/e002b-context-aware-bm25.json \
  --output experiments/results/e002b-vs-e002-comparison.json \
  --diagnostic-query-id query-0056 \
  --diagnostic-query-id query-0186
```

Confirm the query IDs for the two historical `Fatima Ali` cases rather than assuming the examples above if the benchmark changed.

## 8. Validate the preregistered gates

All seven gates must pass:

1. alias-collision NDCG@10 strictly improves;
2. alias-collision Recall@50 does not regress;
3. safe-alias Recall@50 delta is at least -0.01;
4. safe-alias NDCG@10 delta is at least -0.01;
5. `none` NDCG@10 delta is at least -0.01;
6. `none` Recall@50 delta is at least -0.01;
7. both historical diagnostic queries improve in NDCG@10 and do not regress in Recall@50.

The ideal result for the `none` cohort is exactly zero change.

## 9. Compare with E001

After the primary E002b-vs-E002 decision, also compare E002b with E001 to confirm that the final method retains net value over raw BM25. This is a supporting comparison, not the primary acceptance control.

## 10. Interpret conservatively

If all gates pass, the supported conclusion is:

> Context-aware alias eligibility reduced harmful lexical over-expansion while retaining E002's query-normalization benefit in this benchmark.

Do not claim general entity resolution. If the alias-collision cohort remains only the two known queries, mark the cohort-level evidence as limited and expand the synthetic benchmark using preregistered generation rules before making a broader claim.
