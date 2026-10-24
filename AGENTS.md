# Agent Guidelines for Symbolic MLIR Debugger

This document provides guidelines for AI agents working on the Symbolic MLIR Debugger project. It includes build commands, testing instructions, and code style conventions.

## Project tracking and knowledge base (tm)

This project is tracked in the hosted `tm` service at https://www.eventflow.ru, not in
ad-hoc TODO files. Do not depend on a local `tm` checkout or a `TM_HOME` environment
variable.

- Tracker UI: https://www.eventflow.ru
- API base: https://tm.eventflow.ru/api/v1
- Discovery: https://tm.eventflow.ru/.well-known/tm-agent.json
- OpenAPI (authenticated): https://tm.eventflow.ru/api/v1/openapi.json
- Project epic: `symbolic-mlir-debugger` (historical task key `SMD`) in the shared
  project tenant. Agents that are not members of that tenant work in the private epic
  returned by registration (`space.epic`, with key `space.key`) and record project
  documentation there.
- Milestones: `m1-refactor-and-re-plan` and `m2-harden-the-feedback-loop` are closed.
  No successor milestone is defined yet.

Get access and start every session with:

```bash
# One-time bootstrap: register an agent tenant. Save the returned token securely
# (for example, chmod 600 ~/.config/tm/token) and never commit it.
curl -sS -X POST https://tm.eventflow.ru/api/v1/agent/register \
  -H 'Content-Type: application/json' -d '{}'

export TM_API_URL="https://tm.eventflow.ru"
export TM_TOKEN="<token returned once by registration>"
export TM_TEAM="<team id returned by registration>"
export TM_EPIC="<space.epic returned by registration, or symbolic-mlir-debugger>"

# Every request selects the tenant and authenticates with the bearer token.
TM=(-H "Authorization: Bearer $TM_TOKEN" -H "X-TM-Team: $TM_TEAM")

curl -fsS "${TM[@]}" "$TM_API_URL/api/v1/whoami"
curl -fsS "${TM[@]}" "$TM_API_URL/api/v1/tasks?epic=$TM_EPIC"
curl -fsS "${TM[@]}" "$TM_API_URL/api/v1/docs?epic=$TM_EPIC"
curl -fsS "${TM[@]}" "$TM_API_URL/api/v1/milestones?epic=$TM_EPIC"
curl -fsS "${TM[@]}" "$TM_API_URL/api/v1/doc/<DOC_ID>"
```

Create work as tasks, record analysis/decisions as notes or documents, and link them:

```bash
# Create a task or document
curl -fsS -X POST "${TM[@]}" -H 'Content-Type: application/json' \
  -d "{\"kind\":\"task\",\"title\":\"...\",\"epic\":\"$TM_EPIC\"}" \
  "$TM_API_URL/api/v1/new"

# Append a note, change status, or replace a document body
curl -fsS -X POST "${TM[@]}" -H 'Content-Type: application/json' \
  -d '{"text":"..."}' "$TM_API_URL/api/v1/task/<TASK_ID>/note"
curl -fsS -X POST "${TM[@]}" -H 'Content-Type: application/json' \
  -d '{"status":"in_progress"}' "$TM_API_URL/api/v1/task/<TASK_ID>/status"
curl -fsS -X POST "${TM[@]}" -H 'Content-Type: application/json' \
  -d '{"text":"# ..."}' "$TM_API_URL/api/v1/doc/<DOC_ID>/body"

# Link a document to a task
curl -fsS -X POST "${TM[@]}" -H 'Content-Type: application/json' \
  -d '{"op":"add","target":"<DOC_ID>"}' \
  "$TM_API_URL/api/v1/task/<TASK_ID>/link"
```

The shared project records, when the tenant exposes them, are:
- `symbolic-mlir-debugger-usage-and-scope`
- `symbolic-mlir-debugger-current-state-audit` (historical snapshot)
- `symbolic-mlir-debugger-target-architecture`
- `symbolic-mlir-debugger-milestone-1-plan` (historical snapshot, M1 complete)
- `symbolic-mlir-debugger-agent-feedback-api-contract`
- `adr-001-consolidate-trace-execution-and-add-agent-feedback-api`

