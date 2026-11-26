# Documentation Index

## Start here

- [E001-E008 step-by-step guide](experiments/step-by-step-e001-e008.md) - the complete execution sequence, including E002b
- [Project charter](project-charter.md)
- [Milestone 1 requirements](requirements.md)
- [Getting started](development/getting-started.md)
- [Architecture](architecture.md)

## Design

- [Domain model](design/domain-model.md)
- [Retrieval design](design/retrieval.md)
- [Dataset and benchmark](design/dataset-and-benchmark.md)
- [Evaluation metrics](evaluation-metrics.md)

## Research experiments

- [Complete E001-E008 workflow](experiments/step-by-step-e001-e008.md)
- [E001 BM25](experiments/e001-bm25.md)
- [E002 query normalization](experiments/e002-query-normalized-bm25.md)
- [E002b context-aware alias normalization](experiments/e002b-context-aware-alias-normalization.md)
- [E003 field-aware and temporal retrieval](experiments/e003/e003-preregistration.md)
- [E004 synonyms](experiments/e004/e004-preregistration.md)
- [E005 structured benchmark](experiments/e005/e005-preregistration.md)
- [E006 semantic dense retrieval](experiments/e006/e006-preregistration.md)
- [E007 hybrid retrieval](experiments/e007/e007-preregistration.md)
- [E008 cross-encoder reranking](experiments/e008/e008-preregistration.md)
- [Experiment methodology](experiment-methodology.md)

## Supporting integration references

- [E003 integration and control parity](../E003_INTEGRATION.md)
- [E004-E008 roadmap](experiments/e004-e008-roadmap.md)
- [Composable pipeline guide](learning/14-composable-pipeline-e004-e008.md)

## Original Milestone 1 demos

These earlier documents use demo numbering, not the research sequence above.

- [Hashing dense demo (config 002)](experiments/e002-dense.md)
- [Hybrid demo (config 003)](experiments/e003-hybrid.md)
- [Overlap reranking demo (config 004)](experiments/e004-reranking.md)

## Development and operations

- [Contributing](development/contributing.md)
- [Runbook](operations/runbook.md)
- [Security and privacy](security-and-privacy.md)
- [Glossary](glossary.md)
- [ADR 0001](decisions/0001-evaluation-first.md)

## Code explanations

- [Complete code walkthrough](implementation/code-walkthrough.md)
- [E001 BM25 code guide](implementation/e001-bm25-code-guide.md)

## E001-E008 learning notes

- [Implementation learning path](learning/README.md)
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
- [Running and validating E002b](learning/12-running-and-validating-e002b.md)
- [Running and validating E003](learning/13-running-and-validating-e003.md)
- [Composable pipelines for E004-E008](learning/14-composable-pipeline-e004-e008.md)
