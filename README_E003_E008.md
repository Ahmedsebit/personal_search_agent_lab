# E003-E009 workflow

The execution instructions are consolidated in the
[E001-E009 step-by-step guide](docs/experiments/step-by-step-e001-e008.md),
including setup, E002b, control parity, all experiment commands, expected
artifacts, and adoption checkpoints.

If E001-E002b are already reproduced and frozen, continue at
[Step 4 - E003](docs/experiments/step-by-step-e001-e008.md#step-4---e003-isolate-field-and-temporal-effects).

Supporting references:

- [E003 integration and wiring](E003_INTEGRATION.md)
- [E004-E009 preregistered roadmap](docs/experiments/e004-e008-roadmap.md)
- [Composable pipeline explanation](docs/learning/14-composable-pipeline-e004-e008.md)
- [Current frozen control](experiments/frozen/frozen_control.yaml)

## E009 and the U1-U3 amendment

The consolidated E001-E009 guide is the execution reference. The
[U1-U3 preregistration](docs/experiments/u1-u3-amendment-preregistration.md)
adds paraphrase-twin robustness, CPU latency/cost gates, and human validation
of silver labels before E004-E008 results can be adopted.

1. Build paraphrase twins with `python scripts\build_paraphrase_twins.py --qrels datasets\benchmarks\judgments.jsonl`.
2. Freeze the printed annotation hash under `benchmarks.pt` in
   `experiments\configs\shared_data.yaml`, then run both arms with `--benchmark pt`.
3. Follow the [robustness, cost and label guide](docs/learning/15-robustness-cost-and-label-checks.md)
   for timing and the E005 human-label audit. Time both arms back to back on the same idle machine.
4. Build, label and freeze [benchmark v3](docs/experiments/benchmark-v3/benchmark-v3-plan.md).
5. Follow the [E009 preregistration](docs/experiments/e009/e009-preregistration.md):

```powershell
python scripts\run_pipeline.py --config experiments\configs\015_e009_answers.yaml --arm control --benchmark v3
python scripts\run_e009.py --benchmark v3
```

E009 adds grounded answers, citations, layered judges, and planted-failure
evaluation. The default answerer is deterministic and offline; optional LLM
providers are for synthetic lab data only.
