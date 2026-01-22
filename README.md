# Cloud ContainerServer Automated Test Suite

这是一个用于自动化测试云平台开发机（ContainerServer）功能的 Python 测试套件。

该工具能够自动化地完成从资源创建（PVC + ContainerServer）、环境配置、连通性检查（SSH/Jupyter）到脚本执行（CUDA/存储/环境验证）的全生命周期测试，并具备防御性的资源清理机制。


### 📂 项目结构

```plaintext
auto_test/
├── main.py                 # [入口] 主控逻辑
├── config.py               # [配置] 常量定义与参数解析
├── parsers.py              # [工具] JSON数据提取与SSH解析
├── net_checks.py           # [工具] 网络连通性检查
├── k8s_handler.py          # [核心] K8s 资源生命周期管理
├── ssh_handler.py          # [核心] SSH 连接与远程执行
├── utils.py                # [基础] 日志与本地Shell封装
├── requirements.txt        # [依赖] Python 依赖包
├── demo_cs.yaml            # [模板] 原始开发机 YAML
└── scripts/                # [脚本] 远程执行的测试脚本
    ├── 01_check_env.sh         # 环境检查 (Python/Conda)
    ├── 02_check_hardware.sh    # 硬件检查 (GPU/HCA)
    ├── 03_check_cuda_app.sh    # CUDA 功能验证 (NVCC/Tensor)
    └── 04_check_nccl_storage.sh # NCCL与存储读写测试
```

### 🚀 快速开始

#### 1.环境准备
确保本地已安装 Python 3，并配置好 kubectl 以便访问目标集群。

安装依赖：

```bash
pip install -r requirements.txt
```

#### 2. 运行测试
使用默认配置运行（默认使用 RTX_4090 和 Huabei2 存储）：

```python
python main.py
```

#### 3. 常用运行示例
指定任务 ID 和清理策略：

```Bash
# 使用自定义 ID 防止命名冲突，并强制在成功后清理资源
python main.py --job-id "ci-run-001" --cleanup
```

指定测试脚本
```bash
python main.py --scripts "01,02,03" 
# 只跑前三个
```

更换镜像和 GPU 类型：

```Bash
python main.py \
  --image "registry-cn-huabei1-internal.ebcloud.com/custom/image:v1.0" \
  --gpu-type "A800_NVLINK_80GB" \
  --gpu-count 8
```
指定存储类（StorageClass）：

```Bash
# 切换到华北1或其他存储后端
python main.py --storage-class "shared-nvme-cn-huabei1"
```

### ⚙️ 配置与参数说明

所有配置均由 config.py 管理。你可以通过修改该文件调整默认值，或通过命令行参数覆盖。


| 参数 | 默认值 | 说明 |
|---|---|---|
| `--job-id` | `test01` | 任务标识符。用于生成 PVC 和 CS 的名称（如 `cs-test01`），建议每次运行使用不同 ID 以避免冲突。 |
| `--image` | （见 `config.py`） | Docker 镜像地址。指定开发机使用的基础镜像。 |
| `--gpu-type` | `RTX_4090` | GPU 型号。支持 `RTX_4090`、`A800_NVLINK_80GB` 等。 |
| `--gpu-count` | `1` | GPU 数量。申请的卡数。 |
| `--storage-class` | `shared-nvme-cn-huabei2` | 存储类名称。用于创建共享存储 PVC，请确保与集群区域一致。 |
| `--cleanup` | `False` | 清理开关。默认为关闭（保留资源以便 Debug）。加上此参数后，无论测试成功与否都会删除资源。 |
| `--key-path` | `None` | SSH 私钥路径。本项目主要使用固定密码登录，此参数为可选保留项。 |

> 注意：项目中使用了固定的 Root 密码 FIXED_ROOT_PASSWORD (在 config.py 中定义)。该密码会在创建资源时动态注入到 YAML 中，并用于后续的 SSH 自动登录。

### 🛠️ 工作流程
程序执行 (main.py) 遵循以下严谨的自动化流程：

#### 1.资源准备 (Resource Provisioning)

 - 调用 kubectl 创建指定 StorageClass 的 PVC (默认为 256Gi)。

 - 读取 demo_cs.yaml 模板，动态修改镜像、GPU、挂载点和 Root 密码。

 - 提交 ContainerServer CRD 到集群。

#### 2.状态轮询 (Polling)

 - 持续监控资源状态，直到 Phase=Running 且 获取到有效的 SSH 连接地址（解决 SSH 异步生成的时间差问题）。

#### 3.信息提取 (Extraction)

 - 自动解析 SSH 连接字符串（支持 ssh -p port user@host 格式）。

 - 提取 JupyterLab 的 HTTP 访问地址。

#### 4.连通性与功能验证 (Validation)

 - HTTP 检查：验证 JupyterLab 端口是否响应。

 - SSH 连接：使用注入的固定密码建立 SSH 连接。

 - 脚本执行：将 scripts/ 目录下的所有 .sh 文件上传至容器 /root/scripts 并依次执行。

#### 5.资源清理 (Cleanup)

 - 失败时：触发防御性清理，强制删除创建的 CS 和 PVC，防止残留。

 - 成功时：默认保留资源供人工检查（除非指定 --cleanup）。

### 📝 如何添加新测试？
只需在 scripts/ 目录下创建一个新的 .sh 脚本即可（例如 04_check_network.sh）。 程序会自动扫描该目录，上传并执行所有脚本。如果脚本返回非 0 退出码，测试将标记为失败。