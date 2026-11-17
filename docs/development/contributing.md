# Contributing

## Change discipline

1. Write or update a hypothesis for behavior-changing work.
2. Add tests before changing shared metric or interface behavior.
3. Keep generated datasets and experiment outputs out of source control unless intentionally added
   as a reviewed fixture or published result.
4. Preserve backward-compatible interfaces when possible.
5. Record architectural decisions in `docs/decisions`.

## Pull-request checklist

- [ ] Tests pass.
- [ ] Ruff passes.
- [ ] Mypy passes for affected packages.
- [ ] Public functions and non-obvious decisions are documented.
- [ ] Dataset/config/model version is captured for any reported result.
- [ ] No confidential data, secrets, tokens, or proprietary artifacts are included.
- [ ] Experiment conclusions match the evidence and mention limitations.

## Commit suggestions

Use focused commits such as:

- `feat(search): add BM25 retrieval baseline`
- `feat(eval): implement NDCG at K`
- `docs(experiment): add E003 hybrid hypothesis`
- `test(dataset): verify deterministic generation`
