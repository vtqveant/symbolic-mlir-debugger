# Testing

Run tests from the repository root:

```bash
python -m pytest
```

`pyproject.toml` configures the suite:

- `debugger/tests`: parser, interpreter, concolic, memory, DAP, agent API,
  compiler adapter, and safe-expression tests.
- `dap_client/tests`: protocol, client, session, and pipe integration tests.
- `dap_trace_library/tests`: trace execution and shared-schema validation.

## Common commands

```bash
python -m pytest -v
python -m pytest -m parser
python -m pytest -m interpreter
python -m pytest debugger/tests/test_agent_api.py
python -m pytest debugger/tests/test_parser.py::test_cmpi_parsing
```

Markers are declared in `pyproject.toml`: `slow`, `parser`, `interpreter`, `dialect`,
`integration`, `concolic`.

## Fixtures

MLIR fixtures live in `debugger/fixtures/`. DAP trace examples live in
`dap_client/examples/`. Tests use pytest fixtures from `debugger/tests/conftest.py` for
the parser and interpreters.

## Coverage and lint

CI runs a targeted coverage gate over the agent/compiler/safe-eval modules and a black +
flake8 lint job. Locally:

```bash
python -m pytest \
  --cov=debugger.agent --cov=debugger.compiler \
  --cov=debugger.interpreter.safe_eval \
  --cov-report=term-missing --cov-fail-under=60

# Lint the files you changed the same way CI does
python -m black --check <changed-python-files>
python -m flake8 <changed-python-files> \
  --max-line-length=100 --extend-ignore=E203,W503 --select=E9,F63,F7,F82
```

CI applies black and flake8 to a curated file list (agent/CLI, safe evaluation, trace
executor, and related tests) in `.github/workflows/ci.yml`, not to the whole repository.
Pre-existing files outside that scope may not be clean.

## CI

- `.github/workflows/ci.yml`: tests, lint, and local MLIR validation.
- CI does not require network access for tests or MLIR validation.
