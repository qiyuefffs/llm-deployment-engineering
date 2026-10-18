# llama.cpp: build, load, interface and stop

[简体中文](../../../01-deployment-foundations/chapters/frameworks/llama-cpp.md) | **English**

[Contents](../../SUMMARY.md) · [Headquarters](../../02-capability-layers/03-inference-frameworks.md) · [Full CPU running](../../practice/first-service/README.md)

## Overview of this chapter

llama.cpp is a model execution tool that doesn't require PyTorch to be preinstalled. It passed different backend CPUs or acceleration devices, providing CLI, server, benchmark and quantization procedures around the GGUF. This chapter will build, load and link the interfaces into a chain, and platform specific issues will return to the hardware topic.

Constructing fixed examples `b9557`. Author FlowUs provide CUDA, HIP, Vulkan, Metal, SYCL and RPC engineering; The actual running of this round is the official Windows CPU binary, with other building commands serving as instructions for operating the corresponding environment.

## 1. Select a backend and create an independent build directory

Install the Git, CMake, C++ toolchain first, and then prepare the development dependency for the selected backend. The Linux distribution can be installed first.`build-essential `, ` cmake `, ` git `with ` libcurl4-openssl-dev`; The GPU toolchain is prepared according to the official installation instructions of the corresponding device. Windows prioritizes starting with the CPU binary and learning how to build Visual Studio development tools and source code.

```bash
git clone --branch b9557 --depth 1 https://github.com/ggml-org/llama.cpp.git
git -C llama.cpp rev-parse HEAD
```

The following routes select one each time. Independent directories avoid remaining old compilers, CUDA paths, and backend options.

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

When constructing or cross-compilating multi-architecture, precise target computing capabilities are required. Do not directly connect GB10's 121 or historically bypassed 120 to other GPUs. CMake should also check whethernvcc and runtime can find the CUDA library.

### AMD HIP

```bash
cmake -S llama.cpp -B llama.cpp/build-hip \
  -DGGML_HIP=ON -DAMDGPU_TARGETS=gfx1151 \
  -DCMAKE_BUILD_TYPE=Release
cmake --build llama.cpp/build-hip \
  --target llama-cli llama-server llama-bench -j 4
```

`gfx1151 `395 device, other models used ` rocminfo`Confirmed. Problems with operating libraries, kernels and allowable memory [AMD theme](../hardware/amd.md).

### Vulkan

```bash
cmake -S llama.cpp -B llama.cpp/build-vulkan \
  -DGGML_VULKAN=ON -DCMAKE_BUILD_TYPE=Release
cmake --build llama.cpp/build-vulkan \
  --target llama-cli llama-server llama-bench -j 4
```

Vulkan needs support for SDKs/development libraries and device drivers. Use it first.`vulkaninfo --summary` Confirm the device and prevent the actual selection of software from being implemented. Intel records also indicate that driver changes will change the result, and the driver version should be saved.

### Apple Metal

```bash
cmake -S llama.cpp -B llama.cpp/build-metal \
  -DGGML_METAL=ON -DCMAKE_BUILD_TYPE=Release
cmake --build llama.cpp/build-metal \
  --target llama-cli llama-server llama-bench -j 4
```

Metal dependency is a command line tool for macOS and Xcode. Unified memory requires space for systems and other applications. Specific quantization types with MoE kernel failure [Apple theme](../hardware/apple.md).

## 2. Check the identity of the program and re-load the model

The following is a unified list of CPUs. When building GPUs, modify executable paths and `-ngl` In the log, verify the real layer distribution.

```bash
llama.cpp/build-cpu/bin/llama-server --version
llama.cpp/build-cpu/bin/llama-server --help > llama-server-help.txt
llama.cpp/build-cpu/bin/llama-cli \
  -m artifacts/gguf/Qwen3-0.6B-Q4_K_M.gguf \
  -ngl 0 -c 2048 -t 4 -n 64 -p '简要说明KV缓存。'
```

The model path continues [Converted tutorials](../models/gguf-conversion.md). The official GGUF can also be used, but the repository, revision, filename and summary must be recorded. When loading, check the model architecture, word lists, templates, context, backend buffer and warnings, and you can't just confirm that a Chinese paragraph has appeared at the end.

`-ngl` request the number of layers of GPU offloading; Actual offloading is determined by architecture, backend and resources. When part of the offloading is done, the CPU, GPU and the transmission together determine the speed, and the more CPU threads, the faster it will be. First fix 4 or 8 threads and then measure the target workload.

## 3. Launch local services

```bash
llama.cpp/build-cpu/bin/llama-server \
  -m artifacts/gguf/Qwen3-0.6B-Q4_K_M.gguf \
  --alias book-qwen3-06b \
  --host 127.0.0.1 --port 18080 \
  -ngl 0 -c 2048 -np 2 -t 4 -tb 4 \
  --metrics \
  --chat-template-kwargs '{"enable_thinking":false}'
```

The template parameter for disabling reasoning is related to the Qwen3 template and cannot be used on all models.`-c `, `-np` The context allocation syntax should be combined with the version and the start log. See: The real-time version of the system prints total context 2048, two slots, 1024 per slot. Input and output should be within the respective slot budget.

Parallelism slot is not the total number of client requests. Clients can send more requests, and services can be scheduled or waited by resources. Multi-slot variations will increase simultaneous execution capacity, or may compress each slot available on a budget and increase single-request latency.

## 4. Check the complete response on the second terminal

```bash
curl --fail-with-body http://127.0.0.1:18080/health
curl --fail-with-body http://127.0.0.1:18080/v1/models
curl --fail-with-body http://127.0.0.1:18080/v1/chat/completions \
  -H 'Content-Type: application/json' \
  -d '{"model":"book-qwen3-06b","messages":[{"role":"user","content":"计算2+2。只输出一个数字。"}],"max_tokens":64,"temperature":0}'
```

Check the last name, spelling, usage and reason for termination. This is followed by test flows, JSON tasks, extra-long inputs and error requests. In the actual CPU exercises of this system, the same arithmetic problems resulted in a malformed JSON error returning 500. They have been recorded in [Real acceptance testing documents](../../../01-deployment-foundations/practice/first-service/results/2026-10-18-windows-cpu/acceptance.json) It is not possible to ignore the fact that services can also respond.

## 5. Service interruption, re-testing of engine

Click Ctrl+C to stop this instance and confirm that the execution is done after the exit:

```bash
llama.cpp/build-cpu/bin/llama-bench \
  -m artifacts/gguf/Qwen3-0.6B-Q4_K_M.gguf \
  -ngl 0 -t 4 -p 64 -n 32 -r 3 -o json > engine-benchmark.json
```

pp64 measuring input processing, tg32 measuring generation; They don't have HTTP queues, templates and network charges. If the server continues to occupy the same device and runs the bench, resources will be competing. Service performance should also be measured using HTTP, not in a row with the tg engine.

## 6. Test RPC and local multi-GPU in the second stage

Local models passed first to the backend, then to RPC or multi-GPU extensions. The authors of AMD Five Machines Engineering solve the GTT/TTM allocation problem and produce records in a short context, but without the same single-machine baseline, which cannot be claimed as five-machine acceleration.

RPC increases the remote backend and network boundaries, requiring recording of each node's version of the program, backend library, model segmentation, communication and recovery. The specific process [Multi-GPU and multi-node](../performance/parallelism.md). Completion of the single-machine link in this chapter will significantly reduce the range of subsequent failures.
