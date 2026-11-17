from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass(frozen=True)
class Email:
    id: str
    owner_id: str
    sender: str
    recipients: tuple[str, ...]
    subject: str
    body: str
    sent_at: datetime
    has_attachment: bool = False
    attachment_names: tuple[str, ...] = ()
    thread_id: str | None = None
    metadata: dict[str, str] = field(default_factory=dict)

    @property
    def searchable_text(self) -> str:
        parts = [self.sender, *self.recipients, self.subject, self.body, *self.attachment_names]
        return " ".join(parts)


@dataclass(frozen=True)
class SearchResult:
    document_id: str
    score: float
    rank: int
    source: str
