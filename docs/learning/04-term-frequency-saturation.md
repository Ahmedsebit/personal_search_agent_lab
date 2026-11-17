# Learning E001: Term-Frequency Saturation and Document-Length Normalization

IDF answers a corpus-level question: **how informative is a query term?** The next part of BM25 answers two document-level questions:

1. How strongly does this document match the term?
2. Should that evidence be adjusted because the document is unusually long or short?

BM25 handles these through **term-frequency saturation** and **document-length normalization**.

## Why raw term frequency is not enough

Suppose the query contains `ranking` and the corpus has three documents:

```text
docA: ranking appears 1 time
docB: ranking appears 4 times
docC: ranking appears 40 times
```

A raw-count score would make `docC` forty times stronger than `docA`. That is usually excessive. Repeating a word can provide more evidence that a document concerns the term, but each additional occurrence should add less value than the previous one.

This is called **saturation**.

BM25's term-frequency component rises quickly at first and then flattens. Moving from zero occurrences to one matters greatly. Moving from one to two can still matter. Moving from forty to forty-one should matter very little.

## The BM25 term component

For one query term `t` and one document `d`, use:

```text
TF_component(t, d)
=
TF(t, d) × (k1 + 1)
-----------------------------------------------
TF(t, d) + k1 × (1 - b + b × len(d) / avgdl)
```

The complete contribution of that term is:

```text
term_score(t, d) = IDF(t) × TF_component(t, d)
```

Where:

- `TF(t, d)` is the term count in the document;
- `len(d)` is the document length in tokens;
- `avgdl` is the average document length;
- `k1` controls term-frequency saturation;
- `b` controls document-length normalization.

Common starting values are:

```python
k1 = 1.5
b = 0.75
```

These are baseline choices, not universal constants. Keep them fixed in E001 and record them in the experiment configuration.

## First isolate term-frequency saturation

To see saturation without a length effect, assume:

```text
len(d) = avgdl
```

Then:

```text
1 - b + b × len(d) / avgdl = 1
```

So the component simplifies to:

```text
TF × (k1 + 1)
----------------
TF + k1
```

With `k1 = 1.5`:

| TF | Saturated TF component |
|---:|---:|
| 0 | 0.0000 |
| 1 | 1.0000 |
| 2 | 1.4286 |
| 4 | 1.8182 |
| 10 | 2.1739 |
| 40 | 2.4096 |

The score increases, but not linearly. Increasing TF from 1 to 2 adds about 0.43. Increasing TF from 10 to 40 adds only about 0.24 despite thirty additional occurrences.

The upper limit approaches `k1 + 1`, which is 2.5 when `k1 = 1.5`.

## What `k1` controls

`k1` sets how quickly repeated-term benefit saturates.

- A **smaller `k1`** causes faster saturation. The first occurrence matters, but additional repetitions add little.
- A **larger `k1`** allows repeated occurrences to keep adding value for longer.

When `TF = 1` and document length equals average length, the component evaluates to 1 regardless of `k1`. The parameter primarily changes what happens as TF increases.

For E001, avoid tuning `k1` after observing benchmark results. That would turn a simple baseline into an optimized model and weaken the meaning of later comparisons.

## Why normalize document length?

Long documents naturally contain more words and therefore more opportunities to repeat query terms. Without normalization, a long email thread or verbose message could outrank a concise, focused email merely because it contains more text.

Consider:

```text
short document: 20 tokens, ranking appears twice
long document:  200 tokens, ranking appears twice
```

The same TF of 2 represents a denser signal in the short document. BM25 can therefore reduce the long document's contribution.

The length adjustment is:

```text
1 - b + b × len(d) / avgdl
```

If a document has average length, the adjustment is 1.

- If `len(d) < avgdl`, the adjustment is below 1 and the denominator becomes smaller, increasing the score.
- If `len(d) > avgdl`, the adjustment is above 1 and the denominator becomes larger, decreasing the score.

## What `b` controls

`b` determines how strongly document length affects scoring.

### `b = 0`

```text
1 - 0 + 0 × len(d) / avgdl = 1
```

Document length is ignored entirely.

### `b = 1`

```text
1 - 1 + 1 × len(d) / avgdl = len(d) / avgdl
```

Full BM25 length normalization is applied.

### `b = 0.75`

This common baseline value applies substantial, but not complete, length normalization.

## Manual comparison: short versus long document

Use:

```text
TF = 2
k1 = 1.5
b = 0.75
avgdl = 100
```

### Short document

```text
len(d) = 50
```

Length adjustment:

```text
1 - 0.75 + 0.75 × 50 / 100
= 0.25 + 0.375
= 0.625
```

Term component:

```text
2 × 2.5
--------------------
2 + 1.5 × 0.625

= 5 / 2.9375
≈ 1.7021
```

### Long document

```text
len(d) = 200
```

Length adjustment:

```text
1 - 0.75 + 0.75 × 200 / 100
= 0.25 + 1.5
= 1.75
```

Term component:

```text
2 × 2.5
-------------------
2 + 1.5 × 1.75

= 5 / 4.625
≈ 1.0811
```

The two documents have the same term frequency, but the short document receives the stronger contribution because the term occupies a larger share of its content.

## Python implementation

