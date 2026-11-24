# 14 — From one retriever to a pipeline (E004–E008)

Up to E003, each experiment was a new retriever class. From E004 on, each experiment is a **stage** that wraps the current frozen control:

```text
frozen control (E002b + adopted E003 arm + adopted stages)
   └─ E004 synonym rewrite     → changes the query
   └─ E005 field_v2 / range    → routes or filters
   └─ E006 dense               → a different retriever (diagnostic)
   └─ E007 hybrid RRF          → fuses lexical + dense rankings
   └─ E008 re-rank             → re-orders the top 50
```

Adopting a stage means adding one line to `frozen_control.yaml`. The next experiment then automatically runs on top of it. Earlier code is never edited, so every past result stays reproducible.

## Why the gates are YAML

The gate table *is* the preregistration. Keeping it as data means the document, the code and the result use the same definitions, so a threshold can't drift between what was promised and what was checked.

## What each experiment teaches

- **E004:** how much error is pure vocabulary mismatch. This is an upper bound, because the lexicon is benchmark-derived.
- **E005:** whether structured intent (to, subject, date range) can be measured and honoured. It also shows the cost of silver judgments.
- **E006:** whether embeddings capture what lexical retrieval misses, and what they lose (names, IDs).
- **E007:** whether combining the two keeps the strengths of both.
- **E008:** whether a slower and more accurate model is worth it for the final order, and whether it erases recency and sender signals.
