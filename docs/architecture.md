# Milestone 1 Architecture

Milestone 1 enforces three boundaries:

- `datasets`: deterministic evidence and labels
- `search`: retrieval and ranking only
- `eval`: independent measurement and reporting

All retrievers implement the same interface. Rerankers receive a fixed candidate set. The experiment
runner retains per-query output, preventing aggregate metrics from hiding regressions.
