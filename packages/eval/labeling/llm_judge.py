"""U3 (optional) — LLM relevance judge with shared per-email analysis.

Each email is analysed ONCE into a compact structure cached by doc_id. Each query/email judgment
reuses that analysis. Token use is recorded for actual calls and a no-sharing baseline estimate
(full email text in every judgment), so the saving is measured, not assumed.

Providers
  mock                      deterministic, offline; used in tests and smoke runs
  openai_compatible         /chat/completions; LAB_LLM_ENDPOINT, LAB_LLM_API_KEY, LAB_LLM_MODEL

Only send SYNTHETIC lab data to an external endpoint. Never send real mailbox content.
"""

from __future__ import annotations

import json
import os
import re
import urllib.request
from typing import Any, Protocol

Record = dict[str, Any]


class Provider(Protocol):
    name: str

    def complete(self, prompt: str) -> tuple[str, Record]: ...


ANALYSE_PROMPT = """You analyse one email for a search-relevance judge. Return JSON only:
{"summary": "<= 40 words", "people": [...], "topics": [...], "dates": [...],
"attachments": [...], "intent": "<= 12 words"}
EMAIL:
"""
JUDGE_PROMPT = """Grade how well the email satisfies the search query.
2 = clearly what the user is looking for; 1 = partially relevant; 0 = not relevant.
Honour structure: people after "from"/"to", subjects, dates and ranges (reference time: {ref}).
Return JSON only: {{"grade": 0|1|2, "reason": "<= 20 words"}}
QUERY: {query}
EMAIL ANALYSIS: {analysis}
EMAIL METADATA: from={sender}; to={recipients}; date={date};
subject={subject}; attachments={attachments}
"""


def est_tokens(text: str) -> int:
    return max(1, len(text) // 4)


def email_text(d: dict[str, str]) -> str:
    return (
        f"From: {d.get('sender', '')}\nTo: {d.get('recipients', '')}\nDate: {d.get('date', '')}\n"
        f"Subject: {d.get('subject', '')}\nAttachments: {d.get('attachment_names', '')}"
        f"\n\n{d.get('body', '')}"
    )


class MockProvider:
    name = "mock"

    def complete(self, prompt: str) -> tuple[str, Record]:
        if prompt.startswith(ANALYSE_PROMPT[:30]):
            body = prompt[len(ANALYSE_PROMPT) :]
            words = re.findall(r"[a-z]{4,}", body.lower())
            out = json.dumps(
                {
                    "summary": " ".join(words[:30]),
                    "people": [],
                    "topics": sorted(set(words))[:15],
                    "dates": [],
                    "attachments": [],
                    "intent": "",
                }
            )
        else:
            match = re.search(r"QUERY: (.*)", prompt)
            if match is None or "EMAIL ANALYSIS:" not in prompt:
                raise ValueError("mock provider requires an analysis or relevance-judge prompt")
            q = match.group(1).lower()
            rest = prompt.split("EMAIL ANALYSIS:", 1)[1].lower()
            terms = [
                t
                for t in re.findall(r"[a-z]{4,}", q)
                if t not in {"emails", "from", "about", "subject", "latest"}
            ]
            hit = sum(t in rest for t in terms)
            out = json.dumps(
                {
                    "grade": 2 if terms and hit == len(terms) else 1 if hit else 0,
                    "reason": f"{hit}/{len(terms)} terms",
                }
            )
        return out, {
            "prompt_tokens": est_tokens(prompt),
            "completion_tokens": est_tokens(out),
            "estimated": True,
        }


class OpenAICompatibleProvider:
    def __init__(
        self,
        endpoint: str | None = None,
        api_key: str | None = None,
        model: str | None = None,
        timeout: float = 60,
    ) -> None:
        self.endpoint = endpoint or os.environ["LAB_LLM_ENDPOINT"]
        self.api_key = api_key or os.environ.get("LAB_LLM_API_KEY", "")
        self.model = model or os.environ.get("LAB_LLM_MODEL", "")
        self.name = f"openai_compatible:{self.model}"
        self.timeout = timeout

    def complete(self, prompt: str) -> tuple[str, Record]:
        body = json.dumps(
            {
                "model": self.model,
                "temperature": 0,
                "messages": [{"role": "user", "content": prompt}],
            }
        ).encode()
        req = urllib.request.Request(
            self.endpoint,
            data=body,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}",
                "api-key": self.api_key,
            },
        )
        with urllib.request.urlopen(req, timeout=self.timeout) as r:
            obj = json.loads(r.read())
        u = obj.get("usage") or {}
        return obj["choices"][0]["message"]["content"], {
            "prompt_tokens": u.get("prompt_tokens", est_tokens(prompt)),
            "completion_tokens": u.get("completion_tokens", 0),
            "estimated": not u,
        }


