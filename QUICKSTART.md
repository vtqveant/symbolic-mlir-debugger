# Symbolic MLIR Debugger - Quick Start Guide

Get started with the Symbolic MLIR Debugger in **5 minutes** or less!

## 🚀 Installation (1 minute)

### Prerequisites
- Python 3.8 or higher
- Git (optional, for cloning)

### Method 1: One-Command Setup (Recommended)

```bash
# Clone repository (if not already cloned)
git clone https://github.com/vtqveant/symbolic-mlir-debugger.git
cd symbolic-mlir-debugger

# Run the setup script (Linux/macOS)
./setup.sh

# Or run the setup script (Windows PowerShell)
.\setup.ps1
```

The setup script will automatically:
- Create a virtual environment
- Install all dependencies
- Verify the installation
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

# 4. Verify installation
python verify_setup.py
```

✅ **Done!** You're ready to use the debugger.

## 🎯 Your First Debugging Session (4 minutes)

### Step 1: Start the TCP Wrapper

The DAP server uses stdin/stdout, but the DAP client expects TCP. You need the TCP wrapper:

```bash
# Terminal 1 - Start the wrapper
python dap_client/integration/server.py
```

You should see:
```
✅ TCP wrapper listening on localhost:5678
✅ Ready for DAP client connections
```

### Step 2: Run a Basic Example

```bash
# Terminal 2 - Run basic example
python dap_client/examples/basic_session.py
```

This will:
1. Connect to the TCP wrapper
2. Initialize a debugging session
3. Launch an MLIR program
4. Set breakpoints
5. Start execution

### Step 3: Verify It Works

You should see output like:
```
✅ Connected successfully!
✅ Session initialized
✅ Program launched
✅ Breakpoint set
✅ Configuration done
```

## 📚 Next Steps

### 1. Try More Examples

```bash
# TCP wrapper example
python dap_client/examples/tcp_wrapper_example.py

# Manual wrapper test
python dap_client/integration/server.py
python dap_client/examples/basic_session.py
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

## 🔧 Quick Reference

### Activate Virtual Environment

**Linux/macOS:**
```bash
source .venv/bin/activate
```

**Windows:**
```powershell
.\venv\Scripts\Activate.ps1
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

### Start TCP Wrapper

```bash
python dap_client/integration/server.py
```

### Verify Installation

```bash
python verify_setup.py
```

## 🐛 Troubleshooting

### Issue: "Command not found: python"
**Solution:** Use `python3` instead:
```bash
python3 -m venv .venv
python3 setup.sh
```

### Issue: Virtual environment not found
**Solution:** Run the setup script first:
```bash
./setup.sh  # or powershell .\setup.ps1
```

### Issue: "Connection refused" error
**Solution:** Make sure the TCP wrapper is running:
```bash
python dap_client/integration/server.py
```

### Issue: "No module named 'z3'"
**Solution:** Ensure virtual environment is activated and dependencies are installed:
```bash
source .venv/bin/activate  # or activate on Windows
python verify_setup.py
```

### Issue: Python version too old
**Solution:** Use Python 3.8 or higher. Check version:
```bash
python3 --version  # Should show 3.8 or higher
```

### Issue: Setup script fails on macOS
**Solution:** You may need to enable script execution:
```bash
chmod +x setup.sh
```

### Issue: Windows PowerShell execution policy
**Solution:** Run PowerShell as Administrator and execute:
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

## 🎓 Learning Path

1. **Start Here** → Quick Start Guide (this file)
2. **Basic Usage** → `dap_client/examples/basic_session.py`
3. **Complete Workflow** → `dap_client/examples/tcp_wrapper_example.py`
4. **Advanced Features** → Check `dap_client/examples/` directory
5. **API Reference** → See inline docstrings in code

## 📞 Getting Help

- **Documentation**: Read the main [README.md](README.md)
- **DAP Client Docs**: See [dap_client/README.md](dap_client/README.md)
- **Issues**: Check [GitHub Issues](https://github.com/vtqveant/symbolic-mlir-debugger/issues)
- **Examples**: Explore the `examples/` directories

## 🚀 Ready for More?

Now that you have the basics working, explore:
- **Symbolic debugging** with Z3 integration
- **Test generation** from MLIR programs
- **Path exploration** for coverage analysis
- **Custom dialect** development

---

**Time Check:** If you followed this guide, you should be up and running in **under 5 minutes**! 🎉

**Next:** Read the [TUTORIAL.md](docs/TUTORIAL.md) for a more comprehensive walkthrough.
