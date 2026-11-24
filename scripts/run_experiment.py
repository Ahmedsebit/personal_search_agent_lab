from __future__ import annotations

import argparse
from pathlib import Path

from packages.common.config import load_yaml
from packages.datasets.loader import load_dataset
from packages.eval.e002b_runner_support import RETRIEVER_TYPE, build_e002b_retriever
from packages.eval.reporting import write_report
from packages.eval.runner import run_experiment
from packages.search.indexing.indexer import tokenize
from packages.search.interfaces import Retriever
from packages.search.query.normalization import ALIASES, HYPHENATED, MISSPELLINGS
from packages.search.reranking.cross_encoder import TokenOverlapReranker
from packages.search.retrieval.bm25 import BM25Retriever
from packages.search.retrieval.context_aware_bm25 import ContextAwareBM25Retriever
from packages.search.retrieval.dense import HashingDenseRetriever
from packages.search.retrieval.hybrid import ReciprocalRankFusionRetriever
from packages.search.retrieval.normalized_bm25 import QueryNormalizedBM25Retriever

parser = argparse.ArgumentParser()
parser.add_argument("--config", type=Path, required=True)
args = parser.parse_args()
config = load_yaml(args.config)
emails, queries, judgments = load_dataset(Path(config["dataset"]["root"]))
kind = config["retrieval"]["type"]
bm25 = BM25Retriever()
dense = HashingDenseRetriever()
retriever: Retriever | ContextAwareBM25Retriever
if kind == "bm25":
    retriever = bm25
elif kind == "normalized_bm25":
    retriever = QueryNormalizedBM25Retriever()
elif kind == RETRIEVER_TYPE:
    known_full_names = tuple(
        sorted(
            {
                tuple(tokenize(name))
                for email in emails
                for name in (email.sender, *email.recipients)
            }
        )
    )
    retriever = build_e002b_retriever(
        {email.id: email.searchable_text for email in emails},
        config,
        aliases=ALIASES,
        known_full_names=known_full_names,
        misspellings=MISSPELLINGS,
        hyphenations=HYPHENATED,
    )
elif kind == "dense":
    retriever = dense
elif kind == "hybrid":
    retriever = ReciprocalRankFusionRetriever([bm25, dense])
else:
    raise ValueError(f"unsupported retrieval type: {kind}")
reranker = TokenOverlapReranker() if config.get("reranking", {}).get("enabled", False) else None
report = run_experiment(
    config["name"],
    retriever,
    emails,
    queries,
    judgments,
    int(config["retrieval"].get("top_k", 50)),
    reranker,
    int(config.get("reranking", {}).get("top_k", 10)),
)
json_path, md_path = write_report(report, Path(config["report"]["output_dir"]), config)
print(f"Wrote {json_path} and {md_path}")
for key, value in report.aggregate_metrics.items():
    print(f"{key}: {value:.4f}")
