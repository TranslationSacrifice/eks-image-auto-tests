import paramiko
import os
from utils import log

class SSHClient:
    def __init__(self, host, port, user, password=None, key_path=None):
        self.host = host
        self.port = int(port)
        self.user = user
        self.password = password  # 新增：接收密码
        self.key_path = key_path
        self.client = None

    def connect(self):
        log("SSH", f"Connecting to {self.user}@{self.host}:{self.port}...")
        try:
            self.client = paramiko.SSHClient()
            self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            
            # === 修改核心逻辑 ===
            if self.password:
                # 如果提供了密码，优先尝试密码登录
                log("SSH", "Authenticating with PASSWORD...")
                self.client.connect(
                    self.host, 
                    port=self.port, 
                    username=self.user, 
                    password=self.password,
                    look_for_keys=False, # 禁止自动找 Key
                    allow_agent=False,   # 禁止使用 SSH 代理
                    timeout=30
                )
            elif self.key_path and os.path.exists(self.key_path):
                # 如果提供了 Key 路径且文件存在，使用 Key
                log("SSH", f"Authenticating with Private Key ({self.key_path})...")
                self.client.connect(
                    self.host, 
                    port=self.port, 
                    username=self.user, 
                    key_filename=self.key_path,
                    timeout=30
                )
            else:
                raise Exception("No valid password or key provided")
                
            log("SSH", "✅ Connected successfully")
            return True
        except Exception as e:
            log("ERROR", f"SSH Connection failed: {e}")
            return False

    def run_remote_script(self, local_script_path, remote_dir="/root/scripts"):
        # ... (这部分保持不变) ...
        filename = os.path.basename(local_script_path)
        remote_path = f"{remote_dir}/{filename}"
        
        # 1. 创建目录
        self.client.exec_command(f"mkdir -p {remote_dir}")
        
        # 2. 上传
        try:
            sftp = self.client.open_sftp()
            sftp.put(local_script_path, remote_path)
            sftp.close()
        except Exception as e:
            log("ERROR", f"Upload failed for {filename}: {e}")
            return False

        # 3. 执行
        log("TEST", f"Running script: {filename}")
        # 加上 set -e 确保出错即退出
        stdin, stdout, stderr = self.client.exec_command(f"chmod +x {remote_path} && {remote_path}")
        
        exit_code = stdout.channel.recv_exit_status()
        out = stdout.read().decode().strip()
        err = stderr.read().decode().strip()

        if exit_code == 0:
            log("PASS", f"Script {filename} output:\n{out}")
            return True
        else:
            log("FAIL", f"Script {filename} failed:\n{out}\n{err}")
            return False

    def close(self):
        if self.client: self.client.close()