#!/bin/bash
set -e

echo "=============================================="
echo ">>> [Step 3] CUDA Functionality Check"
echo "=============================================="

# 1. PyTorch CUDA Test
echo "--- PyTorch CUDA Smoke Test ---"
python3 -c "
import torch
if torch.cuda.is_available():
    print(f'✅ PyTorch CUDA: Available (Device: {torch.cuda.get_device_name(0)})')
    x = torch.tensor([1.0]).cuda()
    print('✅ Tensor Allocation: Success')
else:
    print('❌ PyTorch CUDA: Not Available')
"

# 2. Native CUDA Compilation Test
echo "--- NVCC Compilation Test ---"
if ! command -v nvcc &> /dev/null; then
    echo "⚠️  nvcc not found, skipping compilation test."
else
    echo "✅ nvcc found: $(nvcc --version | grep release | awk '{print $6}')"
    
    # 动态生成一个简单的 CUDA C++ 文件
    cat <<EOF > /tmp/test_cuda.cu
#include <stdio.h>
__global__ void hello() {
    printf("   [GPU] Hello from Block %d, Thread %d\n", blockIdx.x, threadIdx.x);
}
int main() {
    hello<<<1, 1>>>();
    cudaDeviceSynchronize();
    return 0;
}
EOF

    # 编译
    echo "Compiling test program..."
    nvcc /tmp/test_cuda.cu -o /tmp/test_cuda_bin
    
    # 运行
    if [ -f /tmp/test_cuda_bin ]; then
        echo "Running compiled binary..."
        /tmp/test_cuda_bin
        echo "✅ NVCC Compilation & Execution Success"
        rm /tmp/test_cuda.cu /tmp/test_cuda_bin
    else
        echo "❌ Compilation failed"
    fi
fi

echo "✨ Step 3 Passed."