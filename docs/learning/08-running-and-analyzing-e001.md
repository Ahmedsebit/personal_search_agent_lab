# Running and analyzing E001 across all 200 queries

This step turns the BM25 implementation into a reproducible experiment. It runs the frozen E001 retriever over every benchmark query, calculates aggregate metrics, compares scenarios and difficulty levels, inspects the worst queries, and creates an explicit failure taxonomy.

## Commands

```bash
python scripts/generate_dataset.py --emails 2000 --queries 200 --seed 42 --output datasets
python scripts/run_experiment.py --config experiments/configs/001_bm25.yaml
python scripts/analyze_e001.py \
  --report experiments/results/e001-bm25-baseline.json \
  --dataset datasets \
  --output experiments/results/e001-bm25-analysis-v2.json
```

The final command writes both JSON and Markdown analysis files.

## Experiment sequence

For each query:

1. Retrieve the top 50 BM25 candidates.
2. Record the elapsed retrieval time.
3. Join results to graded relevance judgments.
4. Calculate Precision@10, Recall@10, Recall@50, MRR, DCG@10, and NDCG@10.
5. Save the per-query ranking and metrics.

After all queries, the runner averages metrics overall and by scenario. The analysis module then groups the same per-query measurements by difficulty.

## Reading the aggregate metrics

The current deterministic run produced:

```text
Precision@10  0.4955
Recall@10     0.3357
Recall@50     0.6876
MRR           0.6837
DCG@10       12.1986
NDCG@10       0.5956
```

The key comparison is Recall@10 versus Recall@50. Relevant material is frequently available deeper in the first-stage candidate set, which creates potential headroom for reranking. It does not imply reranking will solve semantic or candidate-generation failures.

## Scenario breakdown

NDCG@10 varies substantially by scenario:

```text
status         1.0000
mixed          0.8905
person         0.8800
attachment     0.5102
thread         0.4478
person_topic   0.4332
topic          0.3600
recency        0.2435
```

This prevents a reasonable aggregate score from hiding systematic weakness. Status queries fit exact lexical matching well. Recency queries require a temporal signal that E001 deliberately does not model.

## Difficulty breakdown

```text
          NDCG@10   Recall@50   MRR
easy       0.9484     0.8740   1.0000
medium     0.3740     0.5520   0.4695
hard       0.4204     0.6134   0.5419
```

Difficulty labels are benchmark metadata, not a mathematical guarantee that every hard query must score below every medium query. The counterintuitive medium/hard ordering is therefore a prompt to inspect scenario composition and query construction rather than rewrite labels after seeing results.

## Worst-query inspection

The analysis sorts queries by NDCG@10 and retains the worst 20. Examples with zero NDCG include:

- `messages about move-over`
- `architecture from O.H.`
- `latest Atlas move-over`
- `messages about quality measurement`
- `latest Quartz service disruption`
- `discussion about Quartz data protection`
- `move-over from OH`

For each bad query, inspect the query text, scenario, difficulty, Recall@50, retrieved IDs, judged grades, and failure labels. A zero NDCG with high Recall@50 means ordering failed; zero NDCG with near-zero Recall@50 means candidate generation failed.

## Failure taxonomy

`packages/eval/analysis.py` assigns transparent heuristic labels to low-NDCG queries. The labels are hypotheses based on scenario, benchmark metadata, query text, and measured recall. They are not manually verified ground truth.

Current categories include:

- **Temporal ordering not modeled:** recency intent cannot be fulfilled by lexical BM25 scoring alone.
- **Structural field flattened into text:** attachment/thread concepts are indexed as undifferentiated tokens instead of modeled fields.
- **Broad intent or lexical candidate gap:** too few judged relevant documents reach the top 50.
- **Hard-negative lexical competition or ordering failure:** useful candidates exist within 50, but lexical scoring orders them poorly.
- **Alias or ambiguous identity:** a surface name does not uniquely or directly match the intended person.
- **Misspelling not corrected:** baseline token equality cannot bridge spelling errors.
- **Semantic paraphrase gap:** intent and document wording differ lexically.
- **Unclassified lexical ranking failure:** evidence is insufficient for a more specific automatic label.

A query may receive more than one label, so taxonomy counts should not be summed as if categories were mutually exclusive.

## Latency interpretation

This run measured approximately:

```text
p50  1.348 ms
p95  9.376 ms
```

Treat these as run-specific observations, not production performance claims. Repeat measurements before drawing conclusions about tail latency.

## Analysis code

- `packages/eval/analysis.py`
  - calculates difficulty metrics;
  - labels low-NDCG failures;
  - builds taxonomy summaries;
  - extracts the worst queries.
- `scripts/analyze_e001.py`
  - loads the saved report and dataset metadata;
  - invokes the reusable analysis functions;
  - writes JSON and Markdown outputs.
- `tests/eval/test_analysis.py`
  - verifies difficulty grouping;
  - verifies recency failure classification.

## Evidence discipline

The benchmark is synthetic and deterministic. Results establish behavior on this designed benchmark, not organic enterprise-email search performance.

Keep E001 frozen after analysis. Do not quietly add recency, aliases, typo correction, field boosts, semantics, or reranking. Each improvement should become a separately configured experiment compared against this baseline.

## Next step

Create a reusable comparison report and then implement E002 as one controlled change. A suitable E002 is query normalization, with a narrow hypothesis about aliases or spelling variants and no other retrieval changes.
