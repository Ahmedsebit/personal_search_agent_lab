from collections import Counter
from dataclasses import dataclass, asdict
from packages.datasets.models import SearchQuery, RelevanceJudgment
from packages.search.models import Email
@dataclass(frozen=True)
class AuditReport:
    valid: bool; errors: tuple[str,...]; statistics: dict[str,object]
    def to_dict(self): return asdict(self)
def audit_benchmark(emails:list[Email], queries:list[SearchQuery], judgments:list[RelevanceJudgment])->AuditReport:
    errors=[]; eids={e.id for e in emails}; qids={q.id for q in queries}; positive=Counter(); pairs=set()
    if len(eids)!=len(emails): errors.append('duplicate email IDs')
    if len(qids)!=len(queries): errors.append('duplicate query IDs')
    for j in judgments:
        if (j.query_id,j.document_id) in pairs: errors.append('duplicate judgment')
        pairs.add((j.query_id,j.document_id))
        if j.query_id not in qids or j.document_id not in eids or j.relevance not in {1,2,3}: errors.append('invalid judgment')
        positive[j.query_id]+=1
    for q in queries:
        if not positive[q.id]: errors.append(f'no positive: {q.id}')
    return AuditReport(not errors, tuple(errors), {'emails':len(emails),'queries':len(queries),'judgments':len(judgments),'scenarios':dict(Counter(q.scenario for q in queries)),'difficulties':dict(Counter(q.difficulty for q in queries)),'grades':dict(Counter(j.relevance for j in judgments))})
