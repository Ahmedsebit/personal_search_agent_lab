# Documentation Index

## Start here

- [Project charter](project-charter.md)
- [Milestone 1 requirements](requirements.md)
- [Getting started](development/getting-started.md)
- [Architecture](architecture.md)

## Design

- [Domain model](design/domain-model.md)
- [Retrieval design](design/retrieval.md)
- [Dataset and benchmark](design/dataset-and-benchmark.md)
- [Evaluation metrics](evaluation-metrics.md)

## Experiments

- [E001 BM25](experiments/e001-bm25.md)
- [E002 dense](experiments/e002-dense.md)
- [E003 hybrid](experiments/e003-hybrid.md)
- [E004 reranking](experiments/e004-reranking.md)
- [Experiment methodology](experiment-methodology.md)

## E003-E008 research sequence

- [Integrated workflow](../README_E003_E008.md)
- [E003 integration and control parity](../E003_INTEGRATION.md)
- [E003 preregistration](experiments/e003/e003-preregistration.md)
- [E004-E008 roadmap](experiments/e004-e008-roadmap.md)
- [Composable pipeline guide](learning/14-composable-pipeline-e004-e008.md)
- [E004 synonyms](experiments/e004/e004-preregistration.md)
- [E005 structured benchmark](experiments/e005/e005-preregistration.md)
- [E006 semantic dense retrieval](experiments/e006/e006-preregistration.md)
- [E007 hybrid retrieval](experiments/e007/e007-preregistration.md)
- [E008 cross-encoder reranking](experiments/e008/e008-preregistration.md)

## Development and operations

- [Contributing](development/contributing.md)
- [Runbook](operations/runbook.md)
- [Security and privacy](security-and-privacy.md)
- [Glossary](glossary.md)
- [ADR 0001](decisions/0001-evaluation-first.md)

## Code explanations

- [Complete code walkthrough](implementation/code-walkthrough.md)
- [E001 BM25 code guide](implementation/e001-bm25-code-guide.md)

## E001 learning notes

- [Learning path](learning/README.md)
- [Tokenization](learning/01-tokenization.md)
- [Inverted statistics](learning/02-inverted-statistics.md)
- [Inverse document frequency](learning/03-inverse-document-frequency.md)
- [Term-frequency saturation and length normalization](learning/04-term-frequency-saturation.md)

- [Full BM25 scoring and ranked search](learning/05-full-bm25-scoring-and-search.md)
- [Implementing search(query, k)](learning/06-search-query-top-k.md)
- [Evaluation metrics learning guide](learning/07-evaluation-metrics.md)
- [Running and analyzing E001](learning/08-running-and-analyzing-e001.md)
- [E002 hypotheses and acceptance criteria](experiments/e002-query-normalized-bm25.md)
- [E002 query-normalization learning guide](learning/09-query-normalization-and-e002.md)
- [E001 vs E002 comparison guide](learning/10-comparing-e001-e002.md)
