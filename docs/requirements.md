# Milestone 1 Requirements

## Functional requirements

### Dataset

1. Generate deterministic synthetic emails from a configurable seed.
2. Include senders, recipients, subjects, bodies, dates, threads, projects, topics, statuses, and attachments.
3. Generate labelled queries for person, topic, person-plus-topic, recency, attachment, thread,
   status, and mixed-constraint scenarios.
4. Store graded relevance judgments from 0 to 3.

### Retrieval

1. Provide a common `Retriever` interface.
2. Support a lexical BM25-style implementation.
3. Support a dependency-light dense baseline.
4. Support hybrid Reciprocal Rank Fusion.
5. Support a replaceable second-stage `Reranker` interface.

### Evaluation

1. Compute Precision@10, Recall@10, Recall@50, MRR, DCG, and NDCG@10.
2. Retain ordered results for every query.
3. Report aggregate and scenario-level metrics.
4. Report p50 and p95 latency.
5. List low-performing queries for error analysis.
6. Save machine-readable JSON and human-readable Markdown reports.

### API

1. Expose a health endpoint.
2. Expose a bounded search endpoint.
3. Reject empty or excessively long queries through request validation.

## Non-functional requirements

- Python 3.11 or later
- Deterministic generation for a fixed seed
- Typed public interfaces
- Automated metric and retrieval tests
- No network dependency for the default smoke test
- No confidential or real workplace data
- Generated artifacts excluded from source control by default
- Clear replacement path for production-grade embedding and reranking models
