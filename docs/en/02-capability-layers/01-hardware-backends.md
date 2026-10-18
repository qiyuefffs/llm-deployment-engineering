# Layer 1: hardware, runtimes, and compute backends

[简体中文](../../01-deployment-foundations/02-capability-layers/01-hardware-backends.md) | **English**

[Contents](../SUMMARY.md) · [Examples of complete hardware engineering](../engineering/README.md)

## 1.1 What this layer addresses

The parameters of the large language model are stored in memory, and matrix multiplication, attention computation and data transfer are continuously performed during inference. This layer answers first: **What hardware is used, what software is used, what capacity and speed are restricted.**

### 1.1.1 Roles of CPUs, GPUs, and NPUs

|Hardware|Basic features|Responsibilities in the deployment of the large language model|
| --- | --- | --- |
| CPU |A master of general control, branch, and system tasks, he can also perform vector and matrix computation.|In addition to this, it is important to understand the importance of the application process and how it is implemented. It is also possible to infer independently or assume a partial model layer.|
| GPU |There is a great deal of parallelism in unit execution, suitable for matrix and vector operations|Execute the main calculations of the model, storing weights, KV Cache and workspace|
|NPU/AI Accelerator|Neural network computing design, usually supported by dependency compilers and operators|Inference within the supported model, precision, shape range, and cannot be defaulted to replace GPUs|

CPU/GPU/NPU refers to the hardware category, CUDA/ROCm/Metal, and other software stacks. The NPU is based on the assumption that the model can be converted, the operator can be compiled, executed and output correctly. The device marked TOPS cannot be directly converted into large language model token/s.

### 1.1.2 Hardware specifications to check first

|Indicators|Meaning|Effects|
| --- | --- | --- |
|Memory / VRAM capacity|Weights and how much we can put in running condition|Model size, context, length, and concurrency|
|memory bandwidth|How much data can be delivered to the computing unit per second|Low-volume decodes are often influenced by weights and KV readings|
|Computational skills|Operating speed at specific precision and shape|Prefill, bulk and matrix computation efficiency|
|Precision and Operator Support|If the hardware and kernel can execute BF16, FP8, INT4, etc.|The question is whether some kind of quantization can work or accelerate.|
|device interconnect|It's like PCIe, NVLink, xGMI, network, and so on.|Offloading, multi-GPU and multi-node data exchange costs|
|Power consumption and heat dissipation|Frequency and energy consumption conditions of continuous runtime|On-device, long running, noise, stable performance|

The capacity to respond to the pumps will affect whether the pumps can drop the pumps, bandwidth and computing ability. FP16/FP8/INT8 compute throughput, scarcity/density compute throughput cannot be separated horizontally directly; It's also about the actual operator, batch and precision.

### 1.1.3 Dedicated VRAM and unified memory

Independent GPUs typically have their own VRAM, requiring data transfer between the host RAM and VRAM. CPU offloading can reduce VRAM requirements, but can also increase CPU computing and PCIe transmission. Two 24GB GPUs are not automatically displayed as a 48GB GPU, requiring the engine to split the model and assume communication.

Apple Silicon and some AMD/Intel integrated GPUs use shared physical memory. CPU/GPUs can access the same memory pool, but operating systems, applications, weights and KVs still compete for capacity and bandwidth; Device allocated budget may also be smaller than physical capacity. Shared memory is not the same as no runtime or unlimited VRAM.

### 1.1.4 Software call paths

```text
Business processor / HTTP interface
        ↓
Inference engine: vLLM / llama.cpp / MLX-LM / OpenVINO GenAI
        ↓
Tensor framework or computation backend: PyTorch / MLX / GGML / OpenVINO Runtime
        ↓
Runtime and operator: CUDA / HIP / Metal / Level Zero / CANN
             + Matrix library, attention kernel, communication library
        ↓
device driver / firmware → GPU or NPU
```

It's a division of responsibilities. The same engine may directly call the device API, self-contained kernel, or pass other frameworks to execute; It doesn't have to go through all the software packages.

the driver is responsible for accessing the device; Runtime is responsible for memory, execution and synchronization; The operator library provides computations such as matrix multiplication; Inference engine manages model loading, KV, request scheduling and output. The toolkit/SDK provides the main files, compilers, tools and library packages needed for development.

```text
Exectability = device Available for the backend of the boot runtime support
         Backup support for Backup dtype/quantisation kernel Backup memory/communication is available
```

