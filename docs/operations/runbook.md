# Milestone 1 Runbook

## Dataset missing

Symptom: experiment runner cannot open JSONL files.

Action: run `python scripts/generate_dataset.py --emails 2000 --queries 200 --seed 42` from the
repository root.

## Import error

Install the project in editable mode with `pip install -e '.[dev]'`, or run repository scripts from
the repository root. Editable installation is preferred.

## Empty search API

The API loads the dataset during startup. Generate the dataset, then restart Uvicorn.

## Unexpected metric change

Check:

1. corpus seed and volume;
2. query and judgment files;
3. experiment configuration;
4. current code commit;
5. retrieval depth and reranking depth;
6. whether generated artifacts came from an older run.

## Slow experiments

Reduce corpus/query size for smoke testing. Do not present smoke-test values as final findings.

## Invalid or confounded run

Keep the raw file for diagnosis if useful, but label the run invalid and exclude it from comparative
claims. Never silently substitute a different configuration.
