# Getting Started

## Prerequisites

- Python 3.11+
- Git
- A shell capable of activating a Python virtual environment

## Installation

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
```

On PowerShell:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
```

## Generate data

```bash
python scripts/generate_dataset.py --emails 2000 --queries 200 --seed 42
```

## Run the baseline

```bash
python scripts/run_experiment.py --config experiments/configs/001_bm25.yaml
```

## Run quality checks

```bash
pytest
ruff check .
mypy packages
```

## Start the API

```bash
uvicorn apps.api.main:app --reload
```
