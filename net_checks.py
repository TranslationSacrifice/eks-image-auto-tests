# net_checks.py
import requests
from utils import log

def check_jupyter(endpoint):
    """Check Jupyter HTTP connection"""
    if not endpoint:
        log("WARN", "No Jupyter endpoint found, skipping check.")
        return
    
    if not endpoint.startswith(('http://', 'https://')):
        url = f"http://{endpoint}"
    else:
        url = endpoint

    log("TEST", f"Checking Jupyter connection to {url}...")
    try:
        requests.packages.urllib3.disable_warnings()
        # 设置短一点的超时，避免卡太久
        resp = requests.get(url, timeout=10, verify=False)
        
        if resp.status_code == 200:
            log("PASS", "JupyterLab connection successful!")
        else:
            log("WARN", f"JupyterLab returned status code: {resp.status_code}")
    except Exception as e:
        # 只打印警告，不中断流程，因为 Jupyter 可能启动慢
        log("WARN", f"JupyterLab connection failed: {e}")