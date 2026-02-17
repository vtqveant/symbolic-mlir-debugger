# Symbolic MLIR Debugger - Setup Script (Windows PowerShell)
# This script sets up the complete development environment in 5 minutes

param(
    [Parameter(Mandatory=$false)]
    [switch]$Force
)

# Define colors for output
$Green = "`e[32m"
$Red = "`e[31m"
$Yellow = "`e[33m"
$Reset = "`e[0m"

function Write-OutputColor {
    param([string]$Message, [string]$Color)
    Write-Host $Message -ForegroundColor $Color -NoNewline
}

function Write-Separator {
    param([string]$Title)
    Write-Output ""
    Write-OutputColor "╔════════════════════════════════════════════════════════╗" $Green
    Write-OutputColor "║  $Title                                                  ║" $Green
    Write-OutputColor "╚════════════════════════════════════════════════════════╝" $Green
    Write-Output ""
}

Write-Separator "Symbolic MLIR Debugger - Setup Script"

# Check Python version
Write-OutputColor "[1/7] Checking Python version..." $Yellow
$pythonVersion = python --version 2>&1
Write-Output $pythonVersion

# Parse Python version
$versionArray = $pythonVersion -split ' '
$major = [int]$versionArray[1].Substring(0,1)
$minor = [int]$versionArray[1].Substring(2,1)

if ($major -lt 3 -or ($major -eq 3 -and $minor -lt 8)) {
    Write-OutputColor "Error: Python 3.8 or higher is required" $Red
    exit 1
}

Write-OutputColor "✓ Python $pythonVersion is compatible" $Green
Write-Output ""

# Create virtual environment
Write-OutputColor "[2/7] Creating virtual environment..." $Yellow
if (Test-Path ".venv") {
    if ($Force) {
        Write-Output "Virtual environment exists. Overwriting..."
        Remove-Item -Recurse -Force ".venv"
    } else {
        Write-OutputColor "Virtual environment already exists. Use -Force to overwrite." $Yellow
        exit 1
    }
}

python -m venv .venv
Write-OutputColor "✓ Virtual environment created at .venv" $Green
Write-Output ""

# Activate virtual environment
Write-OutputColor "[3/7] Activating virtual environment..." $Yellow
& ".venv\Scripts\Activate.ps1"
Write-OutputColor "✓ Virtual environment activated" $Green
Write-Output ""

# Upgrade pip
Write-OutputColor "[4/7] Upgrading pip..." $Yellow
python -m pip install --upgrade pip setuptools wheel
Write-OutputColor "✓ Pip upgraded successfully" $Green
Write-Output ""

# Install dependencies
Write-OutputColor "[5/7] Installing dependencies..." $Yellow
python -m pip install -r requirements.txt
Write-OutputColor "✓ All dependencies installed" $Green
Write-Output ""

# Verify installation
Write-OutputColor "[6/7] Verifying installation..." $Yellow
python verify_setup.py
if ($LASTEXITCODE -ne 0) {
    Write-OutputColor "✗ Verification failed. Please check the errors above." $Red
    deactivate
    exit 1
}
Write-OutputColor "✓ All checks passed" $Green
Write-Output ""

# Installation summary
Write-OutputColor "[7/7] Setup complete!" $Yellow
Write-Output ""

Write-Separator "Installation Summary"

Write-OutputColor "  • Virtual Environment: .venv                         " $Green
Write-OutputColor "  • Dependencies: requirements.txt                     " $Green
Write-OutputColor "  • Python Version: $pythonVersion                      " $Green
Write-OutputColor "  • Status: READY TO USE                               " $Green

Write-Output ""
Write-OutputColor "Next steps:" $Yellow
Write-Output "  1. Activate the virtual environment: ${Green}.\.venv\Scripts\activate.ps1${Reset}"
Write-Output "  2. Run tests: ${Green}python -m pytest debugger/tests/ -v${Reset}"
Write-Output "  3. Start the TCP wrapper: ${Green}python dap_client/integration/server.py${Reset}"
Write-Output "  4. Read QUICKSTART.md for more details"
Write-Output ""

deactivate
