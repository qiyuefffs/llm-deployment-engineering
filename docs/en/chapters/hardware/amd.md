# 1.2.2 AMD GPU and ROCm software stack

[简体中文](../../../01-deployment-foundations/chapters/hardware/amd.md) | **English**

[Contents](../../SUMMARY.md) · [Hardware and runtime overview](../../02-capability-layers/01-hardware-backends.md)

## Hardware basics

AMD's large language model deployments mainly involve Radeon independent GPUs, Instinct data center accelerators, and integrated GPUs in Ryzen processors. Their memory, organization, architecture, and software support range are different, so you can't just look at the AMD GPU's label.

|Hardware category|Typical features|Focus on deployment|
| --- | --- | --- |
|Radeon consumer/professional discrete GPU|There is usually a standalone VRAM for a PC or workstation.|Models with OS support, VRAM, gfx target, kernel coverage|
|Instinct Accelerator|For computing and data centers, partly using HBM and xGMI interconnect|ROCm support, matrix computation, bandwidth, RCCL and topology|
|Ryzen integrated GPU /APU|CPU and GPU use system RAM, limited by device budget|Shared memory bandwidth, allowable capacity, drivers, system surplus|

`gfx ` It is the code target of the AMD GPU. A family of architectures such as RDNA/CDNA with precise gfx target impact instructions and pre-compilation kernels; The same series of products should also read the actual device information. It's the CUDA.`sm_XX` It is not possible to convert it into a generic AMD number.

## What does ROCm have to do with HIP?

ROCm is a complete set of GPU computing software platforms, including runtime, compilers, math libraries, communication libraries, and analytics tools. HIP is the most commonly used C++ programming interface and kernel language used to apply device memory, compute and sync; `hipcc` It's a compilation driver tool.

```text
Model / inference engine → PyTorch ROCm or HIP backend
             → HIP runtime ＋ compute library
             → Underlying runtime/device driver → AMD GPU
```

|Components|Responsibilities|Commonly used locations|
| --- | --- | --- |
|amdgpu and related device interfaces|Device, memory and computational access under Linux|Access to the host driver, container device; Other OSs by corresponding driver|
| ROCr/HSA Runtime |Underlying execution and memory mechanisms on support platforms|Device execution basis for higher runtime such as HIP|
| HIP / hipcc |GPU programming API, kernel language and compilation input|Llama.cpp HIP, PyTorch ROCm and source code expansion|
| rocBLAS / hipBLAS / hipBLASLt |BLAS matrix operations, API interface and flexible GEMM|Linear layers supported by precision and layout|
| MIOpen |Deep learning of the operator library|The framework requires a neural network operator, not all LLM operators are implemented by it.|
| RCCL |Multi-GPU, multi-node collective communication|AllReduce, AllGather, and so on in parallelism execution|
|Special kernel and compilation tools|attention, MoE, quantization and integration computing|Implemented by frameworks, support libraries, or projects, coverage varies with version|

HIP supports portable programming at the source code level; There is a CUDA binary that won't run automatically on AMD devices because ROCm is installed. PyTorch ROCm is still in use `torch.cuda ` Interface names and packet construction information can be checked `torch.version.hip`.

## Choosing between HIP, Vulkan, and platform support

HIP routes use ROCm/HIP and supporting compute library; The Vulkan route passed the Vulkan driver with the corresponding shader executed. Both are different backend, and Vulkan does not require the full ROCm to be installed first, but requires the engine to implement the backend and the driver capabilities accordingly.

Check the exact GPU, OS, ROCm/HIP and frame support matrix before selecting the backend. The driver, library, framework, and device coverage of Linux, Windows, and WSL cannot be considered to be exactly the same; Community patches should also indicate the source and the applicable version.

For integrated GPUs, expandable allowable memory does not increase memory bandwidth. Although the model can be loaded, the speed may still be low if the CPU struggles with severe or some precision failure of the efficient kernel. Quantization and backend selection should compare capacity, speed and output quality at the same time.

