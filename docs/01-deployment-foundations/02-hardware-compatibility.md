# 02 硬件兼容与后端适配

[返回总目录](README.md) · [上一章](01-engineering-and-request.md) · [下一章](03-model-and-quantization.md)

## 1. “支持这个设备”需要逐层成立

兼容链是：**硬件 → OS/驱动/固件 → Runtime/编译器 → 推理框架与后端 → 模型架构 → 精度与算子 → 应用功能**。任一环不成立，都可能表现为加载失败、CPU 回退、结果错误或性能下降。

设备管理工具能看到 GPU，只证明系统枚举到了它；框架打印“CUDA available”，也不证明当前模型每个算子都在 GPU 上执行。应继续检查加载的库、设备分配、模型层卸载日志和运行期 CPU/GPU 活动。

## 2. CPU、GPU、NPU 的差异

CPU 通用性强，负责分词、调度和不支持的算子，也能独立推理。性能受指令集、内存带宽、核心数量、NUMA 和量化 kernel 影响。线程数翻倍通常不会带来速度翻倍，内存通道可能先饱和。

GPU 适合并行计算与高带宽数据访问，但独显还有设备内存、主机内存和总线边界。频繁在 CPU/GPU 间复制中间数据会拖慢整条链路。集显和统一内存减少某些复制需求，但 CPU、GPU、系统仍可能争用同一内存带宽。

NPU 常为能效与特定算子设计。标称 TOPS 只对应某种精度和条件，不等于语言模型 tokens/s。动态形状、Attention、KV 更新、量化布局和图切分是否支持，通常比峰值 TOPS 更先决定能否落地。

## 3. 平台路线图

| 平台 | 组件 | 常见验证路线 | 优先检查 |
| --- | --- | --- | --- |
| NVIDIA 独显 | 驱动、CUDA、cuBLAS、NCCL | llama.cpp CUDA；vLLM/SGLang；TensorRT-LLM | Compute Capability、工具链、kernel、拓扑 |
| AMD | ROCm、HIP、RCCL | llama.cpp HIP/Vulkan；vLLM ROCm | 具体 GPU/OS 支持列表、gfx 架构、算子 |
| Intel | oneAPI/SYCL、驱动、OpenVINO | llama.cpp SYCL/适用版本的 OpenVINO 后端；OpenVINO GenAI | CPU/GPU/NPU 路线差异、驱动、导出限制 |
| Apple Silicon | Metal、Accelerate、MLX | llama.cpp Metal；MLX-LM | 统一内存、OS、权重表示、温度 |
| 昇腾 | CANN、驱动/固件、HCCL | llama.cpp CANN；vLLM Ascend 插件 | 插件与主框架配套、芯片及算子 |
| 摩尔线程 | MUSA 驱动与工具链 | llama.cpp MUSA 等适配路线 | GPU 型号、SDK、量化与算子覆盖 |
| x86/ARM CPU | SIMD、BLAS、线程运行库 | llama.cpp CPU 等 | ISA、带宽、跨编译和二进制可移植性 |
| Android/嵌入式 | NDK、厂商驱动、Vulkan/专用 SDK | 先 CPU，后 GPU/NPU | ABI、权限、算子、内存、持续功耗 |

表中路线是验证入口，不是全部组合都可用的承诺。厂商分支、插件、主仓库新后端可能有不同发布节奏。本次核对时 llama.cpp 主线已出现 OpenVINO 后端；旧资料中“OpenVINO 永远不是 llama.cpp 后端”的说法不应继续沿用。需查固定版本的 [OPENVINO.md](https://github.com/ggml-org/llama.cpp/blob/master/docs/backend/OPENVINO.md)，不能据此推导所有 Intel NPU 都能直接运行 GGUF。

## 4. NVIDIA：驱动、Toolkit 与运行库

以下为 Linux 只读检查模板：

```bash
nvidia-smi
nvcc --version
cmake --version
c++ --version
uname -a
cat /etc/os-release
```

`nvidia-smi` 的 CUDA Version 是驱动报告的兼容能力，**不是本机 Toolkit 版本**。`nvcc --version` 是编译器版本；预编译框架可能携带自己的 CUDA 用户态库。运行预编译程序可能不需要 nvcc；源码构建 CUDA 后端通常需要匹配的工具链。

常见情形是驱动足够新，但没有 nvcc；设备可用，源码构建仍无法进行。另一种是编译成功，运行时却找到了其他目录里的动态库。检查 CMake 的编译器路径、构建日志与实际依赖，不要直接升级所有包。

```bash
# Linux；只对自己构建或来源可信的程序使用
ldd ./build-cuda/bin/llama-server
rg 'CMAKE_CUDA_COMPILER|CMAKE_CUDA_ARCHITECTURES' build-cuda/CMakeCache.txt
```

Compute Capability 决定可编译的设备代码和部分精度能力。架构参数应从厂商表核对；给目标卡使用不匹配的设备代码可能导致 `no kernel image`。驱动兼容也不能替代模型算子和量化 kernel 支持。

## 5. 其他平台的证据采集

以下按平台选择，**不是依次全部执行**。命令名称、权限和适用设备以对应版本文档为准。

| 平台 | 只读入口 | 信息 |
| --- | --- | --- |
| Linux 通用 | `lscpu`、`free -h`、`lspci`、`numactl --hardware` | CPU、内存、PCIe、NUMA |
| AMD | `rocminfo`、`hipcc --version`、适用版本的 `amd-smi`/`rocm-smi` | GPU 架构、工具链与状态 |
| Intel GPU | `sycl-ls`、适用设备的 `xpu-smi discovery` | SYCL 设备与管理信息 |
| 昇腾 | `npu-smi info` 和 CANN 安装信息 | 芯片、驱动、固件、Runtime |
| Apple | `system_profiler SPHardwareDataType SPDisplaysDataType`、`sw_vers` | SoC、统一内存、OS |
| Android | `adb shell getprop ro.product.cpu.abi`、`adb shell cat /proc/meminfo` | ABI、系统内存 |

公开报告保留型号、版本、拓扑与资源信息，移除主机名、序列号、用户名和内部网络地址。对比设备还要记录电源状态、性能模式、散热条件和其他进程。

## 6. 三次最小验证

**验证后端：**构建目标后端，枚举设备，运行小型已支持模型。先确认驱动与 Runtime，不把复杂模型的问题混进来。llama.cpp 可用所选版本的 `--list-devices` 确认可见设备。

**验证模型：**换到目标架构，核对加载器、位置编码、Attention、MoE 和特殊层。两个模型都叫 Transformer，不表示实现相同。检查执行设备与回退算子，完成固定样例、停止条件与长输入验证。

**验证应用：**检查模板、流式响应、结构化输出和工具参数。引擎推理正确与 API 解析正确是不同层；多模态还涉及 encoder/projector、图片处理与 token 预算。

## 7. 兼容矩阵如何记录

不要只写“NVIDIA：支持”。每行至少包含：

```text
设备型号 / OS / 驱动 / SDK / 框架 commit 或包版本 / 后端
模型 revision / 量化 / 模板 / 上下文 / 并发
编译状态 / 加载状态 / 正确性状态 / 性能状态 / 已知回退
日志位置 / 问题单 / 验证日期
```

状态使用“未测、构建通过、可加载、功能通过、性能验收通过”。一次短请求成功只能达到相应状态，不能升级成整个平台“生产可用”。记录不支持项，例如工具调用模板不匹配、某种 KV 精度失败，往往比单一勾选更有价值。

**本章产物：**精确的兼容记录、后端枚举结果、最小模型日志。可用[适配记录模板](templates/adaptation-record.md)归档。
