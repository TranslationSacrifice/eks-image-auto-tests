# config.py
import argparse

# === 默认配置常量 ===
# 镜像地址
DEFAULT_IMAGE = "registry-cn-huabei2-internal.ebcloud.com/ebsys/pytorch:2.5.1-cuda12.2-python3.10-ubuntu22.04-v09"
# 脚本目录
SCRIPT_DIR = "./scripts"
# 资源挂载路径
MOUNT_PATH = "/root/data"
# 固定 root 密码（与 main.py 保持一致）
FIXED_ROOT_PASSWORD = "k@z2a8v.yp(R6037"
# 资源存储大小
PVC_SIZE = "256Gi"
# 存储类
DEFAULT_STORAGE_CLASS = "shared-nvme-cn-huabei2"

def get_args():
    parser = argparse.ArgumentParser(description="Automated Cloud Environment Test")
    parser.add_argument("--job-id", default="test01", help="Unique suffix for resource names")
    parser.add_argument("--image", default=DEFAULT_IMAGE, help="Docker image to use")
    parser.add_argument("--gpu-type", default="RTX_4090", help="GPU Type")
    parser.add_argument("--gpu-count", default=1, help="GPU Count")
    parser.add_argument("--key-path", default=None, help="Optional: SSH Key Path")
    parser.add_argument("--cleanup", action="store_true", help="Force cleanup resources even on success")
    parser.add_argument("--storage-class", default=DEFAULT_STORAGE_CLASS, help="K8s StorageClass Name")
    parser.add_argument("--scripts", default="all", help="Comma-separated list of script keywords to run (e.g., 'env,cuda' or '01,04')")
    
    return parser.parse_args()