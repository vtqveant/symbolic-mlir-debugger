# Agent Guidelines for Symbolic MLIR Debugger

This document provides guidelines for AI agents working on the Symbolic MLIR Debugger project. It includes build commands, testing instructions, and code style conventions.

## Project Structure

- `debugger/`: Python symbolic debugger and DAP server
  - `interpreter/`: Core symbolic execution engine
  - `parser/`: MLIR parser and dialect definitions
  - `tests/`: Python unit tests
  - `fixtures/`: Test MLIR files
- `vscode/`: VS Code extension (TypeScript)
  - `src/`: Extension source code

## Build and Test Commands

### Python Debugger

All commands should be run from the `debugger/` directory unless otherwise noted.

**Install dependencies:**
```bash
cd debugger
pip install -r requirements.txt
```

**Running tests:**
```bash
python -m pytest                         # Run all tests
python -m pytest -v                      # Verbose output
python -m pytest -m parser               # Run tests with marker 'parser'
python -m pytest --cov                   # Run with coverage
python -m pytest --cov-report=html       # Generate HTML coverage report
```

**Running a single test:**
```bash
python -m pytest tests/test_parser.py::test_cmpi_parsing
python -m pytest tests/test_parser.py -k "test_cmpi_parsing"
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
# Run black formatting
python -m black .

# Check formatting without applying changes
python -m black --check .

# Run flake8 linting
python -m flake8 .
```

**Note:** The project uses black (line-length=100) for formatting and flake8 for linting. Always run black before committing to ensure consistent formatting.

### VS Code Extension

All commands should be run from the `vscode/` directory.

**Install dependencies:**
```bash
cd vscode
npm install
```

**Development commands:**
```bash
npm run compile          # Compile TypeScript (tsc)
npm run lint             # ESLint on src directory
npm run typecheck        # TypeScript type checking (no emit)
npm run test             # Currently runs typecheck
npm run build            # Bundle with esbuild (extension + web)
npm run watch            # Watch mode for extension
npm run watch-web        # Watch mode for web extension
npm run package          # Package extension with vsce
npm run publish          # Publish extension to marketplace
```

## Code Style Guidelines

### Python

**Imports:** Group imports: standard library, third-party, local. Use absolute imports for local modules. Sort imports alphabetically within groups. Use `from typing import ...` for type hints.

**Naming:** `snake_case` for functions, variables, modules. `PascalCase` for classes. `UPPER_SNAKE_CASE` for constants. Private members start with `_`.

**Type hints:** Use type hints for function arguments and return values. Use `Optional[T]` for nullable values. Use `Union` for multiple possible types. Use `List[T]`, `Dict[K, V]`, `Tuple[...]` etc.

**Error handling:** Use `try/except` with specific exception types where possible. Log errors with `logger.error()` (see logging). Avoid bare `except:` clauses; use `except Exception:` if needed. Raise appropriate exceptions with descriptive messages.

**Logging:** Use the `logging` module. Create module-level logger: `logger = logging.getLogger(__name__)`. Use appropriate log levels: `debug`, `info`, `warning`, `error`. Prefer structured logging over print statements.

**Docstrings:** Use triple double quotes (`"""`). First line summary, blank line, detailed description. Include `Args:` and `Returns:` sections for functions/methods. Use Google style docstrings (as seen in existing code).

**Formatting:** Indent with 4 spaces (no tabs). Line length: aim for 79-99 characters (no strict limit). Use double quotes for strings (consistent with existing code). Use f-strings for string interpolation.

**Testing:** Write unit tests in `tests/` directory. Use `pytest` fixtures defined in `conftest.py`. Use descriptive test function names prefixed with `test_`. Use `@pytest.mark.*` decorators for test markers. Provide docstrings explaining test purpose.

### TypeScript (VS Code Extension)

**Imports:** Use ES6 imports/exports. Group imports: external modules, internal modules. Use relative paths for internal modules.

**Naming:** `camelCase` for variables, functions, methods. `PascalCase` for classes, interfaces, types, enums. `UPPER_SNAKE_CASE` for constants. Prefix private members with `_`.

**Types:** Use TypeScript strict mode. Explicitly type function parameters and return values. Use interfaces for object shapes. Avoid `any`; use `unknown` or specific types.

**Error handling:** Use `try/catch` for synchronous errors. Use promise `.catch()` or `async/await` with `try/catch` for async. Log errors with `console.error` or extension logger.

**Formatting:** Follow ESLint configuration (see `.eslintrc`). Use 2-space indentation (as per TypeScript/VS Code conventions). Use semicolons. Use double quotes for strings (consistent with existing code).

## Development Workflow

1. **Before making changes:** Ensure tests pass (`python -m pytest` / `npm run test`). Run linting if available (`npm run lint` for TypeScript). For Python, run `python -m black --check .` and `python -m flake8 .` (see Linting and formatting section).
2. **After making changes:** Run relevant unit tests. Verify linting and type checking. Update/add tests as needed. For Python, run `python -m black .` to format code before committing.
3. **Commit messages:** Use present tense imperative ("Add feature", "Fix bug"). Reference issue numbers if applicable. Keep first line under 50 characters, body lines under 72.

## Common Pitfalls

- **Python path issues:** Ensure `sys.path` includes project root when running scripts.
- **Z3 version:** Requires `z3-solver>=4.12.0`.
- **MLIR parsing:** The parser uses Lark grammar; dialect definitions are in `parser/dialects/`.
- **DAP server:** The debug adapter uses stdin/stdout JSON‑RPC; see `dap_server.py`.

## Resources

- [MLIR Documentation](https://mlir.llvm.org/)
- [Z3 Python API](https://z3prover.github.io/api/html/namespacez3py.html)
- [Debug Adapter Protocol](https://microsoft.github.io/debug-adapter-protocol/)
- [VS Code Extension API](https://code.visualstudio.com/api)

---
*This file is intended for AI agents working on the project. Update as needed.*