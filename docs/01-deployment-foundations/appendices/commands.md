---
id: T15
title: "附录 A：常用命令速查"
type: tutorial
volume: book
layer: 0
platform: "general"
device: "general"
status: historical
source_ids: []
updated: 2026-10-19
summary: "命令用于定位和收集信息。模型运行与构建命令还需要对应设备、驱动和固定源码，详见第二部分；不要把此页从头到尾作为安装脚本执行。"
---

# 附录 A：常用命令速查

[总目录](../README.md) · [故障速查](../06-troubleshooting.md) · [参考资料](references.md)

命令用于定位和收集信息。模型运行与构建命令还需要对应设备、驱动和固定源码，详见第二部分；不要把此页从头到尾作为安装脚本执行。

## A.1 Linux环境与磁盘

```bash
uname -m
uname -r
cat /etc/os-release
lscpu
free -h
df -h .
python3 --version
cmake --version
```

看CPU架构、内核、当前可用内存和存储，而不只看产品标称容量。原始环境文件可能包含设备标识，公开前检查。

## A.2 设备与工具链

| 平台 | 命令 | 关注内容 |
| --- | --- | --- |
| NVIDIA | `nvidia-smi`、`nvcc --version` | 驱动与Toolkit分别确认 |
| NVIDIA容器 | `nvidia-ctk --version` | Container Toolkit是否安装 |
| AMD | `rocminfo`、`hipcc --version` | 实际gfx与HIP版本 |
| Intel Vulkan | `vulkaninfo --summary` | 选到哪个设备与驱动 |
| Intel SYCL | `sycl-ls`、`icpx --version` | oneAPI环境与GPU设备 |
| Intel OpenVINO | 下方Python | 插件可发现设备，不代表模型可执行 |
| Apple | `sw_vers`、`uname -m`、`xcode-select -p` | macOS、架构与开发工具 |
| 昇腾 | `npu-smi info` | 芯片与设备状态，另记CANN/插件 |

```python
import openvino as ov
print(ov.__version__)
print(ov.Core().available_devices)
```

Windows只读检查：

```powershell
Get-CimInstance Win32_VideoController | Select-Object Name, DriverVersion
Get-CimInstance Win32_OperatingSystem | Select-Object Caption, Version, BuildNumber
```

## A.3 Python后端确认

```python
import torch
print('torch:', torch.__version__)
print('CUDA:', torch.version.cuda, 'HIP:', torch.version.hip)
print('available:', torch.cuda.is_available())
if torch.cuda.is_available():
    print('device:', torch.cuda.get_device_name(0))
    x = torch.ones(16, device='cuda')
    y = (x + 1).sum()
    torch.cuda.synchronize()
    assert y.item() == 32
```

ROCm版PyTorch也沿用部分`torch.cuda`接口。llama.cpp无需额外安装PyTorch，直接使用自己的后端日志验证。

## A.4 固定源码和制品

```bash
git -C llama.cpp rev-parse HEAD
git -C llama.cpp status --short
sha256sum /srv/models/model.gguf
python -m pip freeze > python-packages.txt
```

模型分片逐一校验；GGUF以外的制品还需记录config、tokenizer、模板和辅助文件。SHA256能核对同一文件，不能证明模型质量或许可。

## A.5 构建和程序帮助

以下是HIP构建模板，`gfx1151`对应395记录：

```bash
cmake -S llama.cpp -B llama.cpp/build-hip \
  -DGGML_HIP=ON -DAMDGPU_TARGETS=gfx1151 -DCMAKE_BUILD_TYPE=Release
cmake --build llama.cpp/build-hip --target llama-cli llama-server llama-bench -j 4
llama.cpp/build-hip/bin/llama-server --version
llama.cpp/build-hip/bin/llama-server --help > llama-server-help.txt
```

CUDA、Vulkan与Metal的独立构建命令见[llama.cpp完整教程](../chapters/frameworks/llama-cpp.md)。保留CMakeCache和完整构建日志。

## A.6 服务与HTTP

```bash
curl --fail-with-body http://127.0.0.1:8001/health
curl --fail-with-body http://127.0.0.1:8001/v1/models
curl --fail-with-body -N http://127.0.0.1:8001/v1/chat/completions \
  -H 'Content-Type: application/json' \
  -d '{"model":"Qwen3.6-35B-A3B-FP8","messages":[{"role":"user","content":"简要解释KV缓存。"}],"max_tokens":256,"temperature":0,"stream":true}'
```

模型别名必须与正在运行的服务一致。流式客户端按SSE解析，先保留原始事件再统计到达时间。

## A.7 基准与资源采样

```bash
llama.cpp/build-hip/bin/llama-bench \
  -m /srv/models/model.gguf -ngl 99 -p 512 -n 128 -r 3
```

```bash
nvidia-smi --query-gpu=timestamp,memory.used,utilization.gpu,temperature.gpu,power.draw \
  --format=csv -l 1 > gpu.csv
```

这两段分别是引擎测试与资源采样，均不证明HTTP性能或答案质量。完整服务压测入口见[性能测试教程](../chapters/performance/benchmarking.md)。

## A.8 CUDA双设备通信

在有两个可用设备、配套PyTorch/NCCL的环境，从仓库根目录执行：

```bash
torchrun --standalone --nproc-per-node=2 \
  docs/01-deployment-foundations/examples/all_reduce_check.py
```

它用于通信正确性冒烟，不是带宽基准或模型推理测试。检查脚本计算值和实际rank输出；本轮文档整理没有在GPU上执行此命令。

## A.9 离线核算历史数据

从仓库根目录执行，无需模型与GPU：

```bash
python docs/01-deployment-foundations/examples/verify_records.py
```

核对范围是[measurements.json](../evidence/measurements.json)的部分计数和算术。实际输出见[verified-output.txt](../examples/verified-output.txt)，它不能代替原始实验。