|Software layer|Responsibilities|Common Failure Evidence|
| --- | --- | --- |
|Driver/ firmware|Manage device, memory and execution queues|device missing, permissions, modules/firmware not matched|
| Runtime |memory allocation, submission execution and sync|Missing so/DLL, versions or symbols not matched|
| Toolkit/SDK |Compiler, headers, development tools and support libraries|Target architecture not supported, missing files, compilation/link errors|
|The back of the frame|Calculating charts and tensors are mapped to the device|CPU fallback, unknown backend, unbuilt backend|
|Kernel/ operator|It's a way to make sense of matmul, attention, norm, MoE, vision, and so on.|Unsupported arch/type/op, incorrect output|
|Communication layer|Data exchange between ranks|P2P failure, wrong network card/topology|

The driver can record the GPU only to prove the first layer. The goal model is the complete generation, quality, and workload passed to form the deployment conclusion.

## 1.2 Platform capability map

### 1.2.1 Platform overview

|Platform|Hardware|compute software stack|Commonly used large language model routes|
| --- | --- | --- | --- |
| NVIDIA |GeForce, RTX professional cards, data center GPUs, and integrated platforms|The CUDA platform; CUDA Runtime, cuBLAS/cuBLASLt, NCCL and so on| PyTorch/vLLM,TensorRT-LLM,llama.cpp CUDA |
| AMD |Radeon,Instinct,Ryzen integrated GPU|ROCm platform; HIP, rocBLAS/hipBLASLt, RCCL, etc.|Supported PyTorch/vLLM ROCm,llama.cpp HIP or Vulkan|
| Apple Silicon Mac |CPU, GPU, Neural Engine integrated into SoC, shared physical memory|macOS GPU driver and Metal; MLX is an upper-level machine learning framework| MLX-LM/MLX-VLM,llama.cpp Metal,PyTorch MPS |
| Intel |CPUs, Arc/integrated GPUs, parts of the Core Ultra NPU|oneAPI/SYCL,Level Zero; OpenVINO Runtime and device plugins|Llama.cpp SYCL/Vulkan, OpenVINO GenAI, supported by XPU routes|
|Ascend|Specialized accelerators for AI with different chip capabilities|Driver/firmware, CANN, operator libraries, HCCL, and framework plugins|Matching MindIE, PyTorch + torch_npu, and vLLM Ascend components|
|Moore Threads|GPUs using the MUSA software stack|MUSA Toolkit, runtime and supporting compute library|The device and version actually support frameworks or the backend of the GGML|
| CPU |x86/ARM processor|Threads, vector instructions, BLAS/oneDNN/Accelerate, etc.|llama.cpp CPUs, OpenVINO CPUs and other CPU engines|

**CUDA and ROCm are computing software platforms; Metal is the GPU API; MLX is a machine learning framework.** They can appear together in the Platform Options table, but have different roles and cannot be understood by the same class of operating libraries. MLX executes dependency Metal on the Apple GPU; llama.cpp can also be used directly with Metal without the need to install MLX.

### 1.2.2 Three typical execution paths

```text
NVIDIA: request → vLLM → PyTorch / special kernel → CUDA / compute library → driver → GPU
AMD: request → vLLM ROCm → PyTorch / special kernel → HIP / compute library → driver → GPU
Mac: request → MLX-LM → MLX CPU/GPU operation → Metal(GPU path) → Apple GPU
```

CUDA Runtime and HIP Runtime are responsible for submitting and executing tasks; The matrix, attention and communication may be done by a support library or a kernel on the engine itself. Installing CUDA is not the same as installing vLLM, and installing MLX is not the same as having all model implementation and service interfaces.

### 1.2.3 Platform topics and examples

The foundation of the platform: [NVIDIA GPU and CUDA](../chapters/hardware/nvidia.md) · [AMD GPU and ROCm](../chapters/hardware/amd.md) · [Mac, Metal and MLX](../chapters/hardware/apple.md) · [Intel, OneAPI and OpenVINO](../chapters/hardware/intel.md) · [Ascend and CANN](../chapters/hardware/ascend.md).

The CPU path follows instructions such as AVX/NEON, number of threads, memory bandwidth, and BLAS/oneDNN/Accelerate or the engine's own kernel. When the software is built using new instructions, the old CPU may not be able to execute; The bandwidth, NUMA and application requirements are also taken into account.

The specific device commands and historical results are focused on [Matrix of engineering examples](../engineering/README.md) It's the process of the MUSA. [Examples to be verified](../engineering/musa.md). Support range based on precise chip, OS, frame version, model and precision judgement.

## 1.3 Hardware adaptation check sequence

### 1.3.1 Versions exist at multiple layers

