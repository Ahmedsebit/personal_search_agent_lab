"""E003-F field-weighted BM25 (BM25F-style), frozen 2026-11-24.

score(d) = sum_t idf(t) * tf~ * (k1 + 1) / (tf~ + k1)
tf~      = sum_f w_f(t) * tf_f(t, d) / (1 - b + b * len_f(d) / avglen_f)
idf(t)   = ln(1 + (N - df + 0.5) / (df + 0.5)), df over documents (any field)

k1 and b are inherited from the frozen E001 BM25; the IDF function can be
injected so it matches E001 exactly.
"""
from __future__ import annotations

import heapq
import math
from collections import Counter, defaultdict
from typing import Callable, Dict, Iterable, List, Mapping, Sequence, Tuple

from packages.search.query.field_cues import FIELDS, default_tokenize


def lucene_idf(n_docs: int, df: int) -> float:
    return math.log(1.0 + (n_docs - df + 0.5) / (df + 0.5))


class FieldAwareBM25:
    def __init__(self, documents: Iterable[Mapping], *, k1: float = 1.2, b: float = 0.75,
                 tokenize: Callable[[str], Sequence[str]] = default_tokenize,
                 idf: Callable[[int, int], float] = lucene_idf, fields: Sequence[str] = FIELDS):
        """documents: mappings with 'doc_id' and one text value per field name."""
        self.k1, self.b, self.idf_fn, self.fields = k1, b, idf, tuple(fields)
        self.tokenize = tokenize
        self.doc_ids: List[str] = []
        self.tf: Dict[str, Dict[str, Counter]] = {f: {} for f in self.fields}
        self.length: Dict[str, Dict[str, int]] = {f: {} for f in self.fields}
        self.postings: Dict[str, set] = defaultdict(set)
        for d in documents:
            did = str(d["doc_id"])
            self.doc_ids.append(did)
            for f in self.fields:
                toks = list(tokenize(d.get(f) or ""))
                self.tf[f][did] = Counter(toks)
                self.length[f][did] = len(toks)
                for t in set(toks):
                    self.postings[t].add(did)
        n = len(self.doc_ids) or 1
        self.n_docs = len(self.doc_ids)
        self.avglen = {f: (sum(self.length[f].values()) / n) or 1.0 for f in self.fields}

    def idf(self, term: str) -> float:
        return self.idf_fn(self.n_docs, len(self.postings.get(term, ())))

    def score_plan(self, plan: Sequence[Tuple[str, Mapping[str, float]]]) -> Dict[str, float]:
        scores: Dict[str, float] = defaultdict(float)
        for term, weights in plan:
            docs = self.postings.get(term)
            if not docs:
                continue
            idf = self.idf(term)
            for did in docs:
                tft = 0.0
                for f, w in weights.items():
                    if w == 0.0 or f not in self.tf:
                        continue
                    tf = self.tf[f][did].get(term, 0)
                    if tf:
                        norm = 1.0 - self.b + self.b * self.length[f][did] / self.avglen[f]
                        tft += w * tf / norm
                if tft > 0:
                    scores[did] += idf * tft * (self.k1 + 1.0) / (tft + self.k1)
        return scores

    def search_plan(self, plan, top_k: int = 50) -> List[Tuple[str, float]]:
        scores = self.score_plan(plan)
        return heapq.nsmallest(top_k, scores.items(), key=lambda kv: (-kv[1], kv[0]))
