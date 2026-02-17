#!/bin/bash
# Symbolic MLIR Debugger - Setup Script (Linux/macOS)
# This script sets up the complete development environment in 5 minutes

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}╔════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║  Symbolic MLIR Debugger - Setup Script              ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════════════════════╝${NC}"
echo ""

# Check Python version
echo -e "${YELLOW}[1/7] Checking Python version...${NC}"
python3 --version
PYTHON_VERSION=$(python3 --version | awk '{print $2}')
PYTHON_MAJOR=$(echo $PYTHON_VERSION | cut -d. -f1)
PYTHON_MINOR=$(echo $PYTHON_VERSION | cut -d. -f2)

if [ "$PYTHON_MAJOR" -lt 3 ] || ([ "$PYTHON_MAJOR" -eq 3 ] && [ "$PYTHON_MINOR" -lt 8 ]); then
    echo -e "${RED}Error: Python 3.8 or higher is required${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Python $PYTHON_VERSION is compatible${NC}"
echo ""

# Create virtual environment
echo -e "${YELLOW}[2/7] Creating virtual environment...${NC}"
if [ -d ".venv" ]; then
    echo -e "${YELLOW}Virtual environment already exists. Overwriting...${NC}"
    rm -rf .venv
fi
python3 -m venv .venv
echo -e "${GREEN}✓ Virtual environment created at .venv${NC}"
echo ""

# Activate virtual environment
echo -e "${YELLOW}[3/7] Activating virtual environment...${NC}"
source .venv/bin/activate
echo -e "${GREEN}✓ Virtual environment activated${NC}"
echo ""

# Upgrade pip
echo -e "${YELLOW}[4/7] Upgrading pip...${NC}"
pip install --upgrade pip setuptools wheel
echo -e "${GREEN}✓ Pip upgraded successfully${NC}"
echo ""

# Install dependencies
echo -e "${YELLOW}[5/7] Installing dependencies...${NC}"
pip install -r requirements.txt
echo -e "${GREEN}✓ All dependencies installed${NC}"
echo ""

# Verify installation
echo -e "${YELLOW}[6/7] Verifying installation...${NC}"
python verify_setup.py
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ All checks passed${NC}"
else
    echo -e "${RED}✗ Verification failed. Please check the errors above.${NC}"
    deactivate
    exit 1
fi
echo ""

# Installation summary
echo -e "${YELLOW}[7/7] Setup complete!${NC}"
echo ""
echo -e "${GREEN}╔════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║  Installation Summary                                  ║${NC}"
echo -e "${GREEN}╠════════════════════════════════════════════════════════╣${NC}"
echo -e "${GREEN}║  • Virtual Environment: .venv                         ║${NC}"
echo -e "${GREEN}║  • Dependencies: requirements.txt                     ║${NC}"
echo -e "${GREEN}║  • Python Version: $PYTHON_VERSION                      ║${NC}"
echo -e "${GREEN}║  • Status: READY TO USE                               ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${YELLOW}Next steps:${NC}"
echo -e "  1. Activate the virtual environment: ${GREEN}source .venv/bin/activate${NC}"
echo -e "  2. Run tests: ${GREEN}python -m pytest debugger/tests/ -v${NC}"
echo -e "  3. Start the TCP wrapper: ${GREEN}python dap_client/integration/server.py${NC}"
echo -e "  4. Read QUICKSTART.md for more details"
echo ""
