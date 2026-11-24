"""Bind E003 to the frozen repository components via dotted paths in the config.

The three paths below are the ONLY repository-specific assumptions. If a path or
method name differs in your repository, edit experiments/configs/00x_e003_*.yaml.
"""

from __future__ import annotations

import importlib
import inspect
from collections.abc import Callable

from packages.search.query.field_cues import default_tokenize


def load_object(path: str):
    mod, _, attr = path.partition(":")
    obj = importlib.import_module(mod)
    for part in attr.split(".") if attr else []:
        obj = getattr(obj, part)
    return obj


def _doc_id(item):
    if isinstance(item, (tuple, list)):
        return str(item[0]), float(item[1]) if len(item) > 1 else 0.0
    if isinstance(item, dict):
        did = (
            item.get("doc_id") or item.get("document_id") or item.get("id") or item.get("email_id")
        )
        return str(did), float(item.get("score", 0.0))
    did = (
        getattr(item, "doc_id", None)
        or getattr(item, "document_id", None)
        or getattr(item, "id", None)
        or getattr(item, "email_id", None)
    )
    return str(did), float(getattr(item, "score", 0.0))


def build_retriever_instance(cls, documents):
    for build in (
        lambda: cls(documents),
        lambda: cls.from_documents(documents),
        lambda: cls(documents=documents),
    ):
        try:
            return build()
        except TypeError:
            continue
    inst = cls()
    for m in ("index", "fit", "add_documents", "build"):
        if hasattr(inst, m):
            getattr(inst, m)(documents)
            return inst
    raise TypeError(
        f"Could not construct {cls!r} from documents; set control.factory in the config"
    )


def make_search_fn(retriever) -> Callable[[str, int], list[tuple[str, float]]]:
    for name in ("search", "retrieve", "query", "rank"):
        fn = getattr(retriever, name, None)
        if callable(fn):
            params = list(inspect.signature(fn).parameters)
            kw = next((p for p in ("top_k", "k", "limit", "n") if p in params), None)

            def search(q, k, _fn=fn, _kw=kw):
                res = _fn(q, **{_kw: k}) if _kw else _fn(q)
                res = getattr(res, "hits", getattr(res, "results", res))
                return [_doc_id(r) for r in list(res)[:k]]

            return search
    raise TypeError(f"{retriever!r} has no search/retrieve/query/rank method")


def make_normalizer(path: str | None, retriever=None) -> Callable[[str], str]:
    if not path:
        return lambda q: q
    if path == "control":
        if retriever is None:
            raise ValueError("normalizer 'control' requires the frozen retriever instance")
        obj = retriever.normalizer
    else:
        obj = load_object(path)
    if inspect.isclass(obj):
        obj = obj()
    fn = obj if callable(obj) and not hasattr(obj, "normalize") else obj.normalize

    def normalize(q):
        r = fn(q)
        if hasattr(r, "terms"):
            return " ".join(r.terms)
        for attr in ("normalized_query", "expanded_query", "text", "query"):
            if hasattr(r, attr):
                r = getattr(r, attr)
                break
        if isinstance(r, dict):
            r = (
                r.get("normalized_query")
                or r.get("expanded_query")
                or r.get("text")
                or r.get("query")
            )
        if isinstance(r, (list, tuple)):
            r = " ".join(map(str, r))
        return str(r)

    return normalize


def resolve_tokenizer(path: str | None):
    if path:
        try:
            return load_object(path), path
        except (ImportError, AttributeError):
            pass
    return default_tokenize, "e003.default_tokenize (fallback)"


def resolve_bm25_params(retriever, default_k1=1.2, default_b=0.75):
    pending = [retriever]
    seen = set()
    while pending:
        r = pending.pop(0)
        if id(r) in seen:
            continue
        seen.add(id(r))
        if hasattr(r, "k1") and hasattr(r, "b"):
            return float(r.k1), float(r.b), f"read from {type(r).__name__}"
        pending.extend(
            getattr(r, attr)
            for attr in ("base", "inner", "retriever", "bm25", "_bm25")
            if hasattr(r, attr)
        )
    return default_k1, default_b, "config defaults (frozen E001 values not found on retriever)"
