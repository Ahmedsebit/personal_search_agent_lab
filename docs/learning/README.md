# E001-E008 Learning Path

For commands, expected outputs, and decision checkpoints, follow the
[E001-E008 step-by-step guide](../experiments/step-by-step-e001-e008.md).
These supporting notes explain how to implement and understand each mechanism,
starting with E001 rather than copying the finished retriever.

1. [Tokenization](01-tokenization.md)
2. [Inverted statistics](02-inverted-statistics.md)
3. [Inverse document frequency](03-inverse-document-frequency.md)
4. [Term-frequency saturation and length normalization](04-term-frequency-saturation.md)
5. [Full BM25 scoring and ranked search](05-full-bm25-scoring-and-search.md)
6. [Implementing search(query, k)](06-search-query-top-k.md)
7. [Evaluation metrics](07-evaluation-metrics.md)
8. [Running and analyzing E001](08-running-and-analyzing-e001.md)

9. [E002 query normalization](09-query-normalization-and-e002.md)
10. [Comparing E001 and E002](10-comparing-e001-e002.md)
11. [Running and validating E002b](12-running-and-validating-e002b.md)
12. [Running and validating E003](13-running-and-validating-e003.md)
13. [Composable pipelines for E004-E008](14-composable-pipeline-e004-e008.md)

Each guide explains the purpose, implementation shape, deliberate baseline
limitations, tests, and readiness checks for the next exercise. Existing
filenames retain their historical numbering so links remain stable.