```python
def saturated_term_frequency(
    term_frequency: int,
    document_length: int,
    average_document_length: float,
    k1: float = 1.5,
    b: float = 0.75,
) -> float:
    if term_frequency <= 0:
        return 0.0

    if average_document_length <= 0:
        return 0.0

    length_adjustment = (
        1
        - b
        + b * document_length / average_document_length
    )

    numerator = term_frequency * (k1 + 1)
    denominator = (
        term_frequency
        + k1 * length_adjustment
    )

    return numerator / denominator
```

The term's full BM25 contribution then becomes:

```python
def bm25_term_score(
    idf: float,
    term_frequency: int,
    document_length: int,
    average_document_length: float,
    k1: float = 1.5,
    b: float = 0.75,
) -> float:
    return idf * saturated_term_frequency(
        term_frequency=term_frequency,
        document_length=document_length,
        average_document_length=average_document_length,
        k1=k1,
        b=b,
    )
```

## Connecting the calculation to the index

For a term and document ID:

```python
tf = self.term_frequencies[document_id].get(term, 0)
document_length = self.document_lengths[document_id]
idf = self.idf(term)

score = bm25_term_score(
    idf=idf,
    term_frequency=tf,
    document_length=document_length,
    average_document_length=self.average_document_length,
    k1=self.k1,
    b=self.b,
)
```

If `tf` is zero, the contribution is zero. You do not need to score documents that do not contain any query term in a lexical baseline.

## Summing multiple query terms

For a query such as:

```text
atlas ranking
```

calculate one contribution for `atlas` and another for `ranking`, then sum them:

```text
BM25(query, document)
= score("atlas", document)
+ score("ranking", document)
```

A document matching both terms will normally score higher than a document matching only one, but IDF, TF saturation, and length normalization determine the exact difference.

For this baseline, process each unique query term once. Query-term frequency is not required for the standard simple implementation used here.

## Common mistakes

### Mistake 1: Multiplying raw TF directly by IDF

```python
score = tf * idf
```

This creates linear term-frequency growth and omits length normalization.

### Mistake 2: Dividing TF by document length before BM25

Do not pre-normalize TF. BM25's denominator already performs its own controlled length adjustment.

### Mistake 3: Using corpus size instead of average document length

Length normalization uses `len(d) / avgdl`, not `len(d) / N`.

### Mistake 4: Replacing document length with unique-token count

Document length is the total number of tokens, including repetitions.

### Mistake 5: Allowing an empty corpus to produce division errors

If `avgdl` is zero, return zero or prevent search before a valid index exists.

### Mistake 6: Tuning `k1` and `b` inside E001

E001 should remain a stable baseline. Parameter tuning belongs in a separately named experiment.

## Suggested tests

```python
import math


def test_zero_frequency_has_zero_score():
    assert saturated_term_frequency(
        term_frequency=0,
        document_length=100,
        average_document_length=100,
    ) == 0.0


def test_tf_increases_with_diminishing_returns():
    score_1 = saturated_term_frequency(1, 100, 100)
    score_2 = saturated_term_frequency(2, 100, 100)
    score_10 = saturated_term_frequency(10, 100, 100)

    assert score_2 > score_1
    assert score_10 > score_2
    assert (score_2 - score_1) > (score_10 - score_2) / 8


def test_average_length_tf_one_equals_one():
    score = saturated_term_frequency(
        term_frequency=1,
        document_length=100,
        average_document_length=100,
        k1=1.5,
        b=0.75,
    )

    assert math.isclose(score, 1.0)


def test_short_document_scores_above_long_document():
    short = saturated_term_frequency(2, 50, 100)
    long = saturated_term_frequency(2, 200, 100)

    assert short > long


def test_b_zero_disables_length_normalization():
    short = saturated_term_frequency(2, 50, 100, b=0.0)
    long = saturated_term_frequency(2, 200, 100, b=0.0)

    assert math.isclose(short, long)


def test_manual_short_document_value():
    score = saturated_term_frequency(
        term_frequency=2,
        document_length=50,
        average_document_length=100,
        k1=1.5,
        b=0.75,
    )

    assert math.isclose(score, 5 / 2.9375)
```

## Small exploration exercises

### Exercise 1: Hold length constant and vary TF

```python
for tf in [0, 1, 2, 4, 10, 40]:
    print(tf, saturated_term_frequency(tf, 100, 100))
```

Confirm that scores rise but approach a ceiling.

### Exercise 2: Hold TF constant and vary length

```python
for length in [25, 50, 100, 200, 400]:
    print(length, saturated_term_frequency(2, length, 100))
```

Confirm that longer documents receive lower scores when `b > 0`.

### Exercise 3: Disable normalization

Repeat Exercise 2 with `b=0`. Every document should receive the same component because length no longer matters.

### Exercise 4: Compare `k1`

Calculate the TF series with `k1` values of 0.5, 1.5, and 3.0. Observe that larger values saturate more slowly.

## Completion check

You are ready to implement full BM25 document scoring when you can explain:

- why raw term counts must not grow linearly forever;
- how `k1` changes the saturation rate;
- why longer documents are normalized;
- how `b=0` disables length normalization;
- why `len(d)` counts all tokens rather than unique terms;
- how IDF and the saturated TF component combine into one term score;
- why scores for multiple query terms are summed.

The next learning step is **full BM25 scoring and ranked search**: tokenize a query, find candidate documents, sum term contributions, sort by descending score, and return the top results.
