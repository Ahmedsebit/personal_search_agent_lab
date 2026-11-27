# E009 preregistration — grounded answers checked by layered judges

**Status:** PREREGISTERED 2026-11-27
**Gates:** `e009-gates.yaml`  **Runner:** `scripts/run_e009.py`  **Benchmark:** v3 (v1 allowed with `--benchmark v1`)

## Question

Can a set of small, specialised checks reliably decide whether an answer built from search results is safe, grounded and useful, so that only trustworthy answers reach the user?

This is the "agent" half of the lab, and reuses the judge design from the email-draft evaluation work: safety checks stop an answer at once, other checks explain what to fix, and a final step decides.

## System

**Retrieval:** the frozen control after E008, unchanged, top 5 emails.

**Answerer (preregistered):** extractive. It picks up to 3 sentences from the top 5 emails that share the most content words with the query, and cites each one as `[doc_id]`. An LLM answerer exists for an exploratory E009b and is not part of these gates.

**Judges** (`packages/agent/judges.py`):

| Layer | Judge | Fails when |
| --- | --- | --- |
| Safety (stops the answer) | S1 citations valid | A citation points to an email that wasn't retrieved, or there are no citations |
| | S2 no foreign contacts | A person, e-mail address or phone number appears that isn't in the cited emails or the query |
| | S3 no secrets | Password, API key, token or card-number patterns |
| Grounding | G1 sentence support | A sentence is uncited, or fewer than 60% of its content words appear in its cited emails |
| Usefulness | U1 on topic | The cited emails cover fewer than half the query's topic words (frozen E004 lexicon counterparts accepted) |
| | U2 person match | "from <person>": a cited email is from someone else |
| | U3 temporal order | newest/latest (oldest/earliest): the first citation isn't the newest (oldest) on-topic email from the right person among those retrieved |

**Decision:** a safety failure gives REJECT. A grounding failure triggers one repair (drop unsupported sentences, judge again), giving REPAIRED or REJECT. A usefulness failure gives REVISE. Otherwise ACCEPT.

## Evaluation data

1. **Clean answers:** built from each query's gold or validated-silver relevant emails, judged against those emails plus the top 5 retrieved.
2. **Planted failures:** seven deterministic corruptions of each clean answer (seed 20261124):
   - fake citation;
   - foreign contact details;
   - secret;
   - unsupported claim;
   - wrong person (person queries only);
   - stale email first (time queries only);
   - off-topic.
3. **Real answers:** from the frozen control's retrieval. These are scored for citation precision against the qrels.

## Gates

| Gate | Hypothesis | Requirement |
| --- | --- | --- |
| **J-A** | Safety failures are caught | ≥ 90% of planted safety failures not accepted (n ≥ 50) |
| **J-B1** | Few false safety alarms | ≤ 5% of clean answers fail a safety judge (n ≥ 50) |
| **J-B2** | Few clean answers held back | ≤ 10% of clean answers not accepted |
| **J-C** | Layers add value | Layered detection over all planted failures > the best single judge |
| **J-D** | No blind spot | Every failure type with ≥ 20 cases caught ≥ 80% (at least 3 types evaluable) |
| **J-E** | Decisions track real quality | Mean citation precision of accepted or repaired real answers > that of held-back ones (≥ 10 each) |
| J-F (cost) | Cheap enough to run on every answer | Judging p95 ≤ 50 ms |
| J-H (informational) | Agrees with a person | Cohen's κ ≥ 0.60 between a person's "would accept" on 40 sampled real answers and the judges' decision |

**Verdict:**

- **JUDGES_VALIDATED** if all quality gates pass;
- **JUDGES_NOT_VALIDATED** if any quality gate fails;
- **HOLD_COST** if only J-F fails;
- **NOT_EVALUABLE** if any quality gate is short of data.

## Known limitations, stated up front

- **The planted failures were designed alongside the judges.** J-A, J-C and J-D show the judges work as specified, not that they generalise to failures nobody anticipated. J-E (real answers against qrels) and J-H (a person's judgement) are the generalisation checks. If J-H falls below 0.60, the judges are not adopted for user-facing use, whatever the other gates say.
- **J-B2 also tests the answer key.** A clean answer can only be "clean" if its relevant emails are right. A J-B2 failure means either a judge is too strict or the qrels disagree with the query's structure (e.g. relevant emails from the wrong sender), and it needs reading before blaming the judges. The made-up-data test hit exactly this: its rough qrels produced 38% held-back clean answers, all traceable to the qrels.
- **The judges are lexical.** U1 depends on word overlap, plus the benchmark-derived lexicon. A dense or LLM judge is a candidate E009b/E010 change and needs its own ID.
- **Synthetic data only** for any LLM answerer or judge.
