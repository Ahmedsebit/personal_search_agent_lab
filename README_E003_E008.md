# Personal Search & Agent Lab — E003 to E008 add-on

This integrated package contains everything after frozen E002b: E003 (field-aware and temporal) and E004–E008 (synonyms, benchmark extension, dense, hybrid, re-ranking). The repository's earlier retrievers remain unchanged. The new semantic dense implementation lives in `semantic_dense.py` so the existing dependency-light `HashingDenseRetriever` is preserved.

## Order of work

Each step starts only after the previous decision is recorded.

| Step | Do | Then |
| --- | --- | --- |
| 0 | `python -m pip install -e ".[dev]"`, then `pytest -q`. The E003 and shared configs already use `datasets/synthetic/emails.jsonl`, `datasets/benchmarks/judgments.jsonl`, and the repository's E002b control factory. | — |
| 1 | **E003:** follow `E003_INTEGRATION.md` (Gate 0 → control parity → arms → `compare_e003.py`) | Set `e003_arm` in `experiments/frozen/frozen_control.yaml`; add a history line |
| 2 | **E004:** run `010_e004_synonyms.yaml` control + treatment, then `evaluate_prereg.py --prereg docs/experiments/e004/e004-gates.yaml` | If ADOPT_CANDIDATE, append `{type: synonym_expansion, bidirectional: true, mode: append}` to `adopted_stages` |
| 3 | **E005:** `build_benchmark_v2.py` → paste the hash into `shared_data.yaml` → run control + treatment on v1 **and** v2 → evaluate | Append each adopted component (`field_v2`, `range_filter`) |
| 4 | `python -m pip install -e ".[models]"` for CPU model runs; this also enables model downloads. | — |
| 5 | **E006:** run dense control + treatment → evaluate | Proceed to E007 if D-A or D-B passes |
| 6 | **E007:** run control, treatment and dense_only (plus v2 if frozen) → evaluate | If adopted, append `{type: hybrid_rrf, k: 60, depth: 100, encoder: sentence_transformer}` |
| 7 | **E008:** run control + treatment → evaluate | If adopted, append `{type: rerank, scorer: cross_encoder, depth: 50}` |

### Command pattern for E004–E008

```powershell
python scripts\run_pipeline.py --config experiments\configs\010_e004_synonyms.yaml --arm control
python scripts\run_pipeline.py --config experiments\configs\010_e004_synonyms.yaml --arm treatment
python scripts\evaluate_prereg.py --prereg docs\experiments\e004\e004-gates.yaml
# E005 adds:  --benchmark v2   (run both arms on v1 and v2)
# E007 adds:  --arm dense_only
```

Results are written to `docs/experiments/e00N/results/e00N-results.md`, which holds the gate table, verdict and per-component verdicts.

## Safeguards

- **Control parity:** while the frozen control is still E002b, the v1 control run must reproduce the frozen per-query numbers. If it doesn't, the run stops.
- **Hash checks:** the v1 annotation hash is fixed, and the v2 hash must be pasted in before v2 can be used.
- **Provenance:** every run file records the exact frozen control, pipeline, tokenizer, k1/b source and annotation hash.
- **Smoke mode:** `E003_SMOKE=1` lets the plumbing run on made-up data. Every output is then stamped "SMOKE RUN — NOT VALID EVIDENCE".

On PowerShell, enable smoke mode with `$env:E003_SMOKE = "1"` and clear it afterward
with `Remove-Item Env:E003_SMOKE`. Hashing encoders and overlap scorers in the new
pipeline are restricted to this mode; they cannot stand in for the preregistered
models in an evidence run.

## Where things are

| Path | What |
| --- | --- |
| `docs/experiments/e004-e008-roadmap.md` | Sequence, shared rules, stated limitations |
| `docs/experiments/e00N/e00N-preregistration.md` and `e00N-gates.yaml` | Each experiment's preregistration; the gates are machine-readable |
| `packages/search/pipeline/` | Composable stages and the YAML pipeline builder |
| `packages/search/query/synonym_expansion.py` | E004 |
| `packages/search/query/field_cues_v2.py`, `packages/search/temporal/ranges.py` | E005 |
| `packages/search/retrieval/semantic_dense.py` | E006; the original `dense.py` is preserved |
| `packages/search/pipeline/stages.py` (`HybridRRFStage`) | E007 |
| `packages/search/rerank/cross_encoder.py` | E008 |
| `packages/eval/prereg_gates.py`, `scripts/evaluate_prereg.py` | Generic gate engine |
| `scripts/build_benchmark_v2.py` | E005 benchmark extension |
| `experiments/frozen/frozen_control.yaml` | The current control |
