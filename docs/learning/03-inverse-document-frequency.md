# Learning E001: Inverse Document Frequency

Inverse document frequency, usually called **IDF**, converts corpus-wide document frequency into a term-importance weight.

The intuition is simple:

> A query term that appears in only a few documents is usually more useful for distinguishing relevant documents than a term that appears almost everywhere.

## Prerequisites

From the inverted-statistics step, we already have:

- `N`: the total number of indexed documents;
- `DF(t)`: the number of documents containing term `t` at least once.

IDF uses those two statistics. It does not use the number of times the term occurs inside one document. That is term frequency and enters a different part of BM25.

## Toy corpus

Continue with the same three documents:

```python
documents = {
    "doc1": ["atlas", "ranking", "ranking", "update"],
    "doc2": ["atlas", "deployment", "update"],
    "doc3": ["falcon", "ranking", "review"],
}
```

The corpus size is:

```text
N = 3
```

Relevant document frequencies are:

```text
DF("ranking")    = 2
DF("deployment") = 1
```

Although `ranking` occurs twice inside `doc1`, its document frequency remains 2 because it appears in two documents: `doc1` and `doc3`.

## BM25 IDF formula

A common BM25 IDF formula is:

```text
IDF(t) = ln(1 + (N - DF(t) + 0.5) / (DF(t) + 0.5))
```

Where:

- `t` is the term;
- `N` is the corpus size;
- `DF(t)` is the number of documents containing the term;
- `ln` is the natural logarithm.

The added `1` keeps the result positive. The `0.5` constants smooth the estimate, especially in small corpora and near the frequency extremes.

## Manual calculation for `ranking`

For `ranking`:

```text
N  = 3
DF = 2
```

Substitute into the formula:

```text
IDF("ranking")
= ln(1 + (3 - 2 + 0.5) / (2 + 0.5))
= ln(1 + 1.5 / 2.5)
= ln(1.6)
≈ 0.4700
```

`ranking` appears in two of the three documents, so it receives a modest weight.

## Manual calculation for `deployment`

For `deployment`:

```text
N  = 3
DF = 1
```

Substitute:

```text
IDF("deployment")
= ln(1 + (3 - 1 + 0.5) / (1 + 0.5))
= ln(1 + 2.5 / 1.5)
= ln(2.6667)
≈ 0.9808
```

`deployment` appears in only one document, so it receives more than twice the IDF weight of `ranking` in this toy corpus.

## Interpretation

| Term | Document frequency | Approximate IDF |
|---|---:|---:|
| `ranking` | 2 | 0.4700 |
| `deployment` | 1 | 0.9808 |

The rarer term is more discriminative. If the query contains `deployment`, only one document is a lexical candidate in this corpus. A match on `ranking` narrows the corpus less because two documents contain it.

IDF does not mean rare terms are automatically relevant. It means a match on a rare query term contributes more evidence to BM25 than a match on a common query term.

## Python implementation

```python
import math


def inverse_document_frequency(
    num_documents: int,
    document_frequency: int,
) -> float:
    if num_documents <= 0:
        return 0.0

    if document_frequency <= 0:
        return 0.0

    return math.log(
        1
        + (
            num_documents
            - document_frequency
            + 0.5
        )
        / (document_frequency + 0.5)
    )
```

Usage:

```python
ranking_idf = inverse_document_frequency(3, 2)
deployment_idf = inverse_document_frequency(3, 1)

assert ranking_idf < deployment_idf
```

## Looking up a term from the index

Once your index stores corpus statistics, an instance method could look like:

```python
def idf(self, term: str) -> float:
    df = self.document_frequency.get(term, 0)

    if df == 0:
        return 0.0

    return inverse_document_frequency(
        self.num_documents,
        df,
    )
```

An unseen term receives zero contribution because no indexed document can match it. This is different from estimating the theoretical rarity of an unseen word. The search engine cannot rank a document for a term that never occurs in the index.

## Common mistakes

### Mistake 1: Using total occurrence count instead of document frequency

Incorrect:

```python
df = sum(counter[term] for counter in term_frequencies.values())
```

This counts all occurrences. IDF needs the number of documents containing the term.

Correct:

```python
df = document_frequency[term]
```

### Mistake 2: Recalculating DF during every search

DF depends only on the indexed corpus. Calculate it during indexing and reuse it for every query.

### Mistake 3: Using query frequency as DF

A query containing the same word twice does not change corpus document frequency. Query frequency and corpus frequency are separate concepts.

### Mistake 4: Assuming the exact IDF formula is universal

Different BM25 implementations use slightly different IDF variants. Some formulas can produce negative values for terms appearing in more than half the corpus. For this lab, choose one formula, document it, test it, and keep it fixed across experiments.

### Mistake 5: Treating high IDF as proof of relevance

A rare term can still occur in an irrelevant document. IDF is one scoring signal, not a relevance judgment.

## Suggested tests

```python
import math


def test_rarer_term_has_higher_idf():
    ranking = inverse_document_frequency(3, 2)
    deployment = inverse_document_frequency(3, 1)

    assert deployment > ranking


def test_known_manual_values():
    assert math.isclose(
        inverse_document_frequency(3, 2),
        math.log(1.6),
    )

    assert math.isclose(
        inverse_document_frequency(3, 1),
        math.log(8 / 3),
    )


def test_empty_corpus_has_zero_idf():
    assert inverse_document_frequency(0, 0) == 0.0


def test_unseen_index_term_has_zero_contribution():
    assert inverse_document_frequency(3, 0) == 0.0
```

## Experiment with corpus size

Keep `DF = 1` and increase the corpus size:

```python
for n in [3, 10, 100, 1000]:
    print(n, inverse_document_frequency(n, 1))
```

The IDF grows because appearing once among 1,000 documents is more distinctive than appearing once among three documents.

Then hold `N = 100` and increase DF:

```python
for df in [1, 5, 20, 50, 90]:
    print(df, inverse_document_frequency(100, df))
```

The IDF decreases as the term becomes common.

These two experiments capture the relationship:

- larger `N` with fixed DF makes a term look rarer;
- larger DF with fixed `N` makes a term look more common.

## How IDF fits into BM25

IDF answers only the corpus-level question:

> How informative is this query term?

The remaining BM25 components answer document-level questions:

- How many times does the term occur in this document?
- Has the repeated-term benefit started to saturate?
- Is this document longer or shorter than the corpus average?

The complete BM25 term contribution will multiply IDF by a term-frequency and length-normalization component. Do not implement the full score until you are comfortable predicting which of two terms should have the higher IDF.

## Completion check

You are ready for the BM25 term-frequency component when you can explain:

- why `deployment` receives higher IDF than `ranking`;
- why IDF uses document frequency rather than total term count;
- why DF is computed once during indexing;
- why an unseen term contributes zero to retrieval;
- why the chosen IDF formula must remain fixed across experiments.

The next learning step is **term-frequency saturation and document-length normalization**, including the roles of `k1`, `b`, document length, and average document length.
