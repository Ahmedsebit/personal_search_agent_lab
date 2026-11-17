# Learning E001: Inverted Statistics

After tokenization, BM25 needs statistics at two levels:

- **per document**: term frequency and document length;
- **across the corpus**: document frequency, document count, and average document length.

The most important distinction is that term frequency counts occurrences, while document frequency counts documents.

## Toy corpus

Use this small corpus to understand and test the index:

```python
documents = {
    "doc1": ["atlas", "ranking", "ranking", "update"],
    "doc2": ["atlas", "deployment", "update"],
    "doc3": ["falcon", "ranking", "review"],
}
```

## Term frequency

Term frequency asks:

> How many times does a term occur in one document?

Python's `Counter` represents this directly:

```python
from collections import Counter

term_frequency = Counter(documents["doc1"])
```

For `doc1`:

```python
{
    "atlas": 1,
    "ranking": 2,
    "update": 1,
}
```

Use raw counts. Do not divide by document length because BM25 applies its own length normalization and term-frequency saturation.

## Document length

Document length is the number of tokens, including repeated tokens:

```python
document_length = len(documents["doc1"])
```

Therefore:

- `doc1` has length 4;
- `doc2` has length 3;
- `doc3` has length 3.

## Document frequency

Document frequency asks:

> In how many documents does a term appear at least once?

For the toy corpus:

```python
{
    "atlas": 2,
    "ranking": 2,
    "update": 2,
    "deployment": 1,
    "falcon": 1,
    "review": 1,
}
```

When calculating document frequency, count a term at most once per document:

```python
for term in set(tokens):
    document_frequency[term] += 1
```

The set is required here because `ranking` appears twice in `doc1`, but `doc1` contributes only one document to `DF("ranking")`.

This yields two different meanings:

```text
TF("ranking", doc1) = 2 occurrences in doc1
DF("ranking")       = 2 documents in the corpus
```

## Number of documents

The corpus size is:

```python
num_documents = len(documents)
```

For the toy corpus, `N = 3`. BM25 later combines `N` with document frequency to calculate inverse document frequency.

## Average document length

Average document length is:

```python
average_document_length = (
    sum(document_lengths.values()) / num_documents
)
```

For lengths 4, 3, and 3:

```text
avgdl = (4 + 3 + 3) / 3
      = 10 / 3
      = 3.333...
```

BM25 uses this value to determine whether a document is unusually short or long relative to the corpus.

## Reference implementation shape

Write your own version, but the indexing logic should have this shape:

```python
from collections import Counter


def build_statistics(documents: dict[str, list[str]]):
    term_frequencies = {}
    document_lengths = {}
    document_frequency = Counter()

    for document_id, tokens in documents.items():
        term_frequencies[document_id] = Counter(tokens)
        document_lengths[document_id] = len(tokens)

        for term in set(tokens):
            document_frequency[term] += 1

    num_documents = len(documents)

    average_document_length = (
        sum(document_lengths.values()) / num_documents
        if num_documents > 0
        else 0.0
    )

    return (
        term_frequencies,
        document_lengths,
        document_frequency,
        num_documents,
        average_document_length,
    )
```

The empty-corpus guard prevents division by zero.

## Expected structures

### Term frequencies

```python
{
    "doc1": Counter({"ranking": 2, "atlas": 1, "update": 1}),
    "doc2": Counter({"atlas": 1, "deployment": 1, "update": 1}),
    "doc3": Counter({"falcon": 1, "ranking": 1, "review": 1}),
}
```

### Document lengths

```python
{
    "doc1": 4,
    "doc2": 3,
    "doc3": 3,
}
```

### Corpus statistics

```python
num_documents = 3
average_document_length = 10 / 3
```

## Connecting the statistics to emails

In the real index, documents are email objects:

```python
for email in emails:
    tokens = tokenize_email(email)

    term_frequencies[email.id] = Counter(tokens)
    document_lengths[email.id] = len(tokens)

    for term in set(tokens):
        document_frequency[term] += 1
```

After tokenization, the retrieval layer mainly sees a mapping from email ID to tokens. This separation means the same BM25 logic can operate on emails or other textual document types.

## Why BM25 needs each statistic

| Statistic | Question answered |
|---|---|
| `TF(t, d)` | How much does document `d` mention term `t`? |
| `DF(t)` | How common is `t` across the corpus? |
| `N` | How many documents are indexed? |
| `len(d)` | How long is this document? |
| `avgdl` | How long is a typical document? |

Two BM25 principles follow from these values:

1. Rare terms are usually more informative than terms appearing in nearly every document.
2. Repetition matters, but its benefit should saturate rather than grow without limit.

## Suggested tests

```python
def test_build_statistics():
    documents = {
        "doc1": ["atlas", "ranking", "ranking", "update"],
        "doc2": ["atlas", "deployment", "update"],
        "doc3": ["falcon", "ranking", "review"],
    }

    tf, lengths, df, n, avgdl = build_statistics(documents)

    assert tf["doc1"]["ranking"] == 2
    assert lengths["doc1"] == 4
    assert df["ranking"] == 2
    assert df["deployment"] == 1
    assert n == 3
    assert avgdl == 10 / 3


def test_empty_corpus():
    _, _, _, n, avgdl = build_statistics({})
    assert n == 0
    assert avgdl == 0.0
```

## Completion check

You are ready to calculate IDF when you can explain:

- why term frequency uses all tokens;
- why document frequency uses `set(tokens)`;
- why document length includes repeated tokens;
- why average document length is a corpus statistic;
- why rare terms should eventually receive more weight.

The next exercise is to calculate IDF manually for `ranking` and `deployment` using `N = 3`, then compare why the rarer term receives more weight.