Basic information: [ROCm overview](https://rocm.docs.amd.com/en/latest/what-is-rocm.html) · [HIP](https://rocm.docs.amd.com/projects/HIP/en/latest/) · [Radeon/Ryzen support](https://rocm.docs.amd.com/projects/radeon-ryzen/en/latest/) · [RCCL](https://rocm.docs.amd.com/projects/rccl/en/latest/).

## Deployment procedures and examples

First, identify the device target and software stack, then perform single-machine generation, memory budget and workload testing. The following are the different operating paths for the Windows integrated GPU and Linux multi-node.

Examples: [780M Windows HIP](../../engineering/amd-780m.md) · [8060S Q4/BF16 Optimized](../../engineering/amd-8060s.md) · [395 five aircraft RPC](../../engineering/amd-395-rpc.md) · [W7900 multi-GPU and multi-node](../../engineering/amd-w7900.md).

## One, understanding the software level.

The kernel driver is responsible for the interface between the device and memory; HIP provides the ability to execute interfaces and compilations; A library such as rocBLAS, hipBLASLt, and other libraries can implement matrix and related calculations. RCCL is responsible for collective communication. Compilation A library is not the same as reinstalling the entire driver.

```bash
uname -m
uname -r
rocminfo > rocminfo.txt
hipconfig --full > hipconfig.txt 2>&1
hipcc --version
```

`gfx` It's the device code target. 780M records involving gfx1103, 395/8060S have device evidence using gfx1151. The product name should also be re-checked to avoid duplicating the architecture variations of another machine.

## Linux routes: first single-machine, then multi-node

In a supported ROCm environment, frame small operator or small model verification is used first. llama.cpp HIP is built using a separate directory:

```bash
cmake -S . -B build-hip   -DGGML_HIP=ON -DAMDGPU_TARGETS=gfx1151   -DCMAKE_BUILD_TYPE=Release
cmake --build build-hip --target llama-server llama-bench llama-cli -j 4
```

Here, gfx1151 applies specifically to the Ryzen AI Max+ 395 example. Complete source code and small model steps [llama.cpp tutorial](../frameworks/llama-cpp.md). If the CMake prompt variable is not used, first verify the submitted option; Confirm backend and device allocation after launch.

It needs to be rebuilt when compared to Vulkan.`build-vulkan`, keeping the same model, offloading, threads, and lengths. The two backend dependencies differ, and the performance differences should be verified by the actual task.

## 3 Windows routes: Running libraries separated by version

The 780M old project uses the HIP SDK, Community Adaptation Library and Ollama branch. It provides a real compatibility experience, but the old DLL cannot be randomly mixed into new programs, nor can it be automatically extended to other devices such as the 890M.

First, check the device with the driver, and then verify the current official or community release. Put the programs, support libraries and logs in a separate version directory and keep a recoverable combination.

```powershell
Get-CimInstance Win32_VideoController | Select-Object Name, DriverVersion
Get-ChildItem -LiteralPath '.\bin' -Filter '*.dll' | Select-Object Name, Length
```

The service is then started, the backend and the device in the log are observed, and a short request is made with the business request. The GPU curve of the task manager can only assist in judging, output and execute logs.

## Four: Examples: 395 physical memory is big enough, why would you assign failure?

The five-node HIP RPC record used Ryzen AI Max+395/8060S, ROCm 7.2.1, HIP 7.2.53211-e1a6bc5663, kernel 6.17.0-35, and llama.cpp b9557. At one stage, the device reported only 63215 MiB, an allocation failure of 87013675008 bytes.

The search found that GTT requested 125829120000 bytes, but TTM actually had about 66286690304 bytes. Compare physical capacity, driver budget and runtime visibility, rather than just adjusting the context of the large language model.

The repaired device can be seen at a total volume of about 120000 MiB. This correction relates to specific cores, DKMS and drivers, and the system retains the cause and check paths, not writing the system-level modification into a general one-key optimization.

## Follow-up verification of the RPC of five, five machines

After capacity was restored, the original project was tested in a small context. Kimi generates about 8.2 tokens/s, while Qwen smokes about 21.3 tokens/s. There is no single-machine baseline with long-term API records, so these figures illustrate short observations and cannot calculate the five-machine acceleration ratio.

Multi-node should be advanced by single-machine device → communication → small model → target short input→ long input→ service workload. Complete dissection, TCP/RDMA judgement and controlled screening [Multi-device topics](../performance/parallelism.md).

## Six: Full operation: Start recording the 395 five-machine HIP RPC

The previous example illustrates the cause of the failure, and this section connects the environment, repair, build, distribute, load and observe in real engineering order. The five devices are marked as `NODE_A ` to `NODE_E`; A runs the main program and participates in local computing, while BE runs RPC. The model shard maintains the tensor allocated to the A, remote receiving frame, without the need for each model to store an entire set of 350G models.

### 6.1 Environment and objectives

|Projects|Original engineering configuration|
| --- | --- |
|single-machine CPU/APU| Ryzen AI Max+395 |
|GPU/Goal| Radeon8060S / gfx1151 |
|single-machine memory|128GB of LPDDR5|
|The system| Ubuntu24.04,6.17.0-35-generic |
| ROCm | 7.2.1 |
| HIP | 7.2.53211-e1a6bc5663 |
| llama.cpp | b9557-0f7fada56 |
|Interconnected|USB4/Thunderbolt direct connection, TCP RPC|
|Targeted model|Kimi-K2.5-Q2 GGUF, catalog of about 350G|

First, make a single-machine record and see if the five machines match. The same CPU model does not represent the same kernel module running; The failure happened to occur between the same Runtime device, different kernel driver modules.

```bash
uname -r
hipcc --version
dpkg-query -W rocm-core hip-runtime-amd hsa-rocr
modinfo amdgpu
ls -l /dev/kfd /dev/dri/renderD*
id
cat /proc/cmdline
```

Recorded `modinfo ` Verify if the file name, version and vermagic are from the current kernel directory or `updates/dkms`. Device permissions are insufficient to repair the current user's access to the device, so that if the device is not encountered, the entire software stack can be reinstalled.

### 6.2 How the BIOS, GTT and TTM interact

The BIOS of these devices `iGPU Memory Size ` At least 2GB. Running logs `2048M of VRAM memory ready ` with `120000M of GTT memory ready` This means that a smaller amount of reserved VRAM can still go through shared memory routes. It is not necessary to judge the device incompatible for the 512MB of the pursuit of another tutorial.

The original engineering uses the following core parameters:

```text
ttm.pages_limit=30720000
ttm.page_pool_size=30720000
amdgpu.gttsize=120000
amdgpu.cwsr_enable=0
```

This is a system optimization record of the kernel/driver combination, which should first check the current supporting documentation and existing parameters, and then change under the restoreable boot configuration.`pages_limit ` The number of pages used; Under the 4KiB page condition, 30720000 pages correspond to 125829120000 bytes, consistent with the original GTT request value. Page size should be `getconf PAGESIZE` Confirmed. The GTT budget is not a new physical memory, and the system and application still share the actual capacity.

The real proof of error is:

```text
GTT size has been set as 125829120000
but TTM size has been set as 66286690304, this is unusual
```

Next, examine the executor: `llama-cli --list-devices` Only 63215 MiB was reported. This was followed by an 87013675008 byte RPC buffer allocation failure of about 81.04GiB. When the HTTP output limit is lowered, the weights buffer can't be dropped, and runtime can be allocated.

### 6.3 How to repair the original construction

The fault node load is: `amdgpu-dkms 1:6.16.13.30300100-2303411.24.04` The modules come from:

```text
/lib/modules/6.17.0-35-generic/updates/dkms/amdgpu.ko.zst
```

Normal nodes use the same kernel self-contained module. The original engineer first checked the package to remove the preview, then removed only the conflicting DKMS package, retaining Runtime and firmware, and then rebooted to verify the actual effect modules:

```bash
sudo apt-get -s remove amdgpu-dkms
# 确认变更范围后，原工程执行：
sudo apt-get remove amdgpu-dkms
sudo reboot
```

This section is used to indicate that the repair has been completed, and cannot be promoted as an offloading of all AMD devices. New devices, such as dependency DKMS, should use a matched core/driver combination. Rebooted acceptance testing includes modules from `kernel/drivers/gpu/drm/amd/amdgpu/` No more TTM fire alarm and HIP executor report 120000 MiB. Three things must be mutually verifiable.

The original log is that once a free is greater than the total of the inconsistent value, so the capacity judgment cannot take the larger of the two fields. First verify the total number of drivers, accounts, and executors that can be seen with an actual allocation, and then move on to the large language model.

### 6.4 Build the same set of HIP+RPCs

It's been fixed.`0f7fada56` In the source code of llama.cpp:

```bash
cmake -S . -B build-hip-rpc \
  -DCMAKE_BUILD_TYPE=Release \
  -DGGML_HIP=ON -DGGML_RPC=ON \
  -DGGML_HIP_ROCWMMA_FATTN=ON \
  -DAMDGPU_TARGETS=gfx1151
cmake --build build-hip-rpc --config Release -j 4
rg 'GGML_HIP|GGML_RPC|ROCWMMA|AMDGPU_TARGETS' build-hip-rpc/CMakeCache.txt
./build-hip-rpc/bin/llama-cli --version
./build-hip-rpc/bin/llama-cli --list-devices
```

The original build automatically detects libverbs and enables `GGML_RPC_RDMA`. This will only prove that the compilation has the relevant capabilities, and this USB4 bridge actually runs TCP; Can't use the built-in switch as proof of RDMA operation. Whether a particular transmission path is used is to be confirmed by running logs and interfaces.

When distributing, use the same build's `bin ` the directory and the required shared library as a comprehensive preservation, recording summary; Don't just copy the rpc-server executable file and fill it out from another version of the directory library. Each remote node runs first.`--version` With the device download and restart the service.

```bash
tar -C build-hip-rpc -czf llama-hip-rpc-bin.tgz bin
sha256sum llama-hip-rpc-bin.tgz
```

After copying and decompressing to BE, each node has its own `bin ` The directory's front desk is running.`NODE_B_ADDRESS` The configuration of the controlled interface for the experimental node is as follows:

```bash
export LD_LIBRARY_PATH="$PWD:${LD_LIBRARY_PATH:-}"
./rpc-server --host "$NODE_B_ADDRESS" -p 50053 -c
```

RPC endpoints need to be limited to a trusted testing network; Do not copy the entire interface of the original note and listen to it and expose it to the public network.`-c` For the RPC cache option of the appropriate version, keep its storage path with first/re-load conditions, and do not confuse the hot cache load with the first transmission when measuring.

### 6.5 Check the device and run the small model

In A configuration, four remote addresses, a list of devices should have local ROCm0 and four RPC devices:

```bash
export RPC_ENDPOINTS="${NODE_B_ADDRESS}:50053,${NODE_C_ADDRESS}:50053,${NODE_D_ADDRESS}:50053,${NODE_E_ADDRESS}:50053"
./llama-cli --rpc "$RPC_ENDPOINTS" --list-devices
```

Once all five devices report the 120000MiB verified in this project, test the smaller Qwen3.5-9B model:

```bash
./llama-cli -m "$QWEN_GGUF" -ngl 999 --rpc "$RPC_ENDPOINTS" \
  -c 512 -b 64 -ub 16 -fa off \
  --single-turn --simple-io --no-display-prompt \
  -p '你好，请用一句话介绍你自己。' -n 8
```

This is the first version of the Prompt40.3 token/s generation21.3 token/s. It is short-lived, with an output budget of only 8, mainly confirming computational pathways and connections; Can't serve as a long answer quality set or high concurrency service acceptance testing.

### 6.6 Load Kimi: Why the distribution ratio is uneven

Specify the first document in all GGUF shards and verify the number, size and abstract of shards. The name of the file is determined by the actual downloaded artifact, rather than a shard name in the tutorial. Variable of the theme `KIMI_GGUF_FIRST` Point to the first shard:

```bash
./llama-cli -m "$KIMI_GGUF_FIRST" -ngl 999 \
  --split-mode layer \
  --tensor-split 0.143,0.21425,0.21425,0.21425,0.21425 \
  --rpc "$RPC_ENDPOINTS" --no-mmap \
  -c 512 -b 32 -ub 8 -fa off \
  --single-turn --simple-io --no-display-prompt \
  -p '你好，请用一句话介绍你自己。' -n 8
```

The five ratios sum to 1. In addition to local computing, A also reads about 350G shard, scheduling RPC and running the system, so it retains a larger amount. For example, it needs to be verified by the actual device list, it is not hard isolated from the overall physical memory, nor does it guarantee that each buffer is cut to the exact same proportion.

Original configuration used `--no-mmap` This is a verified combination. It is not possible to generalize this to all large language models by shutting down the mmap and saving memory. File mapping, page cache, load buffer and backend copying are different, and the load peak and load time should be measured on the same version.

### 6.7 Decades of Loading How to Judge Progress

The first load contained the host disk, RPC transmission and remote tensor allocation. The original readings were observed at 101, 147, 174, 236, 306, and 358 GB respectively. They reflect the cumulative trends of process I/O, cannot be used as an accurate model percentage, nor can they be guaranteed under cache conditions.`read_bytes` It's always the same size as the file.

```bash
ps -p "$LLAMA_PID" -o pid,stat,etime,%cpu,%mem,rss,vsz,nlwp
cat "/proc/$LLAMA_PID/io"
ss -tinp
free -h
```

If the read-in counts, the connection bytes_sent/bytes_acked is still changing, and the target node memory is growing, it is usually still moving forward. When transmitted by layer segments, it is possible for one machine to receive and move to the next one. Just one connection isn't the same as the other three. On the contrary, long-term no I/O progress, continuous increase in retransmissions, disappearance of remote processes, or allocation errors need to be preserved after the positioning of the current state.

The original load stage host has about 123GiB total memory, 81GiB is used, 41GiB is available, and the swap is 0; Approximately 8.6 GiB has been used since the process withdrew. 114 GiB is available. The group data is a phase snapshot used to illustrate loading and unloading behaviour, which does not mean that there is no higher peak during the entire run.

### 6.8 Results, next step and fallback

|Projects|Originally measured|
| --- | --- |
|Kimi is a small context prompt.| 19.3token/s |
|Kimi is a small context generation| 8.2token/s |
|Qwen small model prompt/generation| 40.3 / 21.3token/s |
|Scope of success|HIP RPC loading, short context, short output|

The original text also gave a service recommendation for cctx32768, but lacked the corresponding results. This section should be used as a follow-up test: starting with ctx4096, maintain verified segments, and then add context, batch,ubatch, and FA. Change all switches at different times according to the most recent change to fallback failure. The success of the five-machine capacity expansion and whether the five-machine is faster than the single-machine are two different conclusions.

## Seven, W7900 eight cards: container, model format and OpenAI interface aligned

Another group of engineers used W7900×8, 48GB per card, image.`ghcr.io/embeddedllm/vllm-rocm:v0.8.2-18ed313` It is also used to deploy DeepSeek-R1 AWQ INT4. It uses the vLLM/RCCL path, unlike the previous llama.cpp RPC.

The container is hanging in.`/dev/kfd ` with `/dev/dri ` Verify the video/render access and verify the device inside the container. Model and result respectively `/srv/models `, `/srv/results `. Originally `--ipc=host ` The IPC namespace for shared hosts can't be used anymore `--shm-size=384g` It explains that 384GB of shared memory has been allocated, rather than VRAM extensions.

The key service budgets are as follows: TP8, ctx4096, seqs 8, batched 2048, memory 0.95, eager, AWQ, BF16 computed dtype. 0.95 is the more radical historical configuration, with the new run as the first to perform residual checks. The original notes called normal `api_server` Then request the OpenAI path, and the native system is the OpenAI input:

```bash
python -m vllm.entrypoints.openai.api_server \
  --model /srv/models/DeepSeek-R1-AWQ \
  --served-model-name deepseek-r1-awq \
  --host 127.0.0.1 --port 8001 \
  --tensor-parallel-size 8 \
  --max-model-len 4096 --max-num-seqs 8 \
  --max-num-batched-tokens 2048 \
  --gpu-memory-utilization 0.95 \
  --quantization awq --dtype bfloat16 --enforce-eager
```

The model directory needs to be supported by the AWQ layout of this version, and the number of cards multiplied by VRAM is for rough estimation only, while verifying each rank weights, KV and communication buffer. The original note does not have a complete throughput score, and this section retains the deployment parameters and verification methods.

The old environment `HSA_OVERRIDE_GFX_VERSION=11.0.0` It's a compatibility test to disable the backend of an attention. Confirm that the device actually supports gfx and matrix, and do not disguise architecture, turn off P2P or turn off SDMA as a general default optimization.

## Eight, how to judge AMD failures from the original record

|The phenomenon|The next effective step|Common misconceptions|
| --- | --- | --- |
|system RAM overload, HIP allocation still fails|Module path, TTM/GTT, total runtime, actual allocation|Just look at the physical capacity.|
|Safetensors files a lot but single rank is still OOM|See TP/PP real load with each rank memory|Mistaking file sharding for computation partitioning|
| page fault |See the first kernel/runtime error and access context|Direct qualification as OOM|
|The container sees the device and generates a failure.|Model operator, quantization kernel and communication|The device is fully compatible.|
|multi-node Ray alive|Continued testing of collective communication and model shard|Assuming control-plane success proves successful inference|
|Vulkan had run another model.|Re-create functionality and timing for the current model|Treating another model's speed as a guarantee for this model|

CUDA's specific diagnostic variables cannot be moved to ROCm without judging. When modifying communication or memory-related environmental variables, record the original values, the applicable version and fallback methods, and duplicate the same workload; A setting that can bypass a failure may also reduce the final performance.

## Nine, complete the inspection.

Save the actual gfx, system with runtime, framework commit, model, backend allocation, functionality and workload. Unified memory is a system of simultaneous recording of memory and swap. Add context and concurrency before confirming Runtime availability.

Source: author 780M Adaptation, AMD ROCm compilation and 395 five-machine HIP RPC articles, see [List of corresponding articles](../../evidence/chapter-sources.md).
