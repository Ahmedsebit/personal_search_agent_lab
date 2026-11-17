# E002: Dense Baseline

## Question

Does the dense retrieval interface recover useful matches that lexical retrieval misses, and where
does it regress?

## Important limitation

The default implementation uses feature hashing rather than a learned semantic encoder. The first
run validates the experiment path and comparison tooling. A later version should introduce a public
embedding model as a separately versioned treatment.

## Required comparison

Classify queries as BM25 wins, dense wins, both correct, both fail, or dense regression. Avoid
interpreting average metrics without this query-level analysis.
