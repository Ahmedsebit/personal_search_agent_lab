"""Composable retrieval stages for E004–E008.

Every stage exposes   search(query: str, top_k: int) -> (ranked: [(doc_id, score)], meta: dict)
so experiments are built by wrapping the current frozen control, never by editing it.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import Protocol

from packages.search.retrieval.e003_retrievers import E003Retriever

Ranked = list[tuple[str, float]]
Metadata = dict[str, object]
SearchOutput = tuple[Ranked, Metadata]


class Stage(Protocol):
    def search(self, query: str, top_k: int = 50) -> SearchOutput: ...


class FunctionStage:
    """Adapts a plain search function (query, k) -> ranked into a stage."""

    def __init__(self, fn: Callable[[str, int], Ranked], name: str = "control") -> None:
        self.fn, self.name = fn, name

    def search(self, query: str, top_k: int = 50) -> SearchOutput:
        return list(self.fn(query, top_k))[:top_k], {"stage": self.name}


class E003Stage:
    """Adapts an E003Retriever (any arm) into a stage."""

    def __init__(self, retriever: E003Retriever) -> None:
        self.r = retriever

    def search(self, query: str, top_k: int = 50) -> SearchOutput:
        ranked, meta = self.r.search(query, top_k)
        return ranked, dict(meta, stage=f"e003:{self.r.arm}")


class QueryRewriteStage:
    """E004: rewrite the query, then delegate. Unchanged queries hit the inner stage verbatim."""

    def __init__(
        self,
        inner: Stage,
        rewrite: Callable[[str], tuple[str, Metadata]],
        name: str = "rewrite",
    ) -> None:
        self.inner, self.rewrite, self.name = inner, rewrite, name

    def search(self, query: str, top_k: int = 50) -> SearchOutput:
        new_q, info = self.rewrite(query)
        ranked, meta = self.inner.search(new_q, top_k)
        return ranked, dict(
            meta, **{self.name: dict(info, rewritten_query=new_q, changed=new_q != query)}
        )


class FilterStage:
    """E005: optional candidate filter (e.g. date range). Queries without a filter bypass it."""

    def __init__(
        self,
        inner: Stage,
        parse: Callable[[str], tuple[str, Callable[[str], bool] | None, Metadata]],
        depth: int = 1000,
        name: str = "filter",
    ) -> None:
        self.inner, self.parse, self.depth, self.name = inner, parse, depth, name

    def search(self, query: str, top_k: int = 50) -> SearchOutput:
        q, keep, info = self.parse(query)
        if keep is None:
            ranked, meta = self.inner.search(query, top_k)
            return ranked, dict(meta, **{self.name: dict(info, fired=False)})
        ranked, meta = self.inner.search(q, self.depth)
        kept = [(d, s) for d, s in ranked if keep(d)]
        return kept[:top_k], dict(
            meta,
            **{
                self.name: dict(
                    info, fired=True, stripped_query=q, before=len(ranked), after=len(kept)
                )
            },
        )


def rrf_fuse(
    lists: Sequence[Ranked], k: int = 60, weights: Sequence[float] | None = None
) -> Ranked:
    weights = list(weights or [1.0] * len(lists))
    score: dict[str, float] = {}
    for w, lst in zip(weights, lists, strict=True):
        for rank, (d, _) in enumerate(lst, start=1):
            score[d] = score.get(d, 0.0) + w / (k + rank)
    return sorted(score.items(), key=lambda kv: (-kv[1], kv[0]))


class HybridRRFStage:
    """E007: reciprocal-rank fusion of several stages."""

    def __init__(
        self,
        stages: Sequence[Stage],
        k: int = 60,
        depth: int = 100,
        weights: Sequence[float] | None = None,
        names: Sequence[str] | None = None,
    ) -> None:
        self.stages, self.k, self.depth, self.weights = list(stages), k, depth, weights
        self.names = names or [f"s{i}" for i in range(len(self.stages))]

    def search(self, query: str, top_k: int = 50) -> SearchOutput:
        lists, metas = [], {}
        for n, s in zip(self.names, self.stages, strict=True):
            r, m = s.search(query, self.depth)
            lists.append(r)
            metas[n] = m
        return rrf_fuse(lists, self.k, self.weights)[:top_k], {
            "stage": "hybrid_rrf",
            "k": self.k,
            "inputs": metas,
        }


class RerankStage:
    """E008: re-score the top `depth` of the inner stage. Items below depth keep their order,
    so Recall@depth is identical to the inner stage by construction."""

    def __init__(
        self,
        inner: Stage,
        scorer: Callable[[str, Sequence[str]], Sequence[float]],
        depth: int = 50,
        name: str = "rerank",
    ) -> None:
        self.inner, self.scorer, self.depth, self.name = inner, scorer, depth, name

    def search(self, query: str, top_k: int = 50) -> SearchOutput:
        ranked, meta = self.inner.search(query, max(top_k, self.depth))
        head, tail = ranked[: self.depth], ranked[self.depth :]
        if not head:
            return ranked[:top_k], dict(meta, stage=self.name)
        scores = list(self.scorer(query, [d for d, _ in head]))
        base_rank = {d: i for i, (d, _) in enumerate(head)}
        new = sorted(
            zip([d for d, _ in head], scores, strict=True),
            key=lambda kv: (-kv[1], base_rank[kv[0]]),
        )
        return (new + tail)[:top_k], dict(meta, stage=self.name, reranked=len(head))
