# parsers.py
from utils import log

def extract_connection_info(cs_data):
    """从 K8s JSON 中提取原始连接字符串"""
    ssh_address = None
    jupyterlab_address = None
    status = cs_data.get('status', {})

    # 1. 提取 SSH
    if 'sshAccess' in status and 'format' in status['sshAccess']:
        ssh_address = status['sshAccess']['format']
    elif 'sshEndpoint' in status:
        ssh_address = status['sshEndpoint']
    
    # 2. 提取 Jupyter
    if 'jupyterAccess' in status and 'domain' in status['jupyterAccess']:
        jupyterlab_address = status['jupyterAccess']['domain']
    elif 'jupyterlabEndpoint' in status:
        jupyterlab_address = status['jupyterlabEndpoint']
        
    return ssh_address, jupyterlab_address

def parse_ssh_string(ssh_str):
    """解析 SSH 字符串为 host, port, user"""
    if not ssh_str:
        return None, None, None

    host, port, user = None, 22, "root"

    try:
        if ssh_str.strip().startswith("ssh "):
            parts = ssh_str.split()
            if '-p' in parts:
                port = int(parts[parts.index('-p') + 1])
            user_host = parts[-1]
            if '@' in user_host:
                user, host = user_host.split('@')
            else:
                host = user_host
        elif '@' in ssh_str:
            user, host_part = ssh_str.split('@')
            if ':' in host_part:
                host, port_str = host_part.split(':')
                port = int(port_str)
            else:
                host = host_part
                port = 22
        else:
            log("WARN", f"Unrecognized SSH string format: {ssh_str}")
            return None, None, None

        return host, port, user
    except Exception as e:
        log("ERROR", f"Failed to parse SSH string '{ssh_str}': {e}")
        return None, None, None