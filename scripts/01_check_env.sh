#!/bin/bash
set -e # 遇到错误立即退出

echo "=============================================="
echo ">>> [Step 1] System & Environment Check"
echo "=============================================="

# 1. Check OS
if [ -f /etc/os-release ]; then
    OS_NAME=$(grep PRETTY_NAME /etc/os-release | cut -d= -f2 | tr -d '"')
    echo "✅ OS: $OS_NAME"
else
    echo "⚠️  Unknown OS"
fi

# 2. Check Conda
if command -v conda &> /dev/null; then
    echo "✅ Conda: $(conda --version | head -n 1)"
    echo "   Active Env: ${CONDA_DEFAULT_ENV:-None}"
else
    if [ -f "/root/miniconda3/bin/conda" ]; then
        export PATH="/root/miniconda3/bin:$PATH"
        echo "✅ Conda found (manually added to PATH)"
    elif [ -f "/opt/conda/bin/conda" ]; then
        export PATH="/opt/conda/bin:$PATH"
        echo "✅ Conda found (in /opt/conda)"
    else
        echo "⚠️  Conda not found (This is OK if using native Python)"
    fi
fi

# 3. Check Python Packages
echo "Checking critical packages..."
REQUIRED_PACKAGES="torch|numpy"
INSTALLED=$(pip list 2>/dev/null | grep -E -i "$REQUIRED_PACKAGES" || true)

if [ -n "$INSTALLED" ]; then
    echo "✅ Key packages found:"
    echo "$INSTALLED" | sed 's/^/   - /'
else
    echo "❌ Critical packages (torch/numpy) not found in pip list."
fi

echo "✨ Step 1 Passed."