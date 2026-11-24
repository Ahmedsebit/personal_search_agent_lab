# 13 — Running and validating E003

## What E003 changes

E001 scores an email as one bag of words. E003 asks two separate questions:

1. **Where** a word appears. A person's name in the *sender* field is stronger evidence for "emails from X" than the same name in the body. E003-F weights fields and routes the `from …` and `attachment about …` parts of a query to the fields they describe.
2. **When** the email was sent. "latest" is an instruction, not a topic word. E003-T removes it, retrieves as before, then nudges newer emails up within the top 50.

## Why there are three arms

If only the combined system were run, a gain couldn't be attributed. E003-F and E003-T isolate each mechanism. E003-FT tests whether they add up, interfere or reinforce each other, using the interaction value I.

## Why the control is re-run

The harness re-computes E002b and must reproduce the frozen per-query numbers exactly. This parity check proves three things: the wiring is right, the metrics are identical, and every delta reflects E003 alone.

## Reading the results

| Result | Meaning |
| --- | --- |
| **PASS** | Holds with duplicate queries counted each time and counted once |
| **PASS (fragile)** | Holds only while repeated queries are counted each time. It is usually driven by `attachment about Cedar move-over`, which appears ×14. A fragile result can't justify adoption. |
| **NULL_RESULT** | Nothing broke, but the target didn't improve. The audit predicted limited headroom, so this is a legitimate outcome. |
| **NOT EVALUABLE** | Gate 0 showed the benchmark can't measure that arm |

## What not to do

- Don't tune λ or the field weights after seeing results. That's a new experiment ID.
- Don't expect gains on the 60 paraphrase-limited queries. E004 targets those.
