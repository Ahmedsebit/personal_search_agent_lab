# Full BM25 scoring and ranked search

This step combines the statistics from the previous guides into E001's complete lexical retriever. The implementation lives in `packages/search/retrieval/bm25.py`; the focused behavioral tests live in `tests/search/test_bm25_learning.py`.

## Learning objectives

By the end, you should be able to explain BM25 without reciting the equation:

- **IDF:** rare corpus terms are more discriminative and therefore receive more weight.
- **TF saturation:** repetition helps, but each extra occurrence adds less evidence than the previous one.
- **`k1`:** controls how quickly repetition saturates. A larger value lets repeated occurrences matter for longer.
- **`b`:** controls the strength of document-length normalization. `b=0` disables it; `b=1` applies full normalization.
- **Length normalization:** long documents contain more words and therefore have more opportunities to match by chance. BM25 compensates for that advantage.

## The score

For every unique query term, E001 computes:

```text
term contribution = IDF(term) * saturated_tf_and_length_component(term, document)
document score = sum(term contributions)
```

The positive IDF variant is:

```text
ln(1 + (N - df + 0.5) / (df + 0.5))
```

The saturated TF and length component is:

```text
tf * (k1 + 1)
-----------------------------------------------
tf + k1 * (1 - b + b * document_length / avgdl)
```

E001 uses `k1=1.5` and `b=0.75`.

## Code structure

### `inverse_document_frequency`

Uses corpus-level `N` and `df`. Lower `df` produces a higher IDF, so a rare term such as a project codename contributes more than an extremely common term such as “meeting.”

### `term_frequency_component`

Uses `tf`, document length, average document length, `k1`, and `b`. The numerator grows with TF, but TF also appears in the denominator, creating diminishing returns.

At `tf=1` and `document_length=avgdl`, the component is exactly `1`. This is a useful correctness check.

### `bm25_term_score`

Multiplies IDF by the TF/length component. A term absent from a document has `tf=0` and contributes zero.

### `BM25Retriever.index`

The index stores:

- per-document term frequencies;
- document frequencies;
- document lengths;
- average document length;
- postings from each term to matching document indexes.

The postings structure lets search score only documents containing at least one query term.

### `BM25Retriever.search`

Search performs these steps:

1. Tokenize the query with the same tokenizer used for documents.
2. Deduplicate query terms because E001 does not model query term frequency.
3. Union the postings lists to identify candidates.
4. Sum BM25 term contributions for every candidate.
5. Remove zero-score candidates.
6. Sort by descending score.
7. Break equal-score ties by document ID for reproducibility.
8. Return the requested top-k results with one-based ranks.

## Why the behavioral tests matter

The tests establish properties, not just one memorized numeric value:

1. A rare term scores more than a common term when other inputs are equal.
2. Increasing TF increases the score, but the incremental gain gets smaller.
3. A shorter document scores more than a longer document when TF is equal.
4. Setting `b=0` removes that document-length difference.
5. Increasing `k1` lets repetition influence the score for longer.
6. An absent query term contributes zero.

Run them with:

```bash
pytest tests/search/test_bm25_learning.py -q
```

## Deliberate E001 boundaries

Do not add these features to this baseline:

- stemming or lemmatization;
- synonym or alias expansion;
- typo correction;
- field boosts;
- recency scoring;
- query term-frequency weighting;
- dense semantic similarity;
- reranking.

Those changes belong in separately named experiments so E001 remains a stable lexical baseline.

## Explanation checkpoint

A concise explanation is:

> BM25 gives rare terms more weight through IDF. Within a document, repeated occurrences increase relevance evidence with diminishing returns. `k1` controls the speed of that saturation. `b` controls how strongly document length is normalized. Length normalization prevents long documents from winning merely because they contain more words and therefore have more chances to match.

## Next step

Run the complete 200-query benchmark, inspect aggregate and scenario-level ranking metrics, and classify the worst queries. The next learning guide should explain Precision, Recall, MRR, DCG/NDCG, and latency before interpreting E001's results.
