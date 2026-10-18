# 第1层：硬件后端适配层

[总目录](../SUMMARY.md) · [硬件完整工程实例](../engineering/README.md)

## 1.1 这一层解决什么问题？

```text
可执行性 = 设备可用 ∩ Runtime配套 ∩ 框架后端可用
         ∩ 模型结构支持 ∩ dtype/量化kernel支持 ∩ 内存/通信可用
```

| 软件层 | 职责 | 常见失败证据 |
| --- | --- | --- |
| Driver/固件 | 管理设备、内存与执行队列 | 设备缺失、权限、模块/固件不匹配 |
| Runtime/Toolkit | 分配、调用、编译、链接、设备库 | 缺so/DLL、ABI、目标架构、链接错误 |
| 框架后端 | 将计算图和张量映射到设备 | CPU fallback、未知backend、后端未构建 |
| Kernel/算子 | 实现matmul、attention、norm、MoE、vision等 | unsupported arch/type/op、错误输出 |
| 通信层 | rank间数据交换 | collective挂起、P2P失败、错误网卡/拓扑 |

驱动能枚举GPU只证明第一层。目标模型完整生成、质量与目标负载通过，才形成部署结论。

## 1.2 平台能力地图

| 平台 | Runtime / kernel / 通信 | 常见路线 | 完整实例 |
| --- | --- | --- | --- |
| NVIDIA | CUDA、cuBLAS、Tensor Core、NCCL | vLLM、TensorRT-LLM、llama.cpp CUDA | [2060](../engineering/nvidia-rtx2060.md)、[4080/A6000](../engineering/nvidia-dual-gpu.md)、[GB10](../engineering/nvidia-gb10.md) |
| AMD | ROCm、HIP、rocBLAS/hipBLASLt、RCCL | vLLM ROCm、llama.cpp HIP/Vulkan | [780M](../engineering/amd-780m.md)、[8060S](../engineering/amd-8060s.md)、[五机RPC](../engineering/amd-395-rpc.md)、[W7900](../engineering/amd-w7900.md) |
| Intel | SYCL/oneAPI、Level Zero、OpenVINO/XPU | llama.cpp SYCL/Vulkan、GenAI IR | [Arc GPU与NPU](../engineering/intel-arc-npu.md) |
| MUSA | MUSA Toolkit、厂商设备库及适配算子 | 当前分支支持的GGML MUSA等 | [完整待验证流程](../engineering/musa.md) |
| 昇腾 | CANN、torch_npu、HCCL | vLLM Ascend、配套MindIE等 | [310P3](../engineering/ascend-310p.md) |
| Apple Silicon | Metal、MLX、统一内存 | llama.cpp Metal、MLX-LM/VLM、oMLX | [Metal](../engineering/apple-metal.md)、[MLX/APC/oMLX](../engineering/apple-mlx.md) |
| CPU/端侧 | AVX/NEON、GGML、BLAS、共享内存后端 | llama.cpp及设备支持的IR | [CPU实际运行](../practice/first-service/README.md) |

平台专题：[NVIDIA](../chapters/hardware/nvidia.md) · [AMD](../chapters/hardware/amd.md) · [Intel](../chapters/hardware/intel.md) · [Apple](../chapters/hardware/apple.md) · [昇腾](../chapters/hardware/ascend.md)。支持范围按具体芯片、OS、框架commit、模型与精度记录，不仅按品牌判断。

## 1.3 硬件适配排查顺序

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

```text
设备/任务支持矩阵 → 固定驱动/Toolkit/引擎 → 小算子或小模型
 → 目标模型短输入 → 模板/多模态/工具功能 → 单机负载
 → 多卡/多机 → 优化实验 → 交付
```

| 阶段 | 工程操作 | 实例 |
| --- | --- | --- |
| 构建 | 固定arch与依赖，分backend构建目录 | GB10 ARM64/SM；Mac shader与原生扩展 |
| 容量 | 区分物理、驱动预算与可分配量 | 395 GTT120000但TTM约63215MiB |
| 功能 | 文本、视觉、音频分别验收 | vllm-metal文本可用但encoder未接通 |
| 优化 | 保留CPU/原精度/原参数基线 | 8060S CPU22.9→Vulkan47.2→组合58.4token/s |
| 交付 | 记录成功/失败组合、最终命令与回滚 | Intel全NPU音频错误后回滚混合路径 |

输出：环境清单、构建日志、模型支持表、最小计算与目标任务结果、内存和通信证据。[适配记录模板](../templates/adaptation-record.md)。
