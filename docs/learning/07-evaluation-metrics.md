# Evaluating E001: Precision, Recall, MRR, DCG/NDCG, and latency

Retrieval is implemented. The next learning step is to stop changing BM25 and measure what it actually does. This guide explains the metrics used by E001 and how they answer different questions.

The code lives in `packages/eval/metrics/ranking.py`. The experiment runner in `packages/eval/runner.py` evaluates every query and then aggregates metrics overall and by scenario.

## Start with one query

Imagine there are eight relevant emails for a query. The top 10 retrieves only three of them.

```text
known relevant emails = 8
relevant emails in top 10 = 3
Recall@10 = 3 / 8 = 0.375
```

Recall answers: **How much of the relevant material did retrieval find?**

Now suppose the other five relevant emails occur between ranks 11 and 50. Then:

```text
Recall@10 = 3 / 8 = 0.375
Recall@50 = 8 / 8 = 1.0
```

This tells us something actionable: first-stage retrieval found all relevant material, but much of it is ranked too low. A later reranker may have substantial headroom. If Recall@50 is also low, reranking cannot recover documents that the retriever never surfaced.

## Precision@10

```text
Precision@10 = relevant documents in first 10 / 10
```

Precision asks: **How concentrated are relevant results near the top?**

If six of the first ten results are relevant, Precision@10 is `0.6`.

For user-facing search, top-rank precision matters because users usually inspect only a small result set. Precision does not tell us whether many additional relevant documents were missed elsewhere in the corpus.

### Important implementation detail

E001 divides by `k`, not by the number of returned results. This treats missing ranks inside the requested cutoff as non-relevant slots.

## Recall@10 and Recall@50

```text
Recall@k = relevant documents retrieved by rank k / all known relevant documents
```

We use both depths for different reasons:

- `Recall@10` measures coverage in the immediately visible ranking.
- `Recall@50` measures whether first-stage retrieval made relevant candidates available deeper in the list.

The gap between them is particularly useful when deciding whether reranking is promising.

## Reciprocal Rank and MRR

For one query:

```text
Reciprocal Rank = 1 / rank of first relevant document
```

Examples:

```text
first relevant result at rank 1 -> 1.0
first relevant result at rank 2 -> 0.5
first relevant result at rank 5 -> 0.2
no relevant result              -> 0.0
```

MRR, Mean Reciprocal Rank, averages reciprocal rank across queries.

MRR asks: **How quickly does the system produce its first useful answer?**

It is deliberately insensitive to relevant documents after the first one. That makes it useful for navigational or “find one good answer quickly” behavior, but insufficient by itself for broad-recall queries.

## DCG: ranking graded relevance

Our benchmark uses relevance grades, not merely relevant/non-relevant labels. DCG lets a highly relevant document count more than a marginally relevant one while also rewarding results appearing earlier.

E001 uses:

```text
gain = 2^relevance - 1
discount at rank r = log2(r + 1)
DCG@k = sum(gain / discount) through rank k
```

A relevance-3 document therefore has much greater gain than a relevance-1 document. Moving that strong result from rank 1 to rank 8 decreases its value because the logarithmic rank discount increases.

DCG answers: **How much graded relevance did this ordering deliver near the top?**

Raw DCG is difficult to compare across queries because queries can have different numbers and strengths of relevant documents.

## NDCG@10

NDCG normalizes the observed DCG against the best possible ordering for the same relevance judgments:

```text
NDCG@10 = actual DCG@10 / ideal DCG@10
```

An ideal ordering places the highest grade first, followed by the next-highest grade, and so on.

Useful interpretation:

- `1.0`: ideal judged ordering at that cutoff;
- closer to `0`: increasingly poor placement of judged relevant results;
- `0.0`: no gain at the evaluated ranks, or no positive ideal gain.

NDCG is central to E001 because our benchmark has grades 1-3 and ranking quality matters, not just whether a document appears somewhere in the candidate set.

## Why use several metrics?

No single metric describes search quality.

A system can have:

- high MRR because one relevant result appears first;
- low Recall@50 because most other relevant documents are missing;
- reasonable Recall@50 but poor NDCG@10 because good candidates are ordered badly.

That combination tells a more useful engineering story than one headline number.

## Query latency

The runner measures elapsed retrieval time for every query with a monotonic high-resolution timer.

We summarize latency using percentiles:

- `p50`: the median query, a typical observed latency;
- `p95`: a tail-latency view, where 95% of measured queries were no slower than that value.

Do not overinterpret one short synthetic run. Python process state, machine load, caching, and corpus/query shape can affect timings. Repeated runs are appropriate before drawing performance conclusions.

## One-query evaluation API

`evaluate_ranking()` provides the standard E001 metric set for one query:

```python
from packages.eval.metrics.ranking import evaluate_ranking

ranked_ids = [result.document_id for result in results]
grades = {
    "email-001": 3,
    "email-014": 2,
    "email-090": 1,
}

metrics = evaluate_ranking(ranked_ids, grades)
```

It returns:

```text
precision@10
recall@10
recall@50
mrr
dcg@10
ndcg@10
```

The experiment runner additionally records query latency.

## Behavioral tests

The tests now cover conceptual properties as well as formulas:

- three of eight relevant documents produces Recall@10 = `3/8`;
- deeper relevant results can raise Recall@50 while Recall@10 stays unchanged;
- moving the first relevant result earlier increases reciprocal rank;
- putting stronger graded results earlier increases NDCG;
- a perfect graded ordering has NDCG = `1.0`;
- empty relevance sets and invalid cutoffs behave explicitly.

Run:

```bash
pytest tests/eval/test_metrics.py -q
```

Then:

```bash
pytest -q
```

## Manual evaluation checklist

Before running 200 queries, take three to five queries and inspect:

1. the relevance judgments;
2. the retrieved document IDs;
3. which retrieved IDs are judged relevant;
4. where the first relevant result occurs;
5. how many relevant documents appear by rank 10 and rank 50;
6. whether high-grade documents are near the top;
7. whether the calculated metrics match your intuition.

You should be able to explain a query's metrics without treating the evaluator as a black box.

## From one query to the experiment

Once individual-query calculations make sense, `run_experiment()` performs the same sequence for all 200 benchmark queries:

```text
query
-> search(query, k=50)
-> measure latency
-> collect judged relevance grades
-> calculate per-query metrics
-> repeat for all queries
-> average metrics overall
-> average metrics by scenario
-> calculate latency p50/p95
```

This produces the evidence needed for proper E001 failure analysis.

## Do not tune BM25 yet

The point of evaluation is to expose limitations, not immediately erase them. Examples include semantic paraphrases, aliases, misspellings, recency, ambiguous people, and hard lexical negatives.

Record those failures. Improvements belong in new experiments so E001 remains a stable comparison baseline.

## Next learning step

Run all 200 queries, save per-query metrics, break results down by scenario and difficulty, inspect the worst NDCG queries, and assign each failure to an explicit taxonomy. That turns evaluation numbers into hypotheses for E002 and later retrieval experiments.
