# DAP Client

A Python client for the Symbolic MLIR Debugger's stdio Debug Adapter Protocol (DAP)
server. It launches the adapter as a subprocess, manages the session lifecycle, and
exposes standard plus symbolic debugging commands.

## Architecture

```
DAPClient (dap_client/core)
  -> StdioConnection (subprocess stdin/stdout, Content-Length framing)
  -> DAPSession (lifecycle, breakpoints, inspection, symbolic requests)
  -> debugger/dap_server.py
```

No network ports are used.

## Install

From the repository root:

```bash
pip install -r requirements.txt
pip install -e . --no-deps
```

## Basic usage

```python
from dap_client.core.client import DAPClient

with DAPClient() as client:
    client.initialize(adapter_id="mlir-debugger", client_id="example")
    client.launch(program="debugger/fixtures/conditional_branch.mlir")
    client.set_breakpoints(
        source={"path": "debugger/fixtures/conditional_branch.mlir"},
        breakpoints=[{"line": 4}],
    )
    client.configuration_done()
    client.continue_execution(thread_id=1)
    threads = client.get_threads()
    stack = client.get_stacktrace(thread_id=1)
    variables = client.get_variables(1)
    client.disconnect()
```

The client also exposes symbolic commands:

- `symbolic_set_mode(enabled=True)`
- `symbolic_evaluate(expression, frame_id=0)`
- `symbolic_explore_paths(max_paths=10)`
- `symbolic_get_constraints()`

## Examples

```bash
python dap_client/examples/basic_session.py
python dap_client/examples/full_workflow.py --program debugger/fixtures/conditional_branch.mlir
```

## Tests

```bash
python -m pytest dap_client/tests
```

The root `README.md` and `AGENTS.md` describe the current architecture and task tracking.
