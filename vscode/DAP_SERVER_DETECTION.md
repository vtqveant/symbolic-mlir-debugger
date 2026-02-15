# DAP Server Path Auto-Detection

## Overview

The MLIR Debug extension now automatically detects the Debug Adapter Protocol (DAP) server path (`dap_server.py`) in multiple common locations, eliminating the need for manual configuration in most cases.

## How It Works

### Path Resolution Priority

The extension searches for `dap_server.py` in the following order:

1. **Absolute Path** (from `mlir-debug.dapServerPath` setting) - if file exists
2. **Workspace-Relative Path** (configured path relative to workspace)
3. **Default Paths** (checked in order):
   - `debugger/dap_server.py`
   - `../debugger/dap_server.py`
   - `../../debugger/dap_server.py`
   - `./debugger/dap_server.py`
   - `symbolic_mlir_debugger/dap_server.py`
   - `../symbolic_mlir_debugger/dap_server.py`
   - `../../symbolic_mlir_debugger/dap_server.py`
   - `./symbolic_mlir_debugger/dap_server.py`
4. **Parent Directory Traversal** - Searches up to 10 levels of parent directories

### Supported Project Structures

The auto-detection supports various project layouts:

- **Standard Workspace**: `workspace/debugger/dap_server.py`
- **Nested Projects**: `workspace/subproject/../../debugger/dap_server.py`
- **Monorepo Structure**: Works regardless of depth
- **Symbolic MLIR**: `workspace/symbolic_mlir_debugger/dap_server.py`

## Configuration

### Automatic Detection (Recommended)

Simply open a workspace containing `dap_server.py` in one of the supported locations, and the extension will automatically find it.

### Manual Configuration

If auto-detection fails or you prefer explicit control, you can configure the path in VS Code settings:

```json
{
  "mlir-debug.dapServerPath": "custom/path/to/dap_server.py"
}
```

### Python Path Configuration

You can also configure the Python interpreter:

```json
{
  "mlir-debug.pythonPath": "python3"
}
```

## Error Handling

If the DAP server cannot be located, the extension provides a clear error message with troubleshooting guidance:

```
MLIR Debug: Could not locate DAP server (dap_server.py). Please ensure it exists in one of the following locations:
  - Relative to workspace folder: debugger/dap_server.py
  - Relative to workspace folder: symbolic_mlir_debugger/dap_server.py
  - Absolute path (configure in settings: mlir-debug.dapServerPath)
```

## Testing

The path resolution logic is thoroughly tested with unit tests covering:

- Success cases (finding file at various locations)
- Error cases (file not found scenarios)
- Configuration override scenarios
- Path resolution order verification

Run tests:
```bash
cd vscode
npm test
```

## Implementation Details

- **Platform Compatibility**: Uses Node.js `path.join()` and `path.dirname()` for cross-platform support
- **Search Depth**: Configurable at 10 levels (see `pathResolver.ts`)
- **Exported Function**: `resolveDapServerPath()` is exported for future optimizations and testing
- **Performance**: No caching implemented (to keep changes minimal), but function signature supports future enhancements

## Troubleshooting

### Auto-Detection Not Working

1. Verify `dap_server.py` exists in one of the supported locations
2. Check that the file has execute permissions
3. Ensure the workspace folder is correctly set
4. Review the VS Code console logs for detailed resolution attempts

### Path Resolution Order

The extension checks paths in order of priority. If multiple files match, the first one found is used. To override this behavior, use explicit configuration.
