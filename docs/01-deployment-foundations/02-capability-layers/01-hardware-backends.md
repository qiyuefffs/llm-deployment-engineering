# 第 1 层：硬件后端适配层

[总目录](../README.md) · [整体地图](../01-knowledge-map.md) · [下一层：模型格式与量化](02-model-formats-quantization.md)

## 1.1 这一层解决什么问题？

硬件适配先确认模型有没有一条可靠的执行路线：设备能否被系统识别？框架是否装有目标后端？模型结构、精度和关键算子是否能执行？驱动、Runtime、编译器和通信库是否配套？

| 概念 | 主要职责 | 例子 |
| --- | --- | --- |
| 驱动 | 让系统管理和访问设备 | NVIDIA Driver、amdgpu、Intel GPU driver |
| Runtime / 工具链 | 提供执行接口、库和编译能力 | CUDA、HIP、oneAPI、CANN |
| 框架后端 | 把框架计算交给具体平台 | llama.cpp CUDA/HIP/Metal、vLLM Ascend 插件 |

设备管理器能看到显卡，只完成了系统识别。框架能枚举设备，也没有证明注意力、量化、MoE 或视觉算子全部可用。要一直验证到实际模型生成，才能填写该模型的适配结论。

## 1.2 平台能力地图

| 平台 | 后端关键词 | 常见部署入口 | 适配重点 |
| --- | --- | --- | --- |
| NVIDIA | CUDA、cuBLAS、NCCL、Tensor Core | vLLM、TensorRT-LLM、llama.cpp CUDA | CPU 架构、计算能力、wheel、精度 kernel、通信 |
| AMD | ROCm、HIP、rocBLAS、hipBLASLt、RCCL | vLLM ROCm、llama.cpp HIP | gfx、系统支持、库目标、运行时可用内存 |
| Intel | Level Zero、SYCL、oneAPI、OpenVINO | OpenVINO GenAI、llama.cpp SYCL/Vulkan、XPU 路线 | GPU/NPU 分开验证、IR、驱动、算子与形状 |
| MUSA | MUSA Toolkit、厂商算子与通信库 | 厂商支持的框架或后端 | 精确版本、模型、精度与功能 |
| 昇腾 | CANN、NPU、HCCL | vLLM Ascend、受支持的 CANN 后端 | 芯片代际、驱动/固件、插件、图与算子 |
| Apple Silicon | Metal、Accelerate、MLX | llama.cpp Metal、MLX-LM/MLX-VLM、oMLX | 制品类型、统一内存、架构、视觉链路 |
| CPU / 通用端侧 | CPU kernel、BLAS、Vulkan 等 | llama.cpp、支持的厂商运行时 | 指令集、内存带宽、线程、部分卸载、温度 |

这张表用于选择入口。具体支持落实到“设备 + 系统 + 版本 + 模型 + 精度 + 功能”，不能按厂商名称直接判断。

## 1.3 硬件适配排查顺序

```text
1. 确认硬件：型号、CPU 架构、物理内存、设备内存
2. 确认系统：OS、内核、驱动、固件
3. 确认运行环境：Runtime、编译器、Python、原生库
4. 确认框架：安装包、源码 commit、后端构建开关
5. 确认模型：架构、精度、量化布局、算子
6. 最小运行：分配 → 计算 → 同步 → 校验
7. 实际模型：加载 → 生成 → 模板和质量
8. 多设备：通信 → 模型切分 → API → 目标负载
```

底层通过后再排上层问题。例如模型建图失败时先看具体算子；不能因为 GPU 已经枚举，就反复更换 API 请求格式。

### 采集 Linux 环境

在自己的实验目录执行：

```bash
mkdir -p environment logs
uname -m > environment/cpu-architecture.txt
cat /etc/os-release > environment/os-release.txt
lscpu > environment/cpu.txt
free -h > environment/memory.txt
df -h . > environment/disk.txt
python3 --version > environment/python.txt 2>&1
```

