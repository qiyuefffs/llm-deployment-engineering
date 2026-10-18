# 第1层：硬件、运行时与计算后端

[总目录](../SUMMARY.md) · [硬件完整工程实例](../engineering/README.md)

## 1.1 这一层解决什么问题？

大模型的参数存放在内存中，推理时不断进行矩阵乘法、注意力计算和数据搬运。这一层先回答：**用什么硬件执行，通过哪些软件调用，容量和速度受什么限制。**

### 1.1.1 CPU、GPU、NPU分别负责什么

| 硬件 | 基本特点 | 在大模型部署中的职责 |
| --- | --- | --- |
| CPU | 擅长通用控制、分支和系统任务，也能执行向量与矩阵计算 | 分词、输入预处理、请求管理；也可独立推理或承担部分模型层 |
| GPU | 有大量并行执行单元，适合矩阵和向量运算 | 执行模型的主要计算，存放权重、KV Cache和工作区 |
| NPU/AI加速器 | 针对神经网络计算设计，通常依赖配套编译器和算子 | 在支持的模型、精度、shape范围内执行推理，不能默认替代GPU |

CPU/GPU/NPU指硬件类别，CUDA/ROCm/Metal等属于软件栈。使用NPU的前提是模型能转换、算子可编译、执行和输出正确；设备标注的TOPS不能直接换算成大模型token/s。

### 1.1.2 先看哪些硬件指标

| 指标 | 含义 | 影响 |
| --- | --- | --- |
| 内存/显存容量 | 权重和运行状态能放多少 | 模型规模、上下文长度、并发上限 |
| 内存带宽 | 每秒能向计算单元提供多少数据 | 低批量decode常受权重与KV读取影响 |
| 计算能力 | 在特定精度和形状下的运算速度 | prefill、大批量和矩阵计算效率 |
| 精度与算子支持 | 硬件和kernel能否执行BF16、FP8、INT4等 | 某种量化是否能运行、是否能加速 |
| 设备互联 | PCIe、NVLink、xGMI、网络等 | 卸载、多卡和多机的数据交换成本 |
| 功耗与散热 | 持续运行时的频率和能耗条件 | 端侧长时间运行、噪声、稳定性能 |

容量回答“能否放下”，带宽和计算能力影响“跑得多快”。FP16/FP8/INT8算力、稀疏/稠密算力不能直接横向相除；还要看实际算子、batch和精度。

### 1.1.3 独立显存与统一内存

独立显卡通常有自己的VRAM，主机RAM和VRAM之间需要数据传输。CPU卸载能降低显存需求，但也可能增加CPU计算和PCIe传输。两张24GB显卡不会自动表现成一张48GB显卡，需要引擎切分模型并承担通信。

Apple Silicon和部分AMD/Intel集成GPU使用共享物理内存。CPU/GPU能够访问同一内存池，但操作系统、应用、权重和KV仍竞争容量与带宽；设备可分配预算也可能小于物理容量。共享内存不等于没有运行时开销或无限显存。

### 1.1.4 软件调用关系

```text
业务程序 / HTTP接口
        ↓
推理引擎：vLLM / llama.cpp / MLX-LM / OpenVINO GenAI
        ↓
张量框架或计算后端：PyTorch / MLX / GGML / OpenVINO Runtime
        ↓
运行时与算子：CUDA / HIP / Metal / Level Zero / CANN
             ＋矩阵库、attention kernel、通信库
        ↓
设备驱动 / 固件 → GPU或NPU
```

这是职责划分。同一个引擎可能直接调用设备API、自带kernel，或通过其他框架执行；不一定依次经过所有软件包。

驱动负责访问设备；运行时负责内存、执行和同步；算子库提供矩阵乘法等计算；推理引擎管理模型加载、KV、请求调度和输出。Toolkit/SDK则把开发需要的头文件、编译器、工具和库打包提供。

```text
可执行性 = 设备可用 ∩ Runtime配套 ∩ 框架后端可用
         ∩ 模型结构支持 ∩ dtype/量化kernel支持 ∩ 内存/通信可用
```

| 软件层 | 职责 | 常见失败证据 |
| --- | --- | --- |
| Driver/固件 | 管理设备、内存与执行队列 | 设备缺失、权限、模块/固件不匹配 |
| Runtime | 内存分配、提交执行与同步 | 缺so/DLL、版本或符号不匹配 |
| Toolkit/SDK | 编译器、头文件、开发工具及配套库 | 目标架构不支持、缺头文件、编译/链接错误 |
| 框架后端 | 将计算图和张量映射到设备 | CPU fallback、未知backend、后端未构建 |
| Kernel/算子 | 实现matmul、attention、norm、MoE、vision等 | unsupported arch/type/op、错误输出 |
| 通信层 | rank间数据交换 | collective挂起、P2P失败、错误网卡/拓扑 |

