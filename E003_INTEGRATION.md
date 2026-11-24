# E003 integration — field-aware and temporal lexical retrieval

This package is integrated into the Personal Search & Agent Lab repository. It adds E003 without changing the frozen E001, E002 or E002b retrieval algorithms.

## New files

```text
packages/search/query/temporal_intent.py          E003-T detector (closed lexicon)
packages/search/query/field_cues.py               E003-F cue routing → field-aware query plan
packages/search/retrieval/field_aware_bm25.py     BM25F-style scorer (inherits k1, b, tokenizer)
packages/search/retrieval/temporal_rerank.py      Recency re-rank, λ = 0.30
packages/search/retrieval/e003_retrievers.py      The arms: control | e003_f | e003_t | e003_ft
packages/search/retrieval/e003_wiring.py          Binds the frozen E002b retriever, normalizer and tokenizer
packages/search/data/e003_corpus.py               Loads emails, qrels and annotations in any common format
packages/eval/e003_metrics.py                     Metrics + control-parity check
packages/eval/e003_comparison.py                  Preregistered gates, de-duplication, bootstrap, verdicts
scripts/audit_e003_corpus.py                      Gate 0
scripts/run_e003.py                               Runs one arm
scripts/compare_e003.py                           Evaluates every gate → results JSON and markdown
experiments/configs/000_e003_control.yaml
experiments/configs/007_e003_f.yaml
experiments/configs/008_e003_t.yaml
experiments/configs/009_e003_ft.yaml
tests/search/test_temporal_intent.py
tests/search/test_field_cues.py
tests/search/test_field_aware_bm25.py
tests/search/test_temporal_rerank.py
tests/search/test_e003_retrievers.py
tests/eval/test_e003_metrics.py
tests/eval/test_e003_annotations.py
tests/eval/test_e003_comparison.py
docs/experiments/e003/                            Audit, preregistration, parameters, annotations, implementation notes
docs/learning/13-running-and-validating-e003.md
```

The `__init__.py` files are empty. Skip any that would overwrite an existing one.

## Three things to verify before running

Every config file has a `control:` block binding the existing frozen E002b pieces:

```yaml
factory: packages.search.retrieval.e003_repository:build_control
normalizer: control
tokenizer: packages.search.retrieval.bm25:tokenize
```

The factory reuses E002b's aliases, known corpus identities, and BM25 parameters. `normalizer: control` uses that same retriever's normalizer. Data paths are already configured for `datasets/synthetic/emails.jsonl` and `datasets/benchmarks/judgments.jsonl`. Only change them when using a different corpus.

You cannot get this wrong silently. The **control parity check** compares the harness's control metrics with the frozen E002b values for every one of the 200 queries. If they don't reproduce, the run stops, and no E003 number is reported against a wrongly wired control.

## Run order

```powershell
python -m pip install -e ".[dev]"
python -m pytest -q tests\search tests\eval

python scripts\audit_e003_corpus.py `
  --emails datasets\synthetic\emails.jsonl `
  --qrels datasets\benchmarks\judgments.jsonl `
  --annotations docs\experiments\e003\e003-query-annotations.csv `
  --out runs\e003\gate0-corpus-audit.json

python scripts\run_e003.py --config experiments\configs\000_e003_control.yaml # parity PASS required
python scripts\run_e003.py --config experiments\configs\007_e003_f.yaml # if Gate 0 allows F
python scripts\run_e003.py --config experiments\configs\008_e003_t.yaml # if Gate 0 allows T
python scripts\run_e003.py --config experiments\configs\009_e003_ft.yaml # if Gate 0 allows both

python scripts\compare_e003.py --runs runs\e003 --out docs\experiments\e003\results
```

`compare_e003.py` writes `e003-results.md`, which has the gate table, interaction table, mechanism predictions and final decision. Per-arm JSON files go next to it.

Each arm is run **once**. The parameters are frozen, and `run_e003.py` refuses to run if the annotation file's hash differs from the preregistered one.
