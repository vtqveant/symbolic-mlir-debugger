# Symbolic MLIR Debugger - Quick Start Guide

Get started with the Symbolic MLIR Debugger in **5 minutes** or less!

## 🚀 Installation (2 minutes)

### Prerequisites
- Python 3.8 or higher
- Git

### Step 1: Clone the Repository
```bash
git clone https://github.com/vtqveant/symbolic-mlir-debugger.git
cd symbolic-mlir-debugger
```

### Step 2: Install Dependencies
```bash
pip install -r requirements.txt
```

### Step 3: Install Optional Dependencies (Recommended)
```bash
pip install z3-solver  # For symbolic execution capabilities
```

✅ **Done!** You now have the debugger installed.

## 🎯 Your First Debugging Session (3 minutes)

### Step 1: Start the TCP Wrapper
The DAP server uses stdin/stdout, but the DAP client expects TCP. You need the TCP wrapper:

```bash
# In Terminal 1 - Start the wrapper
python dap_client/integration/server.py
```

You should see:
```
✅ TCP wrapper listening on localhost:5678
✅ Ready for DAP client connections
```

### Step 2: Run a Basic Example
```bash
# In Terminal 2 - Run basic example
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

### 1. Try the TCP Wrapper Example
```bash
python dap_client/examples/tcp_wrapper_example.py
```
This shows the complete workflow with better explanations.

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

## 🔧 Common Issues & Solutions

### Issue: "Connection refused" error
**Solution:** Make sure the TCP wrapper is running:
```bash
python dap_client/integration/server.py
```

### Issue: Missing dependencies
**Solution:** Install all requirements:
```bash
pip install -r requirements.txt
pip install z3-solver
```

### Issue: Python version problems
**Solution:** Use Python 3.8+:
```bash
python --version  # Should show 3.8 or higher
```

## 🎓 Learning Path

1. **Start Here** → Quick Start Guide (this file)
2. **Basic Usage** → `dap_client/examples/basic_session.py`
3. **Complete Workflow** → `dap_client/examples/tcp_wrapper_example.py`
4. **Advanced Features** → Check `dap_client/examples/` directory
5. **API Reference** → See inline docstrings in code

## 📞 Getting Help

- **Documentation**: Read the main [README.md](README.md)
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