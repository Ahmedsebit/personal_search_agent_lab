# E005 preregistration — benchmark extension, recipient/subject routing and date ranges

**Status:** PREREGISTERED 2026-11-24, provisional control
**Gates:** `e005-gates.yaml`
**Config:** `011_e005_structure_ranges.yaml`

## Why

The E003 audit found zero recipient queries, zero subject queries and no date expressions other than "latest". E005 first extends the benchmark, then tests the mechanisms that need it.

## Step 1 — build and freeze benchmark v2 (before any treatment run)

`scripts/build_benchmark_v2.py` (seed 20261124) generates up to 25 queries each for three scenarios. Each query must have between 1 and 60 relevant emails.

| Scenario | Query form | Silver relevance |
| --- | --- | --- |
| recipient | `emails to <person>` | Person in to/cc. People on more than 50% of emails (the mailbox owner) are excluded. |
| subject | `subject: <subject>` | Exact subject = grade 2; all subject words present = grade 1 |
| date_range | `<topic> from last week`, `<topic> yesterday`, `<topic> last month`, `emails about <topic> this month`, `<topic> in <Month>` | Inside the range **and** topic word in subject/body |

The reference time is the newest email in the corpus, never the wall clock. After building, paste the printed SHA-256 into `shared_data.yaml`; the runner refuses an unfrozen v2.

## Step 2 — treatment

- **`field_v2`:** recipient and subject cues. It routes to the field index only when a v2 cue fires; otherwise the query goes to the frozen control.
- **`range_filter`:** a closed set of range expressions (today, yesterday, this/last week, this/last month, in Month, since/before/on a date). The expression is stripped, 1,000 candidates are retrieved, and only those inside the range are kept.

## Gates

| Gate | Component | Hypothesis | Cohort | Requirement |
| --- | --- | --- | --- | --- |
| R-0 | all | Original 200 queries unchanged | v1 all | Identical top 50 |
| **R-A** | field_v2 | Recipient routing helps | v2 recipient (n ≥ 15) | ΔNDCG@10 > 0 |
| R-B | field_v2 | Recipient recall not harmed | v2 recipient | ΔRecall@50 ≥ −0.01 |
| **R-C** | field_v2 | Subject routing helps | v2 subject (n ≥ 15) | ΔNDCG@10 > 0 |
| **R-D** | range_filter | Range filter improves ranking | v2 date_range (n ≥ 15) | ΔNDCG@10 > 0 |
| **R-E** | range_filter | Range filter improves precision | v2 date_range | ΔP@10 > 0 |
| R-F | range_filter | In-range recall kept | v2 date_range | ΔRecall@50 ≥ −0.01 |

**Decision:** each component is judged on its own gates plus R-0. A component with any gate below its minimum sample size is NOT EVALUABLE.

## Expectations

- **Date ranges:** a large gain is expected. The control cannot express ranges at all, and silver qrels reward exactly this behaviour, so this result shows correctness more than magnitude.
- **Subject queries:** these may already be near the ceiling for the control, because subject words are also lexical matches. A null result on R-C is plausible.
