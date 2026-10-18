# Appendix A: Frequently ordered speed checks

[简体中文](../../01-deployment-foundations/appendices/commands.md) | **English**

[Contents](../README.md) · [Accelerated failure checks](../06-troubleshooting.md) · [References](references.md)

The commands are used to locate and collect information. The model also requires a corresponding device, driver and fixed source code to run and build commands, see Part II; Do not run this page from beginning to end as an installation script.

## A.1 Linux environment and disk

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

Look at the CPU architecture, the core, the current memory and storage available, not just the product labels. The original environment file may contain a device identifier, public pre-check.

## A.2 device and toolchain

|Platform|Orders|Focus on content|
| --- | --- | --- |
| NVIDIA | `nvidia-smi `, ` nvcc --version` |Driver and Toolkit confirmed separately|
|NVIDIA container| `nvidia-ctk --version` |Container Toolkit is installed|
| AMD | `rocminfo `, ` hipcc --version` |Real gfx and HIP versions|
| Intel Vulkan | `vulkaninfo --summary` |Select which device and driver|
| Intel SYCL | `sycl-ls `, ` icpx --version` |OneAPI environment with GPU device|
| Intel OpenVINO |Python below|Plugins can detect devices, not models can be executed|
| Apple | `sw_vers `, ` uname -m `, ` xcode-select -p` |MacOS, architecture and development tools|
|Ascend| `npu-smi info` |The state of the chip and device, as well as the CANN/plugin|

```python
import openvino as ov
print(ov.__version__)
print(ov.Core().available_devices)
```

Windows only reads checks:

```powershell
Get-CimInstance Win32_VideoController | Select-Object Name, DriverVersion
Get-CimInstance Win32_OperatingSystem | Select-Object Caption, Version, BuildNumber
```

## A.3 Python backend confirmed

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

The ROCm version of PyTorch is also available in parts.`torch.cuda` The interface. llama.cpp does not require additional installation of PyTorch, and uses its own backend log verification directly.

## A.4 Fixed source code and artifact

```bash
git -C llama.cpp rev-parse HEAD
git -C llama.cpp status --short
sha256sum /srv/models/model.gguf
python -m pip freeze > python-packages.txt
```

The model shard is tested one at a time. In addition to GGUF, artifacts also need to record configurations, tokenizers, templates, and auxiliary files. SHA256 can verify the same document and cannot prove model quality or license.

## A.5 Building and programming assistance

Here's a template for building HIP.`gfx1151` This is the 395th episode of the series.

```bash
cmake -S llama.cpp -B llama.cpp/build-hip \
  -DGGML_HIP=ON -DAMDGPU_TARGETS=gfx1151 -DCMAKE_BUILD_TYPE=Release
cmake --build llama.cpp/build-hip --target llama-cli llama-server llama-bench -j 4
llama.cpp/build-hip/bin/llama-server --version
llama.cpp/build-hip/bin/llama-server --help > llama-server-help.txt
```

CUDA, Vulkan and Metal independently constructed commands [This is a complete tutorial.](../chapters/frameworks/llama-cpp.md). Keep the CMakeCache and complete log construction.

## A.6 Services with HTTP

```bash
curl --fail-with-body http://127.0.0.1:8001/health
curl --fail-with-body http://127.0.0.1:8001/v1/models
curl --fail-with-body -N http://127.0.0.1:8001/v1/chat/completions \
  -H 'Content-Type: application/json' \
  -d '{"model":"Qwen3.6-35B-A3B-FP8","messages":[{"role":"user","content":"简要解释KV缓存。"}],"max_tokens":256,"temperature":0,"stream":true}'
```

The model name must be consistent with the service being run. The stream client is SSE-parsed, retaining the original event and then counting the arrival time.

## A.7 benchmark and resources sampling

```bash
llama.cpp/build-hip/bin/llama-bench \
  -m /srv/models/model.gguf -ngl 99 -p 512 -n 128 -r 3
```

```bash
nvidia-smi --query-gpu=timestamp,memory.used,utilization.gpu,temperature.gpu,power.draw \
  --format=csv -l 1 > gpu.csv
```

These two sections are engine testing and resource sampling, which do not prove HTTP performance or response quality. Full service load testing [Performance testing tutorials](../chapters/performance/benchmarking.md).

## A.8 CUDA dual device communication

In environments with two available devices, supporting PyTorch/NCCL, execute from the repository root directory:

```bash
torchrun --standalone --nproc-per-node=2 \
  docs/01-deployment-foundations/examples/all_reduce_check.py
```

It is used for communication accuracy smoking, not bandwidth benchmark or model inference testing. Check the calculated value of the script and the actual rank output; This round of documentation does not execute this command on GPUs.

## A.9 Offline billing of historical data

From the repository root directory, models and GPUs are not required:

```bash
python docs/01-deployment-foundations/examples/verify_records.py
```

The scope of the verification is [measurements.json](../../01-deployment-foundations/evidence/measurements.json) Part of the calculation and arithmetic. Actual output views [verified-output.txt](../../01-deployment-foundations/examples/verified-output.txt) It can't replace the original experiment.
