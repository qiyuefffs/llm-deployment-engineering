---
id: T21
title: "llama.cpp：构建、加载、接口与停止"
type: tutorial
volume: book
layer: 3
platform: "general"
device: "general"
status: historical
source_ids: []
updated: 2026-10-19
summary: "llama.cpp是一套模型执行工具，不要求先装PyTorch。它通过不同后端使用CPU或加速设备，围绕GGUF提供CLI、server、benchmark与量化程序。本章将构建、加载与接口串成一条链，平台特殊问题回到硬件专题查看。"
---

# llama.cpp：构建、加载、接口与停止

[总目录](../../SUMMARY.md) · [所属总章](../../02-capability-layers/03-inference-frameworks.md) · [CPU完整实跑](../../cases/C14-windows-cpu/README.md)

## 本章概览

llama.cpp是一套模型执行工具，不要求先装PyTorch。它通过不同后端使用CPU或加速设备，围绕GGUF提供CLI、server、benchmark与量化程序。本章将构建、加载与接口串成一条链，平台特殊问题回到硬件专题查看。

构建示例固定`b9557`。作者FlowUs提供CUDA、HIP、Vulkan、Metal、SYCL以及RPC工程；本轮实际运行的是Windows官方CPU二进制，其他构建命令作为对应环境的操作说明。

## 1. 选择一个后端，建立独立构建目录

先安装Git、CMake、C++工具链，再准备所选后端的开发依赖。Linux可先安装发行版的`build-essential`、`cmake`、`git`与`libcurl4-openssl-dev`；GPU工具链按对应设备官方安装说明准备。Windows优先从CPU二进制开始，再学习Visual Studio开发工具和源码构建。

```bash
git clone --branch b9557 --depth 1 https://github.com/ggml-org/llama.cpp.git
git -C llama.cpp rev-parse HEAD
```

下面的路线每次选一条。独立目录避免旧的编译器、CUDA路径和后端选项残留。

### CPU

```bash
cmake -S llama.cpp -B llama.cpp/build-cpu -DCMAKE_BUILD_TYPE=Release
cmake --build llama.cpp/build-cpu \
  --target llama-cli llama-server llama-bench llama-quantize -j 4
```

### NVIDIA CUDA

```bash
cmake -S llama.cpp -B llama.cpp/build-cuda \
  -DGGML_CUDA=ON -DCMAKE_BUILD_TYPE=Release
cmake --build llama.cpp/build-cuda \
  --target llama-cli llama-server llama-bench -j 4
```

在多架构构建或交叉编译时，需要明确目标计算能力。不要把GB10的121或历史绕过的120直接套用到其他GPU。CMake是否发现nvcc与运行时能否找到CUDA库，也要分别检查。

### AMD HIP

```bash
cmake -S llama.cpp -B llama.cpp/build-hip \
  -DGGML_HIP=ON -DAMDGPU_TARGETS=gfx1151 \
  -DCMAKE_BUILD_TYPE=Release
cmake --build llama.cpp/build-hip \
  --target llama-cli llama-server llama-bench -j 4
```

`gfx1151`对应作者395设备，其他型号用`rocminfo`确认。运行库、kernel与可分配内存问题见[AMD专题](../hardware/amd.md)。

### Vulkan

```bash
cmake -S llama.cpp -B llama.cpp/build-vulkan \
  -DGGML_VULKAN=ON -DCMAKE_BUILD_TYPE=Release
cmake --build llama.cpp/build-vulkan \
  --target llama-cli llama-server llama-bench -j 4
```

Vulkan需要配套SDK/开发库和设备驱动。先用`vulkaninfo --summary`确认设备，防止实际选择软件实现。Intel记录也说明驱动变化会改变结果，应保存驱动版本。

### Apple Metal

```bash
cmake -S llama.cpp -B llama.cpp/build-metal \
  -DGGML_METAL=ON -DCMAKE_BUILD_TYPE=Release
cmake --build llama.cpp/build-metal \
  --target llama-cli llama-server llama-bench -j 4
```