检查方法：`x86_64` 与 `aarch64` 的二进制不能直接互换；内存看当前可用量；权重、源码、编译目录和下载缓存都占磁盘；终端 Python 与 Notebook Kernel 分别确认。

## 1.4 适配流程

| 步骤 | 操作 | 检查结果 |
| --- | --- | --- |
| 选择路线 | 根据设备、模型和任务选一个后端 | 有明确支持依据与版本 |
| 准备环境 | 安装配套运行时或使用固定镜像 | 当前程序与库来自同一套组合 |
| 验证小算子 | 设备张量、计算与同步 | 数值正确，无设备错误 |
| 运行目标模型 | 先短输入、低并发 | 日志显示目标设备实际执行 |
| 验证功能 | 文本、视觉、模板、流式分别检查 | 按功能记录通过或失败 |
| 验收资源 | 目标长度与持续负载 | 内存、温度和性能满足约束 |

至少保留设备、OS/内核、驱动、Runtime、编译器、框架 commit、模型 revision、精度、实际功能和证据文件。可直接使用[适配模板](../templates/adaptation-record.md)。

### 最小 CUDA / ROCm 张量验证

前提：已安装对应后端的 PyTorch。llama.cpp 不依赖 PyTorch，无需为了它额外安装。

```python
import torch
print('torch:', torch.__version__)
print('CUDA wheel:', torch.version.cuda)
print('HIP wheel:', torch.version.hip)
assert torch.cuda.is_available(), '当前环境未识别计算设备'
print('device:', torch.cuda.get_device_name(0))
x = torch.ones((512, 512), device='cuda')
y = x @ x
torch.cuda.synchronize()
assert y[0, 0].item() == 512.0
print('basic compute: PASS')
```

ROCm 沿用部分 `torch.cuda` API。结合 `torch.version.hip` 与设备名称判断后端。这个测试只验证一条基础路径，模型量化、注意力和通信仍要单独验证。

## 1.5 NVIDIA：驱动、Toolkit、wheel 分开看

```bash
nvidia-smi
nvcc --version
ptxas --version
```

| 输出 | 实际含义 |
| --- | --- |
| nvidia-smi 的 CUDA 字段 | 驱动支持的 CUDA 兼容能力 |
| nvcc / ptxas | 当前 PATH 中的编译工具链 |
| torch.version.cuda | PyTorch wheel 的构建信息 |
| get_device_capability | 当前设备计算能力 |

数字不必完全相同，但组合必须受支持。使用源码扩展时，还要检查编译器、PyTorch ABI、GPU 架构和动态库搜索路径。

### 工程参考：DGX Spark GB10

[E01](../evidence/README.md)的部署涉及 Ubuntu 24.04、ARM64、128GB 内存、CUDA 13.0 和 vLLM 源码。该设备同时有两个兼容问题：

1. **CPU 架构：** 需要 aarch64 包或镜像，不能把 x86_64 wheel 直接装上。
2. **GPU 架构：** 框架能识别 GB10，不代表构建过程中涉及的每种低精度 kernel 都能通过。

记录中的具体错误为：

```text
Instruction 'cvt with .e2m1x2' not supported on .target 'sm_121'
```

先找出出错 kernel 和目标精度，核对源码、NVCC/PTXAS 与设备架构，再应用该组合的修复。原笔记曾以 `TORCH_CUDA_ARCH_LIST=12.0` 进行特定构建；不能把它当成所有 GB10 项目的通用设置。

### 容器还多一层设备接入

宿主 `nvidia-smi` 正常，而容器无法访问 GPU 时，检查 NVIDIA Container Toolkit、Docker GPU 配置及容器内依赖。宿主驱动不会自动让任意镜像拥有完整推理环境。

## 1.6 AMD：gfx、用户态库与内核驱动配套

```bash
lspci | grep -Ei 'vga|display|amd'
rocminfo > environment/rocminfo.txt
hipconfig --full > environment/hipconfig.txt 2>&1
```

### 先确认 gfx，再处理编译目标

