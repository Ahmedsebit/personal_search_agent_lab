from __future__ import annotations

import argparse
from pathlib import Path

from packages.common.config import load_yaml
from packages.datasets.loader import load_dataset
from packages.eval.reporting import write_report
from packages.eval.runner import run_experiment
from packages.search.reranking.cross_encoder import TokenOverlapReranker
from packages.search.retrieval.bm25 import BM25Retriever
from packages.search.retrieval.dense import HashingDenseRetriever
from packages.search.retrieval.hybrid import ReciprocalRankFusionRetriever

parser = argparse.ArgumentParser()
parser.add_argument("--config", type=Path, required=True)
args = parser.parse_args()
config = load_yaml(args.config)
emails, queries, judgments = load_dataset(Path(config["dataset"]["root"]))
kind = config["retrieval"]["type"]
bm25 = BM25Retriever(); dense = HashingDenseRetriever()
if kind == "bm25": retriever = bm25
elif kind == "dense": retriever = dense
elif kind == "hybrid": retriever = ReciprocalRankFusionRetriever([bm25, dense])
else: raise ValueError(f"unsupported retrieval type: {kind}")
reranker = TokenOverlapReranker() if config.get("reranking", {}).get("enabled", False) else None
report = run_experiment(config["name"], retriever, emails, queries, judgments, int(config["retrieval"].get("top_k", 50)), reranker, int(config.get("reranking", {}).get("top_k", 10)))
json_path, md_path = write_report(report, Path(config["report"]["output_dir"]), config)
print(f"Wrote {json_path} and {md_path}")
for key, value in report.aggregate_metrics.items(): print(f"{key}: {value:.4f}")
