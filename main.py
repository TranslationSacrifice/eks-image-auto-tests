#!/usr/bin/env python3
import sys
import os
import traceback

# === 导入自定义模块 ===
import config
import parsers
import net_checks
from k8s_handler import K8sManager
from ssh_handler import SSHClient
from utils import log

def main():
    # 1. 获取参数
    args = config.get_args()
    
    pvc_name = f"pvc-{args.job_id}"
    cs_name = f"cs-{args.job_id}"
    
    k8s = K8sManager("demo_cs.yaml")
    success_flag = False

    try:
        log("MAIN", f"=== Start Test (Job ID: {args.job_id}) ===")

        # --- Phase 1: Resource Deployment ---
        log("MAIN", "Step 1: Prepare Shared Storage PVC")
        if not k8s.apply_pvc(pvc_name, size=config.PVC_SIZE, storage_class=args.storage_class):
            raise Exception("Failed to create PVC")

        log("MAIN", "Step 2: Create ContainerServer (Inject Password)")
        if not k8s.apply_cs_with_patch(cs_name, pvc_name, config.MOUNT_PATH, 
                                       args.image, args.gpu_type, args.gpu_count,
                                       config.FIXED_ROOT_PASSWORD):
            raise Exception("Failed to create ContainerServer")

        log("MAIN", "Step 3: Wait for Running")
        cs_data = k8s.wait_for_running(cs_name)

        # --- Phase 2: Information Extraction ---
        log("MAIN", "Step 4: Extract Connection Info")
        raw_ssh, raw_jupyter = parsers.extract_connection_info(cs_data)
        
        if not raw_ssh:
            raise Exception("Failed to extract SSH address from resource status")
        
        log("INFO", f"Raw SSH info: {raw_ssh}")
        log("INFO", f"Raw Jupyter info: {raw_jupyter}")

        ssh_host, ssh_port, ssh_user = parsers.parse_ssh_string(raw_ssh)
        if not ssh_host:
            raise Exception("Could not parse SSH host/port")

        # --- Phase 3: Validation & Execution ---
        net_checks.check_jupyter(raw_jupyter)

        ssh = SSHClient(
            host=ssh_host, 
            port=ssh_port, 
            user=ssh_user, 
            password=config.FIXED_ROOT_PASSWORD,
            key_path=args.key_path
        )
        
        if ssh.connect():
            if not os.path.exists(config.SCRIPT_DIR):
                os.makedirs(config.SCRIPT_DIR)
                log("WARN", f"Script dir {config.SCRIPT_DIR} created but empty.")

            all_scripts = sorted([f for f in os.listdir(config.SCRIPT_DIR) if f.endswith('.sh')])

            scripts_to_run = []
            if args.scripts.lower() == "all":
                scripts_to_run = all_scripts
            else:
                keywords = args.scripts.split(',')
                for s in all_scripts:
                    # 只要文件名包含任一关键字，就选中
                    # 例如 keywords=['01', 'cuda']，那么 '01_check_env.sh' 和 '02_check_cuda.sh' 都会被选中
                    if any(k in s for k in keywords):
                        scripts_to_run.append(s)
            log("INFO", f"Selected scripts: {scripts_to_run}")

            if not scripts_to_run:
                log("WARN", "No scripts matched your filter!")
            else:
                for s in scripts_to_run:
                    local_path = os.path.join(config.SCRIPT_DIR, s)
                    if not ssh.run_remote_script(local_path):
                        # 可以选择是否遇到错误就中断
                        # raise Exception(f"Script {s} Failed!") 
                        log("ERROR", f"Script {s} Failed, but continuing...")
                        success_flag = False # 标记最终结果为失败，但继续跑后面
            
            ssh.close()
            success_flag = True
        else:
            raise Exception("SSH Login Failed")

    except Exception as e:
        log("FATAL", f"Test Aborted: {e}")
        # log("DEBUG", traceback.format_exc())
    
    finally:
        log("MAIN", "=== Testing Finished ===")
        
        if success_flag:
            log("SUCCESS", "All tests passed successfully.")
            if args.cleanup:
                k8s.cleanup_all()
            else:
                log("INFO", "Resources are KEPT for inspection.")
                log("INFO", f"Login Command: ssh -p {ssh_port} {ssh_user}@{ssh_host}")
        else:
            log("FAILURE", "Tests failed. Performing DEFENSIVE CLEANUP...")
            k8s.cleanup_all()
            sys.exit(1)

if __name__ == "__main__":
    main()