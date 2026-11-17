# Retrieval Design

## Lexical baseline

The BM25-style retriever tokenizes each document, records term and document frequency, then scores
query terms with length normalization. It is expected to be strong for exact entities, project
names, status words, and attachment names.

## Dense baseline

Milestone 1 uses deterministic feature hashing over unigrams and bigrams. It is not presented as a
state-of-the-art semantic model. Its purposes are to:

- preserve a dense-vector retrieval interface;
- enable offline execution without downloading a model;
- create a controlled baseline that can later be replaced.

A future implementation may use a public sentence embedding model and vector index behind the same
interface.

## Hybrid retrieval

Reciprocal Rank Fusion combines ranked results without requiring score calibration:

`score(document) = sum(1 / (rrf_k + rank_i))`

This tests whether lexical and dense candidate sets provide complementary coverage.

## Reranking

The reranker receives a fixed candidate set. This is an important experimental boundary: a
reranking experiment should not silently change candidate generation.

The initial token-overlap reranker is transparent and replaceable. A later experiment can substitute
a public cross-encoder or late-interaction model.

## Known limitations

- Tokenization is intentionally simple.
- The hashing retriever is not a learned semantic encoder.
- The initial reranker is lexical rather than neural.
- Indexes are in memory and rebuilt for every process.
- Temporal intent is represented in the benchmark but not yet handled by a dedicated recency model.
