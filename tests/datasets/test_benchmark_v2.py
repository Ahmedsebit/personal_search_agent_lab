from packages.datasets.generator import build_dataset
from packages.datasets.audit import audit_benchmark
def test_full_shape_and_audit():
 e,q,j=build_dataset(2000,200,42); assert (len(e),len(q))==(2000,200); assert audit_benchmark(e,q,j).valid
def test_difficulty_and_recency():
 e,q,j=build_dataset(400,80,42); assert {x.difficulty for x in q}=={'easy','medium','hard'}
 for x in q:
  if x.scenario=='recency': assert sum(y.relevance==3 for y in j if y.query_id==x.id)==1
