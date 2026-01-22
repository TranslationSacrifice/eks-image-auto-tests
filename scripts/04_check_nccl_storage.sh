#!/bin/bash
set -e

echo "=============================================="
echo ">>> [Step 4] NCCL & Storage Check"
echo "=============================================="

MOUNT_PATH="/root/data"
NCCL_TEST_DIR="$MOUNT_PATH/nccl-tests" # 放在共享盘，避免重复下载
BUILD_DIR="/tmp/nccl-build"

# --- Part 1: Storage Check ---
echo "--- Storage I/O Check ($MOUNT_PATH) ---"
if [ ! -d "$MOUNT_PATH" ]; then
    echo "❌ Mount path $MOUNT_PATH does not exist!"
fi

# 写入测试
TEST_FILE="$MOUNT_PATH/io_test_$(date +%s).tmp"
if echo "WriteTest" > "$TEST_FILE"; then
    echo "✅ Write Permission: OK"
    rm "$TEST_FILE"
else
    echo "❌ Write Permission: FAILED"
fi

SOURCE_CODE_PATH="$MOUNT_PATH/nccl-tests"
BUILD_DIR="/tmp/nccl-build"

echo "=============================================="
echo ">>> [Step 4] Storage & NCCL Check"
echo "=============================================="

# ==========================================
# Part 1: 存储挂载与读写测试
# ==========================================
echo "📂 [Part 1] Storage I/O Check ($MOUNT_PATH)"

if [ ! -d "$MOUNT_PATH" ]; then
    echo "❌ Mount path $MOUNT_PATH does not exist!"
fi

# 写入测试
TEST_FILE="$MOUNT_PATH/io_test_$(date +%s).tmp"
if echo "WriteTest_$(date)" > "$TEST_FILE"; then
    echo "✅ Storage Write: OK"
else
    echo "❌ Storage Write: FAILED"
fi

# 读取测试
if grep -q "WriteTest" "$TEST_FILE"; then
    echo "✅ Storage Read: OK"
else
    echo "❌ Storage Read: FAILED"
    rm -f "$TEST_FILE"
fi

# 清理
rm -f "$TEST_FILE"
echo "----------------------------------------------"

# ==========================================
# Part 2: NCCL 智能编译与测试
# ==========================================
echo "🚀 [Part 2] NCCL Integration Test"

# --- 0. 检查 NVCC ---
if ! command -v nvcc &> /dev/null; then
    echo "❌ nvcc not found. Cannot compile NCCL tests."
    echo "   Please use a CUDA-devel image."
fi
echo "✅ NVCC Found: $(nvcc --version | grep release | awk '{print $6}')"

# --- 1. 准备源码 (自动下载) ---
echo "📦 Preparing Source Code..."
if [ ! -d "$SOURCE_CODE_PATH" ]; then
    echo "   Source not found in $SOURCE_CODE_PATH. Cloning..."
    # 尝试访问 GitHub，如果失败则尝试 Gitee 或者报错
    if git clone https://github.com/NVIDIA/nccl-tests.git "$SOURCE_CODE_PATH"; then
        echo "   ✅ Git clone success."
    else
        echo "   ❌ Git clone failed. Please check network."
        exit 1
    fi
else
    echo "   ✅ Found existing source in $SOURCE_CODE_PATH"
fi

# --- 2. NCCL 侦探模式 (环境探测) ---
echo "🕵️‍♂️ Detecting NCCL Headers..."

# 排除 /root/data 和系统目录，加快速度
NCCL_HEADER=$(find /usr /opt -name "nccl.h" 2>/dev/null | head -n 1)

if [ -n "$NCCL_HEADER" ]; then
    echo "   ✅ Found header: $NCCL_HEADER"
    NCCL_HOME_GUESS=$(dirname $(dirname $NCCL_HEADER))
else
    echo "   ⚠️  nccl.h not found."
    echo "   🛠  Attempting auto-fix: install libnccl-dev..."

    # 更新 apt 并安装，使用非交互模式
    export DEBIAN_FRONTEND=noninteractive
    apt-get update >/dev/null 2>&1 && apt-get install -y libnccl-dev >/dev/null 2>&1 || echo "   ❌ apt install failed"
    
    NCCL_HEADER=$(find /usr -name "nccl.h" 2>/dev/null | head -n 1)
    if [ -z "$NCCL_HEADER" ]; then
        echo "   ❌ CRITICAL: Still cannot find nccl.h."
        echo "   Reason: Image likely contains NCCL Runtime only, missing Dev headers."
    fi
    NCCL_HOME_GUESS=$(dirname $(dirname $NCCL_HEADER))
fi

echo "   🎯 NCCL_HOME set to: $NCCL_HOME_GUESS"

# --- 3. 编译环境准备 ---
echo "🔨 Building..."
rm -rf "$BUILD_DIR"
mkdir -p "$BUILD_DIR"
# 复制源码到 /tmp 编译，避免污染共享存储或遇到文件系统锁问题
cp -r "$SOURCE_CODE_PATH"/* "$BUILD_DIR"/
cd "$BUILD_DIR"

export CUDA_HOME=$(dirname $(dirname $(which nvcc)))
echo "   CUDA_HOME: $CUDA_HOME"

# 清理旧构建
make clean >/dev/null 2>&1 || true

# 编译 (静默模式，除非出错)
if make MPI=0 CUDA_HOME=$CUDA_HOME NCCL_HOME=$NCCL_HOME_GUESS -j $(nproc) >/dev/null; then
    echo "   ✅ Compilation Success"
else
    echo "   ❌ Compilation Failed. Retrying with verbose output..."
    make MPI=0 CUDA_HOME=$CUDA_HOME NCCL_HOME=$NCCL_HOME_GUESS -j 1
fi

if [ ! -f "./build/all_reduce_perf" ]; then
    echo "   ❌ Binary not found after make."
fi

# --- 4. 运行测试 ---
echo "🏃 Running all_reduce_perf..."
GPU_COUNT=$(nvidia-smi -L | wc -l)
echo "   GPUs detected: $GPU_COUNT"

# 运行参数：从 128MB 到 512MB，倍增因子 2
if ./build/all_reduce_perf -b 128M -e 512M -f 2 -g "$GPU_COUNT"; then
    echo ""
    echo "✨ Step 4 Passed: NCCL & Storage are healthy."
    exit 0
else
    echo "❌ NCCL Runtime Error"
fi
