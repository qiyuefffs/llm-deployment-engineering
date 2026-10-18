# 1.2.4 Mac hardware, Metal and MLX

[简体中文](../../../01-deployment-foundations/chapters/hardware/apple.md) | **English**

[Contents](../../SUMMARY.md) · [Hardware and runtime overview](../../02-capability-layers/01-hardware-backends.md)

## Hardware basics

This is the main topic of Apple Silicon Mac. M-series SoCs integrate CPUs, GPUs, Neural Engines and others on the same platform, with CPUs and GPUs sharing physical memory. Intel Mac software and hardware conditions are different and cannot be directly deployed using MLX/Apple Silicon deployment routes.

|Hardware composition|Role in the deployment of large language models|Limitations You Need to Know|
| --- | --- | --- |
| CPU |In addition to this, it is important to know that the system is not a computer.|It will also compete with GPUs for memory bandwidth and system resources.|
| GPU |Matrix and model calculations that support routes such as Metal/MLX|Operator, precision and model implementation are determined by the software stack|
|unified memory|Shared physical memory for direct access to CPU/GPU|Systems, applications, weights, KV and workspace are shared|
| Neural Engine |Specialized Neural Network Acceleration Units|MLX/Metal GPU inference will not use it automatically, requiring routing and support accordingly.|

In addition to the unified memory capacity, memory bandwidth, GPU capacity and heat dissipation are also included. It can be placed on a larger model, which does not mean that it decodes at the same speed as an independent GPU. M-series chips cannot be compared by memory capacity alone.

## What is Metal, Mlx, Mlx-LM?

**Metal is a GPU computing interface; MLX is an array and machine learning framework. MLX-LM is a software package based on functionality such as text model loading, generation and quantization.**

```text
Text applications → MLX-LM → MLX array/model computing → Metal(GPU execution) → Apple GPU
Local service → llama.cpp → GGML Metal backend → Metal → Apple GPU
```

|Components|Software Levels and Responsibilities|Commonly Used|
| --- | --- | --- |
|MacOS driver and Metal|GPU device access, command submission, shader and computation execution|Systems and development tools are available, usually without installing CUDA drivers separately|
| Accelerate |Compute library of Apple's CPU vectors, matrix and more|CPU computing and CPU path of the engine|
| MPS / MPSGraph |High-level computing components on metal|use of some frameworks; PyTorch's `mps` It's the backend of the device.|
| MLX |Compute graphics with CPU/GPU execution|The basic framework for Apple Silicon machine learning code|
| MLX-LM / MLX-VLM |Model functionality for text or visual language in MLX|model loading, tokenizer/processor, generating and matching tools|
| Core ML |Model conversion, optimization and deployment frameworks|Using computing units such as CPU/GPU/Neural Engine under supported conditions|

MLX and PyTorch are different frameworks and can't be compared to `device='cuda'` It's a string that completes the migration. Llama.cpp Metal does not require the installation of MLX; GGUF and MLX compatible models are two types of artifact routes.

## How Unified Memory Affects Deployment

MLX uses shared memory to allow supported CPU/GPU operations to access the same data pool, reducing the need for explicit cross-device copying. Data dependency, sync execution, memory bandwidth and workspace are still costly; Model file size is not peak memory.

The budget includes at least system and desktop applications, weights, KV, preprocessing and temporary space. Long context, multiple concurrency requests and multiple model residencies will continue to increase demand. The memory pressure reported by the system is much higher than the total memory of the swap.

MLX uses inertial derivatives: when constructing array expressions, the computation may not have been completed. To be a small operator, timing should trigger demand values within timing boundaries, such as `mx.eval(result)` It is also used to synchronize with the current API. Just measuring the time Python submits will overestimate the execution speed.

## How to choose a route to deploy

|Demand|Candidate routes|Check first|
| --- | --- | --- |
|GGUF is already available, local CLI/API is required|llama.cpp Metal or its higher applications|GGUF tensor types, Metal kernels, templates and actual offloading|
|MLX ecosystem model developed with Python|MLX-LM; Visual mission checking for MLX-VLM|architecture implementation, quantization configuration, processor and model versions|
|PyTorch app migration|PyTorch MPS supporting missions|Operator, dtype, fallback and application code compatibility|
|Native applications, deployment of dedicated accelerators|Core ML routes supporting the model|Converting, shaping, computing units and actually executing devices|

