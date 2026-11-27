"""U2 — latency and cost-benefit measurement.

Run files written by scripts/run_pipeline.py carry `latency_ms` (median of R timed repeats)
after a warm-up) and, at top level, `timing` = {machine fingerprint, warm-up, repeats, build_ms}.
Latency gates compare two runs ONLY if they were timed on the same machine fingerprint.
"""

from __future__ import annotations

import hashlib
import os
import platform
import socket
from typing import Any

Record = dict[str, Any]


def machine_fingerprint() -> Record:
    fp: Record = {
        "system": platform.system(),
        "machine": platform.machine(),
        "processor": platform.processor(),
        "cpu_count": os.cpu_count(),
        "python": platform.python_version(),
        "host_hash": hashlib.sha256(socket.gethostname().encode()).hexdigest()[:12],
        "cuda_visible_devices": os.environ.get("CUDA_VISIBLE_DEVICES"),
    }
    fp["id"] = hashlib.sha256(repr(sorted((k, v) for k, v in fp.items())).encode()).hexdigest()[:16]
    return fp


def percentile(xs: list[float], p: float) -> float:
    s = sorted(xs)
    if not s:
        return float("nan")
    i = (len(s) - 1) * p / 100.0
    lo, hi = int(i), min(int(i) + 1, len(s) - 1)
    return s[lo] + (s[hi] - s[lo]) * (i - lo)


def latency_summary(per_query: list[Record]) -> Record:
    xs = [q["latency_ms"] for q in per_query if q.get("latency_ms") is not None]
    return {
        "n": len(xs),
        "p50": percentile(xs, 50),
        "p95": percentile(xs, 95),
        "mean": sum(xs) / len(xs) if xs else None,
    }


def comparable(a_timing: Record | None, b_timing: Record | None) -> str | None:
    """None if comparable, else the reason they are not."""
    if not a_timing or not b_timing:
        return "run file has no timing block (re-run with the U2 runner)"
    if a_timing["machine"]["id"] != b_timing["machine"]["id"]:
        return "control and treatment were timed on different machines"
    return None


def latency_gate(g: Record, ctrl_pq: list[Record], trt_pq: list[Record]) -> Record:
    """Check all supplied max_ms, max_added_ms and max_ratio limits for p50 or p95."""
    st = g.get("stat", "p95")
    c, t = latency_summary(ctrl_pq)[st], latency_summary(trt_pq)[st]
    checks = {}
    if "max_ms" in g:
        checks["max_ms"] = t <= g["max_ms"]
    if "max_added_ms" in g:
        checks["max_added_ms"] = (t - c) <= g["max_added_ms"]
    if "max_ratio" in g:
        checks["max_ratio"] = (t / c if c > 0 else float("inf")) <= g["max_ratio"]
    return {
        "control_ms": c,
        "treatment_ms": t,
        "added_ms": t - c,
        "checks": checks,
        "passed": all(checks.values()),
    }


def gain_per_latency_gate(
    g: Record, quality_delta: float, ctrl_pq: list[Record], trt_pq: list[Record]
) -> Record:
    """Require min_gain_per_100ms of quality per added median latency (free if not slower)."""
    added = latency_summary(trt_pq)["p50"] - latency_summary(ctrl_pq)["p50"]
    if added <= g.get("free_below_ms", 1.0):
        return {
            "added_p50_ms": added,
            "gain": quality_delta,
            "gain_per_100ms": None,
            "passed": True,
            "note": "not slower (within free_below_ms); no cost-benefit test needed",
        }
    gp = quality_delta / (added / 100.0)
    return {
        "added_p50_ms": added,
        "gain": quality_delta,
        "gain_per_100ms": gp,
        "passed": gp >= g["min_gain_per_100ms"],
    }
