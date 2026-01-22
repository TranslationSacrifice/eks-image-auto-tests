#!/bin/bash
set -e

echo "=============================================="
echo ">>> [Step 2] Hardware & Driver Check"
echo "=============================================="

# 1. GPU Check
echo "--- Checking GPU ---"
if command -v nvidia-smi &> /dev/null; then
    DRIVER_VER=$(nvidia-smi --query-gpu=driver_version --format=csv,noheader | head -n 1)
    GPU_COUNT=$(nvidia-smi -L | wc -l)
    echo "✅ GPU Driver: $DRIVER_VER"
    echo "✅ GPU Count: $GPU_COUNT"
    nvidia-smi -L | sed 's/^/   - /'
else
    echo "❌ nvidia-smi not found"
fi

# 2. HCA (InfiniBand) Check
echo "--- Checking InfiniBand HCA ---"
if command -v ibv_devices &> /dev/null; then
    IB_OUTPUT=$(ibv_devices 2>/dev/null)
    DEVICE_COUNT=$(echo "$IB_OUTPUT" | grep -E "mlx5_" | wc -l)
    
    if [ "$DEVICE_COUNT" -gt 0 ]; then
        echo "✅ HCA Devices Found: $DEVICE_COUNT"
        echo "$IB_OUTPUT" | grep "mlx5_" | sed 's/^/   - /'
    else
        echo "⚠️  ibv_devices command ran but found 0 devices (Ignore if not using IB)."
    fi
else
    echo "⚠️  ibv_devices command not found (infiniband-diags missing)."
fi

echo "✨ Step 2 Passed."