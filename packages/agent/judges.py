"""E009 — layered answer judges (deterministic baseline).

Layer 1 SAFETY (fail-fast: a failure stops the answer, later layers are skipped)
  S1 citations_valid     at least one citation; all point to retrieved emails
  S2 no_foreign_contacts names and contacts must occur in the cited emails or query
  S3 no_secrets          no password / API key / token / card-number patterns
Layer 2 GROUNDING
  G1 sentence_support    each sentence is cited and has >= SUPPORT word coverage
Layer 3 USEFULNESS
  U1 on_topic            cited emails cover topic words (E004 lexicon counterparts accepted)
  U2 person_match        "from <person>": every cited email is from that person
  U3 temporal_order      first citation is the newest (oldest), as requested,
                         on-topic retrieved email from the right person
Decision
  S fails -> REJECT; G1 fails -> drop unsupported sentences once, then recheck
  any U fails -> REVISE ; otherwise ACCEPT
"""

from __future__ import annotations

import re
from collections.abc import Callable, Collection, Iterable, Sequence
from datetime import datetime
from typing import Any

from packages.agent.answer import Answer, content_words, doc_text, render
from packages.search.query.synonym_expansion import LEXICON

SUPPORT = 0.6
Record = dict[str, Any]
Judgment = tuple[bool, str] | tuple[bool, str, list[int]]
EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+")
PHONE_RE = re.compile(r"(?<!\w)\+?\d[\d\s().-]{7,}\d(?!\w)")
SECRET_RES = [
    re.compile(p, re.I)
    for p in (
        r"\b(password|passcode|passwd|pwd)\s*[:=]\s*\S+",
        r"\b(api[_ -]?key|secret|token)\s*[:=]\s*\S+",
        r"\bsk-[A-Za-z0-9]{16,}\b",
        r"\bAKIA[0-9A-Z]{16}\b",
        r"(?<!\d)(?:\d[ -]?){13,16}(?!\d)",
    )
]
NEWEST = re.compile(r"\b(latest|newest|most recent|recent)\b", re.I)
OLDEST = re.compile(r"\b(earliest|oldest|first)\b", re.I)
FROM = re.compile(r"\bfrom\s+(.+?)\s*$", re.I)
COUNTERPART = {**{p: c for p, c in LEXICON.items()}, **{c: p for p, c in LEXICON.items()}}
LAYERS = {
    "S1": "safety",
    "S2": "safety",
    "S3": "safety",
    "G1": "grounding",
    "U1": "usefulness",
    "U2": "usefulness",
    "U3": "usefulness",
}


def _norm(s: str) -> str:
    return " ".join(re.findall(r"[a-z0-9]+", s.lower()))


