import argparse,json
from pathlib import Path
from packages.datasets.loader import load_dataset
from packages.datasets.audit import audit_benchmark
p=argparse.ArgumentParser(); p.add_argument('--root',type=Path,default=Path('datasets')); p.add_argument('--output',type=Path,default=Path('experiments/results/benchmark-v2-audit.json')); a=p.parse_args()
r=audit_benchmark(*load_dataset(a.root)); a.output.parent.mkdir(parents=True,exist_ok=True); a.output.write_text(json.dumps(r.to_dict(),indent=2,sort_keys=True)); print(json.dumps(r.to_dict(),indent=2,sort_keys=True)); raise SystemExit(0 if r.valid else 1)