驱动能枚举GPU只证明第一层。目标模型完整生成、质量与目标负载通过，才形成部署结论。

## 1.2 平台能力地图

### 1.2.1 先认识各平台

| 平台 | 硬件 | 计算软件栈 | 常见大模型路线 |
| --- | --- | --- | --- |
| NVIDIA | GeForce、RTX专业卡、数据中心GPU、集成平台 | CUDA平台；CUDA Runtime、cuBLAS/cuBLASLt、NCCL等 | PyTorch/vLLM、TensorRT-LLM、llama.cpp CUDA |
| AMD | Radeon、Instinct、Ryzen集成GPU | ROCm平台；HIP、rocBLAS/hipBLASLt、RCCL等 | 受支持的PyTorch/vLLM ROCm、llama.cpp HIP或Vulkan |
| Apple Silicon Mac | CPU、GPU、Neural Engine集成在SoC中，共享物理内存 | macOS GPU驱动、Metal；MLX是上层机器学习框架 | MLX-LM/MLX-VLM、llama.cpp Metal、PyTorch MPS |
| Intel | CPU、Arc/集成GPU、部分Core Ultra NPU | oneAPI/SYCL、Level Zero；OpenVINO Runtime与设备插件 | llama.cpp SYCL/Vulkan、OpenVINO GenAI、受支持的XPU路线 |
| 昇腾 | 面向AI的专用加速器，具体芯片能力不同 | 驱动/固件、CANN、算子库、HCCL、框架插件 | 配套MindIE、PyTorch＋torch_npu、vLLM Ascend |
| 摩尔线程 | 使用MUSA软件栈的GPU | MUSA Toolkit、运行时与配套计算库 | 该设备和版本实际支持的框架或GGML后端 |
| CPU | x86/ARM处理器 | 线程、向量指令、BLAS/oneDNN/Accelerate等 | llama.cpp CPU、OpenVINO CPU及其他CPU引擎 |

**CUDA与ROCm是计算软件平台；Metal是GPU API；MLX是机器学习框架。** 它们可以一起出现在平台选型表中，但职责不同，不能按同一类运行库理解。MLX在Apple GPU上的执行依赖Metal；llama.cpp也能直接使用Metal，不需要先安装MLX。

### 1.2.2 三条典型执行链

```text
NVIDIA：请求 → vLLM → PyTorch/专用kernel → CUDA/计算库 → 驱动 → GPU
AMD：   请求 → vLLM ROCm → PyTorch/专用kernel → HIP/计算库 → 驱动 → GPU
Mac：   请求 → MLX-LM → MLX CPU/GPU运算 → Metal（GPU路径）→ Apple GPU
```

CUDA Runtime和HIP Runtime负责提交执行等工作；矩阵、attention和通信可能由配套库或引擎自带kernel完成。安装CUDA不等于安装vLLM，安装MLX也不等于已经具备所有模型实现和服务接口。

### 1.2.3 平台专题与实例

平台基础：[NVIDIA GPU与CUDA](../chapters/hardware/nvidia.md) · [AMD GPU与ROCm](../chapters/hardware/amd.md) · [Mac、Metal与MLX](../chapters/hardware/apple.md) · [Intel、oneAPI与OpenVINO](../chapters/hardware/intel.md) · [昇腾与CANN](../chapters/hardware/ascend.md)。

CPU路线关注AVX/NEON等指令、线程数、内存带宽，以及BLAS/oneDNN/Accelerate或引擎自带kernel。软件构建使用了新指令时，旧CPU可能无法执行；线程也不是越多越快，还要考虑带宽、NUMA和应用争用。

具体设备命令与历史结果集中在[工程实例矩阵](../engineering/README.md)，MUSA流程在[待验证实例](../engineering/musa.md)。支持范围按精确芯片、OS、框架版本、模型与精度判断。

## 1.3 硬件适配排查顺序

### 1.3.1 版本不是一个数字

| 版本层 | 要确认什么 | 典型问题 |
| --- | --- | --- |
| 硬件架构 | 精确型号、CUDA计算能力、AMD gfx等 | 软件包没有包含该设备的kernel |
| 系统与驱动 | OS、内核、固件、设备驱动 | 设备不可见、权限或驱动初始化失败 |
| 运行时与计算库 | 程序实际加载的动态库和版本 | 缺少so/DLL、符号不匹配、加载了其他环境的库 |
| 编译工具链 | nvcc/hipcc/clang、SDK、宿主编译器 | 构建失败、目标架构不支持 |
| 框架与引擎 | PyTorch/MLX等构建、引擎版本、原生扩展 | 框架能用GPU，但某模型或量化kernel失败 |

