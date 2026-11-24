# E002b: Context-Aware Alias Normalization

## Status

**Pre-implementation / preregistration.**

E002 remains frozen. E002b is a new controlled experiment motivated by the alias-collision failure observed in E002. E002b must not modify or reinterpret historical E002 outputs.

## Motivation

E002 showed that query normalization can improve lexical retrieval while leaving untouched queries invariant. The strongest gains came from alias expansion, but the same mechanism also produced substantial regressions when an alias token appeared as part of a different explicit full name.

The clearest example was `Ali`:

- as a standalone alias, expanding `Ali` toward `Alice Morgan` can improve retrieval;
- inside `Fatima Ali`, the same expansion adds misleading `Alice` and `Morgan` evidence.

This suggests that alias expansion should depend on query context rather than token identity alone.

## Research Question

> Can context-aware alias expansion preserve the retrieval gains of E002 while preventing harmful expansion when an alias-like token is embedded in an explicit full-name phrase?

## Controlled Change

E002b changes **only alias-expansion eligibility**.

Everything else remains frozen relative to E002:

- corpus and relevance judgments;
- E001 BM25 indexing and scoring;
- BM25 `k1` and `b` parameters;
- top-k retrieval depth;
- initials handling;
- hyphenation handling;
- misspelling rules;
- evaluation metrics;
- deterministic result ordering.

E002b must implement a **general context rule**, not query-ID-specific or `Fatima Ali`-specific exceptions.

## Proposed Behavioral Rule

The experiment should distinguish a standalone alias use from an alias-like token embedded in an explicit person-name phrase.

Expected behavior:

```text
emails from Ali
    -> alias expansion allowed

spend plan from Ally
    -> alias expansion allowed

architecture from O.H.
    -> existing initials/alias behavior retained

emails from Fatima Ali
    -> standalone Ali expansion suppressed

rollout from Fatima Ali
    -> standalone Ali expansion suppressed
```

The implementation may use phrase/context recognition available from the benchmark-owned identity vocabulary. It must not hard-code benchmark query IDs or special-case only the two known failing strings.

---

# Hypotheses

## H1: Alias candidate-recall retention

**Hypothesis:** Context-aware alias normalization will retain the candidate-recall benefit established by E002 for queries where alias expansion remains appropriate.

### Primary metric

- Recall@50 on the **safe-alias cohort**: queries where E002 alias expansion is still eligible under the E002b context rule.

### Expected direction

E002b Recall@50 should not materially regress relative to E002 on this cohort.

### Why this matters

Suppressing unsafe expansion is easy if we simply disable alias expansion broadly. H1 prevents E002b from solving precision errors by throwing away the recall benefit that motivated E002.

---

## H2: Alias-collision correction

**Hypothesis:** E002b will improve retrieval quality relative to E002 for queries where an alias-like token occurs inside an explicit full name and E002 previously over-expanded it.

### Primary metric

- NDCG@10 on the **alias-collision cohort**.

### Secondary metric

- Recall@50 on the alias-collision cohort.

### Expected direction

Both NDCG@10 and Recall@50 should improve relative to E002 at the cohort level.

### Known diagnostic examples

- `emails from Fatima Ali`
- `rollout from Fatima Ali`

These examples motivate the experiment but must not be the implementation rule. The cohort should be defined by the general context condition.

---

## H3: Preserve successful E002 alias ranking gains

**Hypothesis:** E002b will not materially degrade ranking quality on alias queries that improved under E002 and do not represent alias collisions.

### Primary metric

- NDCG@10 on the safe-alias cohort.

### Secondary metrics

- MRR
- Recall@50

### Expected direction

Safe-alias NDCG@10 should remain within a small regression guardrail relative to E002.

This specifically protects useful E002 behavior such as standalone aliases and ambiguous short forms that the experiment intentionally still supports.

---

## H4: Untouched-query invariance

**Hypothesis:** Queries unaffected by E002b alias-context logic will retain E002 behavior.

### Metrics

- NDCG@10
- Recall@50

### Expected direction

The `none` cohort should remain effectively invariant.

This is the isolation check. If unrelated queries change, E002b is modifying more than the intended alias-context boundary.

---

## H5: Scope discipline

**Hypothesis:** E002b should not be credited with solving failure classes outside context-sensitive alias normalization.

E002b does **not** attempt to solve:

- recency or temporal ranking;
- semantic paraphrase mismatch;
- field-aware ranking;
- attachment or thread structure;
- general fuzzy matching;
- learned entity resolution;
- dense retrieval;
- reranking.

Any movement on those cases is incidental unless a causal connection to the preregistered alias-context intervention is demonstrated.

---

# Cohorts

E002b reporting should include at least:

## 1. `alias_collision`

Queries where an alias-like token appears in a context that identifies it as part of an explicit full-name phrase and E002 would otherwise expand it as a standalone alias.

## 2. `safe_alias`

Queries where alias expansion remains eligible under the E002b rule.

## 3. `other_targeted`

Queries affected by E002 normalization families other than the alias-context change, such as initials or hyphenation. Their behavior should remain unchanged unless alias handling also applies.

## 4. `none`

Queries untouched by E002/E002b normalization.

