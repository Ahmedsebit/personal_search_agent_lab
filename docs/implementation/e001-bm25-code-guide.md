# E001 BM25 Code Guide

## Files involved

| File | Responsibility |
|---|---|
| `experiments/configs/001_bm25.yaml` | Declares dataset, retriever, top-k values, and output path. |
| `scripts/run_experiment.py` | Composition root that loads dependencies and starts the run. |
| `packages/datasets/loader.py` | Loads corpus, queries, and judgments. |
| `packages/search/retrieval/bm25.py` | Builds the lexical index and scores documents. |
| `packages/eval/runner.py` | Executes queries, measures latency, and computes metrics. |
| `packages/eval/metrics/ranking.py` | Implements ranking metrics. |
| `packages/eval/reporting.py` | Writes JSON and Markdown artifacts. |
| `experiments/results/e001-bm25-analysis.md` | Explains scenario results, worst queries, and failures. |

## Execution pseudocode

```text
config = load experiment YAML
emails, queries, judgments = load benchmark
retriever = BM25Retriever()
retriever.index(emails)

for query in queries:
    start timer
    candidates = retriever.search(query.text, top_k=50)
    stop timer
    metrics = compare candidates with query judgments
    store ranking, metrics, scenario, and latency

aggregate query metrics
calculate scenario slices and latency percentiles
write JSON and Markdown reports
```

## Why top 50 and top 10 coexist

The first-stage retriever returns 50 candidates so candidate recall can be measured and future rerankers have sufficient input. User-facing ranking quality is evaluated primarily at 10. Therefore E001 reports Recall@50 alongside Recall@10 and NDCG@10.

## Reading one query result

A per-query record contains the original query, scenario, ranked document IDs, latency, and metrics. The ranked IDs can be joined with `emails.jsonl`; relevance grades can be joined with `judgments.jsonl`. This allows inspection of false positives, missed positives, and their positions without running search again.

## Expected future experiments

A change should improve targeted slices without silently altering the benchmark, and its latency cost must be reported. Query normalization, for example, should improve alias, typo, and paraphrase queries while preserving exact-match status performance.