This is about the relationship between the candidates, not the speed rankings. First verify tasks, artifacts and resources, then compare them with the same workload.

Basic information: [Metal](https://developer.apple.com/metal/) · [MLX](https://ml-explore.github.io/mlx/build/html/index.html) · [unified memory](https://ml-explore.github.io/mlx/build/html/usage/unified_memory.html) · [MLX-LM](https://github.com/ml-explore/mlx-lm).

## Deployment procedures and examples

Subsequently, GGUF+Metal builds, MLX services and model capability verification respectively. Examples: [The M3 Ultra Metal is built with GGUF in error.](../../engineering/apple-metal.md) · [Optimization of MLX, APC and full deployment of oMLX](../../engineering/apple-mlx.md).

## One, first, to distinguish model routes.

llama.cpp uses GGUF and the Metal kernel. MLX-LM uses a corresponding text model, while MLX-VLM also involves visual processors and encoders. oMLX-like service layers provide model detection, scheduling and interfaces on the engine; Vllm-metal belongs to another set of plugins.

These routes cannot only be used to exchange files with the same model name. First, check the model artifact and current version support, and then connect the application.

## Second, systems and development tools.

```bash
sw_vers
uname -m
xcode-select -p
clang --version
cmake --version
```

The source code is built using Xcode command line tools and the corresponding CMake. Once ready, the fixed llama.cpp is submitted to build Metal and Accelerate in a separate directory:

```bash
cmake -S . -B build-metal   -DGGML_METAL=ON -DGGML_ACCELERATE=ON   -DCMAKE_BUILD_TYPE=Release
cmake --build build-metal --target llama-cli llama-server llama-bench -j 4
./build-metal/bin/llama-server --version
```

Small model ready and service request reuse [llama.cpp tutorial](../frameworks/llama-cpp.md). Check the Metal device with the actual layer allocation, then see the generated content and the reason for the end.

## Three, how to observe unified memory

Model, KV, runtime, application and system sharing capacity. Predict load with short inputs and increase length with concurrency; Simultaneously view system RAM pressure, swap and continuous speed. Short-term generation does not guarantee long-term operation without a change of page or temperature effect.

No system protection or unlimited allocation is removed as the default step. First, a budget should be established to compare models and configurations within acceptable resources.

## Example 4: Engine compilation passed, specific model still fails

The authors of M3 Ultra512GB, macOS26.3 record using the special llama.cpp branch commit9d36408. Appears when subsequently executing specific FP4/FP8 GGUF `Asserting on type 42` It is the first of its kind in the world, and the first of its kind in the world.

This conclusion is limited to this branch, artifact and functionality. Check the tensor type with the kernel, don't pass compilation when the model passed, and don't extend to all Metal low precision model failures.

## Example 5: Text is successful, vision is not yet connected

Another record uses Python 3.12.13 vllm-metal 0.2.0 vLLM 0.21.0+cpu MLX 0.31.2 Text request available, image request Multimodal encoder has not yet been connected.

Therefore, text, images, tool calls and structured output should be recorded separately. Increased memory and context can't compensate for missing encoders, and implementations or versions should be selected to support the required task.

## Six, oMLX model detection and service checks

In the original operational records `--model-dir` The service is directed to the model from the parent's directory. After launching, check the model list to confirm the name of the application used, and then check the common and current request. It's only when the path is right that it enters the concurrency.

oMLX's historical concurrency results are placed [Topics related to load testing](../performance/benchmarking.md) This is the only link between the model found and the functionality. Cache status, environment and sample size limitations will be shown next to the results.

## Seven: Complete operation: How to build metal and acceptance testing

The device was originally built for M3 Ultra, 8E+24P CPU, 80 core GPUs, 512GB of unified memory, macOS 26.3; The toolchain is used for Xcode 26.3, Apple clang 17.0.0, CMake 4.3.2, Ninja 1.13.2. The system requirements here come from a specific branch, and should not be derived to all versions of llama.cpp that must use macOS 26.

### 7.1 Configuration, compilation, linking, execution divided into four checks

`cmake -S ... -B ...` Just build configuration and see `Generating done` There is no program yet. When used for the first time, configuration and build should be completed under a fixed source code set, and dynamic library and device initialization should be checked.

```bash
cmake -S . -B build-metal -G Ninja \
  -DCMAKE_BUILD_TYPE=Release \
  -DGGML_METAL=ON -DGGML_ACCELERATE=ON \
  -DGGML_METAL_EMBED_LIBRARY=ON
cmake --build build-metal --target llama-cli llama-server llama-bench llama-gguf-split -j 4
rg '^GGML_METAL|^GGML_ACCELERATE|^CMAKE_BUILD_TYPE' build-metal/CMakeCache.txt
otool -L build-metal/bin/llama-server
./build-metal/bin/llama-cli --list-devices
```

Embedded Metal library can reduce the chances of leaking shader resources when deployed, but shared dynamic libraries are still supported.`otool -L` It is used to check program dependency and does not guarantee that all backends are statically linked or listed on the main program. A dynamically loaded version is also used to run logs.

Runtime focuses on verifying Apple device names, Metal backend, unified memory tags and working set hints.`--version ` whether to trigger device initialization as version changes, use when necessary `--list-devices` Or a short model load verification. Don't assume that the compilation option must be OFF because there is no Metal line in the output of a certain version.

### 7.2 Why branches and GGUF must be reconciled

The original design was used to support special models.`nisparks/llama.cpp ` of `wip/deepseek-v4-support ` Branch, commit `9d36408`. The combination encounters two different types of errors:

|Mistakes|Stage of development|The focus of screening|
| --- | --- | --- |
| `missing tensor 'hc_head_base'` |Weights / tensor name matching|GGUF conversion source, model, implementation, fork settings|
| `Asserting on type 42 ` with `mul_mm_id_map0` |Warm-up to Metal operator|The current type of MoE kernel is implemented.|

Adding memory is not an appropriate fix for the first type of error; The second class is also not compatible with the kernel by lowering the ctx from 64K to 4K. The model architecture, GGUF sources, quantization types, forks and commits should be listed first, and the matching combinations that are supported should be found.

The original FP4/FP8 artifact contains 365.`f8_e4m3_b128` The expert tensor is about 145 GiB. This branch of the Metal MoE path failure, which can be derived from this set of artifacts that have not passed through this commit; This does not imply that every FP8 implementation is unavailable on Mac. Similarly, the 64/64 layer offloading log only indicates weights allocation, and subsequent air runs are still likely to fail.

### 7.3 Model Load and System Observation

On GGUF supported, make a small context, short output. Record the number of actual offload layers, Metal model buffer, KV and compute buffer, and then synchronize the observation `memory_pressure `, ` vm_stat`It's also the site of Activity Monitor. The 512GB also requires a budget, so you can't give all of your memory to weights.

Branching uses new build directories to avoid confusion with old CMakeCache and shader products. When switching back to the verified version, the program is restored along with the shared library. When you need to convert a model, rebuild the Python environment, and C++ build successfully does not mean that the transformers' conversion dependency is satisfied.

## Eight: Full operation: vllm-metal text service and template error

This 2026-05-18 record contains a very valuable complete link: successfully installed locally, native extensions can be imported, model text can be generated, and then problems with templates and visual support. If you separate each stage, you can avoid repeated replaying.

### 8.1 Fixed environment and native expansion

|Components|Recorded version|
| --- | --- |
| Python | 3.12.13 |
| vllm-metal | 0.2.0 |
| vLLM | 0.21.0+cpu |
| mlx / mlx-metal | 0.31.2 / 0.31.2 |
| mlx-lm / mlx-vlm | 0.31.3 / 0.4.4 |
| torch / transformers | 2.11.0 / 5.8.1 |
| nanobind | 2.10.2 |

Initial installed and operational projects `./install.sh ` Created `.venv-vllm-metal ` Preparing the vLLM source code and building the Rust extension `_rs.cpython-312-darwin.so`. Rebuild a fixed project commit, check the installed script and dependency, and don't use a pip version table as a complete build lock.

When you check the extension, leave the source code root directory:

```bash
cd /private/tmp
# 在此之前激活已安装vllm-metal的虚拟环境
python - <<'PY'
import vllm
import vllm_metal
import vllm_metal._rs
print(vllm.__version__)
print(vllm_metal.__file__)
print(vllm_metal._rs.__file__)
PY
```

Source code in the directory `vllm_metal/` It's possible to hide site packages, causing `ModuleNotFoundError: No module named 'vllm_metal._rs'`. Let's see.`__file__` the decision on whether to rewrite; There is no need to delete the environment every time an import fails.

Installation downloads have resulted in a disconnect between curl16 HTTP/2 and curl56. For public downloads, try HTTP/1.1, retries, and resume support. Verify the artifact after downloading. Dependence resolution failure should be checked for trusted indexes, packet versions and Python support, without directly relaxing the selection rules for all indexes.

### 8.2 Restore the original parameters of this service

Model directory unified writing `/srv/models/Qwen3.6-35B-A3B-bf16`, port 18092. The following environment variables and options belong to the fixed version above and should be re-verified after upgrading:

```bash
export VLLM_METAL_USE_MLX=1
export VLLM_MLX_DEVICE=gpu
export VLLM_METAL_USE_PAGED_ATTENTION=1
export VLLM_METAL_MEMORY_FRACTION=0.90
export VLLM_METAL_GDN_LAZY_DECODE=1
export VLLM_METAL_MULTIMODAL_MODE=auto
export VLLM_METAL_PREFIX_CACHE=1
export VLLM_METAL_PREFIX_CACHE_FRACTION=0.05
export VLLM_WORKER_MULTIPROC_METHOD=spawn
export TOKENIZERS_PARALLELISM=false

vllm serve /srv/models/Qwen3.6-35B-A3B-bf16 \
  --host 127.0.0.1 --port 18092 \
  --served-model-name qwen36-bf16 \
  --dtype bfloat16 --kv-cache-dtype bfloat16 \
  --max-model-len 8192 --max-num-seqs 16 \
  --max-num-batched-tokens 32768 --block-size 16 \
  --enable-prefix-caching \
  --chat-template /srv/models/Qwen3.6-35B-A3B-bf16/chat_template.jinja \
  --default-chat-template-kwargs '{"enable_thinking":false}' \
  --generation-config vllm \
  --override-generation-config '{"do_sample":false,"temperature":0,"top_p":1}' \
  --scheduler-reserve-full-isl
```

The remote code option of the original model should be enabled on demand from a fixed source and reviewed, and the system does not take it as the default for all services. 0.90 memory for instance and 16 sequences is the historical service parameter, not the 16 concurrency SLO that can be committed to 512GB; The new environment starts with a smaller budget.

### 8.3 From the mouse output only reasoning mouse position to template

Failure response Results `Here's a thinking process ` After 128 output tokens, `finish_reason=length `. Original inspection findings ` tokenizer_config.json `The chat_template is none, and the actual template is kept independent.` chat_template.jinja `; The default generated prefix is introduced.`<think>`.

Processing to simultaneously verify three layers: which template is loaded by the service, whether the template is supported `enable_thinking` What parameters are used in the final request? Only in the system write a template without reasoning a template control that cannot replace the model.

```bash
curl --fail-with-body http://127.0.0.1:18092/v1/chat/completions \
  -H 'Content-Type: application/json' \
  -d '{"model":"qwen36-bf16","messages":[{"role":"user","content":"用三句话介绍统一内存。"}],"temperature":0,"max_tokens":128,"chat_template_kwargs":{"enable_thinking":false},"stream":false}' \
  -o text-response.json
```

The original model generation_config `do_sample=true、temperature=1.0、top_p=0.95`. The service's default configuration and request cover the final sampling of the final decision, and cannot be changed to assume that all requests are consistent. After repair, save the template abstract, command and response, acceptance testing to see if the form is complete, rather than just checking the reasoning.

### 8.4 Image request Why change the route

When the same service receives images, the front end is generated.`mm_features、pixel_values、image_grid_thw` But the runner threw out:

```text
NotImplementedError: Multimodal encoder execution is not wired on Metal yet.
```

This shows that the request analysis and visual execution are located at different nodes. The error was subsequently triggered `EngineDeadError` In this example, the text success can't cover the image failure. Adding VRAM, extending HTTP overtime or continuing to submit the same image cannot add encoder without a connection.

The appropriate treatment is to preserve text service records, visually alter the model's already supported mlx-vlm implementation, re-enact functionality and performance acceptance testing. After upgrading the plugins, the same public map can be re-evaluated and the old failure can't be automatically rewritten into a new version.

## 9MLX-VLM: Go from single chart command to API

The multi-visual model guides in the original space cover MiniCPM-V-4.6, Qwen 3.6-35B-A3B and Gemma 4. Check first.`mlx_vlm.__file__` and source code commit, verify that the target environment is actually imported, and then check Metal device:

```bash
python - <<'PY'
import mlx.core as mx
import mlx_vlm
print(mlx_vlm.__file__)
print(mx.default_device())
print(mx.device_info())
PY
```

The shortest link is the command line, rather than overlapping HTTP with concurrency:

```bash
python -m mlx_vlm.generate \
  --model /srv/models/Qwen3.6-35B-A3B-bf16 \
  --image ./inputs/vision-card.png \
  --prompt '逐行读出图片中的文字，再描述图形，不补充图片外的信息。' \
  --max-tokens 512 --temperature 0
```

Public image generated view [Multi-mode example of vLLM](../frameworks/vllm-service.md#seven-complete-links-from-image-files-to-streaming-answers). Using the same diagram, it is easier to distinguish between model, processor and service packaging differences. Can't use the private working snapshot as the default input.

After the command line passes, the service is restarted. The original Qwen stable configuration was for max-tokens 4096, max-kv-size 32768 prefill-step-size 2048, vision-cache-size 32, port 8081:

```bash
python -m mlx_vlm.server \
  --model /srv/models/Qwen3.6-35B-A3B-bf16 \
  --host 127.0.0.1 --port 8081 \
  --max-tokens 4096 --max-kv-size 32768 \
  --prefill-step-size 2048 --vision-cache-size 32 --log-level INFO
```

Save it first `python -m mlx_vlm.server --help ` The current version confirms that these options are supported. The server is running at the time of launch.`--model ` It's not possible to directly connect to the oMLX.`/v1/models/{id}/load` The interface. The image structure of the request is also checked by the fixed server version, so it is not possible to see all OpenAI-style endpoints as completely consistent fields.

The original guide to try MiniCPM `downsample_mode=4x、max_slice_nums=36 `, try this for Qwen: ` max_pixels=3211264`. These parameters belong to a specific processor. Increasing the resolution/cut count may make small letters clearer, or increase the visual tokens, prefill and memory, and the identification results and resources should be stored separately in the same graph, without the need for a large graph parameter.

## OMLX: model detection, loading and memory budget

oMLX and the mlx-vlm independent servers use different model management processes. Originally `omlx serve --model-dir` Refer to the parent directory containing multiple model subcategories, list the detectable models after the service starts, then load and request the target model.

```bash
omlx serve --help
omlx serve --model-dir /srv/models --host 127.0.0.1 --port 8000
curl --fail-with-body http://127.0.0.1:8000/v1/models
```

Model ID is determined by the return value of the list. The original recording then used a corresponding version of the `POST /v1/models/{id}/load` And then call the chat endpoint. Whether runtime load is supported, how to provide the body, should be checked according to the current version of the API, avoiding using a directory name in the document as a model ID for all versions.

After the original 512GB device loaded DeepSeek-V4-Flash-4bit, the memory snapshot was 183.5/512GB, swap inactive. In vacuum, the GPUs of about 3% and 683 MHz are only after load, not as a result of inference of power consumption and continuous frequency.

Historical startup records have set max-model-memory and max-process-memory as disabled, SSD paged cache 100GB, hot cache 8GB. It explains how it worked at the time and should not be used as a default delivery: the model should be given a residence, process, system and disk budget, record the location of the cache and the remaining space, and then raise the ceiling. The size of the file in the model parent directory cannot be directly added to the sum of all models that are simultaneously loaded with RAM.

EvalScope scores for the model received [Concurrency testing](../performance/benchmarking.md#10-omlx-full-concurrency-results-and-workpoint-selection) This is the same as the TFT, TPOT, average and P99 latency. The MLM-VLM configuration of the other route of the APC is received [Cache topics](../performance/cache-scheduling.md#8-mlx-vlm-apc-from-configuration-to-cold-heat-cache-experiments). Hardware, engine, service management, and cache all have roles, so reading doesn't confuse the three programs into one set.

## List of acceptance testing deployed by Apple

At the very least, keep the following: toolchain with commit, model artifact identity, native extension source, template with sample, actual Metal allocation, text/visual segmentation results, load with heat inference, unified memory, pressure, swap and continuous workload. It was discovered that the kernel was missing in the version/artifact matching process, that the template was incorrect in checking the tokenization path, and that the system changed pages and processed the budget.

Source: Author of Mac Metal, vllm-metal, MLX-VLM and oMLX engineering articles, see [List of corresponding articles](../../evidence/chapter-sources.md).