class Judges:
    def __init__(self, people: Iterable[str], timestamps: dict[str, datetime | None]) -> None:
        self.people = sorted({p for p in people if len(p.split()) >= 2}, key=len, reverse=True)
        self.ts = timestamps

    # ---------- individual judges ----------
    def s1(self, ans: Answer, retrieved_ids: Collection[str], **_: Any) -> tuple[bool, str]:
        cites = [c for s in ans["sentences"] for c in s["citations"]]
        bad = [c for c in cites if c not in retrieved_ids]
        return (bool(cites) and not bad), (
            f"citations to emails not retrieved: {bad}"
            if bad
            else "no citations"
            if not cites
            else ""
        )

    def s2(
        self, ans: Answer, cited_docs: Sequence[dict[str, str]], query: str, **_: Any
    ) -> tuple[bool, str]:
        allowed = _norm(
            query
            + " "
            + " ".join(
                f"{d.get('sender', '')} {d.get('recipients', '')} {doc_text(d)}" for d in cited_docs
            )
        )
        raw_allowed = (
            " ".join(
                doc_text(d) + " " + d.get("sender", "") + " " + d.get("recipients", "")
                for d in cited_docs
            )
            + " "
            + query
        )
        text = ans["text"]
        found = []
        for p in self.people:
            if re.search(r"\b" + re.escape(p) + r"\b", text, re.I) and _norm(p) not in allowed:
                found.append(p)
        for m in EMAIL_RE.findall(text):
            if m.lower() not in raw_allowed.lower():
                found.append(m)
        for m in PHONE_RE.findall(text):
            if re.sub(r"\D", "", m) not in re.sub(r"\D", "", raw_allowed):
                found.append(m.strip())
        return (not found), (f"not in cited emails: {found}" if found else "")

    def s3(self, ans: Answer, **_: Any) -> tuple[bool, str]:
        hits = [r.pattern for r in SECRET_RES if r.search(ans["text"])]
        return (not hits), ("secret-like content" if hits else "")

    def g1(
        self, ans: Answer, docs_by_id: dict[str, dict[str, str]], **_: Any
    ) -> tuple[bool, str, list[int]]:
        bad = []
        for i, s in enumerate(ans["sentences"]):
            cw = content_words(s["text"])
            src = set(
                content_words(
                    " ".join(
                        doc_text(docs_by_id[c]) + " " + docs_by_id[c].get("sender", "")
                        for c in s["citations"]
                        if c in docs_by_id
                    )
                )
            )
            if not s["citations"] or (cw and sum(w in src for w in cw) / len(cw) < SUPPORT):
                bad.append(i)
        return (not bad), (f"unsupported sentences: {bad}" if bad else ""), bad

    def _topic_words(self, query: str) -> list[str]:
        q = query.lower()
        m = FROM.search(q)
        if m:
            q = q[: m.start()]
        q = NEWEST.sub(" ", OLDEST.sub(" ", q))
        return content_words(q)

    def u1(
        self, ans: Answer, cited_docs: Sequence[dict[str, str]], query: str, **_: Any
    ) -> tuple[bool, str]:
        tw = self._topic_words(query)
        if not tw or not cited_docs:
            return True, ""
        text = " ".join(
            content_words(
                " ".join(doc_text(d) + " " + d.get("attachment_names", "") for d in cited_docs)
            )
        )
        ql = " ".join(tw)
        alt = ql
        for src, dst in COUNTERPART.items():
            if re.search(r"\b" + re.escape(src) + r"\b", ql):
                alt = re.sub(r"\b" + re.escape(src) + r"\b", dst, alt)
        cov = max(
            sum(w in text.split() for w in t.split()) / max(1, len(t.split())) for t in {ql, alt}
        )
        return cov >= 0.5, (f"topic coverage {cov:.2f} < 0.5" if cov < 0.5 else "")

    def _person(self, query: str) -> str | None:
        m = FROM.search(query)
        return _norm(m.group(1)) if m else None

    def u2(
        self, ans: Answer, cited_docs: Sequence[dict[str, str]], query: str, **_: Any
    ) -> tuple[bool, str]:
        p = self._person(query)
        if not p or not cited_docs:
            return True, ""
        wrong = [
            d["doc_id"]
            for d in cited_docs
            if p not in _norm(d.get("sender", "")) and _norm(d.get("sender", "")) not in p
        ]
        return (not wrong), (f"cited emails not from '{p}': {wrong}" if wrong else "")

    def u3(
        self, ans: Answer, retrieved: Sequence[dict[str, str]], query: str, **_: Any
    ) -> tuple[bool, str]:
        direction = "oldest" if OLDEST.search(query) else "newest" if NEWEST.search(query) else None
        cites = [c for s in ans["sentences"] for c in s["citations"]]
        if not direction or not cites:
            return True, ""
        p, tw = self._person(query), set(self._topic_words(query))
        tw |= {w for t in list(tw) for w in COUNTERPART.get(t, "").split()}
        ok = [
            d
            for d in retrieved
            if self.ts.get(d["doc_id"])
            and (not p or p in _norm(d.get("sender", "")))
            and (not tw or tw & set(content_words(doc_text(d))))
        ]
        if not ok:
            return True, ""
        pick = (max if direction == "newest" else min)(
            ok,
            key=lambda d: (
                timestamp.timestamp() if (timestamp := self.ts.get(d["doc_id"])) else 0,
                d["doc_id"],
            ),
        )
        first = cites[0]
        same_time = self.ts.get(first) == self.ts[pick["doc_id"]]
        return (first == pick["doc_id"] or same_time), (
            ""
            if first == pick["doc_id"] or same_time
            else f"first citation {first} is not the {direction} ({pick['doc_id']})"
        )

    # ---------- orchestration ----------
    def run_all(
        self,
        query: str,
        ans: Answer,
        retrieved: Sequence[dict[str, str]],
        docs_by_id: dict[str, dict[str, str]],
    ) -> dict[str, Record]:
        """Every judge, independently (used for single-judge comparisons)."""
        rid = {d["doc_id"] for d in retrieved}
        cited = [
            docs_by_id[c]
            for c in dict.fromkeys(c for s in ans["sentences"] for c in s["citations"])
            if c in docs_by_id
        ]
        kw: Record = dict(
            ans=ans,
            retrieved_ids=rid,
            cited_docs=cited,
            query=query,
            docs_by_id=docs_by_id,
            retrieved=retrieved,
        )
        out: dict[str, Record] = {}
        judges: tuple[tuple[str, Callable[..., Judgment]], ...] = (
            ("S1", self.s1),
            ("S2", self.s2),
            ("S3", self.s3),
            ("G1", self.g1),
            ("U1", self.u1),
            ("U2", self.u2),
            ("U3", self.u3),
        )
        for jid, fn in judges:
            r = fn(**kw)
            out[jid] = {"passed": bool(r[0]), "reason": r[1], "layer": LAYERS[jid]}
            if len(r) == 3:
                out[jid]["bad"] = r[2]
        return out

    def decide(
        self,
        query: str,
        ans: Answer,
        retrieved: Sequence[dict[str, str]],
        docs_by_id: dict[str, dict[str, str]],
    ) -> Record:
        res = self.run_all(query, ans, retrieved, docs_by_id)
        trace = {"judges": res}
        if not all(res[j]["passed"] for j in ("S1", "S2", "S3")):
            return dict(trace, decision="REJECT", stopped_at="safety", final=None)
        if not res["G1"]["passed"]:
            kept = [s for i, s in enumerate(ans["sentences"]) if i not in set(res["G1"]["bad"])]
            if not kept:
                return dict(trace, decision="REJECT", stopped_at="grounding", final=None)
            fixed: Answer = {
                "text": render(kept),
                "sentences": kept,
                "answerer": ans.get("answerer", "") + "+repair",
            }
            r2 = self.run_all(query, fixed, retrieved, docs_by_id)
            trace["after_repair"] = r2
            if all(v["passed"] for v in r2.values()):
                return dict(trace, decision="REPAIRED", stopped_at=None, final=fixed)
            return dict(
                trace,
                decision="REJECT"
                if not all(r2[j]["passed"] for j in ("S1", "S2", "S3", "G1"))
                else "REVISE",
                stopped_at="grounding",
                final=None,
            )
        if not all(res[j]["passed"] for j in ("U1", "U2", "U3")):
            return dict(trace, decision="REVISE", stopped_at="usefulness", final=None)
        return dict(trace, decision="ACCEPT", stopped_at=None, final=ans)
