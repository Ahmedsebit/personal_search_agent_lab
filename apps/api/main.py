from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from pydantic import BaseModel, Field

from packages.datasets.loader import load_dataset
from packages.search.retrieval.bm25 import BM25Retriever

app = FastAPI(title="Personal Search & Agent Lab", version="0.1.0")
_retriever: BM25Retriever | None = None


class SearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=500)
    limit: int = Field(default=10, ge=1, le=100)


@app.on_event("startup")
def startup() -> None:
    global _retriever
    dataset_root = Path("datasets")
    if (dataset_root / "synthetic" / "emails.jsonl").exists():
        emails, _, _ = load_dataset(dataset_root)
        _retriever = BM25Retriever(); _retriever.index(emails)


@app.get("/health")
def health() -> dict[str, object]:
    return {"status": "ok", "index_ready": _retriever is not None}


@app.post("/search")
def search(request: SearchRequest) -> dict[str, object]:
    if _retriever is None: return {"results": [], "message": "Generate the dataset and restart the API."}
    return {"results": [result.__dict__ for result in _retriever.search(request.query, request.limit)]}