The project documentation set maintained in the agent workspace is:
- `symbolic-mlir-debugger-overview`
- `symbolic-mlir-debugger-architecture`
- `symbolic-mlir-debugger-agent-api`
- `symbolic-mlir-debugger-dap-and-traces`
- `symbolic-mlir-debugger-development`

Old repository design/plan files were removed. Their critical review, rejected options,
current architecture, and active plan are preserved in the tm records above. Do not
hand-edit tm data or configuration. If the HTTP API cannot express a needed change,
create a task for the tooling gap first.

### Current entry points

```bash
# Install once (editable); provides the `smlir` console entry point
pip install -e . --no-deps

# One-shot structured feedback for automated coding loops
smlir analyze debugger/fixtures/conditional_branch.mlir --json
# Equivalent module form:
python -m debugger analyze debugger/fixtures/conditional_branch.mlir --json

# Interactive stdio DAP adapter
python -m debugger dap

# Existing Python DAP client
python dap_client/examples/basic_session.py
```

`debugger.agent.analyze_file` / `analyze_text` is the stable agent API. `smlir analyze`
is its console wrapper. The API runs local compiler validation via `mlir-opt` when
available and never requires a network service; `summary.compiler` records which adapter
was used. `dap_client` owns DAP automation. `dap_trace_library` now contains only the
batch trace execution and trace-validation adapters over `dap_client`; it must not spawn
a separate debugger CLI. The Jinja2-first experiment was shelved; its old repository
design/plan files were removed and the critical review is preserved in tm (audit +
ADR-001). Do not resurrect it without a concrete need and a new accepted decision.

### Milestone rules

- Fix the feedback loop before expanding dialects or templating.
- Keep compiler validation local-first; remote MCP/LSP is optional and opt-in.
- Add tests for new entry points and include `dap_trace_library/tests` in pytest.
- Do not delete working modules merely to match an old plan.
- Record every non-trivial decision in tm, including rejected options.

Current milestone: none. M1 delivered the stable agent API, deterministic exploration,
fixed trace execution, packaging/CLI, DAP inspection, shared trace schema, local compiler
adapter, safe expression evaluation, and hermetic CI. M2 closed the remaining hardening
tasks. Before substantial new work, create and accept a successor milestone plan in tm,
then create tasks against it.

## Project Structure

- `debugger/`: Python symbolic debugger, agent API, compiler adapter, and DAP server
  - `interpreter/`: Core symbolic/concolic execution engine
  - `parser/`: MLIR parser and dialect definitions
  - `tests/`: Python unit tests
  - `fixtures/`: Test MLIR files
- `dap_client/`: Python DAP client, generators, runners, and examples
- `dap_trace_library/`: batch trace execution and trace validation
- `scripts/mlir_validation/`: hermetic local MLIR validation helpers
- `docs/`: agent API, testing, and MLIR validation reference (`API.md` is the detailed API
  reference; the tm records remain authoritative for scope and decisions)
- `reference/`: local, gitignored vendored MLIR/Triton documentation snapshot; not
  project docs and not part of CI

## Build and Test Commands

### Python Debugger

All commands should be run from the repository root unless otherwise noted. Activate the
project virtualenv first so `python`, `pytest`, and `smlir` resolve to Python 3.9+.

**Install dependencies:**
```bash
pip install -r requirements.txt
```

**Running tests (configured in `pyproject.toml`):**
```bash
python -m pytest                         # debugger, dap_client, and dap_trace_library tests
python -m pytest -v                      # Verbose output
python -m pytest -m parser               # Run tests with marker 'parser'
python -m pytest --cov                   # Run with coverage
python -m pytest --cov-report=html       # Generate HTML coverage report
```

