# E002: Query-normalized BM25

## Status

**Implemented / pre-run.** This document freezes the E002 hypotheses, metrics, and acceptance criteria before the 200-query experiment is executed.

E001 remains unchanged and is the comparison baseline.

## Motivation from E001

E001 reached NDCG@10 = 0.5956 and Recall@50 = 0.6876 on the deterministic synthetic benchmark. Its strongest scenarios were status, mixed, and person; its weakest included recency, topic, person-topic, thread, and attachment. Inspection also exposed surface-form failures such as aliases/initials, misspellings, and hyphenated variants.

E002 intentionally addresses only **lexical surface-form mismatch at query time**. It does not attempt to solve semantics, time, structured fields, or reranking.

## Research question

> Does explicit, benchmark-owned query normalization improve BM25 candidate retrieval and top-rank quality for aliases, initials, hyphenation, and known misspellings without materially degrading E001's strong exact-match behavior?

## Intervention

Treatment pipeline:

```text
raw query
-> explicit E002 normalization
-> preserve original lexical evidence + add canonical terms
-> unchanged E001 BM25 index and scoring
-> top 50
-> unchanged E001 evaluation
```

The indexed corpus is not normalized in E002. BM25 parameters stay at `k1=1.5` and `b=0.75`.

Allowed normalization families:

1. **Aliases** encoded by the synthetic benchmark.
2. **Initials**, including dotted forms such as `O.H.`.
3. **Hyphenation** variants explicitly defined for the benchmark.
4. **Known misspellings** explicitly emitted by the benchmark generator.

Out of scope:

- generic edit distance or fuzzy matching;
- semantic synonyms/paraphrases;
- temporal scoring;
- field boosts;
- corpus rewriting;
- dense retrieval;
- reranking.

## Hypotheses

### H1: targeted candidate recall

For queries belonging to alias, initials, hyphenation, or misspelling cohorts, E002 will increase mean Recall@50 relative to E001.

**Primary hypothesis.** Candidate recovery is the most direct expected consequence of query normalization.

### H2: targeted top-rank quality

For the targeted normalization cohorts, E002 will increase mean NDCG@10 relative to E001.

### H3: regression control

On queries with normalization cohort `none`, E002 will not materially reduce aggregate NDCG@10 or Recall@50 relative to E001.

### H4: scope control

E002 is not expected to materially fix recency-only, semantic-paraphrase, or structured-field failures. Large gains there must be investigated for accidental intervention leakage rather than credited automatically to the hypothesis.

## Metrics

Use exactly the E001 metric definitions:

- Precision@10
- Recall@10
- Recall@50
- MRR
- DCG@10
- NDCG@10
- latency p50 and p95

For every quality metric record:

```text
delta = E002 - E001
```

Report deltas:

1. overall;
2. by benchmark scenario;
3. by difficulty;
4. by normalization cohort: `alias`, `initials`, `hyphenation`, `misspelling`, `multiple`, and `none`.

The cohort analysis is required because an aggregate metric can hide whether E002 helped the queries it was designed to change.

## Acceptance criteria

E002 is accepted as a useful controlled experiment when all of the following hold.

### A. Correctness gate

- All E001 tests continue to pass unchanged.
- Dedicated normalization tests pass for aliases, initials, hyphenation, misspellings, untouched queries, and unknown tokens.
- The original query evidence is preserved rather than silently replaced.
- No fuzzy, semantic, temporal, field-aware, or reranking behavior is introduced.

### B. Primary effectiveness gate

- Mean Recall@50 for the combined targeted-normalization cohort is **strictly higher** than E001.
- At least one targeted family shows a positive Recall@50 delta with inspectable per-query examples explaining the gain.

No minimum percentage gain is preregistered because we do not yet have an independently justified effect-size threshold. The observed delta must be reported rather than retrofitting a threshold after seeing results.

### C. Ranking-quality gate

- Mean targeted-cohort NDCG@10 must not decrease overall.
- Per-family regressions must be reported even if the combined cohort improves.

### D. Regression gate

For cohort `none`:

- NDCG@10 degradation must be no worse than **0.01 absolute** versus E001.
- Recall@50 degradation must be no worse than **0.01 absolute** versus E001.

The 0.01 bound is an engineering guardrail for preserving baseline behavior, not a statistical-significance claim.

### E. Latency gate

- Report p50 and p95 latency deltas.
- No hard millisecond pass/fail threshold is set for this in-memory synthetic experiment; any material increase must be explained by normalization work rather than ignored.

### F. Interpretation gate

Do not claim E002 solves failures outside its intervention. The final conclusion must distinguish:

- targeted gains;
- unchanged queries;
- regressions;
- remaining semantic, temporal, structural, and ranking failures.

## Required pre-run tests

`tests/search/test_query_normalization.py` locks the intended normalization semantics before E002 is run:

- alias expansion;
- dotted-initial normalization plus alias expansion;
- hyphenation expansion;
- known misspelling expansion;
- preservation of ordinary/unknown lexical terms.

These tests should be reviewed before connecting normalization to BM25.

## Retriever wiring

E002 is implemented as `QueryNormalizedBM25Retriever` in `packages/search/retrieval/normalized_bm25.py`. The wrapper owns query normalization and delegates indexing/scoring to the unchanged E001 `BM25Retriever`.

The E002 experiment config is `experiments/configs/005_query_normalized_bm25.yaml` with retrieval type `normalized_bm25`.

`tests/search/test_normalized_bm25.py` verifies targeted candidate recovery, unchanged ranking for the `none` cohort, distinct result provenance, and the alias/initial/hyphenation/misspelling integration path.

## Next implementation step

Add comparison tooling that joins E001 and E002 by query ID and reports per-query and cohort deltas. After smoke-query review, run the frozen 200-query E002 experiment.
