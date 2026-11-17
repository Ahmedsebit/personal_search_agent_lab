# ADR 0001: Evaluation-first architecture

## Decision
Build corpus generation, judgments, metrics, and the experiment runner before RAG or agents.

## Rationale
Later capabilities must demonstrate measurable value at the layer they change. This prevents a
plausible end-to-end answer from hiding retrieval, ranking, routing, or evidence failures.

## Consequences
Milestone 1 excludes generation, tool calling, memory, personalization, and LLM judges.
