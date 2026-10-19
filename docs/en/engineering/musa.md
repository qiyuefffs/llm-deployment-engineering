# MUSA:llama.cpp deploys adaptive and accelerated verification processes

[简体中文](../../01-deployment-foundations/cases/C13-musa/README.md) | **English**

[Platform instance matrix](README.md) · [The backend of the hardware](../02-capability-layers/01-hardware-backends.md)

## Status and input

The MUSA and Moore Threads data for FlowUs has been retrieved, and the current readable record does not contain evidence of complete device operation. This page provides complete engineering execution and acceptance testing steps without filling in GPU models, drivers, performance or plugins. After the actual device is available, press the tables to fill in the run records one by one.

|Must be fixed|Recorded content|
| --- | --- |
|Device|Specific GPUs, number of cards, physical VRAM and availability|
|The system|CPU architecture, OS/kernel, drivers, MUSA toolkit and compiler versions|
|Engine|llama.cpp accurate commit, GGML_MUSA support, CMakeCache and complete build log|
|Model|It can be used to publish small GGUF, model revision, file name, SHA256, tokenizer/template.|
|Workload|Fixed prompt, pp/tg, output budget, threads, context, concurrency, cache|

## 1. driver and compilation toolchain

Install driver and toolkit according to the official support table of the GPU. device Tool name confirmed by installed version, common input is `mthreads-gmi ` and `mcc` Do not use CUDA packages because the command name is close to it.

```bash
uname -a
lspci -nn
command -v mthreads-gmi
command -v mcc
mthreads-gmi
mcc --version
cmake --version
```

Save the device model with VRAM; The toolkit itself comes with minimal calculation cases, which must be completed before allocation, copying and calculation. device can be enumerated, allocated, calculated, model can be performed separately.

## 2. Fixed source code and build

```bash
git clone https://github.com/ggml-org/llama.cpp.git
cd llama.cpp
# 检出已经选定并记录的commit后继续
git rev-parse HEAD
rg GGML_MUSA CMakeLists.txt ggml
cmake -S . -B build-musa \
  -DCMAKE_BUILD_TYPE=Release -DGGML_MUSA=ON
cmake --build build-musa --target llama-cli llama-server llama-bench -j 4
./build-musa/bin/llama-cli --version
./build-musa/bin/llama-cli --list-devices
```

If a fixed submission without the backend option is submitted, branch verification and official adaptation instructions are required, CMake cannot be ignored as a successful MUSA construct for unknown variables. Verify the compiler, the link library, the target architecture and the device log.

## 3. CPU baseline and GPU offloading

model using small size, engine-supported GGUF; Can be reused first [CPU exercises](../practice/first-service/README.md) The Qwen3-0.6B-Q8_0 artifact is fixed in the target device and the model architecture is supported. Put the file in the following designated location, with a summary of the test corresponding to the model page.

```bash
sha256sum /srv/models/Qwen3-0.6B-Q8_0.gguf
./build-musa/bin/llama-bench \
  -m /srv/models/Qwen3-0.6B-Q8_0.gguf -ngl 0 -p 512 -n 128 -r 3
./build-musa/bin/llama-bench \
  -m /srv/models/Qwen3-0.6B-Q8_0.gguf -ngl 99 -p 512 -n 128 -r 3
```

Check the actual offloading, MUSA buffer, pp/tg and answer; We can't just rely on `-ngl99` conclude that execution occurs on the GPU. The same binary CPU fallback and GPU routing keep the input and threads comparable.

## 4. Services and API acceptance testing

```bash
./build-musa/bin/llama-server \
  -m /srv/models/Qwen3-0.6B-Q8_0.gguf \
  --alias musa-smoke --host 127.0.0.1 --port 8080 \
  -ngl 99 -c 2048 -np 1
```

The second terminal execution:

```bash
curl --fail-with-body http://127.0.0.1:8080/health
curl --fail-with-body http://127.0.0.1:8080/v1/models
curl --fail-with-body http://127.0.0.1:8080/v1/chat/completions \
  -H 'Content-Type: application/json' \
  -d '{"model":"musa-smoke","messages":[{"role":"user","content":"计算12乘13，只输出数字。"}],"temperature":0,"max_tokens":128}'
```

Acceptance testing 156, full text and reasons for termination, re-check SSE, over-entry, wrong model, cancellation and continued health. Functionality passed and the acceleration experiment was completed.

## 5. Accelerate the optimization matrix

|Experiments|Variable|Fixed conditions|Passed Standards|
| --- | --- | --- | --- |
|offloading|ngl0/part/full layer|Model, prompt, thread, ctx|Implementing the right location, resources and budget|
| batch |Grade b/ub|Other services and workload|pp, tg, peak, error recording at the same time|
| Attention |The backend clearly supports FA off/on|The same length as the KV dtype|The result is consistent with the quality, complete log preservation|
|quantization| Q8/Q5/Q4 |The same task/length/sample|Capacity gains and quality costs|
|concurrency| np1/2/4 |Fixed length, sufficient request|TTFT/TPOT/p95 and total throughput in line with target|

## 6. Delivery and rollback

Save the environment, model, list, build, baseline, each set of commands, initial results and final acceptance testing. In the previous instance, Ctrl+C stops, and the verification process and port are released; Driver and library changes retain the original package and restore steps. No actual output grid is maintained pending testing, and no other GPU data can be filled.
