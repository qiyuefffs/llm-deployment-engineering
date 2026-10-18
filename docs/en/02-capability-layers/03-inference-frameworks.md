# Layer 3: inference frameworks

[简体中文](../../01-deployment-foundations/02-capability-layers/03-inference-frameworks.md) | **English**

[Contents](../SUMMARY.md) · [The VLLM process](../chapters/frameworks/vllm-service.md) · [llama.cpp workflow](../chapters/frameworks/llama-cpp.md) · [The OpenVINO process](../chapters/frameworks/openvino.md)

## 3.1 Framework roles

Inference engine to convert model files into executable programs: load weights, set templates, manage KVs, select kernels, schedule requests, and convert tokens to output. It works with device software stacks such as CUDA, ROCm.

### Distinguish frameworks, engines, and services

|Levels|Responsibilities|Examples|
| --- | --- | --- |
|Tensor/machine learning framework|Operator and device execution| PyTorch,MLX |
|Inference engine or model pipeline|Modeling, generating cycles, KV, batching and sampling| vLLM,llama.cpp,MLX-LM,OpenVINO GenAI |
|model services|Protocols, requests, checks, queues, flow outputs and monitoring|Engine with self-contained server, independent service packaging|
|Application layer|Interfaces for conversations, business organization, knowledge retrieval, tool calls|Desktop clients, web applications, and application APIs|

A project may cover several layers simultaneously, such as a vLLM engine that also provides HTTP services. When judging responsibilities, look at the actual execution chain, not deduce all functionality from the project name.

### Loading and generation are different stages

```text
Start: read configuration / weights → allocate device memory → compilation or load kernel/graph
    → allocating cache and workspace → warm-up → ready
Request: template/tokenization → queueing → prefill → decode/sampling → output → release state
```

Loading time, first request time and steady generation time should be observed separately. the model port has been listened to, not the model is ready; The first request is slow, and it doesn't necessarily mean slow every decode.

### Roles of common engines

|The Framework|Major project objects|Priority verification|
| --- | --- | --- |
| vLLM |Multiple requests for services, KV scheduling, TP/PP/EP, OpenAI API|model / quantization kernel, backend and scheduling parameter|
| llama.cpp |GGUF, CPU/GPU offloading, multi-backend, CLI/server|tensor type, backend, memory, slot|
| TensorRT-LLM |NVIDIA supports compilation and service optimization|GPU intergenerational, model, execute artifact and version|
| SGLang |Service scheduling, caching, structured output, etc.|model/backend, prefix, management and protocol|
| OpenVINO GenAI |IR pipes supporting devices such as Intel|Export models, device compilations and shapes|
| MLX-LM / MLX-VLM |Implementation of the text/visual model based on MLX|Model artifact, processor, template and service packaging|
| Ollama/LM Studio |Local model management and interfaces|Templates, real backend and resources, UI is not a substitute for load testing|

## 3.2 vLLM components

```text
HTTP/API testing → chat template/tokenizer → waiting in line
 → Scheduler → KV Block Manager/Prefix Cache
 → Model Executor → attention/matmul/MoE kernel
 → sampler → detokenize → SSE/JSON → End with resources
```

|Subsystems|Parameters / Data|Mechanical engineering|
| --- | --- | --- |
|Access to| model,messages/prompt,max_tokens,stop |Parameters, lengths, templates and input tests|
| Prefill/Decode |Input tokens, historical KVs, current tokens|Prefill state, decode generated step by step|
|KV management|Block, dtype, references, blocks are available|Block allocation/recycling, prefix reusable|
|scheduling| max-num-seqs,max-num-batched-tokens |The number of activity sequences and the budget for each round of tokens are not equal to the number of client requests.|
|Long input| enable-chunked-prefill |Block scheduling that affects prefill/decode interference|
|Repeat the prefix| enable-prefix-caching |With the same token prefix, reuse, cache cooling and tenant recording|
|model parallelism| tensor/pipeline parallel,expert parallel |Rank mapping, communication, and budget per card|
|Planning and execution| enforce-eager,attention-backend |Warm-up / graph capture, workspace and support for kernel|
|Output| reasoning/content,finish_reason,usage |EOS/stop/length/delete/wrong records respectively|

Process monitoring port, model ready, functionality passed and workload passed are four states. In addition to the original extensions, torch, Triton/FlashInfer/device repositories are required to be installed. The source code directory can hide the installed modules, and the Python package may still be loaded after the upgrade.

## 3.3 Common vLLM launch templates

```bash
vllm serve /srv/models/example-model \
  --served-model-name example-model \
  --host 127.0.0.1 --port 8001 \
  --tensor-parallel-size 1 \
  --gpu-memory-utilization 0.80 \
  --max-model-len 4096 --max-num-seqs 1
```

