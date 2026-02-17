# Symbolic MLIR Debugger - Quick Start Guide

Get started with the Symbolic MLIR Debugger in **5 minutes** or less!

## Installation

### Prerequisites
- Python 3.9 or higher

### Method 1: One-Command Setup (Recommended)

```bash
# Clone repository (if not already cloned)
git clone https://github.com/vtqveant/symbolic-mlir-debugger.git
cd symbolic-mlir-debugger

# Run the setup script (Linux/macOS)
./setup.sh
```

The setup script will automatically:
- Create a virtual environment
- Install all dependencies
- Show you how to activate the environment

### Method 2: Manual Setup

If you prefer manual setup, follow these steps:

```bash
# 1. Clone repository
git clone https://github.com/vtqveant/symbolic-mlir-debugger.git
cd symbolic-mlir-debugger

# 2. Create virtual environment
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt
```

✅ **Done!** You're ready to use the debugger.

## Your First Debugging Session

### Step 1: Run a Basic Example

The DAP client directly communicates with the DAP server via stdio. Simply run:

```bash
python dap_client/examples/basic_session.py
```

This will:
1. Automatically launch the DAP server as a subprocess
2. Initialize a debugging session
3. Launch an MLIR program
4. Set breakpoints
5. Start execution

### Step 2: Verify It Works

You should see output like:
```
✅ Connected successfully!
✅ Session initialized
✅ Program launched
✅ Breakpoint set
✅ Configuration done
```

## Next Steps

### 1. Try More Examples

```bash
# Full workflow example
python dap_client/examples/full_workflow.py
```

### 2. Explore MLIR Examples

Check out the example MLIR files:
```bash
ls debugger/fixtures/*.mlir
```

### 3. Run the Test Suite

```bash
cd debugger
python -m pytest tests/ -v
```

## Quick Reference

### Activate Virtual Environment

**Linux/macOS:**
```bash
source .venv/bin/activate
```

### Deactivate Virtual Environment

```bash
deactivate
```

### Run Tests

```bash
# Run all tests
python -m pytest -v

# Run specific test file
python -m pytest tests/test_parser.py -v

# Run with coverage
python -m pytest --cov=. --cov-report=html
```



### Verify Installation

```bash
python verify_setup.py
```

## Troubleshooting

### Issue: "Command not found: python"
**Solution:** Use `python3` instead:
```bash
python3 -m venv .venv
python3 setup.sh
```

### Issue: Virtual environment not found
**Solution:** Run the setup script first:
```bash
./setup.sh  
```

### Issue: "Connection refused" error
**Solution:** The DAP client now uses direct stdio communication and automatically launches the DAP server. Ensure the debugger path is correct and the DAP server (`debugger/dap_server.py`) is present.

### Issue: "No module named 'z3'"
**Solution:** Ensure virtual environment is activated and dependencies are installed:
```bash
source .venv/bin/activate
python verify_setup.py
```

## Learning Path

1. **Start Here** → Quick Start Guide (this file)
2. **Basic Usage** → `dap_client/examples/basic_session.py`
3. **Complete Workflow** → `dap_client/examples/full_workflow.py`
4. **Advanced Features** → Check `dap_client/examples/` directory
5. **API Reference** → See inline docstrings in code

## Getting Help

- **Documentation**: Read the main [README.md](README.md)
- **DAP Client Docs**: See [dap_client/README.md](dap_client/README.md)
- **Issues**: Check [GitHub Issues](https://github.com/vtqveant/symbolic-mlir-debugger/issues)
- **Examples**: Explore the `examples/` directories

## Ready for More?

Now that you have the basics working, explore:
- **Symbolic debugging** with Z3 integration
- **Test generation** from MLIR programs
- **Path exploration** for coverage analysis
- **Custom dialect** development

---

**Time Check:** If you followed this guide, you should be up and running in **under 5 minutes**! 🎉

**Next:** Read the [TUTORIAL.md](docs/TUTORIAL.md) for a more comprehensive walkthrough.
