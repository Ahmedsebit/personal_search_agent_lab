from __future__ import annotations

import argparse
from pathlib import Path

from packages.datasets.generator import build_dataset
from packages.datasets.loader import save_dataset

parser = argparse.ArgumentParser()
parser.add_argument("--emails", type=int, default=2000)
parser.add_argument("--queries", type=int, default=200)
parser.add_argument("--seed", type=int, default=42)
parser.add_argument("--output", type=Path, default=Path("datasets"))
args = parser.parse_args()
emails, queries, judgments = build_dataset(args.emails, args.queries, args.seed)
save_dataset(args.output, emails, queries, judgments)
print(f"Wrote {len(emails)} emails, {len(queries)} queries, and {len(judgments)} judgments to {args.output}")
