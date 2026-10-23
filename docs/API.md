# Symbolic MLIR Debugger - API Documentation

Reference for the agent feedback API, DAP client, test automation helpers, and trace
adapters. The tm records listed in `AGENTS.md` remain authoritative for scope and
decisions; this file documents the current code.

## Contents

1. [Agent feedback API](#1-agent-feedback-api)
2. [DAP client API](#2-dap-client-api)
3. [Test generation API](#3-test-generation-api)
4. [Test runner and orchestration API](#4-test-runner-and-orchestration-api)
5. [Trace execution and validation API](#5-trace-execution-and-validation-api)
6. [Core debugger API](#6-core-debugger-api)
7. [Protocol and connection utilities](#7-protocol-and-connection-utilities)
8. [Examples](#8-examples)

## 1. Agent feedback API

`debugger.agent` is the stable interface for automated coding loops. It returns
JSON-serializable dictionaries and never prints analysis output to stdout.

### `analyze_file(path, inputs=None, max_paths=10, seed=0)`

Analyze an MLIR file.

```python
from debugger.agent import analyze_file

report = analyze_file(
    "debugger/fixtures/conditional_branch.mlir",
    inputs={"a": 5, "b": 3},
    max_paths=10,
    seed=0,
)
```

Arguments:

- `path` (`str | pathlib.Path`): MLIR file to analyze.
- `inputs` (`Mapping[str, Any]`, optional): concrete integer values for function
  arguments. A leading `%` in a name is stripped.
- `max_paths` (`int`): maximum number of feasible paths to explore (default `10`).
  Negative values produce a `limit` diagnostic.
- `seed` (`int | None`): deterministic path-exploration seed (default `0`).

A missing or unreadable file is returned as an `io` diagnostic, not an exception.

### `analyze_text(text, source_name="<memory>", inputs=None, max_paths=10, seed=0)`

Analyze MLIR source held in memory. The text is written to a temporary file so the
same parser and stepper path is used.

### Report shape

```json
{
  "schema_version": "1.0",
  "status": "ok",
  "program": "path/to/program.mlir",
  "function": "max",
  "diagnostics": [],
  "paths": [
    {
      "index": 0,
      "inputs": {"a": 2, "b": 3},
      "path_condition": ["a < b"],
      "return_value": "b",
      "depth": 1
    }
  ],
  "summary": {
    "path_count": 1,
    "function_count": 1,
    "truncated": false,
    "limit_reason": null,
    "seed": 0,
    "duration_ms": 12.34,
    "compiler": {
      "source": "mlir-opt",
      "available": true,
      "tool": "/usr/bin/mlir-opt"
    },
    "unsupported_operations": 0
  }
}
```

Fields:

- `status`: `ok` or `error`. It is `error` when any diagnostic has severity `error`.
- `function`: analyzed function name, or `null`.
- `diagnostics`: objects with `severity` (`error`, `warning`, `info`), `kind`, `message`,
  `line`, and `operation`. Kinds include `parse`, `execution`, `path`, `limit`, `input`,
  `io`, and `validation`.
- `paths`: feasible paths with concrete `inputs`, symbolic `path_condition`, optional
  `return_value`, and exploration `depth`.
- `summary.compiler.source`: `mlir-opt`, `internal`, `remote`, or `unavailable`.
  Validation is local-first; remote validation is opt-in through
  `debugger.compiler.validate_mlir_text(..., endpoint=...)`.
- `summary.truncated` / `summary.limit_reason`: report exploration limits instead of
  silently dropping work.
- `summary.unsupported_operations`: number of unsupported-operation warnings.

### Command line

```bash
smlir analyze program.mlir --json
python -m debugger analyze program.mlir --json

python -m debugger analyze program.mlir \
  --input a=5 --input b=3 \
  --max-paths 5 --seed 0 --json
```

Options:

- `--input NAME=VALUE`: concrete integer input (repeatable).
- `--max-paths N`: maximum feasible paths (default `10`).
- `--seed N`: deterministic exploration seed (default `0`).
- `--json`: emit the complete report. Without it, a human summary is printed.

Exit codes: `0` when `status == "ok"`, `1` for analysis errors, `2` for CLI usage errors.

### Compiler validation

```python
from debugger.compiler import validate_mlir_file, validate_mlir_text

result = validate_mlir_text("func.func @main() { return }")
result = validate_mlir_file("program.mlir", fallback_to_internal=True)
```

`validate_mlir_text(text, filename="<memory>", *, local_tool=None, endpoint=None,
fallback_to_internal=False, timeout=30)` and `validate_mlir_file(path, *, ...)` try a
local `mlir-opt` first, then an explicitly configured remote endpoint, then the in-tree
parser only when `fallback_to_internal=True`. The result carries `valid`, `source`,
`available`, `tool`, and `diagnostics`.

## 2. DAP client API

`dap_client.core.client.DAPClient` launches the stdio DAP server as a subprocess and
manages the session lifecycle.

### Constructor

```python
DAPClient(debugger_path=None, timeout=30, read_timeout=10)
```

- `debugger_path` (`str`, optional): DAP server script. Auto-detected when omitted.
- `timeout` (`int`): connection timeout in seconds.
- `read_timeout` (`int`): response read timeout in seconds.

Use as a context manager or call `connect()` / `close()` explicitly:

```python
from dap_client.core.client import DAPClient

with DAPClient() as client:
    client.initialize(adapter_id="mlir-debugger", client_id="example")
    client.launch(program="debugger/fixtures/conditional_branch.mlir")
    client.set_breakpoints(
        source={"path": "debugger/fixtures/conditional_branch.mlir"},
        breakpoints=[{"line": 6}],
    )
    client.configuration_done()
    client.continue_execution(thread_id=1)
    threads = client.get_threads()
    stack = client.get_stacktrace(thread_id=1)
    scopes = client.get_scopes(frame_id=1)
    variables = client.get_variables(variable_reference=1)
    client.disconnect()
```

### Session lifecycle

- `connect() -> bool`: start the adapter subprocess and connect.
- `initialize(adapter_id="mlir-debugger", client_id="automated-test-client") -> dict`
- `launch(program, no_debug=True, **kwargs) -> dict`: `kwargs` are forwarded to the
  launch request arguments.
- `set_breakpoints(source, breakpoints, line_breakpoints=None, column_breakpoints=None)
  -> dict`
- `configuration_done() -> dict`
- `continue_execution(thread_id) -> dict`
- `disconnect(terminate_debuggee=True) -> dict`
- `close() -> None`: disconnect the session and close the subprocess connection.

### Inspection and evaluation

- `get_threads() -> dict`
- `get_stacktrace(thread_id) -> dict`
- `get_scopes(frame_id) -> dict`
- `get_variables(variable_reference) -> dict`
- `evaluate(expression, frame_id=None) -> dict`

### Symbolic commands

- `symbolic_set_mode(enabled=True) -> dict`
- `symbolic_evaluate(expression, frame_id=0) -> dict`
- `symbolic_explore_paths(max_paths=10) -> dict`
- `symbolic_get_constraints() -> dict`

### Events

Register a handler per event type:

```python
def on_stopped(event):
    print(f"stopped: {event}")

client.register_event_handler("stopped", on_stopped)
client.register_event_handler("output", on_output)
```

Common events are `stopped`, `continued`, `output`, `breakpoint`, `exited`, and
`terminated`.

## 3. Test generation API

Both generators live in `dap_client.generator` and use `DAPClient` internally.

### `TestCaseGenerator`

```python
TestCaseGenerator(debugger_path=None, timeout=30, read_timeout=10)
```

- `connect() -> bool`
- `disconnect() -> None`
- `generate_from_program(program_path, max_paths=10, test_name=None)
  -> list[dict]`
- `save_test_scripts(test_scripts, output_dir="generated_tests") -> list[str]`

The generator enables symbolic mode, launches the program without debugging, calls
`symbolic_explore_paths`, and builds one test script per feasible path.

### `PathAwareGenerator`

Subclasses `TestCaseGenerator`:

```python
PathAwareGenerator(debugger_path=None, timeout=30, read_timeout=10)
```

- `generate_for_branch_condition(program_path, condition_expr, test_name=None,
  max_attempts=5) -> list[dict]`
- `generate_edge_cases(program_path, variable_ranges, test_name=None, num_cases=5)
  -> list[dict]`
- `generate_memory_model_tests(program_path, test_name=None) -> list[dict]`
- Inherits `generate_from_program` and `save_test_scripts`.

`variable_ranges` maps variable names to `(min, max)` tuples. Methods return an empty
list when Z3 is unavailable or generation fails.

## 4. Test runner and orchestration API

### `TestRunner`

```python
TestRunner(debugger_path=None, timeout=30, read_timeout=10)
```

- `connect() -> bool`
- `disconnect() -> None`
- `run_test_script(test_script_data, script_path=None) -> dict`
- `run_test_file(test_script_path) -> dict`
- `get_summary() -> dict`
- `save_results(output_path="test_results.json") -> str`

`run_test_script` executes the `session` steps and returns a result with `success`,
`steps`, `duration`, and any step-level errors. `get_summary` aggregates
`total_tests`, `passed_tests`, `failed_tests`, `success_rate`, `total_duration`, and
`results`.

### `TestOrchestrator`

```python
TestOrchestrator(debugger_path=None, timeout=30, read_timeout=10, max_workers=None)
```

- `run_test_files(test_files, parallel=True) -> dict`
- `generate_and_run(program_path, max_paths=5, output_dir="generated_tests",
  run_tests=True, clean_generated=False) -> dict`
- `run_memory_model_tests(program_path, output_dir="memory_model_tests",
  run_tests=True) -> dict`
- `save_report(results, output_path="test_report.json") -> str`
- `print_summary(results) -> None`

Aggregated reports include `total_tests`, `passed_tests`, `failed_tests`,
`success_rate`, step counts, timing, and per-test results.

## 5. Trace execution and validation API

`dap_trace_library` is a thin batch adapter over `dap_client`; it does not implement a
second execution stack.

### `TraceExecutor`

```python
from dap_trace_library.execution.trace_executor import TraceExecutor

executor = TraceExecutor(debugger_path=None, timeout=30)
result = executor.execute_file("trace.json")
```

- `execute_trace(trace_data, trace_name="unknown") -> dict`
- `execute_file(trace_file) -> dict`
- `execute_directory(directory, recursive=True) -> dict`
- `execute_with_validation(trace_data, validator=None) -> dict`
- `generate_report(results=None) -> dict`

Execution delegates to `dap_client.runner.test_runner.TestRunner`.

### `TraceValidator`

```python
from dap_trace_library.validation.trace_validator import TraceValidator

validator = TraceValidator(strict=False)
result = validator.validate_file("trace.json")
```

- `validate_file(filepath) -> dict`
- `validate_trace(trace_data, source="unknown") -> dict`
- `validate_directory(directory, recursive=True) -> dict`
- `validate_trace_execution(trace_data, execution_result) -> dict`

The structural schema is owned by `dap_client/schema/test_script_schema.json`; the
validator adds semantic checks only.

## 6. Core debugger API

### DAP server

```bash
python -m debugger dap
python debugger/dap_server.py
```

The server speaks DAP over stdin/stdout with `Content-Length` framing. It is normally
launched by `dap_client`.

### Interpreter

`debugger.interpreter` exports `MLIRValue`, `BasicBlock`, `MLIRFunction`, `SymbolicState`,
`MLIRParser`, `SymbolicInterpreter`, `ConcolicInterpreter`, `ExecutionStepper`,
`SymbolicExpressionEvaluator`, `PathExplorer`, and `SymbolicVariableTracker`.

### Parser

```python
from debugger.parser import parse_string, parse_file

module = parse_string("func.func @main() { return }")
module = parse_file("program.mlir")
```

The parser is a vendored pymlir fork with dialect definitions under
`debugger/parser/dialects/`.

## 7. Protocol and connection utilities

### Schema validation

```python
from dap_client.schema import load_test_script, validate_test_script, TestScript

script = load_test_script("trace.json")
error = validate_test_script(script)
```

`load_test_script` raises `FileNotFoundError` or a jsonschema `ValidationError`.
`SCHEMA_PATH` points at the bundled schema.

### Protocol messages

`dap_client.protocol` exports `DAPRequest`, `DAPResponse`, `DAPEvent`, and the request
classes (`InitializeRequest`, `LaunchRequest`, `SetBreakpointsRequest`,
`ConfigurationDoneRequest`, `ContinueRequest`, `DisconnectRequest`,
`SymbolicSetModeRequest`, `SymbolicEvaluateRequest`, `SymbolicExplorePathsRequest`,
`SymbolicGetConstraintsRequest`). Message constants are exported from the same package.

### Stdio connection

`dap_client.core.stdio_connection` provides `StdioConnection` and
`DAPConnectionError`. `StdioConnection(debugger_path=None, timeout=30, read_timeout=10)`
manages the subprocess pipes and DAP framing. It is normally used through `DAPClient`.

## 8. Examples

```bash
python dap_client/examples/basic_session.py
python dap_client/examples/full_workflow.py --program debugger/fixtures/conditional_branch.mlir
```

Minimal agent loop:

```python
from debugger.agent import analyze_file

report = analyze_file("program.mlir", seed=0)
if report["status"] != "ok":
    for diagnostic in report["diagnostics"]:
        if diagnostic["severity"] == "error":
            print(diagnostic["kind"], diagnostic.get("line"), diagnostic["message"])
else:
    for path in report["paths"]:
        print(path["inputs"], "->", path["return_value"])
```

## Resources

- [Debug Adapter Protocol](https://microsoft.github.io/debug-adapter-protocol/)
- [MLIR Documentation](https://mlir.llvm.org/)
- [Z3 Python API](https://z3prover.github.io/api/html/namespacez3py.html)
