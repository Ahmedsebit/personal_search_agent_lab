# E002 learning guide: query normalization

E002 studies one narrow question: can we repair lexical surface-form mismatches before BM25 sees the query?

The normalization implementation begins in `packages/search/query/normalization.py`. It is wired into a **separate E002 retriever** and E001 remains unchanged.

## Preserve evidence, add compatibility

A normalization system can introduce mistakes. E002 therefore keeps the raw lexical evidence and adds explicitly known compatible forms.

Examples:

```text
rankng -> rankng + ranking
Dan    -> dan + daniel + kim
O.H.   -> oh + benchmark-owned alias terms
```

This differs from silently rewriting the query. The original tokens remain available to retrieval.

## Why rules are explicit

The benchmark generator already owns the alias and misspelling transformations. E002 mirrors only those controlled phenomena. We do not use fuzzy matching, external person knowledge, or a semantic model.

That keeps causal attribution understandable: if candidate recall improves, the change came from explicit lexical normalization.

## Four behaviors under test

### Aliases

Known benchmark aliases add their canonical-name tokens while retaining the alias token.

### Initials

Dotted initials are joined before token expansion. `O.H.` becomes `oh`, which can then participate in the benchmark alias map.

### Hyphenation

Explicit hyphenated forms can add split and joined forms, allowing lexical compatibility across formatting choices.

### Misspellings

Only known benchmark-produced misspellings add a canonical token. An unknown typo remains unknown.

## Cohorts

`normalize_query()` returns both the terms and the normalization cohorts that fired. Cohorts make E002 analysis possible without guessing after the experiment.

Possible labels currently include:

```text
alias
initials
hyphenation
misspelling
none
```

A query can activate more than one targeted behavior.

## Tests first

Run:

```bash
pytest tests/search/test_query_normalization.py -q
```

Then run the full suite:

```bash
pytest -q
```

Do not connect the normalizer to BM25 until these semantics are stable. That preserves E001 and gives E002 one clearly defined intervention.

## E002 wrapper

`QueryNormalizedBM25Retriever` performs normalization at search time, joins the normalized term tuple into the lexical query passed to the frozen BM25 implementation, and rewrites only the result `source` to identify E002 provenance. Indexing is delegated unchanged.

The `none`-cohort regression test compares E001 and E002 document IDs and scores directly for an ordinary query.
