"""Build a retrieval pipeline from YAML: frozen control + experiment stages.

pipeline:
  base: frozen_control            # read from experiments/frozen/frozen_control.yaml
  stages:                         # applied in order, each wraps the previous result
    - {type: synonym_expansion, bidirectional: true, mode: append}       # E004
    - {type: field_v2}                                                   # E005
    - {type: range_filter, reference_time: corpus_max}                  # E005
    - {type: dense, encoder: sentence_transformer}                       # E006 (replaces)
    - {type: hybrid_rrf, k: 60, depth: 100, encoder: sentence_transformer}  # E007
    - {type: rerank, scorer: cross_encoder, depth: 50}                   # E008
"""

from __future__ import annotations

import os
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

import yaml

from packages.search.pipeline.stages import (
    E003Stage,
    FilterStage,
    HybridRRFStage,
    QueryRewriteStage,
    Ranked,
    RerankStage,
    SearchOutput,
    Stage,
)
from packages.search.query.field_cues_v2 import _SUBJ, _TO, build_query_plan_v2
from packages.search.query.synonym_expansion import expand
from packages.search.retrieval.e003_retrievers import E003Retriever
from packages.search.retrieval.field_aware_bm25 import FieldAwareBM25
from packages.search.temporal.ranges import make_range_parser

if TYPE_CHECKING:
    from packages.search.retrieval.semantic_dense import DenseRetriever, Encoder

Config = dict[str, Any]


@dataclass
class Context:
    control_search: Callable[[str, int], Ranked]
    normalize: Callable[[str], str]
    tokenize: Callable[[str], list[str]]
    k1: float
    b: float
    field_docs: list[dict[str, str]]
    timestamps: dict[str, datetime | None]
    cache_dir: str = "runs/cache"
    _field_index: FieldAwareBM25 | None = None
    extras: dict[str, DenseRetriever] = field(default_factory=dict)

    @property
    def field_index(self) -> FieldAwareBM25:
        if self._field_index is None:
            self._field_index = FieldAwareBM25(
                self.field_docs, k1=self.k1, b=self.b, tokenize=self.tokenize
            )
        return self._field_index

    @property
    def docs_by_id(self) -> dict[str, dict[str, str]]:
        return {d["doc_id"]: d for d in self.field_docs}

    def corpus_max_time(self) -> datetime:
        return max(t for t in self.timestamps.values() if t is not None)


def load_frozen_control(path: str = "experiments/frozen/frozen_control.yaml") -> Config:
    with open(path, encoding="utf-8") as f:
        payload = yaml.safe_load(f)
    if not isinstance(payload, dict) or not isinstance(payload.get("current"), dict):
        raise ValueError("frozen control must contain a 'current' pipeline specification")
    current: Config = payload["current"]
    return current


def build_base(spec: Config, ctx: Context) -> Stage:
    arm = spec.get("e003_arm", "control")
    r = E003Retriever(
        arm,
        control_search=ctx.control_search,
        normalize=ctx.normalize,
        field_index=ctx.field_index if arm in ("e003_f", "e003_ft") else None,
        timestamps=ctx.timestamps if arm in ("e003_t", "e003_ft") else None,
        tokenize=ctx.tokenize,
    )
    stage: Stage = E003Stage(r)
    for s in spec.get("adopted_stages", []):  # stages adopted by later experiments (E004+)
        stage = apply_stage(stage, s, ctx)
    return stage


class FieldV2Stage:
    """Uses the v2 field plan only when a recipient/subject cue fires; otherwise delegates."""

    def __init__(self, inner: Stage, ctx: Context) -> None:
        self.inner, self.ctx = inner, ctx

    def search(self, query: str, top_k: int = 50) -> SearchOutput:
        if not (_TO.search(query) or _SUBJ.search(query)):
            r, m = self.inner.search(query, top_k)
            return r, dict(m, field_v2={"fired": False})
        plan = build_query_plan_v2(query, self.ctx.tokenize, normalize=self.ctx.normalize)
        return self.ctx.field_index.search_plan(plan.terms, top_k), {
            "stage": "field_v2",
            "field_v2": dict(plan.to_metadata(), fired=True),
        }


def make_encoder(name: str) -> Encoder:
    from packages.search.retrieval import semantic_dense as dense

    if name == "sentence_transformer":
        return dense.SentenceTransformerEncoder()
    if name == "hashing":
        if os.environ.get("E003_SMOKE") != "1":
            raise ValueError("hashing is a test encoder; set E003_SMOKE=1 for smoke runs")
        return dense.HashingEncoder()
    raise ValueError(name)


def dense_retriever(spec: Config, ctx: Context) -> DenseRetriever:
    from packages.search.retrieval.semantic_dense import DenseRetriever

    enc = spec.get("encoder", "sentence_transformer")
    key = f"dense:{enc}"
    if key not in ctx.extras:
        cache = None if enc == "hashing" else f"{ctx.cache_dir}/dense_{enc}.npy"
        ctx.extras[key] = DenseRetriever(ctx.field_docs, make_encoder(enc), cache)
    return ctx.extras[key]


def apply_stage(current: Stage, s: Config, ctx: Context) -> Stage:
    t = s["type"]
    if t == "synonym_expansion":
        bid, mode = s.get("bidirectional", True), s.get("mode", "append")
        return QueryRewriteStage(current, lambda q: expand(q, bid, mode), name="synonym_expansion")
    if t == "field_v2":
        return FieldV2Stage(current, ctx)
    if t == "range_filter":
        ref = s.get("reference_time", "corpus_max")
        ref = (
            ctx.corpus_max_time()
            if ref == "corpus_max"
            else datetime.fromisoformat(ref).astimezone(UTC)
        )
        return FilterStage(
            current,
            make_range_parser(ctx.timestamps, ref),
            depth=s.get("depth", 1000),
            name="range_filter",
        )
    if t == "dense":
        return dense_retriever(s, ctx)
    if t == "hybrid_rrf":
        return HybridRRFStage(
            [current, dense_retriever(s, ctx)],
            k=s.get("k", 60),
            depth=s.get("depth", 100),
            weights=s.get("weights"),
            names=["lexical", "dense"],
        )
    if t == "rerank":
        from packages.search.rerank import cross_encoder as ce

        scorer_name = s.get("scorer", "cross_encoder")
        scorer: ce.CrossEncoderScorer | ce.OverlapScorer
        if scorer_name == "cross_encoder":
            scorer = ce.CrossEncoderScorer(ctx.docs_by_id)
        elif scorer_name == "overlap":
            if os.environ.get("E003_SMOKE") != "1":
                raise ValueError("overlap is a test scorer; set E003_SMOKE=1 for smoke runs")
            scorer = ce.OverlapScorer(ctx.docs_by_id)
        else:
            raise ValueError(f"unknown rerank scorer {scorer_name!r}")
        return RerankStage(current, scorer, depth=s.get("depth", 50))
    raise ValueError(f"unknown stage type {t!r}")


def build_pipeline(
    pipeline_spec: Config,
    ctx: Context,
    frozen_path: str = "experiments/frozen/frozen_control.yaml",
) -> tuple[Stage, Config]:
    base = pipeline_spec.get("base", "frozen_control")
    base_spec = load_frozen_control(frozen_path) if base == "frozen_control" else base
    if not isinstance(base_spec, dict):
        raise ValueError("pipeline base must be 'frozen_control' or a pipeline specification")
    stage = build_base(base_spec, ctx)
    for s in pipeline_spec.get("stages", []):
        stage = apply_stage(stage, s, ctx)
    return stage, base_spec
