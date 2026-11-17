from dataclasses import dataclass, field
@dataclass(frozen=True)
class SearchQuery:
    id: str; text: str; scenario: str; difficulty: str = 'medium'; intent: dict[str,str] = field(default_factory=dict); notes: str = ''
@dataclass(frozen=True)
class RelevanceJudgment:
    query_id: str; document_id: str; relevance: int; rationale: str = ''
