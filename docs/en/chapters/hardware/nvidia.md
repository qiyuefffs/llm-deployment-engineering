# 1.2.1 NVIDIA GPU and CUDA software stack

[简体中文](../../../01-deployment-foundations/chapters/hardware/nvidia.md) | **English**

[Contents](../../SUMMARY.md) · [Hardware and runtime overview](../../02-capability-layers/01-hardware-backends.md)

## Hardware basics

NVIDIA GPUs execute matrix and vector operations using many parallel compute units. CUDA is a software platform that uses these devices for general computing, both for training and for inference.

|Hardware category|Common deployment features|Focus on selection|
| --- | --- | --- |
| GeForce RTX |It is commonly used for personal workstations with local inference, rather than independent VRAM.|VRAM, heat dissipation, practical precision, support, PCIe and power supply|
|RTX Professional Card|Designed for professional workstations, specific models offer different capacities and professional functionality|Capacity, drivers, reliability requirements, actual interconnect|
|Data center GPUs|Server-oriented, some models use HBM and high-speed interconnect|Bandwidth, low-precision support, multi-GPU topology, server support|
|Integrated CPU/GPU platform|CPU architecture, memory, organization, and software packages may differ from ordinary PCs.|ARM/x86, shared memory, compilation Goals and platform support|

CUDA Core performs general computing; Tensor Core supports matrix operations that accelerate, and which precisions support architecture changes. GPUs with Tensor Core are not representative of the efficient execution of any Int4/FP8 model, requiring a corresponding kernel, layout and shape.

`compute capability ` It's a powerful version of the GPU.`sm_XX` The device code target is not the same concept as VRAM capacity and CUDA Toolkit versions. Two generations of GPUs with the same capacity and supporting instructions may differ from the kernel.

## What each component of CUDA does

```text
PyTorch or engine with kernel
             → CUDA Runtime/Driver API ＋ compute library
             → NVIDIA driver → GPU
```

|Components|Responsibilities|Meaning of deployment|
| --- | --- | --- |
| NVIDIA Driver |Manage device and provide underlying device access, including CUDA Driver API support|The host must have a driver compatible with hardware and programs|
| CUDA Runtime |It provides memory allocation, execution flows, kernel startup and synchronization APIs.|Common library names `libcudart`; It may be provided by software packages or operating environments|
| CUDA Toolkit |development toolkit containing `nvcc`, headers, runtimes, selected libraries, and development tools|compilation is typically required when a CUDA program or extension; Running an existing program doesn't have to be a complete set|
| cuBLAS / cuBLASLt |In this case, it is possible to calculate the value of a matrix multiplier. Lt offers more flexible layout and algorithm choices|The model may use a linear layer or a special kernel for the engine.|
| cuDNN |Neural network compute library with supported operator and graph execution capabilities|Not all LLM deployments have to be installed separately for engine dependency use.|
| NCCL |Collective communication between GPUs, such as AllReduce, AllGather|It is commonly used for multi-GPU and multi-node; Communication efficiency also depends on topology and networking.|
|attention/ quantization kernel|Implement attention, dequantization, fused computation, etc.|FlashAttention is an operator implementation, not a GPU driver.|

CUDA Runtime, cuBLAS, cuDNN, NCCL have their respective responsibilities and versions; They don't have to be all in the same package. PyTorch or container-carried user mode dependency cannot replace host drivers.

## How to choose and understand performance

First check the target model and engine support, then estimate weights, KV and workspace. When the model is fully residing in VRAM, it is usually possible to avoid additional data paths from CPU offloading. If you can't, compare quantization, small model, offloading or multi-GPU.

Long input prefill, large batch matrix operations may be more dependency computing throughput; Low-volume decodes are often affected by weights and KV readings. Tensor computing capabilities, VRAM bandwidth, startup costs and communication can all be bottlenecks, and can't be limited to GPU peak TFLOPS.

There are three versions of the information that must be separated: `nvidia-smi ` display the driver and its CUDA compatibility; `nvcc --version ` The current compilation toolchain is shown; `torch.version.cuda` Displays the corresponding CUDA information that PyTorch builds. They don't have to be exactly the same, but they have to meet compatibility conditions.

