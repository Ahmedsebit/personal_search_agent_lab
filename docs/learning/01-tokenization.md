# Learning E001: Tokenization

This guide captures the first implementation step for the E001 BM25 baseline: converting email fields and query text into comparable tokens.

## Goal

The E001 tokenizer should be intentionally simple. It should:

1. lowercase text;
2. split text into letter-and-number tokens;
3. combine the searchable email fields;
4. preserve repeated tokens.

It should not add aliases, synonyms, spelling correction, stemming, or semantic interpretation. Those limitations must remain visible in the baseline.

## A minimal text tokenizer

```python
import re


def tokenize(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", text.lower())
```

Example:

```python
tokenize("Atlas: Ranking Update for Alice!")
```

Result:

```python
["atlas", "ranking", "update", "for", "alice"]
```

### Why lowercase?

Without lowercasing, `Ranking` and `ranking` would be treated as different terms. Capitalization should not determine lexical matching in E001.

### Why this regular expression?

The pattern `[a-z0-9]+` finds consecutive lowercase letters or digits. Punctuation acts as a separator and is not retained as a token.

Examples:

- `ranking-update` becomes `ranking`, `update`;
- `v2` remains `v2`;
- `report.pdf` becomes `report`, `pdf`.

## Combining email fields

An email is structured rather than a single string. For the first baseline, flatten the searchable fields into one text representation:

```python
def email_to_text(email: Email) -> str:
    parts = [
        email.sender,
        " ".join(email.recipients),
        email.subject,
        email.body,
        " ".join(email.attachment_names),
        " ".join(str(value) for value in email.metadata.values()),
    ]

    return " ".join(parts)


def tokenize_email(email: Email) -> list[str]:
    return tokenize(email_to_text(email))
```

This representation includes:

- sender;
- recipients;
- subject;
- body;
- attachment names;
- metadata values such as project, topic, and status.

The timestamp and internal IDs do not need to become lexical tokens for E001.

## Preserve repeated tokens

Do not convert the token list into a set.

For example:

```python
["atlas", "ranking", "ranking", "update"]
```

must retain both occurrences of `ranking`. BM25 later needs the raw term frequency in each document.

## Use the same tokenizer for queries

```python
query_tokens = tokenize("Atlas Ranking")
```

Result:

```python
["atlas", "ranking"]
```

Using the same tokenizer ensures queries and documents occupy the same lexical token space.

## Intentionally unsupported behavior

The tokenizer must not silently perform these transformations:

| Input | Canonical term | E001 behavior |
|---|---|---|
| `move-over` | `migration` | No semantic mapping |
| `OH` | `Omar Hassan` | No alias expansion |
| `rankng` | `ranking` | No spelling correction |
| `deployments` | `deployment` | No stemming or lemmatization |

These failures belong in the E001 measurements. Later experiments can add normalization and compare against the frozen baseline.

## Suggested tests

```python
def test_tokenize_lowercases_text():
    assert tokenize("Atlas RANKING") == ["atlas", "ranking"]


def test_tokenize_removes_punctuation():
    assert tokenize("ranking-update!") == ["ranking", "update"]


def test_tokenize_keeps_numbers():
    assert tokenize("report v2 2026") == ["report", "v2", "2026"]


def test_tokenize_preserves_repetition():
    assert tokenize("ranking ranking") == ["ranking", "ranking"]


def test_email_to_text_includes_searchable_fields(sample_email):
    text = email_to_text(sample_email).lower()
    assert sample_email.sender.lower() in text
    assert sample_email.subject.lower() in text
    assert sample_email.body.lower() in text
```

## Completion check

You are ready for indexing when you can explain:

- why documents and queries use the same tokenizer;
- why repeated tokens must be preserved;
- why punctuation is removed;
- why aliases, typo correction, and synonyms are deliberately omitted.
