# E006 preregistration — dense retrieval alone (CPU-only)

**Status:** PREREGISTERED 2026-11-24
**Gates:** `e006-gates.yaml`
**Config:** `012_e006_dense.yaml`

## Treatment

- **Encoder:** `sentence-transformers/all-MiniLM-L6-v2` on CPU, maximum 256 tokens, normalized embeddings.
- **Search:** exact cosine (brute force), ties broken by document ID.
- **Document text:** subject, "from <sender>", attachment names, body.
- **Query:** raw text, without E002b normalization.
- **Caching:** embeddings are cached in `runs/cache/`.

E006 replaces the lexical system entirely. Its purpose is diagnostic: it shows whether dense retrieval carries the signal lexical retrieval misses. That decides whether E007 is worth running.

## Gates

| Gate | Hypothesis | Cohort | Requirement |
| --- | --- | --- | --- |
| **D-A** | Dense bridges paraphrase | paraphrase (96) | ΔNDCG@10 > 0 |
| **D-B** | Dense recovers missed documents | recall-limited paraphrase (60) | ΔRecall@50 > 0 |
| D-C | Not worse overall | all (200) | ΔNDCG@10 ≥ −0.01 |
| D-D | Not worse on people | person + person_topic (50) | ΔNDCG@10 ≥ −0.01 |
| D-E | E002b wins retained | 2 diagnostics | Each ≥ control − 0.01 |

## Decision rules

- **E007 proceeds if D-A or D-B passes.** Dense carries complementary signal even when dense alone isn't adoptable.
- **Dense alone becomes the control only if every gate passes.** That is not expected: names and IDs favour lexical retrieval, so D-D is likely to fail.


## Amendment U1–U3 (2026-11-27)

Gates added to `e006-gates.yaml` before any run. See `../u1-u3-amendment-preregistration.md`. Adds paraphrase-twin gates P-A (wording gap narrows) and P-B (worst wording improves), informational P-C (top-10 overlap), latency C-1 (p95 ≤ 150 ms) and cost-benefit C-2 (≥ 0.01 NDCG@10 per +100 ms).