|edition layer|What to verify|Typical problems|
| --- | --- | --- |
|Hardware architecture|It's the exact model, the CUDA computing capability, the AMD gfx, and so on.|The software package does not contain the device's kernel|
|Systems and drivers|OS, kernel, firmware, device driver|device not visible, permissions or driver initialization failure|
|runtime and compute library|Dynamic libraries and versions of actual loads of programs|So/DLL is missing, the symbols don't match, the library is loaded with other environments.|
|compilation toolchain|nvcc/hipcc/clang, SDK, and host compiler|Build failures, target architecture not supported|
|Frameworks and Engines|PyTorch/MLX builds, engine versions, and native extensions|The framework can use GPUs, but some model or quantization kernel failure|

When using pre-compilation software packages, some user mode libraries may have been installed with the packages or dependency; Source code compilation often requires the development of a toolchain. Whether or not to install the full toolkit depends on the build and run requirements of the program, and it is not necessary to install the entire SDK for each platform.

container encapsulates user mode dependency, device access remains dependency, host driver and container access. There's nothing in the container `nvcc` There is no need to impede the operation of binaries; However, a temporary compilation may need to be expanded.

### 1.3.2 Check each layer from device to task

|Order|Check it out|Orders / Evidence|Passed conditions|
| --- | --- | --- | --- |
| 1 |device and architecture| uname/lscpu/lspci,nvidia-smi,rocminfo,npu-smi |CPU architecture, GPU model, card number, gfx/SM specified|
| 2 |Driver and Runtime|Module sources,nvcc/hipcc,one API/CANN, and dynamic libraries|Hardware support, library path aligned with ABI|
| 3 |The back of the engine|Torch device with matrix calculation instance, llama --list-devices, IR available_devices|It's really all about distribution, calculation, synchronization.|
| 4 |model / precision / operator|Read config with quantization_config, load log|It's all about text, MoE, visuals, and so on.|
| 5 |Memory and communication|Per-component buffers, GTT/TTM, topology, and collectives|Model +KV+ workspace Included, target communication passed|
| 6 |Targeted tasks|API, full answer, error and workload|Task length, concurrency and resources reach thresholds|

```python
import torch
print(torch.__version__, torch.version.cuda, torch.version.hip)
assert torch.cuda.is_available()
x = torch.ones((32, 32), device='cuda')
y = x @ x
torch.cuda.synchronize()
assert y[0, 0].item() == 32
```

The above ROCm builds used for CUDA or along the torch.cuda interface are not used for all NPU/XPUs. llama.cpp does not require additional installation of PyTorch for listing; OpenVINO also verifies with its own device and pipeline.

## 1.4 Adaptation workflow

### 1.4.1 Choose a deployment route first

|Demand|Candidate routes|Confirmed first|
| --- | --- | --- |
|Local single users, offline, limited resources|Llama.cpp, MLX-LM, device supported IR engine|Model format, memory, single request latency|
|Multi-user online services|VLLM, SGLang, and vendor service engines supporting the platform|Scheduling, KV, target concurrency, tail latency and monitoring|
|Multimodal or voiced|There is an implementation of the corresponding processor/encoder/decoder|Input preprocessing, model operators and output quality|
|Models can't fit into a single device|Reduced bit width, smaller models, offloading, multi-GPU/multi-node|Quality, host memory, communication, costs and total costs|

The same model can be loaded on multiple platforms, which does not mean that the same engine or parameter should be used. First, match tasks and resources, and then compare what can be achieved.

### 1.4.2 General deployment sequence

```text
Device / Task Support Matrix → Fixed driver / Toolkit / Engine → Small operator or small model
 → Goal model short input → template / multi-mode / tool functionality → single-machine workload
 → Multi-GPU / multi-node → Optimizing experiments → Delivery
```

|Stages|Engineering operations|Examples|
| --- | --- | --- |
|Construction|Fixedarch and dependency, split backend build directories|whether the pre-compilation package covers the target architecture; Whether the expansion matches|
|Capacity|Distinguish between physics, drivers, budgets and allowable|Weights + KV + workspace + system surplus|
|functionality|Acceptance testing for text, visual and audio|Full output, template correct, no unexpected CPU fallback|
|Optimization|Keeping the CPU/original precision/original parameter baseline|Control the input, sampling, concurrency and timing boundaries|
|Delivery|Fixing final orders and recovery steps|Cold start, workload, stop, restart and rollback|

Outputs: Environmental lists, building logs, model support tables, minimal calculation and targeted task results, memory and communication evidence. [Adjusted records template](../templates/adaptation-record.md).

Continuation of common infrastructure [Model formatting and quantization](02-model-formats-quantization.md), [inference framework](03-inference-frameworks.md) and [Memory and performance](04-memory-performance.md). If you need specific device commands and historical results, check again. [Matrix of engineering examples](../engineering/README.md).

## October 2026 engineering update

Current hardware detail: [DGX Spark / GB10](../chapters/hardware/dgx-spark.md). Check ARM64, unified-memory accounting, bandwidth, and exact kernel coverage.