## 5. `all_queries`

The full 200-query benchmark, used for overall reporting but **not** as a substitute for targeted cohort analysis.

---

# Acceptance Criteria

E002b is accepted only if **all required quality gates pass**.

## Gate A: Alias-collision NDCG improvement

**PASS if:**

```text
mean NDCG@10(E002b, alias_collision)
    > mean NDCG@10(E002, alias_collision)
```

This is the primary correction gate.

---

## Gate B: Alias-collision Recall@50 non-regression

**PASS if:**

```text
Delta Recall@50(E002b - E002, alias_collision) >= 0
```

Ideally Recall@50 improves, but E002b must at minimum avoid making candidate recall worse while correcting ranking precision.

---

## Gate C: Safe-alias Recall@50 retention

**PASS if:**

```text
Delta Recall@50(E002b - E002, safe_alias) >= -0.01
```

The 0.01 threshold is an engineering guardrail, not a significance threshold.

This gate prevents the experiment from eliminating E002's recall gains by becoming overly conservative.

---

## Gate D: Safe-alias NDCG@10 retention

**PASS if:**

```text
Delta NDCG@10(E002b - E002, safe_alias) >= -0.01
```

Again, 0.01 is a preregistered practical guardrail rather than a statistical-significance claim.

---

## Gate E: Untouched NDCG@10 invariance

**PASS if:**

```text
Delta NDCG@10(E002b - E002, none) >= -0.01
```

Because the intervention is narrow, the ideal observed delta is exactly zero.

---

## Gate F: Untouched Recall@50 invariance

**PASS if:**

```text
Delta Recall@50(E002b - E002, none) >= -0.01
```

The ideal observed delta is exactly zero.

---

## Gate G: Historical E002 regression cases corrected individually

The two motivating E002 regressions are retained as **diagnostic guardrails**, not as the definition of the algorithm.

For each of:

- `emails from Fatima Ali`
- `rollout from Fatima Ali`

require:

```text
NDCG@10(E002b) > NDCG@10(E002)
```

and:

```text
Recall@50(E002b) >= Recall@50(E002)
```

Passing these cases alone is not sufficient for experiment acceptance. Gates A-F must also pass.

---

# Comparison Plan

E002b should be evaluated against both historical systems:

| Comparison | Purpose |
|---|---|
| E002b vs E002 | Measures whether context awareness fixes E002's alias over-expansion without losing E002 gains. |
| E002b vs E001 | Shows the final net value relative to the original frozen BM25 baseline. |

The primary acceptance gates use **E002 as the control**, because E002b changes the alias policy introduced by E002.

E001 remains useful for confirming that E002b still provides net value over raw BM25.

---

# Metrics

Continue using the same ranking metrics as E001/E002:

- Precision@10
- Recall@10
- Recall@50
- MRR
- DCG@10
- NDCG@10
- latency p50/p95 as descriptive run-specific observations

Primary E002b decision metrics are:

1. alias-collision NDCG@10;
2. alias-collision Recall@50;
3. safe-alias Recall@50;
4. safe-alias NDCG@10;
5. untouched-cohort NDCG@10 and Recall@50.

---

# Required Pre-Implementation Tests

Before running the benchmark, add behavioral tests for at least these classes.

## Expansion allowed

```text
emails from Ali
spend plan from Ally
architecture from O.H.
```

## Expansion suppressed because alias token belongs to explicit full name

```text
emails from Fatima Ali
rollout from Fatima Ali
```

## No normalization behavior changed

Include representative ordinary queries that belong to the `none` cohort and verify E002 and E002b produce identical normalized terms/rankings.

## Generalization test

Add at least one synthetic full-name case beyond `Fatima Ali` where a surname or name token overlaps with an alias vocabulary entry. This is important to demonstrate that the algorithm encodes a general context rule rather than a special-case fix derived from the observed regressions.

---

# Decision Rule

## Accept E002b

Accept if all required Gates A-G pass and test evidence confirms that the implementation uses a general context-aware rule.

## Reject E002b

Reject if the collision cases improve only by materially sacrificing the safe-alias gains, or if unrelated queries regress beyond the guardrails.

## Inconclusive

Mark the experiment inconclusive rather than accepted when the alias-collision cohort is too small to support a cohort-level conclusion beyond the known diagnostic cases. In that situation, expand the **synthetic benchmark before rerunning**, using preregistered generative rules for alias/full-name collisions rather than hand-picking examples based on desired outcomes.

---

# Interpretation Boundaries

If E002b passes, the supported conclusion is:

> Context-aware alias eligibility can reduce harmful lexical over-expansion while retaining the benefits of explicit query normalization in this benchmark.

Do **not** conclude that E002b implements general entity resolution or solves arbitrary name ambiguity. It is still an explicit, benchmark-owned lexical normalization strategy.

---

# Planned Learning Outcome

E001 taught how BM25 uses lexical evidence.

E002 taught that adding lexical evidence through query normalization can materially improve retrieval.

E002b is intended to teach the next principle:

> More query evidence is not always better. Query expansion must consider precision, ambiguity, and context because BM25 will faithfully score misleading terms just as it scores useful ones.
