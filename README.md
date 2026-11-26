# Personal Search & Agent Lab

An evaluation-first research platform for retrieval, reranking, context engineering, agents,
personalization, and LLM evaluation. Milestone 1 focuses only on reproducible search evaluation.

## Milestone 1 capabilities

- Deterministic synthetic email corpus and labelled benchmark generation
- BM25-style lexical retrieval
- Deterministic hashing-based dense retrieval with no model download
- Reciprocal Rank Fusion hybrid retrieval
- Token-overlap second-stage reranker
- Precision@K, Recall@K, MRR, DCG@K, and NDCG@K
- YAML-driven experiments with per-query results and p50/p95 latency
- JSON and Markdown reports
- FastAPI search endpoint
- Unit tests for metrics, retrieval, and deterministic generation

The hashing retriever and overlap reranker are intentionally dependency-light reference implementations.
They preserve stable interfaces so public embedding models, vector databases, cross-encoders, or
late-interaction models can be added in later experiments.

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
```

## Generate the Milestone 1 dataset

```bash
python scripts/generate_dataset.py --emails 2000 --queries 200 --seed 42
```

## Run E001-E008 step by step

Follow the [E001-E008 step-by-step guide](docs/experiments/step-by-step-e001-e008.md)
for setup, dataset generation, every experiment command, expected artifacts,
and the decision checkpoints between experiments. The sequence includes E002b
and keeps earlier baselines frozen.

The original Milestone 1 configs `002_dense.yaml`, `003_hybrid.yaml`, and
`004_hybrid_reranker.yaml` remain available as dependency-light demos; their
numbers are not the research experiment IDs.

## Tests and quality checks

```bash
pytest
ruff check .
mypy packages
```

## API

```bash
uvicorn apps.api.main:app --reload
```

Then call `GET /health` or `POST /search`.

## Milestone 1 definition of done

1. A fixed seed regenerates the same corpus and benchmark.
2. At least 200 labelled queries cover multiple scenarios.
3. Search metrics pass edge-case tests.
4. BM25, dense, hybrid, and reranked systems share stable contracts.
5. Every experiment retains configuration, per-query rankings, metrics, and latency.
6. Reports include aggregate, scenario-level, and worst-query analysis.
7. No example metric is represented as measured until the experiment runs.

See the complete [documentation index](docs/index.md), including the project charter, requirements, design notes, experiment plans, runbook, security guidance, and contribution workflow.

## Understanding the code

Read [`docs/implementation/code-walkthrough.md`](docs/implementation/code-walkthrough.md) for the architecture and [`docs/implementation/e001-bm25-code-guide.md`](docs/implementation/e001-bm25-code-guide.md) for the E001 execution path.

## Implement E001 yourself

Use [`docs/learning/README.md`](docs/learning/README.md) as the guided learning path. It covers tokenization, inverted statistics, IDF, term-frequency saturation, document-length normalization, and full BM25 ranked search with behavioral tests and baseline boundaries.

## Research implementation references

The [E003 integration reference](E003_INTEGRATION.md) documents control wiring
and parity. The [E004-E008 roadmap](docs/experiments/e004-e008-roadmap.md) and
[pipeline learning guide](docs/learning/14-composable-pipeline-e004-e008.md)
explain the later stages. Use the consolidated guide above for execution order.
