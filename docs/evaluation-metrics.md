# Evaluation Metrics

## Precision@K

The proportion of the first K retrieved documents that are relevant. Useful when the displayed list
is small, but sensitive to the chosen relevance threshold.

## Recall@K

The proportion of all known relevant documents retrieved in the first K. Recall@50 is especially
useful for assessing whether a reranker was given an adequate candidate set.

## Mean Reciprocal Rank

Rewards placing the first relevant result near the top. It does not describe the quality of the
remaining ranked list.

## DCG and NDCG

Discounted Cumulative Gain rewards highly relevant documents appearing early. NDCG divides the
observed gain by the best possible gain for that query, enabling comparison across queries with
different numbers and grades of relevant documents.

## Latency

The runner reports p50 and p95 query latency. Measurements include retrieval and optional reranking
inside the experiment process. They are useful for relative local comparisons, not production SLO
claims.

## Reporting rules

- Always retain per-query outcomes.
- Slice metrics by scenario.
- Inspect the worst-performing queries.
- Report quality and latency together.
- Do not treat a smoke-test measurement as a final scientific result.
