# Code Walkthrough

This guide explains how Milestone 1 fits together, how data moves through the system, and where to extend it without coupling retrieval to evaluation.

## End-to-end execution path

Running `python scripts/run_experiment.py --config experiments/configs/001_bm25.yaml`:

1. loads YAML through `packages.common.config.load_yaml`;
2. reconstructs emails, queries, and judgments with `packages.datasets.loader.load_dataset`;
3. selects the configured retriever, which is `BM25Retriever` for E001;
4. indexes the corpus once;
5. executes every query and records rankings and elapsed time;
6. computes per-query, aggregate, and scenario metrics;
7. writes JSON and Markdown reports.

The retriever returns rankings but does not judge itself. The evaluator measures every retriever through the same interface, keeping model code separate from measurement.

## Core models

### `packages/search/models.py`

`Email` is the evidence object. It preserves text plus sender, recipients, timestamp, attachments, thread ID, and metadata. Later experiments can therefore add field-aware ranking without replacing the dataset.

`SearchResult` contains a document ID and implementation-specific score. Evaluation uses ranking order rather than assuming scores from different retrievers are calibrated.

### `packages/datasets/models.py`

`SearchQuery` carries text, scenario, difficulty, structured intent, and notes. Structured intent supports auditing; it is not secretly provided to retrieval.

`RelevanceJudgment` links a query to a document with a 1-3 grade and rationale. Unlisted pairs are treated as irrelevant.

## Dataset generation and audit

### `packages/datasets/generator.py`

`build_dataset` is deterministic for a fixed seed. It generates emails, then queries, then relevance judgments. Benchmark v2 introduces ambiguous people, similar project names, aliases, paraphrases, misspellings, hard negatives, and attachment, thread, status, and recency intents.

Recency labels are graded: the newest qualifying item receives grade 3, while older matches receive lower grades. Query constraints drive judgments so labels are not based on one arbitrary target when several documents legitimately match.

### `packages/datasets/audit.py`

The audit detects duplicate IDs, unknown references, invalid grades, duplicate judgment pairs, and queries without positive judgments. It reports scenario, difficulty, and grade distributions. This establishes structural validity but does not replace independent human review of realism.

### `packages/datasets/loader.py`

The loader owns serialization. It converts timestamps and tuples for JSONL and reconstructs typed objects during loading, preventing the experiment pipeline from depending on raw dictionaries.

## Retrieval interfaces

### `packages/search/interfaces.py`

`Retriever` defines `index(documents)` and `search(query, limit)`. `Reranker` consumes a query, candidate ranking, and document map, then returns a reordered ranking. This supports independent testing of candidate generation and second-stage ranking.

## BM25 code

### `packages/search/retrieval/bm25.py`

`BM25Retriever` is an in-memory lexical baseline.

During indexing it tokenizes searchable email fields, records term frequency and document length, counts document frequency, and calculates average document length.

During search it tokenizes the query, calculates inverse document frequency for known terms, applies term-frequency saturation and document-length normalization, sums term contributions, sorts by score, and returns the requested number of results.

`k1` controls how quickly repeated terms stop adding value. `b` controls document-length normalization. The implementation intentionally has no stemming, typo correction, synonym expansion, field weighting, temporal boost, or semantic similarity. Those omissions make E001 interpretable.

## Evaluation runner

### `packages/eval/runner.py`

`run_experiment` builds document and judgment lookups, indexes once, and loops through the benchmark. Timing surrounds retrieval and optional reranking, excluding loading and report writing.

Each query receives Precision@10, Recall@10, Recall@50, MRR, DCG/NDCG@10, and latency. The same per-query records are then averaged globally and by scenario. Latency is summarized with p50 and p95.

## Metrics

### `packages/eval/metrics/ranking.py`

- **Precision@k**: fraction of the first k results that are relevant.
- **Recall@k**: fraction of all judged relevant documents appearing in the first k.
- **MRR**: reciprocal rank of the first relevant result.
- **DCG**: graded relevance discounted by rank.
- **NDCG**: DCG normalized against the ideal ranking.

Metrics answer different questions. A broad person or topic query can have MRR 1.0 but low Recall@10 because many relevant documents cannot fit into ten positions.

## Reporting and analysis

### `packages/eval/reporting.py`

`write_report` stores complete per-query output in JSON and creates a readable Markdown summary. Persisting ranked IDs, metrics, scenarios, and latency makes deeper analysis possible without rerunning retrieval.

### `experiments/results/e001-bm25-analysis.*`

The E001 analysis joins saved output with query metadata and judgments, computes scenario latency percentiles, identifies worst-NDCG queries, and assigns failure categories. The taxonomy belongs to analysis rather than retrieval and should evolve when the benchmark changes.

## Interpreting E001

E001 records NDCG@10 of 0.5956, Recall@10 of 0.3357, Recall@50 of 0.6876, and MRR of 0.6837. The Recall@50 gap means BM25 often retrieves relevant candidates but positions them below rank 10, creating room for reranking. Zero-result paraphrase queries justify query normalization or semantic retrieval.

Keep E001 frozen. Improvements should be separate experiments so comparisons remain reproducible and auditable.

## Extension points

- E002: normalize aliases, spelling, and synonyms before BM25 while retaining raw queries in reports.
- E003: add sender, attachment, metadata, and timestamp-aware scoring in a separate retriever.
- E004: implement dense retrieval behind the same `Retriever` protocol.
- E005: fuse lexical and dense rankings with reciprocal-rank fusion.
- E006: rerank the top 50 through the `Reranker` protocol.