`gfx` 用于识别 AMD GPU 的架构目标。780M 记录涉及 `gfx1103`；395 / 8060S 的有设备输出记录使用 `gfx1151`。不能凭相近产品名称复制另一设备的目标。

`AMDGPU_TARGETS`、`PYTORCH_ROCM_ARCH` 等变量只影响相应组件的构建目标，不会补齐缺失的 kernel、驱动功能和硬件指令。

### 区分“编译 ROCm 组件”和“安装驱动”

原笔记将 rocBLAS、rocWMMA、CK、MIOpen、RCCL 等编译归入“ROCm 驱动”。工程记录应进一步区分：

| 组件类别 | 作用 | 什么时候检查 |
| --- | --- | --- |
| 内核驱动 / DKMS | 设备管理、内存和系统接口 | 系统识别、运行时容量异常 |
| HIP / 编译器 | 程序接口与目标代码生成 | 后端编译、设备代码错误 |
| BLAS / attention kernel | 矩阵与特定算子实现 | 模型执行、精度与速度 |
| RCCL | 多设备集合通信 | TP、多进程通信 |

先选支持目标设备的完整发行组合。定位到具体缺失后再编译对应组件，不把“所有 TARGETS 加一遍”当成适配完成。

### Windows 与 Linux 运行库分开管理

780M 旧记录采用 HIP SDK、社区库和 Ollama 适配分支。[E04](../evidence/README.md)保留其历史背景。现在使用时核对当前支持情况，把程序、DLL 与日志按版本隔离。

PowerShell 可先检查：

```powershell
Get-CimInstance Win32_VideoController |
  Select-Object Name, DriverVersion
Get-ChildItem -LiteralPath '.\bin' -Filter '*.dll' |
  Select-Object Name, Length
```

GPU 使用率只作辅助。最终确认日志中的后端、实际设备与生成输出。

### 统一内存仍有 GPU 分配上限

AMD 五机记录中，启动参数请求约 120000MiB GTT，但设备运行时一度只报告 `63215 MiB`。大分配失败与运行时上限直接相关。完整排查见[故障表的 AMD 内存实例](../06-troubleshooting.md)。

## 1.7 Intel：GPU、NPU 与制品路线分别验证

同一台 Intel 设备可能有 CPU、GPU、NPU；它们不是同一个执行目标。

| 路线 | 常见输入制品 | 主要依赖 |
| --- | --- | --- |
| llama.cpp Vulkan | 受支持 GGUF | Vulkan 驱动、shader 与框架版本 |
| llama.cpp SYCL | 受支持 GGUF | oneAPI、Level Zero、相应构建 |
| OpenVINO GenAI | 匹配版本 IR 与 tokenizer 配套文件 | OpenVINO、GenAI、设备插件 |
| XPU 框架路线 | 框架支持的 HF 模型 | 对应 XPU 软件栈与 kernel |

### 工程参考：16GB Intel 笔记本

[E02](../evidence/README.md)设备为 Core Ultra 7 256V / Arc Lunar Lake，Ubuntu 24.04.4，16GB 统一内存。

- Vulkan 与 SYCL 都有实际生成记录。
- OpenVINO GenAI GPU 使用官方 IR 完成生成。
- OpenVINO 可枚举 NPU，但该 9B INT4 编译失败、INT8 编译超时。
- llama.cpp OpenVINO 后端能构建和枚举，当前 GGUF 却在建图时遇到 `CPY` 不支持。

“OpenVINO GPU + IR 可用”和“llama.cpp OpenVINO + GGUF 可用”是两个不同结论。后端、制品和模型图要作为一组验证。

检查设备：

```python
import openvino as ov
core = ov.Core()
print(core.available_devices)
for device in core.available_devices:
    print(device, core.get_property(device, 'FULL_DEVICE_NAME'))
```

之后实际创建管线并生成。设备枚举不计作模型推理成功。

## 1.8 Apple Silicon：区分 Metal、MLX 和服务插件