Metal依赖macOS与Xcode命令行工具。统一内存需要给系统和其他应用保留空间。特殊量化类型与MoE kernel失败见[Apple专题](../hardware/apple.md)。

## 2. 检查程序身份，再加载模型

下面统一沿用CPU目录。使用GPU构建时同时修改可执行路径与`-ngl`，并在日志确认真实层分配。

```bash
llama.cpp/build-cpu/bin/llama-server --version
llama.cpp/build-cpu/bin/llama-server --help > llama-server-help.txt
llama.cpp/build-cpu/bin/llama-cli \
  -m artifacts/gguf/Qwen3-0.6B-Q4_K_M.gguf \
  -ngl 0 -c 2048 -t 4 -n 64 -p '简要说明KV缓存。'
```

模型路径接续[转换教程](../models/gguf-conversion.md)。也可以使用官方GGUF，但要记录仓库、revision、文件名和摘要。加载时检查模型架构、词表、模板、上下文、后端缓冲与警告，不能只确认最后出现了一段中文。

`-ngl`提出GPU卸载层数请求；实际卸载由架构、后端和资源决定。部分卸载时，CPU、GPU与传输共同决定速度，CPU线程越多也不一定越快。先固定4或8线程，再用目标负载测量。

## 3. 启动本地服务

```bash
llama.cpp/build-cpu/bin/llama-server \
  -m artifacts/gguf/Qwen3-0.6B-Q4_K_M.gguf \
  --alias book-qwen3-06b \
  --host 127.0.0.1 --port 18080 \
  -ngl 0 -c 2048 -np 2 -t 4 -tb 4 \
  --metrics \
  --chat-template-kwargs '{"enable_thinking":false}'
```

禁用思考的模板参数与Qwen3模板有关，不能用于所有模型。`-c`、`-np`的上下文分配语义要结合版本与启动日志看：本体系实跑版本打印总上下文2048、两槽位、每槽位1024。输入与输出应在对应槽位预算内。

并行槽位不是客户端请求总数。客户端可以发送更多请求，服务会按资源调度或等待。槽位变多会增加同时执行能力，也可能压缩每槽位可用预算并增加单请求延迟。

## 4. 在第二个终端检查完整响应

```bash
curl --fail-with-body http://127.0.0.1:18080/health
curl --fail-with-body http://127.0.0.1:18080/v1/models
curl --fail-with-body http://127.0.0.1:18080/v1/chat/completions \
  -H 'Content-Type: application/json' \
  -d '{"model":"book-qwen3-06b","messages":[{"role":"user","content":"计算2+2。只输出一个数字。"}],"max_tokens":64,"temperature":0}'
```

检查别名、正文、usage和结束原因。随后测试流式、JSON任务、超长输入与错误请求。在本体系实际CPU演练中，相同算术题输出错误，畸形JSON返回500。它们已经记录在[真实验收文件](../../cases/C14-windows-cpu/results/2026-10-18-windows-cpu/acceptance.json)，不能因为服务还能响应就忽略。

## 5. 先停服务，再测引擎

前台按Ctrl+C停止这个实例，确认退出后执行：

```bash
llama.cpp/build-cpu/bin/llama-bench \
  -m artifacts/gguf/Qwen3-0.6B-Q4_K_M.gguf \
  -ngl 0 -t 4 -p 64 -n 32 -r 3 -o json > engine-benchmark.json
```

pp64测输入处理，tg32测生成；它们没有HTTP排队、模板和网络开销。让server继续占用同一设备再跑bench，会引入资源竞争。服务性能应另测HTTP，不与引擎tg混成一列。

## 6. RPC 与本地多卡放到第二阶段

本地模型与后端先通过，再做RPC或多卡扩展。作者AMD五机工程解决了GTT/TTM分配问题，并得到短上下文生成记录，但没有同口径单机基线，不能据此宣称五机加速。

RPC增加远端后端与网络边界，需要记录各节点程序版本、后端库、模型切分、通信与恢复。具体过程见[多卡与多节点](../performance/parallelism.md)。先完成本章单机链路，能够显著缩小后续故障范围。
