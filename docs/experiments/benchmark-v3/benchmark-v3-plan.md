# Benchmark v3 — cleaned and extended (preregistered 2026-11-27)

**Builder:** `scripts/build_benchmark_v3.py` (two phases: draft → human check → finalize)
**Role:** the main benchmark **from E009 onward**. E003–E008 keep v1, so their preregistrations and the E002b parity check stay valid.

## Problems in v1 it fixes

| v1 problem (E003 audit) | v3 change |
| --- | --- |
| 200 queries but only 155 unique; one attachment query appears 14 times | Each unique query kept once (gold qrels unchanged). Removed IDs are listed in the card. Duplicates with different qrels would be kept and flagged; on the frozen v1 there are none. |
| Only 6 unique attachment queries | New `attachment_file` scenario (20): "attachment about …" and "spreadsheet / deck / document / pdf about …", from real attachment names |
| 0 recipient and 0 subject queries | E005's v2 recipient / subject / date-range queries are included, **only for scenarios validated by the U3 human check** |
| "latest" is the only time word | New `temporal_newest` (20: "newest", "most recent") and `temporal_oldest` (20: "earliest", "oldest", "first"). Grade 2 goes to the newest (or oldest) matching email; each query has at least 2 matching emails, so order matters |

## Rules

1. **Gold and silver are never mixed silently.** Every row has `qrels_type` (gold | silver) and `source` (v1 | v2 | v3). Results should be reported for gold only, silver only, and all.
2. **Every silver scenario must pass the U3 human check** (κ ≥ 0.60 and silver precision ≥ 0.80, at least 30 labelled pairs). Scenarios that fail are dropped at `--finalize`, and the card lists them.
3. **Freeze:** paste the final SHA-256 into `shared_data.yaml → benchmarks.v3.annotations_sha256`. `run_pipeline.py` refuses an unfrozen v3 outside smoke mode.
4. **Re-baseline before E009:** run the frozen control (as it stands after E008) on v3. That run is E009's retrieval, and the reference for any later experiment on v3.

## Steps

```powershell
python scripts\build_benchmark_v3.py --emails datasets\synthetic\emails.jsonl --v1-qrels datasets\benchmarks\judgments.jsonl
python scripts\make_label_sheet.py --annotations data\benchmark_v3\queries_v3_draft.csv --qrels data\benchmark_v3\qrels_v3_draft.jsonl `
    --only-silver --exclude-scenarios recipient subject date_range --emails datasets\synthetic\emails.jsonl --out data\benchmark_v3\label_audit
#   ...label data/benchmark_v3/label_audit/label_sheet.csv (about 60 queries' worth of pairs)...
python scripts\label_agreement.py --dir data\benchmark_v3\label_audit
python scripts\build_benchmark_v3.py --emails datasets\synthetic\emails.jsonl --v1-qrels datasets\benchmarks\judgments.jsonl --finalize `
    --label-audit data\benchmark_v2\label_audit\label_audit.json data\benchmark_v3\label_audit\label_audit.json
```

## Known limitations

- New silver qrels come from metadata (attachment names, sender, topic word, timestamp), and topic matching is literal. The human check is what makes them usable.
- "first" is read as "oldest". A query like "first draft of …" would be misread; the generator never produces one.
- The E003-T temporal lexicon does not include earliest/oldest/first. The `temporal_oldest` scenario is expected to expose that gap rather than reward it.
