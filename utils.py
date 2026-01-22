import subprocess
import sys
from datetime import datetime

def log(step, message):
    """格式化日志输出"""
    print(f"[{datetime.now().strftime('%H:%M:%S')}] [{step}] {message}")

def run_shell(cmd):
    """执行本地 Shell 命令"""
    try:
        # log("SHELL", f"Exec: {cmd}")
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, check=True)
        return True, result.stdout.strip()
    except subprocess.CalledProcessError as e:
        return False, e.stderr.strip()