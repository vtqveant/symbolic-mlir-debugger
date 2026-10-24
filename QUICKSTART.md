# Quick Start

## Install

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install -e . --no-deps
```

## Get structured feedback

```bash
smlir analyze debugger/fixtures/conditional_branch.mlir --json
```

The report includes diagnostics and feasible paths. Exit code 0 means `status == "ok"`;
exit code 1 means an analysis error.

Provide concrete inputs or change exploration limits:

```bash
smlir analyze debugger/fixtures/simple_add.mlir \
  --input a=5 --input b=3 --max-paths 5 --seed 0 --json
```

The Python API is available as:

```python
from debugger.agent import analyze_file

report = analyze_file("debugger/fixtures/conditional_branch.mlir", seed=0)
```

## Use the DAP adapter

```bash
python -m debugger dap
```

The adapter speaks DAP over stdin/stdout. The Python client launches it automatically:

```bash
python dap_client/examples/basic_session.py
```

## Run tests

```bash
python -m pytest
```

For architecture, the feedback contract, and current work, see `README.md`, `AGENTS.md`,
and the hosted tm tracker at https://www.eventflow.ru.