使用预编译软件包时，部分用户态运行库可能已经随包或依赖安装；源码编译时通常还需要开发工具链。是否安装完整Toolkit取决于程序的构建和运行要求，不必把每个平台的SDK全部安装。

容器封装用户态依赖，设备访问仍依赖宿主驱动与容器接入。容器中没有`nvcc`不一定妨碍运行已有二进制；但临时编译扩展时可能需要它。

### 1.3.2 从设备到目标任务逐层检查

| 顺序 | 检查 | 命令 / 证据 | 通过条件 |
| --- | --- | --- | --- |
| 1 | 设备与架构 | uname/lscpu/lspci、nvidia-smi、rocminfo、npu-smi | CPU架构、GPU型号、卡数、gfx/SM明确 |
| 2 | 驱动与Runtime | 模块来源、nvcc/hipcc、oneAPI/CANN、动态库 | 对应硬件支持，库路径与ABI一致 |
| 3 | 引擎后端 | torch设备与矩阵算例、llama --list-devices、IR available_devices | 真正完成分配、计算、同步 |
| 4 | 模型/精度/算子 | 读取config与quantization_config、加载日志 | 文本、MoE、视觉等所需路径均实现 |
| 5 | 内存与通信 | 分项buffer、GTT/TTM、拓扑、collective | 模型＋KV＋工作区容纳，目标通信通过 |
| 6 | 目标任务 | API、完整答案、异常与负载 | 任务、长度、并发和资源达到门槛 |

```python
import torch
print(torch.__version__, torch.version.cuda, torch.version.hip)
assert torch.cuda.is_available()
x = torch.ones((32, 32), device='cuda')
y = x @ x
torch.cuda.synchronize()
assert y[0, 0].item() == 32
```

上述用于CUDA或沿用torch.cuda接口的ROCm构建，不用于所有NPU/XPU。llama.cpp不需要为枚举额外安装PyTorch；OpenVINO也用自己的设备与管线验证。

## 1.4 适配流程

### 1.4.1 先选部署路线

| 需求 | 候选路线 | 先确认 |
| --- | --- | --- |
| 本地单用户、离线、资源有限 | llama.cpp、MLX-LM、设备支持的IR引擎 | 模型格式、内存、单请求延迟 |
| 多用户在线服务 | 支持该平台的vLLM、SGLang、厂商服务引擎 | 调度、KV、目标并发、尾延迟与监控 |
| 多模态或语音 | 有相应processor/encoder/decoder的实现 | 输入预处理、各模态算子和输出质量 |
| 模型放不进单设备 | 降位宽、较小模型、卸载、多卡/多机 | 质量、主机内存、通信代价和总成本 |

同一模型在多个平台上都能加载，不代表应该使用同一引擎或参数。先匹配任务和资源，再比较可用实现。

### 1.4.2 通用部署顺序

```text
设备/任务支持矩阵 → 固定驱动/Toolkit/引擎 → 小算子或小模型
 → 目标模型短输入 → 模板/多模态/工具功能 → 单机负载
 → 多卡/多机 → 优化实验 → 交付
```

| 阶段 | 工程操作 | 实例 |
| --- | --- | --- |
| 构建 | 固定arch与依赖，分backend构建目录 | 预编译包是否覆盖目标架构；扩展是否匹配 |
| 容量 | 区分物理、驱动预算与可分配量 | 权重＋KV＋工作区＋系统余量 |
| 功能 | 文本、视觉、音频分别验收 | 输出完整、模板正确、无意外CPU回退 |
| 优化 | 保留CPU/原精度/原参数基线 | 控制输入、采样、并发和计时边界 |
| 交付 | 固定最终命令和恢复步骤 | 冷启动、负载、停止、重启和回滚 |

输出：环境清单、构建日志、模型支持表、最小计算与目标任务结果、内存和通信证据。[适配记录模板](../templates/adaptation-record.md)。

通用基础接续[模型格式与量化](02-model-formats-quantization.md)、[推理框架](03-inference-frameworks.md)和[内存与性能](04-memory-performance.md)。需要具体设备命令和历史结果时，再查[工程实例矩阵](../engineering/README.md)。

## 2026-10 工程更新

当前硬件补充：[DGX Spark / GB10](../chapters/hardware/dgx-spark.md)，重点核对ARM64、统一内存预算、带宽与精确kernel支持。
