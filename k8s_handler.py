import yaml
import time
import json
import os
from utils import log, run_shell

class K8sManager:
    def __init__(self, template_path="demo_cs.yaml"):
        self.template_path = template_path
        self.created_resources = [] # Record created resources for rollback

    def apply_pvc(self, name, size="1024Gi", storage_class="shared-nvme-cn-huabei2"):
        """Create PVC"""
        log("K8S", f"Preparing PVC: {name}...")
        pvc_dict = {
            "apiVersion": "v1",
            "kind": "PersistentVolumeClaim",
            "metadata": {"name": name, "namespace": "default"},
            "spec": {
                "accessModes": ["ReadWriteMany"],
                "resources": {"requests": {"storage": size}},
                "storageClassName": storage_class
            }
        }
        
        file_path = f"temp_{name}.yaml"
        return self._apply_and_record(pvc_dict, file_path, "pvc", name)

    def apply_cs_with_patch(self, cs_name, pvc_name, mount_path, image, gpu_type, gpu_count, root_password):
        """Read template, patch mount/config/password, and Apply"""
        log("K8S", f"Patching ContainerServer template for: {cs_name}...")
        
        if not os.path.exists(self.template_path):
            raise FileNotFoundError(f"Template {self.template_path} not found!")

        with open(self.template_path, 'r', encoding='utf-8') as f:
            cs_data = yaml.safe_load(f)

        # === Core Patching Logic ===
        # 1. Update Name
        cs_data['metadata']['name'] = cs_name
        
        # 2. Update Image
        if image:
            cs_data['spec']['image'] = image
            
        # 3. Update GPU
        if gpu_type:
            cs_data['spec']['resources']['gpu']['type'] = gpu_type
        if gpu_count:
            cs_data['spec']['resources']['gpu']['count'] = str(gpu_count)

        # 4. === Critical: Update Root Password ===
        # This ensures the password in the container matches what main.py uses for SSH
        if root_password:
             cs_data['spec']['initRootPassword'] = root_password

        # 5. === Critical: Update Mount to point to our test PVC ===
        new_mount = {
            "name": pvc_name, # Keep name consistent
            "mountPath": mount_path,
            "persistentVolumeClaim": {"claimName": pvc_name}
        }
        # Overwrite existing mounts to ensure we are testing the correct storage
        cs_data['spec']['volumeMounts'] = [new_mount]
        
        log("K8S", f"Updated Config: PVC({pvc_name}) | GPU({gpu_type} x{gpu_count}) | Password Set")

        file_path = f"temp_{cs_name}.yaml"
        return self._apply_and_record(cs_data, file_path, "containerserver", cs_name)

    def _apply_and_record(self, data_dict, file_path, kind, name):
        """Internal helper: Write -> Apply -> Record"""
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                yaml.dump(data_dict, f, default_flow_style=False)
            
            success, out = run_shell(f"kubectl apply -f {file_path}")
            if success:
                log("K8S", f"Apply Success: {kind}/{name}")
                # Insert at beginning for LIFO cleanup (Delete CS first, then PVC)
                self.created_resources.insert(0, {"kind": kind, "name": name}) 
                return True
            else:
                log("ERROR", f"Apply Failed: {out}")
                return False
        finally:
            if os.path.exists(file_path):
                os.remove(file_path)

    def wait_for_running(self, cs_name, timeout=600):
        log("WAIT", f"Waiting for {cs_name} to be Ready (Running + SSH)...")
        start = time.time()
        while time.time() - start < timeout:
            success, out = run_shell(f"kubectl get containerserver {cs_name} -o json")
            if success:
                try:
                    data = json.loads(out)
                    status = data.get('status', {})
                    phase = data.get('status', {}).get('phase', 'Unknown')

                    ssh_access = status.get('sshAccess', {})
                    ssh_exists = ssh_access.get('format')

                    if phase == 'Running':
                        if ssh_exists:
                            log("WAIT", f"✅ Status is Running and SSH is Ready! ({ssh_exists})")
                            return data  # 只有当 SSH 也有值了，才返回
                        else:
                            # 打印一个临时日志（可选），表示正在等 IP
                            log("WAIT", "Resource is Running, waiting for SSH endpoint assignment...")
                            pass
                    elif phase in ['Failed', 'Error']:
                        raise Exception(f"Resource entered {phase} state")
                except json.JSONDecodeError:
                    pass
            time.sleep(5)
        raise TimeoutError(f"Timeout waiting for {cs_name}")

    def cleanup_all(self):
        """Clean up all created resources"""
        log("CLEANUP", "Starting resource cleanup...")
        for res in self.created_resources:
            kind = res['kind']
            name = res['name']
            log("CLEANUP", f"Deleting {kind}/{name}...")
            run_shell(f"kubectl delete {kind} {name} --ignore-not-found=true")
        self.created_resources.clear()