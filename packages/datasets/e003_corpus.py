"""Corpus / qrels / annotation loading for E003 (format-tolerant)."""
from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from typing import Dict, List, Optional

CANDIDATES = {
    "doc_id": ["doc_id", "id", "email_id", "message_id", "docid"],
    "sender": ["sender", "from", "from_name", "sender_name", "author"],
    "recipients": ["recipients", "to", "to_recipients", "recipient"],
    "cc": ["cc", "cc_recipients"],
    "subject": ["subject", "title"],
    "body": ["body", "text", "content", "body_text"],
    "attachment_names": ["attachment_names", "attachments", "attachment_filenames", "files"],
    "timestamp": ["timestamp", "sent_at", "date", "received_at", "datetime", "sent_date_time", "created_at"],
}


def load_records(path: str) -> List[dict]:
    with open(path, encoding="utf-8") as f:
        txt = f.read().strip()
    if not txt:
        return []
    if txt[0] == "[":
        return json.loads(txt)
    if txt[0] == "{":
        try:
            obj = json.loads(txt)
            for k in ("emails", "documents", "docs", "items", "records"):
                if isinstance(obj.get(k), list):
                    return obj[k]
            return [obj]
        except json.JSONDecodeError:
            pass
    return [json.loads(l) for l in txt.splitlines() if l.strip()]


def load_qrels(path: str) -> Dict[str, Dict[str, float]]:
    with open(path, encoding="utf-8") as f:
        txt = f.read().strip()
    q: Dict[str, Dict[str, float]] = {}
    def add(r):
        q.setdefault(str(r.get("query_id") or r.get("qid")), {})[str(r.get("doc_id") or r.get("docid"))] = \
            float(r.get("grade", r.get("relevance", 1)))
    if txt[:1] in "{[":
        try:
            obj = json.loads(txt)
            if isinstance(obj, dict):
                return {str(k): {str(d): float(g) for d, g in v.items()} for k, v in obj.items()}
            for r in obj:
                add(r)
            return q
        except json.JSONDecodeError:
            for l in txt.splitlines():
                if l.strip():
                    add(json.loads(l))
            return q
    for l in txt.splitlines():
        p = l.split()
        if len(p) >= 4:
            q.setdefault(p[0], {})[p[2]] = float(p[3])
    return q


def load_annotations(path: str) -> List[dict]:
    with open(path, encoding="utf-8") as f:
        return list(csv.DictReader(f))


def resolve_fields(records: List[dict], override: Optional[dict] = None) -> Dict[str, Optional[str]]:
    override = override or {}
    keys = set().union(*[set(d.keys()) for d in records[:500]]) if records else set()
    return {f: override.get(f) or next((c for c in cands if c in keys), None) for f, cands in CANDIDATES.items()}


def as_text(v) -> str:
    if v is None:
        return ""
    if isinstance(v, str):
        return v
    if isinstance(v, dict):
        return " ".join(as_text(x) for x in v.values())
    if isinstance(v, (list, tuple)):
        return " ".join(as_text(x) for x in v)
    return str(v)


def parse_ts(v) -> Optional[datetime]:
    if v is None or v == "":
        return None
    if isinstance(v, (int, float)):
        x = float(v)
        return datetime.fromtimestamp(x / 1000 if x > 1e11 else x, tz=timezone.utc)
    s = str(v).strip().replace("Z", "+00:00")
    try:
        d = datetime.fromisoformat(s)
        return d if d.tzinfo else d.replace(tzinfo=timezone.utc)
    except ValueError:
        pass
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y/%m/%d %H:%M", "%d/%m/%Y %H:%M", "%a, %d %b %Y %H:%M:%S %z"):
        try:
            d = datetime.strptime(s, fmt)
            return d if d.tzinfo else d.replace(tzinfo=timezone.utc)
        except ValueError:
            pass
    return None


def to_field_documents(records: List[dict], fm: Dict[str, Optional[str]]) -> List[dict]:
    """Project raw email records onto the five E003 fields (recipients = to + cc)."""
    out = []
    for r in records:
        g = lambda f: r.get(fm[f]) if fm.get(f) else None
        out.append({
            "doc_id": str(g("doc_id")),
            "sender": as_text(g("sender")),
            "recipients": (as_text(g("recipients")) + " " + as_text(g("cc"))).strip(),
            "subject": as_text(g("subject")),
            "body": as_text(g("body")),
            "attachment_names": as_text(g("attachment_names")),
        })
    return out


def timestamps_of(records: List[dict], fm) -> Dict[str, Optional[datetime]]:
    return {str(r.get(fm["doc_id"])): parse_ts(r.get(fm["timestamp"]) if fm.get("timestamp") else None)
            for r in records}