Basic information: [The CUDA platform](https://docs.nvidia.com/cuda/cuda-programming-guide/01-introduction/cuda-platform.html) · [Compatibility](https://docs.nvidia.com/deploy/cuda-compatibility/) · [cuBLAS](https://docs.nvidia.com/cuda/cublas/index.html) · [NCCL](https://docs.nvidia.com/deeplearning/nccl/user-guide/docs/overview.html).

## Deployment procedures and examples

Following are the environmental checks, source code, construction and model operations. The historical device is only used to explain specific problems, versions and parameters, read according to the record.

Examples: [RTX 2060 mixed offloading](../../engineering/nvidia-rtx2060.md) · [RTX4080/A6000 dual-GPU](../../engineering/nvidia-dual-gpu.md) · [GB10 quantization and speculative decoding](../../engineering/nvidia-gb10.md) · [More than 10 GB models](../../engineering/nvidia-gb10-multimodal.md).

## First, create an environmental record

RTX4090 records using Ubuntu 22.04, 32GB host memory, 24GB device memory and the CUDA Toolkit 12.9. GB10 records the use of Ubuntu 24.04 ARM64, 128GB and CUDA13. The two environments have different CPU architectures and device targets, and software packages cannot be interchanged directly.

```bash
uname -m
nvidia-smi
nvcc --version
ptxas --version
nvidia-smi --query-gpu=name,compute_cap --format=csv
```

`nvidia-smi ` The CUDA field reflects driver compatibility.`nvcc ` with `ptxas ` It's part of the current toolchain.`torch.version.cuda` It's a reflection of the information that PyTorch builds. The numbers don't have to be completely consistent, but combinations should be supported. Source code extensions also require verification of PyTorch ABI and build dependency.

If the system doesn't `nvcc ` First, check if the toolkit is actually installed and where the PATH is pointing. Don't just do it.`nvidia-smi` conclude that the complete build environment is installed.

## 2 Installation and configuration in which order

Prepare the driver according to the official support of the operating system and device, and restart the request according to the installer instructions. Runtime or Toolkit required to prepare the framework. Environmental pre-recording has been done to avoid simultaneous replacement of drivers, compilers and frameworks.

It's already installed in `/usr/local/cuda-12.9` For example, the toolkit can be set to the current experiment shell:

```bash
export CUDA_HOME=/usr/local/cuda-12.9
export PATH="$CUDA_HOME/bin:$PATH"
export LD_LIBRARY_PATH="$CUDA_HOME/lib64:${LD_LIBRARY_PATH:-}"
command -v nvcc
nvcc --version
```

This is done by verifying the current terminal and then deciding whether the configuration is durable. When multiple toolkits coexist, the actual paths are recorded to prevent different versions from being read in build and run respectively.

## 3 - Complete a CUDA framework check

The PyTorch environment can perform the minimal tensor calculations in Chapter 1. The llama.cpp route enters [Construction and service tutorials](../frameworks/llama-cpp.md) and use `-DGGML_CUDA=ON` Pass log confirms device and actual offloading, and then runs a small model.

```bash
cmake -S . -B build-cuda   -DGGML_CUDA=ON -DCMAKE_BUILD_TYPE=Release
cmake --build build-cuda --target llama-server llama-bench llama-cli -j 4
```

Let CMake identify the target device. When explicit architecture is required, the native check value is used: the original 4090 record is 89, and GB10 needs to be verified according to its actual supporting combination. Compilation Successfully saved the version with CMakeCache and generated it again.

## Example 4: I found nvcc, why do I still make mistakes when linking?

The author 4090 records:

```text
No rule to make target '/usr/lib/x86_64-linux-gnu/libcudart.so'
```

The error pointed to the library path to which the cache reference was built. The library of the machine is actually in the Toolkit directory. The installation file and CMake configuration should be checked instead of replicating the dynamic library of other machines.

```bash
ls -l /usr/local/cuda-12.9/lib64/libcudart.so*
cmake -S . -B build-cuda-clean   -DGGML_CUDA=ON   -DCMAKE_CUDA_COMPILER=/usr/local/cuda-12.9/bin/nvcc   -DCMAKE_BUILD_TYPE=Release
cmake --build build-cuda-clean --target llama-server -j 4
```

The new directory avoids the old cache and keeps the wrong path. Specific results are based on in-house configuration and log construction; The original notes are not preserved in the dependency lock that can be used for the complete reconstruction of this round.

## Example: GB10 architecture with low-precision kernel

GB10 Engineering vLLM Submitted `17d87168d ` If you encounter `cvt with .e2m1x2 ` Not supported `sm_121` It's a mistake. It explains that the construction of the frame architecture involves instruction paths that are not applicable to the target. The original record had a specific attempt to use Objective 12.0 and could not set this as the default value for all GB10 projects.

First locate the failure kernel, precision and target, then verify the source code, fix and CUDA requirements. CPU architecture correct, device recognized, common tensor success is not enough to prove that all low-precision paths are available.

## Six, container and multi-GPU, what more checks to add?

When the host GPU is normal and the container is not visible to the device, check the NVIDIA Container Toolkit and Docker GPU access. Container maintains user-friendly environment while still dependency host driver. The whole process [Environment and containers](../delivery/environment-operations.md).

Multi-GPU checks first `nvidia-smi topo -m`, then validate collective communication. RTX4080 does not support NVLink, the bridge recommendation in the old notebook has been corrected. The total capacity of dual-GPUs cannot be considered as a single-device capacity directly, and communication needs to be supported by a framework.

## Seven, complete engineering examples: How does the RTX 2060 12GB model work larger than VRAM?

This record is suitable for answering a common on-device question: How do you judge whether mixed inference is still useful when VRAM can't put all the weights? The original device is i5-12400F, 32GB of system RAM, RTX 2060. **12GB edition** This is the first version of the Windows CUDA version of llama.cpp. Do not use the 6GB version 2060. The difference in capacity changes the number of layers and the pressure of the host that can be offloaded.

The main model in the record is `Qwen3-30B-A3B-Q6_K.gguf`. 30B represents the total parameter scale, and A3B represents the activation scale for each token; Unactivation experts are still part of the model asset. If you think of it as a small model with only 3B weights, you're going to get it wrong in terms of capacity estimates.

### 7.1 Separate the three types of memory

Before loading, record the number of bytes of model files, available system RAM, dedicated VRAM and current page file activity. Weights can be distributed in CPUs and GPUs, and execution also requires KV and temporary buffer. The CPU's CPU shared GPU memory cannot be directly viewed as storage at the same speed as the GPU's local VRAM.

```powershell
Get-CimInstance Win32_Processor | Select-Object Name, NumberOfCores, NumberOfLogicalProcessors
Get-CimInstance Win32_OperatingSystem | Select-Object TotalVisibleMemorySize, FreePhysicalMemory
Get-Item -LiteralPath '.\models\Qwen3-30B-A3B-Q6_K.gguf' | Select-Object Name, Length
nvidia-smi --query-gpu=name,memory.total,memory.used --format=csv
.\llama-server.exe --version
.\llama-server.exe --list-devices
```

First confirm binary from the same distribution package, CUDA dependency matches the program. The log needs to appear on the backend of the CUDA and RTX 2060, not just the CPU. Then look at the actual number of offloading layers in the model load log, the CPU/GPU buffer and the size of the KV; These are the results of the distribution.

### 7.2 How to read original configuration

Original notes used `--top-k 1 -c 2048 -n 1000 -ngl 99 --mlock --parallel 8` Wait for the parameters. They describe different things:

|Parameters|Meaning of engineering|What should be checked in this case|
| --- | --- | --- |
| `-ngl 99` |As many layers as possible of offload|Real offloading logs, VRAM and whether the load was successful|
| `-c 2048` |Budget for this edition|The total context in the launch log and each slot context|
| `--parallel 8` |Configuration service slot|Capacity of each slot, simultaneous active request and KV occupancy|
| `-n 1000` |Default generated upper limit|request whether the end has an alternate limit, whether it ends naturally|
| `--top-k 1` |Putting Candidate Limits at the Top|Model Template and Quality|
| `--mlock` |Try locking the mapping memory|System permissions, whether it is actually successful, other processes remaining|

`-ngl 99` This does not mean that when VRAM is not enough, the best hybrid solution is automatically obtained. Some versions fail directly during the allocation phase, while other combinations have automatic adaptation behavior. Public tutorials should start with the smallest amount of offloading that can be explained and adjusted according to the log.

The original records are still there.`--tensor-split 0.9,0.1`. This option is used to allocate between the backend devices. **Not CPU/GPUs account for 10%/90% of the general switches**. Baseline of primary primary layer offloading performed by a single CUDA device; Multi-device disconnect [Multi-GPU themes](../performance/parallelism.md).

### 7.3 Reorganize to verifiable order of operation

The following is a check configuration based on the original design, with a single slot, short output, to locate the capacity. It differs from the complete configuration of historical performance, not giving it the old performance figures.

```powershell
.\llama-server.exe -m .\models\Qwen3-30B-A3B-Q6_K.gguf `
  --alias qwen30b-q6 -ngl 20 -c 2048 --parallel 1 `
  --host 127.0.0.1 --port 8081
```

After the first stage is started, the other terminal submits `你好` And a short question with a clear answer. Check the full response, the reason for the end, the actual number of prompt/eval tokens. Loading failure first reduces offloading or replaces smaller artifact; After the short questions are normal, try more offloading layers with fixed inputs respectively. Save commands, load logs, and empty resources before each restart, and do not scrape multiple configuration resources into a set of results.

After the number of layers of offloading increases, the GPU's standing weights increase, CPU side weights and execution load may change, but the model structure, buffer and mapping make the memory not strictly linearly linear by layer. One attempt is only worth keeping if the functionality is correct, no continuous page changes and speed gains are visible.

### 7.4 An authentic reproduction of the original

In the Q6 record, the full engine timing for this generation is:

|Stages|The number of tokens|The Time|The rate|
| --- | --- | --- | --- |
| Prompt eval | 9 | 995.30ms | 9.04token/s |
| Eval | 182 | 34618.63ms | 5.26token/s |
|Two times combined| 191 | 35613.93ms |Decode the average of the two phases|

According to the original time calculation, Prompt is about 110.59ms/token and Eval is about 190.21ms/token. 182 here is the actual generating number, not the 1000 of the configuration. The table is engine-observed, does not contain a complete set of HTTP concurrency tests, nor does it indicate the same speed for long inputs.

At the same time, about 21% of the CPU, 85% of the system RAM, 89% of the CPU, 98% of the GPU, 100% of the CPU were observed. High GPU utilization can be created simultaneously with generating only about 5.26 tokens/s: the bandwidth of the large language model, CPU/GPU data pathways and each step of the workflow affect speed, and utilization is not a user experience score.

The original note described pressure as “100% disk swapping,” but did not retain enough context to identify whether this meant page-file activity, disk active time, or another metric. This knowledge base therefore leaves the metric definition unspecified. For further judgement, synchronous page readings, disk throughput, process working set and TTFT/TPOT should be collected.

### 7.5 concurrency Why add to last

The original Q6 load testing command was EvalScope.`parallel=8、number=2 ` Another Q5 record is: `Qwen3-32B-Q5_K_M.gguf ` Service slot 4, testing `parallel=1、number=5、max-tokens=200`. There is no readable complete request score, can't fill out 8 concurrency passes or add speed to Q5.

Adding slots would affect the context allocation with KV, and allow multiple requests to compete for the same memory bandwidth. The correct order of extension is: complete the length of the target input and output of a single request, then measure c1, c2, see if the total throughput increases and whether the wait for each request is acceptable. When system RAM is running out, the model/context/concurrency stress is reduced.

### 7.6 What conclusions can be drawn from this example

Under this 32GB RAM+12GB VRAM configuration, the Q6 model larger than VRAM completed a hybrid generation, leaving a decode observation of about 5.26 tokens/s. Whether or not it is suitable for everyday use will also be decided jointly by the complete answer, the length of the target, the continuous change of pages and interaction. If the goal is fluid interaction, a smaller model, full GPU and large language model should be mixed together as two independent candidate comparisons.

## Visual deployment of GB10: What links should be verified after the text endpoint?

The author's GB10 material includes Qwen3-VL, Qwen3-Omni and granite-docling. They share devices, not all operating borders. Visual needs processors, image encoders and image splicing; Omni may also involve audio encoding, output heads, and flow protocols. One of them.`/v1/models` Successful responses can only prove that the service is accessible.

Primary engineering use `nvcr.io/nvidia/vllm:25.12-py3` It's a supporting environment. For example, as deployment records are retained, a larger upper limit in the table is not equal to the acceptance testing of the same length:

|Model|The original port|The main configuration|Content for separate acceptance testing|
| --- | --- | --- | --- |
| Qwen3-VL-30B-A3B | 8006 |TP1,PP1,memory0.8,batched4096; Ctx used to set 100000/131072|Multi-graphics, image sizes, long input of actual tokens|
| Qwen3-VL-8B | 8007 |One device, memory 0.8.|It's the end of image analysis, the end of the word, the end of the flow.|
| Qwen3-Omni-30B-A3B | 8008 | TP1,PP1,memory0.9 |Testing of text, images, audio input and audio output respectively|
| granite-docling-258M | 8009 | TP1,PP1,seqs512,batched8192,chunked prefill,memory0.9 |Structure, order and accuracy of transcription of documents|

These ports belong to different experiments and cannot be judged by all models staying at the same time. In the 16/128GB device's unified memory, image preprocessing, visual tokens, KV, and multi-mode cache also account for the budget. The new deployments complete the link with a single model, single diagram, single request, and then gradually restore the original budget.

Complete image input generation, base64 request, SSE client and verification process followed [VLLM service chapter](../frameworks/vllm-service.md#seven-complete-links-from-image-files-to-streaming-answers).

## Completion checks

Environmental records can distinguish between drivers, toolkits and frameworks; Minimum completion of the calculation; the actual model used in the backend of the target; Builds with errors that can be traced back to a fixed version. After that, go to the Models and Services section.

Source: author of the Linux compilation llama.cpp-CUDA version of the DGX Spark compilation vLLM deployment Qwen 3.6-35B-A3B and dual-GPU deployment records, see [List of corresponding articles](../../evidence/chapter-sources.md).
