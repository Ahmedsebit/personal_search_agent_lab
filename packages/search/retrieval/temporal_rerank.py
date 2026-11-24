"""E003-T recency re-rank (preregistered, frozen 2026-11-24).

score = (1 - lambda) * lex_norm + lambda * rec
lex_norm: min-max of lexical score within the candidate set (all 1.0 if constant)
rec     : 1 - (time_rank - 1) / (n - 1), newest candidate = 1 (1.0 if n == 1)
time_rank ties broken by doc_id ascending; final ties by lexical score desc, then doc_id asc.
"""
from __future__ import annotations

from datetime import datetime
from typing import Mapping, Optional, Sequence, Tuple

FROZEN_LAMBDA = 0.30


def recency_rerank(candidates: Sequence[Tuple[str, float]], timestamps: Mapping[str, Optional[datetime]],
                   lam: float = FROZEN_LAMBDA) -> list:
    if not candidates:
        return []
    n = len(candidates)
    lex = {d: s for d, s in candidates}
    lo, hi = min(lex.values()), max(lex.values())
    lex_norm = {d: (1.0 if hi == lo else (s - lo) / (hi - lo)) for d, s in lex.items()}
    missing = [d for d in lex if timestamps.get(d) is None]
    if missing:
        raise ValueError(f"E003-T needs a timestamp for every candidate; missing for {missing[:5]} (Gate 0 G0-1)")
    by_time = sorted(lex, key=lambda d: (-timestamps[d].timestamp(), d))
    rec = {d: (1.0 if n == 1 else 1.0 - i / (n - 1)) for i, d in enumerate(by_time)}
    final = {d: (1.0 - lam) * lex_norm[d] + lam * rec[d] for d in lex}
    return sorted(((d, final[d]) for d in lex), key=lambda kv: (-kv[1], -lex[kv[0]], kv[0]))