This is a small budget configuration template, model and parameter that needs to be verified by device.`gpu-memory-utilization ` It's the engine memory budget, not GPU compute throughput utilization rate.`trust-remote-code` Only used when fixed models are needed and have been reviewed.

```bash
curl --fail-with-body http://127.0.0.1:8001/health
curl --fail-with-body http://127.0.0.1:8001/v1/models
curl --fail-with-body http://127.0.0.1:8001/v1/chat/completions \
  -H 'Content-Type: application/json' \
  -d '{"model":"example-model","messages":[{"role":"user","content":"计算12乘13，只输出数字。"}],"temperature":0,"max_tokens":128}'
```

First acceptance testing functionality, SSE, error and cancellation, and then fixed tokenizer load testing. Start-up, KV budget, hot body and real 200 request data [Full example of GB10](../engineering/nvidia-gb10.md).

## 3.4 llama.cpp components

```text
GGUF reading/architecture recognition → Tensor and GGML graph → CPU/device backend
 → weights /KV/ cycle state/ workspace → prefill/decode → sample/ template
Tools: llama-cli / llama-bench / llama-server / llama-quantize
```

|Parameters|The role|Objects observed|
| --- | --- | --- |
| -ngl / --n-gpu-layers |number of layers of request offloading|The actual offloaded layer, per backend buffer|
| -c / --ctx-size |Context Budget|Total ctx, per slot ctx, KV/ state and long input|
| -np / --parallel |Parallelism slot Budget|Activity sequence, waiting for request, length of each slot|
| -b / --batch-size |Logical token batch|Prefill throughput, scheduling and workspace|
| -ub / --ubatch-size |Physical microbatch|Temporary buffer peak and kernel efficiency|
| -t / --threads |The CPU executes threads|CPU workload and decoding time|
| --threads-batch |Prefill side threads|pp time, scheduling and competition|
| -fa |Attention to make choices|backend support, KV dtype, accuracy and speed|
| tensor-split / split-mode |device allocating and cutting|Each device weights, KV, communication|

Start log verification in a fixed version of the ctx-parallel semantics and can't be estimated using only one general rule of thumb. The CPU/GPU mix is also influenced by both computing, data transmission and RAM. Structures such as GDN/SSM have a circular state and cannot be based solely on the pure attention KV model.

## 3.5 Common llama.cpp build templates

The same source code, separate build directories at each end. First record the commit, compiler, runtime and targetarch, and then configure the actual enabled items in the CMakeCache.

```bash
# 选择当前设备的一条路线；依赖按平台实例准备
cmake -S . -B build-cpu -DCMAKE_BUILD_TYPE=Release
cmake -S . -B build-cuda -DGGML_CUDA=ON -DCMAKE_BUILD_TYPE=Release
cmake -S . -B build-hip -DGGML_HIP=ON -DCMAKE_BUILD_TYPE=Release
cmake -S . -B build-vulkan -DGGML_VULKAN=ON -DCMAKE_BUILD_TYPE=Release
cmake -S . -B build-metal -DGGML_METAL=ON -DCMAKE_BUILD_TYPE=Release
```

```bash
# 示例：已经配置CUDA目录后
cmake --build build-cuda --target llama-server llama-bench llama-cli -j 4
./build-cuda/bin/llama-cli --version
./build-cuda/bin/llama-cli --list-devices
./build-cuda/bin/llama-server \
  -m /srv/models/model.Q4_K_M.gguf -ngl 99 -c 4096 -np 1 \
  --host 127.0.0.1 --port 8080
```

SYCL,MUSA,CANN is prepared separately by the corresponding submission and manufacturer toolchain, and the unknown CMake variable may be ignored, so it cannot be determined that the backend is enabled. See full steps of the platform [Example matrix](../engineering/README.md).

## 3.6 vLLM vs llama.cpp selection table

|Restrictions|Priority Candidate|Evidence of decision-making|
| --- | --- | --- |
|GGUF, low VRAM, mixed offloading| llama.cpp |Support architecture, RAM/VRAM, offloading and quality|
|Multi-request services and model parallelism|Service engines such as vLLM|kernel, scheduling, effective throughput under target SLO|
|Intel on-device| IR/GenAI,SYCL/Vulkan |Graphics/shape, device compilation, full output|
|Apple unified memory|Metal or MLX routes|Artifact, text/visual, cache and concurrency|
|Deep optimization for specific NVIDIA|TensorRT-LLM and so on|Model support, cost of construction, actual performance|
|Quick local management| Ollama/LM Studio |Backend, templates, APIs and maintenance costs|

First, the hardware, artifact, functionality, three screens, and then the task quality, latency, resources and delivery costs are compared. Complete FlowUs framework/service articles are written in device instances, with no replacement deployment steps.
