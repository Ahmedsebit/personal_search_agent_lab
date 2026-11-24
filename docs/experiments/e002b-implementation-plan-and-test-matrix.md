# E002b Implementation Plan and Test Matrix

## Objective

Implement the preregistered E002b intervention: preserve E002 alias gains while suppressing alias expansion when an alias-like token belongs to a known explicit full-name phrase.

## Frozen components

E002b must not modify the corpus, relevance judgments, BM25 indexing/scoring, `k1`, `b`, top-k depth, deterministic ranking, misspelling rules, hyphenation rules, or initials behavior.

## Algorithm

1. Normalize dotted initials before ordinary tokenization.
2. Tokenize the query using the existing lexical convention.
3. Match benchmark-owned known full names using longest-match-first phrase matching.
4. Mark positions covered by those phrases as protected identity positions.
5. Iterate through query terms:
   - retain every original term;
   - suppress alias expansion at protected positions;
   - record a `SuppressedAlias` event with alias, phrase, reason, and token index;
   - otherwise apply the existing alias expansion.
6. Apply the otherwise-frozen misspelling and hyphenation rules.
7. Return stable, de-duplicated terms and observable cohort metadata.
8. Pass the resulting terms to the frozen E001 BM25 retriever in the integrated repository.

## Implementation boundary

The implementation belongs in the query-understanding layer. BM25 should not know about aliases, names, protected spans, or cohorts.

## Test matrix

| Area | Input | Expected behavior |
|---|---|---|
| Standalone alias | `emails from Ali` | Keep `ali`; add `alice`, `morgan`; cohort `alias`. |
| Historical collision 1 | `emails from Fatima Ali` | Keep `fatima`, `ali`; suppress `alice`, `morgan`; cohort `alias_collision`. |
| Historical collision 2 | `rollout from Fatima Ali` | Same suppression behavior; one suppression event. |
| Generalization | `updates from Miriam Dan` | Suppress `daniel`, `kim` because `Miriam Dan` is a known full name. |
| Existing alias | `spend plan from Ally` | Preserve E002 expansion to `alice`, `moreno`. |
| Initials | `architecture from O.H.` | Preserve dotted-initial normalization and existing `oh` expansion. |
| Misspelling | `latest rankng experiment` | Preserve original evidence and add `ranking`. |
| Hyphenation | `move-over from OH` | Preserve `move`, `over`, `moveover` variants and alias behavior. |
| Untouched query | `latest Atlas ranking` | Terms unchanged; no cohorts or suppression metadata. |
| Longest match | `mail from Dr Fatima Ali` | Protect the longest known phrase rather than the nested shorter name. |

## Integration tests to add when the full repository is restored

1. E002b and E002 rankings are identical for representative `none` queries.
2. E002b retains E002 ranking behavior for safe standalone aliases.
3. E002b improves the two historical `Fatima Ali` diagnostic rankings.
4. E002b result source is distinct and traceable.
5. Top-50 behavior is unchanged.
6. E002b-vs-E002 and E002b-vs-E001 comparison reports include `alias_collision` and `safe_alias` cohorts.
7. Every preregistered E002b gate is calculated from stable query-ID joins.

## Definition of done

- Unit and generalization tests pass.
- No BM25 code changes.
- E002 remains reproducible.
- Full integrated test suite passes after merging into the original repository.
- The 200-query benchmark is run only after pre-implementation tests pass.

## Implemented extension

The standalone package now also includes:

- `packages/search/retrieval/context_aware_bm25.py`: a separate E002b retriever;
- `packages/search/retrieval/simple_bm25.py`: a local frozen-style BM25 test double used because the historical repository is unavailable;
- `tests/search/test_context_aware_bm25.py`: retrieval integration tests;
- `packages/eval/e002b_comparison.py`: E002b cohort and gate tooling;
- `tests/eval/test_e002b_comparison.py`: query-ID join, cohort, summary, and gate tests.

When merged into the original repository, replace the local BM25 test double with the existing frozen E001 `BM25Retriever`; the E002b wrapper and its query-normalization boundary should remain unchanged.
