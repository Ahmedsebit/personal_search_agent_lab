# 15 — Robustness, cost and label checks (U1–U3)

Three questions every result in this lab now has to answer, beyond "did the average go up?"

## 1. Does it give the same answer however you ask? (U1)

An average over 200 queries can rise while the system stays brittle. The twin benchmark asks each need twice, once in canonical wording and once reworded, with **the same correct answers**. So any difference in score is caused by wording alone.

We track two things together:

- **the gap** between the two wordings, which should shrink;
- **the worse of the two**, which should rise.

Watching only the gap would reward a system that got worse on the canonical wording ("levelling down"). Requiring the worse wording to improve rules that out.

## 2. Is the gain worth the time? (U2)

Dense search and cross-encoders cost time. A stage that adds 300 ms for +0.002 NDCG should not ship. Every run now records a CPU-only, warmed-up, median-of-3 latency per query plus a machine fingerprint. Two gates follow:

- a **latency budget** (p95);
- a **gain per +100 ms** threshold.

If quality passes but cost fails, the verdict is **HOLD_COST**: the stage is real but not ready. The next step is a cheaper variant under a new ID, not an argument about whether it "really" helped.

## 3. Are the answers in the answer key right? (U3)

E005's new queries have answers generated from metadata. Before trusting them, a person labels a blind sample, and we measure agreement:

- **Cohen's κ** corrects for chance agreement. 0.60 is "substantial".
- **Silver precision:** when the generated key says "relevant", how often does a person agree?

A scenario whose key fails is NOT EVALUABLE. E005 can't claim a win on an answer key nobody checked.

An LLM judge can be measured against the same human labels. To keep it affordable, each email is analysed once and that analysis is reused for every query it is judged against. The script measures the token saving instead of assuming it. The saving only appears when emails are judged several times, so on small samples it can be negative, and the report says so.