**Running a single test:**
```bash
python -m pytest debugger/tests/test_parser.py::test_cmpi_parsing
python -m pytest debugger/tests/test_parser.py -k "test_cmpi_parsing"
```

**Test markers** (defined in `pyproject.toml`):
- `slow`: marks tests as slow
- `parser`: parser-related tests
- `interpreter`: interpreter-related tests
- `dialect`: dialect-specific tests
- `integration`: integration tests
- `concolic`: concolic execution tests

**Linting and formatting:**
```bash
# Format the Python files you changed
python -m black <changed-python-files>
```

CI does not run `black --check .` or `flake8 .` across the whole repository. It runs
black and flake8 on a curated scope (agent/CLI, safe evaluation, trace executor, related
tests) defined in `.github/workflows/ci.yml`; flake8 there selects `E9,F63,F7,F82`.
Do not assume unrelated pre-existing files are clean. Match the CI scope for files you
touch and always format changed Python files with black before committing.

**Note:** The project uses black (line-length=100) for formatting and flake8 for linting.



## Code Style Guidelines

### Python

**Imports:** Group imports: standard library, third-party, local. Use absolute imports for local modules. Sort imports alphabetically within groups. Use `from typing import ...` for type hints.

**Naming:** `snake_case` for functions, variables, modules. `PascalCase` for classes. `UPPER_SNAKE_CASE` for constants. Private members start with `_`.

**Type hints:** Use type hints for function arguments and return values. Use `Optional[T]` for nullable values. Use `Union` for multiple possible types. Use `List[T]`, `Dict[K, V]`, `Tuple[...]` etc.

**Error handling:** Use `try/except` with specific exception types where possible. Log errors with `logger.error()` (see logging). Avoid bare `except:` clauses; use `except Exception:` if needed. Raise appropriate exceptions with descriptive messages.

**Logging:** Use the `logging` module. Create module-level logger: `logger = logging.getLogger(__name__)`. Use appropriate log levels: `debug`, `info`, `warning`, `error`. Prefer structured logging over print statements.

**Docstrings:** Use triple double quotes (`"""`). First line summary, blank line, detailed description. Include `Args:` and `Returns:` sections for functions/methods. Use Google style docstrings (as seen in existing code).

**Formatting:** Indent with 4 spaces (no tabs). Line length: 100 (enforced by black). Use double quotes for strings (consistent with existing code). Use f-strings for string interpolation.

**Testing:** Write unit tests in `tests/` directory. Use `pytest` fixtures defined in `conftest.py`. Use descriptive test function names prefixed with `test_`. Use `@pytest.mark.*` decorators for test markers. Provide docstrings explaining test purpose.

## Development Workflow

1. **Before making changes:** Ensure tests pass (`python -m pytest`). Run the lint scope from `.github/workflows/ci.yml` on the files you plan to touch.
2. **After making changes:** Run relevant unit tests. Format changed Python files with `python -m black <files>` and verify the CI lint scope. Update/add tests as needed.
3. **Commit messages:** Use present tense imperative ("Add feature", "Fix bug"). Reference issue numbers if applicable. Keep first line under 50 characters, body lines under 72.

## Common Pitfalls

- **Imports:** use package-qualified imports (`debugger.*`, `dap_client.*`); install with `pip install -e . --no-deps` for console scripts.
- **Z3 version:** Requires `z3-solver>=4.12.0`.
- **MLIR parsing:** The parser uses Lark grammar; dialect definitions are in `parser/dialects/`.
- **DAP server:** The debug adapter uses stdin/stdout JSON‑RPC; see `dap_server.py`.
- **Emoji not allowed:** Never use emoji in documentation, scripts and comments.

## Resources

- [MLIR Documentation](https://mlir.llvm.org/)
- [Z3 Python API](https://z3prover.github.io/api/html/namespacez3py.html)
- [Debug Adapter Protocol](https://microsoft.github.io/debug-adapter-protocol/)
- [VS Code Extension API](https://code.visualstudio.com/api)

---
*This file is intended for AI agents working on the project. Update as needed.*