# Synthetic Dataset and Benchmark Design

## Why synthetic data

Synthetic data allows the repository to be public, deterministic, and free from workplace or
personal confidentiality concerns. It also provides known latent structure for relevance labels.

## Corpus structure

The default target is 2,000 emails spanning:

- 30 fictional people;
- 10 fictional projects;
- multiple topics and lifecycle statuses;
- threads, timestamps, and attachments;
- intentionally repeated vocabulary and ambiguous relationships.

## Query scenarios

- `person`: sender-oriented query
- `topic`: topical retrieval
- `person_topic`: multiple explicit constraints
- `recency`: temporal intent over project and topic
- `attachment`: evidence should include an attachment
- `thread`: retrieve members of a discussion thread
- `status`: project lifecycle state or decision
- `mixed`: person, topic, status, and recency constraints

## Benchmark cautions

Generated queries can be easier than organic user queries because they share vocabulary with the
corpus. Results should therefore be described as engineering baselines, not claims of real-world
search quality.

Planned benchmark improvements include paraphrases, misspellings, aliases, harder negatives,
conflicting constraints, and independently reviewed labels.
