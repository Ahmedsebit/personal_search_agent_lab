# E003: Hybrid Retrieval

## Question

Can rank fusion preserve lexical strengths while benefiting from complementary dense candidates?

## Method

Use Reciprocal Rank Fusion over BM25 and dense ranked lists. Keep the corpus, benchmark, evaluation
metrics, and requested depth unchanged from E001/E002.

## Required analysis

- candidate overlap between retrievers;
- query-level gains and regressions;
- scenario-level changes;
- additional latency;
- whether gains are caused by improved candidate recall or ordering.