| 路线 | 需要检查 |
| --- | --- |
| llama.cpp Metal | GGUF 架构、张量类型、Metal kernel、实际卸载 |
| MLX-LM / MLX-VLM | MLX 制品、模型实现、视觉输入、缓存行为 |
| oMLX | 模型目录组织、引擎版本、内存与 API 配置 |
| vllm-metal | 插件、vLLM 与 MLX 配套版本、具体功能 |

Apple 的统一内存让 CPU/GPU 共享物理资源，但系统、运行时和模型仍竞争同一容量。要同时观察应用内存、系统可用量、交换和持续运行速度。

### 工程参考：编译成功而模型 kernel 不支持

[E05](../evidence/README.md)记录了 M3 Ultra 512GB、macOS 26.3、特定 llama.cpp 分支与 FP4/FP8 GGUF 的执行失败，问题涉及张量类型和 MoE Metal kernel。

另一份 vllm-metal 记录中文本成功，图片请求报：

```text
NotImplementedError: Multimodal encoder execution is not wired on Metal yet.
```

功能矩阵分别列文本、图像、多轮、工具调用和结构化输出。升级后逐项回归，不把某次文本成功扩写为所有功能支持。

## 1.9 昇腾与其他厂商：先核对代际和插件组合

昇腾记录涉及 310P3、CANN 与 vLLM Ascend 的特定历史镜像。[E12](../evidence/README.md)用于说明适配条件和压测检查。

```text
芯片代际 → 驱动 / 固件 → CANN → 框架插件
 → 模型结构与精度 → 图 / 算子执行 → API → 压力
```

```bash
npu-smi info
```

旧版本的高权限容器与整目录挂载不作为默认步骤。按所需设备、库与权限配置，保留可恢复的已知可用组合。

MUSA 等平台按同一链条记录。框架图列出平台表示学习范围；没有目标设备运行证据时，不填写成功结果。

## 1.10 源码编译时记录什么

| 记录 | 原因 |
| --- | --- |
| 源码 commit、子模块 | 防止分支更新后无法重建 |
| 编译器、CMake、Python 与包版本 | 排除“命令相同、实际工具不同” |
| 后端开关与目标架构 | 确认真正生成了目标路径 |
| 完整构建日志与退出码 | 区分配置成功、编译成功和运行成功 |
| 运行时动态库位置 | 防止启动时加载另一套库 |

更换后端或工具链时使用独立构建目录，例如 `build-hip`、`build-vulkan`、`build-metal`。CMake 提示变量未使用时先查当前源码选项，不能忽略后宣称功能已开启。

## 1.11 多卡 / 多节点先验证通信

```bash
nvidia-smi -L
nvidia-smi topo -m
```

RTX 4080 不支持 NVLink，旧笔记中添加桥接器的建议应删除；以实际 PCIe 拓扑和通信测试判断。

先验证设备集合通信，再让框架加载大模型。本仓库提供[最小 all-reduce](../examples/all_reduce_check.py)：

```bash
# 在仓库根目录，已准备好双 GPU 的 CUDA/ROCm PyTorch 环境时执行
torchrun --standalone --nproc-per-node=2 \
  docs/01-deployment-foundations/examples/all_reduce_check.py
```

每个 rank 输入 1，两卡求和应为 2。该脚本本轮只做语法检查，未在双 GPU 设备运行。多节点还要核对各节点版本、网络、通信接口与超时，不能把单机命令原样扩展。

## 1.12 本层验收

- 能准确指出当前程序、运行库、后端和设备。
- 基础运算通过，目标模型真正执行到目标设备。
- 文本、视觉等功能分别有结果。
- 构建产物、模型、版本和日志能关联。
- 多设备先有通信证据，再有模型和 API 证据。
- 失败结论限定到具体组合，并有明确回退路线。

**本层产物：** 环境清单、兼容表、最小运行日志、功能矩阵。下一步进入[模型格式与量化层](02-model-formats-quantization.md)。
