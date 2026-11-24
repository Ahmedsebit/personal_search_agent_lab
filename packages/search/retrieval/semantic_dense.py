"""E006 exact cosine retrieval, separate from the original hashing baseline."""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Protocol

import numpy as np
from numpy.typing import NDArray

PREREGISTERED_MODEL = "sentence-transformers/all-MiniLM-L6-v2"


class Encoder(Protocol):
    name: str
    cache_identity: str

    def encode(self, texts: Sequence[str]) -> NDArray[np.float32]: ...


def document_text(doc: Mapping[str, str]) -> str:
    """Preregistered text view: subject, sender, attachment names, then body."""
    parts = (
        doc.get("subject", ""),
        "from " + doc.get("sender", ""),
        doc.get("attachment_names", ""),
        doc.get("body", ""),
    )
    return " \n".join(part for part in parts if part.strip())


class SentenceTransformerEncoder:
    def __init__(
        self, model: str = PREREGISTERED_MODEL, batch_size: int = 64, max_seq_length: int = 256
    ) -> None:
        from sentence_transformers import SentenceTransformer  # type: ignore[import-not-found]

        self.model = SentenceTransformer(model, device="cpu")
        self.model.max_seq_length = max_seq_length
        self.batch_size, self.name = batch_size, model
        self.cache_identity = f"{model}:{max_seq_length}"

    def encode(self, texts: Sequence[str]) -> NDArray[np.float32]:
        return np.asarray(
            self.model.encode(
                list(texts),
                batch_size=self.batch_size,
                normalize_embeddings=True,
                show_progress_bar=False,
            ),
            dtype=np.float32,
        )


class HashingEncoder:
    """Deterministic stand-in for tests and explicitly labelled smoke runs only."""

    name = "hashing-encoder (test only)"

    def __init__(self, dim: int = 512) -> None:
        self.dim = dim
        self.cache_identity = f"hashing:{dim}"

    def encode(self, texts: Sequence[str]) -> NDArray[np.float32]:
        out = np.zeros((len(texts), self.dim), dtype=np.float32)
        for index, text in enumerate(texts):
            for token in re.findall(r"[a-z0-9]+", text.lower()):
                bucket = int(hashlib.md5(token.encode()).hexdigest(), 16) % self.dim
                out[index, bucket] += 1.0
        norm = np.linalg.norm(out, axis=1, keepdims=True)
        return np.asarray(out / np.where(norm == 0, 1, norm), dtype=np.float32)


class DenseRetriever:
    def __init__(
        self,
        documents: Sequence[Mapping[str, str]],
        encoder: Encoder,
        cache_path: str | None = None,
    ) -> None:
        self.doc_ids = [str(doc["doc_id"]) for doc in documents]
        self.encoder = encoder
        texts = [document_text(doc) for doc in documents]
        fingerprint = hashlib.sha256(
            json.dumps(
                [encoder.cache_identity, list(zip(self.doc_ids, texts, strict=True))]
            ).encode("utf-8")
        ).hexdigest()
        cache = Path(cache_path) if cache_path else None
        metadata = cache.with_suffix(cache.suffix + ".json") if cache else None
        if (
            cache is not None
            and metadata is not None
            and cache.is_file()
            and metadata.is_file()
            and json.loads(metadata.read_text(encoding="utf-8"))["fingerprint"] == fingerprint
        ):
            self.emb = np.asarray(np.load(cache, allow_pickle=False), dtype=np.float32)
        else:
            self.emb = encoder.encode(texts) if texts else np.empty((0, 0), dtype=np.float32)
            if cache is not None and metadata is not None:
                cache.parent.mkdir(parents=True, exist_ok=True)
                with cache.open("wb") as handle:
                    np.save(handle, self.emb)
                metadata.write_text(json.dumps({"fingerprint": fingerprint}), encoding="utf-8")
        if self.emb.ndim != 2 or self.emb.shape[0] != len(self.doc_ids):
            raise ValueError("embedding matrix does not match the corpus")

    def search(
        self, query: str, top_k: int = 50
    ) -> tuple[list[tuple[str, float]], dict[str, object]]:
        metadata: dict[str, object] = {"stage": "dense", "encoder": self.encoder.name}
        if top_k <= 0 or not self.doc_ids:
            return [], metadata
        scores = self.emb @ self.encoder.encode([query])[0]
        order = sorted(
            range(len(scores)), key=lambda index: (-float(scores[index]), self.doc_ids[index])
        )[:top_k]
        return [(self.doc_ids[index], float(scores[index])) for index in order], metadata
