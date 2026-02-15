This is a VSCode extension for Concolic MLIR Debugger

Based on https://github.com/microsoft/vscode-mock-debug
See also: https://code.visualstudio.com/api/extension-guides/debugger-extension

How to build:

1. Install Prerequisites: Ensure you have Node.js and npm installed
2. Install vsce globally using npm:
    $ npm install -g @vscode/vsce
3. Navigate to the source directory:
    $ cd path/to/extension-source
4. Install project dependencies (if required by the extension's package.json file):
    $ npm install
5. Run a build command (if the source requires compilation, e.g., TypeScript to JavaScript):
    $ npm run build
6. Package the extension using vsce:
    $ vsce package --no-yarn

This command generates a .vsix file in the current directory (e.g., my-extension-1.0.0.vsix).

Configuration:

DAP Server Path: Extension automatically detects `dap_server.py` in:
- `debugger/dap_server.py` (workspace relative)
- `symbolic_mlir_debugger/dap_server.py` (workspace relative)
- Parent directories (up to 10 levels)

Manual override:
```json
{
  "mlir-debug.dapServerPath": "custom/path/to/dap_server.py",
  "mlir-debug.pythonPath": "python3"
}
``` 