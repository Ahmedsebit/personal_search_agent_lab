# Domain Model

## Email

An email is the initial searchable document. It contains identity, participants, content, time,
attachment state, thread membership, and structured metadata.

Key invariant: `searchable_text` is a projection for indexing, not the canonical record.

## SearchQuery

A benchmark query contains:

- stable query ID
- natural-language text
- scenario label used for slicing results

## RelevanceJudgment

A judgment relates one query to one document:

- 0: irrelevant
- 1: somewhat relevant
- 2: relevant
- 3: highly relevant

Current generation writes only positive judgments; unlisted query-document pairs are interpreted
as relevance 0.

## SearchResult

A result contains:

- document ID
- retrieval/reranking score
- one-based rank
- source component name

Scores are implementation-specific and must not be compared directly across retrievers without
normalization or rank-based fusion.

## ExperimentReport

An experiment report includes:

- experiment identity
- active retriever or reranker
- aggregate metrics
- scenario metrics
- p50/p95 latency
- per-query results
- exact configuration used by the run
