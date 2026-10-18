# 第1层：硬件后端适配层

## 本章概览

模型计算最终需要落到CPU、GPU或NPU。硬件适配的工作，是把设备、系统、驱动、Runtime、框架和模型连成一条可以正确执行的链路。本章按原稿四节展开，平台细节在1.2的子章节中讲解。

读完本章，应能采集一份环境记录，解释各软件层的作用，完成一次最小设备检查，并知道模型失败时先查哪一层。

## 1.1 这一层解决什么问题？

首先要确认设备是否被系统管理。驱动负责与设备交互、管理资源和提供底层接口。随后确认应用是否具备对应的Runtime与库，例如CUDA、HIP、oneAPI或CANN。最后确认框架编译了该后端，并实现了模型需要的算子。

这三个条件分别属于系统、执行环境和框架。系统能识别设备，不代表Python包带有目标后端；框架能分配一个张量，也不代表特定FP8、MoE或视觉算子已经实现。因此适配应持续验证到目标模型的真实生成。

模型本身也参与兼容关系。架构、张量类型、量化布局、head dimension和输入形状，都可能决定执行路径。记录支持范围时，应写“设备＋系统＋版本＋模型＋精度＋功能”，这样升级或迁移后才能判断需要重新验证什么。

### 驱动、Runtime与框架后端

| 层次 | 作用 | 例子 |
| --- | --- | --- |
| 驱动 | 让操作系统管理设备 | NVIDIA Driver、amdgpu、Intel GPU driver |
| Runtime与工具链 | 提供执行接口、库和编译工具 | CUDA、HIP、oneAPI、CANN |
| 框架后端 | 把模型计算交给设备执行 | llama.cpp CUDA/HIP/Metal、vLLM对应设备实现 |

源码构建还涉及CPU架构、编译器、ABI和目标设备架构。ARM64与x86_64二进制不同；CUDA计算能力与AMD gfx决定设备代码目标；同一个框架名字也可能对应不同后端的安装包。

## 1.2 平台能力地图

平台地图用于选择入口，具体支持以固定版本和实际模型为准。先选一条与目标设备匹配的路线，完成最小运行后再扩展功能。

| 平台 | 主要软件路线 | 本书对应教程 |
| --- | --- | --- |
| NVIDIA | CUDA、NCCL、vLLM、llama.cpp CUDA | [NVIDIA：环境、架构与构建排查](../chapters/hardware/nvidia.md) |
| AMD | ROCm/HIP、RCCL、Vulkan、CPU/GPU混合 | [AMD：gfx、运行库与共享内存](../chapters/hardware/amd.md) |
| Intel | OpenVINO、SYCL、Vulkan、XPU | [Intel：GPU与NPU分开验证](../chapters/hardware/intel.md) |
| Apple Silicon | Metal、MLX及相应服务层 | [Apple：模型制品与功能边界](../chapters/hardware/apple.md) |
| 昇腾 | CANN、HCCL、vLLM Ascend | [昇腾：芯片与插件配套](../chapters/hardware/ascend.md) |
| MUSA | 厂商工具链与受支持框架后端 | 本节基础说明与官方支持矩阵 |
| CPU | 原生CPU kernel、BLAS、llama.cpp | [Windows CPU完整演练](../practice/first-service/README.md) |

### MUSA与尚未实测的平台

先核对具体芯片、操作系统、驱动、SDK、框架版本、模型与精度。上游存在后端选项，只表示有该入口；是否适用于目标组合，需要设备执行证据。当前资料没有整理出可公开的MUSA完整运行记录，因此本书不补写速度或成功结果。

CPU同样需要适配。指令集、线程、内存带宽、NUMA和温度会影响执行。入门演练使用固定Windows x64 CPU二进制，Linux与ARM64需要对应构建或发行产物。

## 1.3 硬件适配排查顺序

适配按底层到上层检查。先确认型号、CPU架构与物理容量，再确认系统和驱动；随后查看Runtime、编译器与框架后端；最后进入模型与接口。这样每一步都有明确前提。

```text
硬件识别 → 系统与驱动 → Runtime / 编译器 → 框架后端
 → 最小计算 → 目标模型 → 功能与质量 → 长度与负载
```

### 第一步：采集环境

Linux项目在独立目录执行：

```bash
mkdir -p environment
uname -m > environment/architecture.txt
uname -r > environment/kernel.txt
cat /etc/os-release > environment/os-release.txt
lscpu > environment/cpu.txt
free -h > environment/memory.txt
python3 --version > environment/python.txt 2>&1
```

Windows可以在PowerShell查看CPU和显卡型号，并用`python --version`确认当前解释器。公开记录只保留需要的型号和版本，不包含设备序列号、账户或私人目录。

### 第二步：验证最小计算

已经安装CUDA或ROCm版PyTorch时，可以用一次小矩阵计算检查设备执行：

```python
import torch
print('torch:', torch.__version__)
print('CUDA:', torch.version.cuda, 'HIP:', torch.version.hip)
assert torch.cuda.is_available()
x = torch.ones((32, 32), device='cuda')
y = x @ x
torch.cuda.synchronize()
assert y[0, 0].item() == 32
print('basic compute passed')
```

ROCm沿用部分`torch.cuda`接口，需要结合`torch.version.hip`确认后端。llama.cpp不依赖PyTorch，可以直接通过自己的设备日志和小模型生成验证，无需额外安装一套框架。

### 第三步：进入目标模型

基础计算通过后，再检查架构、精度、量化kernel和实际卸载。文本、图片、工具调用分别测试。遇到失败时保存第一条错误、触发输入与版本，回到对应软件层排查。

## 1.4 适配流程

完整适配从任务要求开始。先确定输入类型和资源，再选择平台路线；准备环境后运行小算子或小模型，最后加载目标模型、接API并测目标负载。

第一次操作建议按[完整CPU演练](../practice/first-service/README.md)执行。它按“准备文件→启动→功能→异常→流式→基准→停止”走完链路，每一步都有产物。迁移到GPU时保留相同输入和验收方式，重新检查后端、内存和性能。

平台工程中常见的变化包括：GB10需要ARM64包和匹配kernel；AMD共享内存要核对运行时可分配量；Intel GPU和NPU要分别完成生成；Apple的文本与视觉支持需要分开确认。这些细节在1.2的平台教程中展开。

本层结束时，应留下一份环境清单、一条最小执行证据和一张功能范围表。记录模板见[适配记录](../templates/adaptation-record.md)。下一章根据这条执行路线准备模型制品。
