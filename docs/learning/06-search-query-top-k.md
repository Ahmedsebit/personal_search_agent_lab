# Implementing `search(query, k)`

This exercise turns BM25 scoring into the retrieval operation used by E001. The important goal is to test individual queries and inspect rankings before running the complete 200-query benchmark.

## Contract

```python
results = retriever.search(query, k=50)
```

`k` defaults to **50**, matching E001's retrieval depth. The older keyword `limit=` remains available as a compatibility alias for the shared retriever interface.

The operation has four conceptual stages:

1. **Tokenize the query** with the exact tokenizer used while indexing documents.
2. **Calculate BM25 scores** for documents containing at least one query term.
3. **Sort documents** by descending BM25 score, then document ID for deterministic ties.
4. **Return the top k**, with E001 defaulting to the top 50.

## 1. Tokenize the query

E001 keeps query processing deliberately simple. Lowercase and split with the same lexical rules used for documents. Repeated query tokens are deduplicated because query-term-frequency weighting is outside this baseline.

Using a different query tokenizer from the document tokenizer can create invisible retrieval failures: the query and index would disagree about what a term is.

## 2. Find candidates

The postings index maps each term to documents containing it. For a multi-term query, union those posting sets.

A document containing none of the query terms has a BM25 score of zero, so there is no need to score it.

This is the first important efficiency property of an inverted index: retrieval work is proportional to matching postings instead of automatically scanning every document.

## 3. Score candidates

For every candidate document and every unique query term:

```text
score += IDF(term) * TF_length_component(term, document)
```

An absent term contributes zero. A document matching several discriminative query terms can therefore outrank one that strongly repeats only a single common term.

## 4. Sort and truncate

Sort using:

```text
(-score, document_id)
```

The first key gives descending BM25 score. The document ID provides deterministic ordering when scores are exactly equal, which matters for reproducible experiments.

Only after sorting do we take the first `k` results.

## Why top 50?

E001 measures both top-10 quality and deeper retrieval recall. Retrieving 50 candidates lets us measure `Recall@50` and later examine whether a reranker has useful relevant documents available below the first 10 positions.

This is different from saying the product UI should show 50 results. It is an experimental retrieval depth.

## Behavioral tests

`tests/search/test_bm25_learning.py` now verifies that:

- `search("ranking")` returns at most 50 results by default;
- `search("ranking", k=7)` respects an explicit retrieval depth;
- returned scores are descending;
- ranks are one-based and contiguous;
- a no-match query returns an empty list.

Run the focused tests:

```bash
pytest tests/search/test_bm25_learning.py -q
```

Then run the whole suite:

```bash
pytest -q
```

## Test individual queries before the benchmark

Before averaging 200 queries into metrics, inspect several query types manually. This makes failures interpretable.

Generate the deterministic benchmark if needed:

```bash
python scripts/generate_dataset.py --emails 2000 --queries 200 --seed 42 --output datasets
```

Then use a small Python session:

```python
from pathlib import Path
from packages.datasets.loader import load_dataset
from packages.search.retrieval.bm25 import BM25Retriever

emails, queries, judgments = load_dataset(Path("datasets"))
retriever = BM25Retriever(k1=1.5, b=0.75)
retriever.index(emails)

for query in queries[:5]:
    print("QUERY:", query.text)
    for result in retriever.search(query.text, k=10):
        print(result.rank, result.document_id, round(result.score, 4))
    print()
```

Do not ask only whether results “look good.” For each query inspect:

- Which query terms actually matched?
- Is a rare term dominating the score for a sensible reason?
- Is repetition helping without dominating linearly?
- Are long documents being moderated by length normalization?
- Are relevant documents present but below rank 10?
- Does a failure require a capability deliberately excluded from E001, such as aliases, semantics, or recency?

## Recommended manual smoke-query set

Choose at least one benchmark query from each important behavior:

- exact lexical topic;
- person or identity;
- person + topic;
- attachment;
- thread;
- status;
- recency;
- paraphrase or misspelling hard case.

The goal is not to tune BM25 after every failure. The goal is to understand the baseline before freezing and measuring it.

## Benchmark gate

Move to the 200-query run when:

- focused search tests pass;
- full repository tests pass;
- several individual queries return plausible, deterministic rankings;
- no implementation bug is being confused with an expected lexical limitation;
- `k=50` returns no more than 50 results and preserves decreasing score order.

After this gate, run E001 without changing its scoring behavior. Any improvement becomes a new experiment.