def _json(text: str) -> Record:
    m = re.search(r"\{.*\}", text, re.S)
    if m is None:
        raise ValueError("provider response contains no JSON object")
    obj = json.loads(m.group(0))
    if not isinstance(obj, dict):
        raise ValueError("provider response must be a JSON object")
    return obj


class SharedAnalysisJudge:
    def __init__(self, provider: Provider, cache_path: str | None = None) -> None:
        self.p, self.cache_path = provider, cache_path
        self.analyses: dict[str, Record] = {}
        self.usage: Record = {
            "analyse_calls": 0,
            "judge_calls": 0,
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "baseline_prompt_tokens_est": 0,
            "any_estimated": False,
        }
        if cache_path and os.path.exists(cache_path):
            for line in open(cache_path, encoding="utf-8"):
                r = json.loads(line)
                self.analyses[r["doc_id"]] = r["analysis"]

    def _call(self, prompt: str) -> str:
        out, u = self.p.complete(prompt)
        self.usage["prompt_tokens"] += u["prompt_tokens"]
        self.usage["completion_tokens"] += u["completion_tokens"]
        self.usage["any_estimated"] |= bool(u.get("estimated"))
        return out

    def analyse(self, doc: dict[str, str]) -> Record:
        if doc["doc_id"] not in self.analyses:
            a = _json(self._call(ANALYSE_PROMPT + email_text(doc)))
            self.usage["analyse_calls"] += 1
            self.analyses[doc["doc_id"]] = a
            if self.cache_path:
                with open(self.cache_path, "a", encoding="utf-8") as f:
                    f.write(json.dumps({"doc_id": doc["doc_id"], "analysis": a}) + "\n")
        return self.analyses[doc["doc_id"]]

    def judge(self, query: str, doc: dict[str, str], ref: str = "") -> Record:
        a = self.analyse(doc)
        fill = dict(
            ref=ref,
            query=query,
            sender=doc.get("sender", ""),
            recipients=doc.get("recipients", ""),
            date=doc.get("date", ""),
            subject=doc.get("subject", ""),
            attachments=doc.get("attachment_names", ""),
        )
        prompt = JUDGE_PROMPT.format(analysis=json.dumps(a), **fill)
        self.usage["baseline_prompt_tokens_est"] += est_tokens(
            JUDGE_PROMPT.format(analysis=email_text(doc), **fill)
        )
        r = _json(self._call(prompt))
        self.usage["judge_calls"] += 1
        g = r.get("grade")
        if str(g) not in ("0", "1", "2"):
            raise ValueError("provider grade must be 0, 1 or 2")
        return {
            "grade": int(str(g)),
            "reason": r.get("reason", ""),
        }

    def cost_report(self) -> Record:
        u = dict(self.usage)
        u["total_tokens"] = u["prompt_tokens"] + u["completion_tokens"]
        base = u["baseline_prompt_tokens_est"] + u["completion_tokens"]
        u["baseline_total_tokens_est"] = base
        u["saving_vs_baseline_est"] = (1 - u["total_tokens"] / base) if base else None
        return u


def make_provider(name: str) -> Provider:
    if name == "mock":
        return MockProvider()
    if name == "openai_compatible":
        return OpenAICompatibleProvider()
    raise ValueError(f"unknown provider {name!r}")
