# 1.2.3 Intel hardware, oneAPI and OpenVINO

[简体中文](../../../01-deployment-foundations/chapters/hardware/intel.md) | **English**

[Contents](../../SUMMARY.md) · [Hardware and runtime overview](../../02-capability-layers/01-hardware-backends.md)

## Hardware basics

Intel platforms may offer CPUs, integrated GPUs, Arc discrete GPUs, and NPUs. The CPU is responsible for the overall work; The GPU is suitable for parallelism models. NPU is geared towards supporting neural network workloads. Core Ultra is the name of a series of processor products that cannot be used alone to determine the range of support for GPU/NPU interfaces or large language models.

|Device|Memory and computational features|Focus on deployment|
| --- | --- | --- |
| CPU |Using system RAM, passed supported vector/matrix instruction calculations|Instruction sets, threads, memory channels, NUMA and operator library|
|integrated GPU|Shared system RAM|Bandwidth, device, budget, CPU/GPU and driver|
|Arc discrete GPU|There's usually independent VRAM.|Models, VRAM, drivers, supported kernels and precision|
| NPU |Usually dependency special compilation and execution plugins|Model diagram, shape, operator, precision and compilation time|

GPU devices do not represent the availability of NPU plugins, and NPUs do not represent the ability to execute any voice model, nor do they represent the ability to execute any LLM directly.

## What are oneAPI, SYCL and OpenVINO?

|Components|Responsibilities|Relationship with the deployment of the large language model|
| --- | --- | --- |
| oneAPI |Cross-architecture software specifications and tools/library ecology|It provides compilers, compute libraries, analytics tools, etc., not a single runtime.|
| SYCL |Parallelism programming standards based on C++|Development and execution routes at the backend of llama.cpp SYCL|
| Level Zero |Intel GPU's underlying device access and execution interfaces|GPU paths commonly used for the corresponding SYCL runtime|
| oneDNN / oneMKL |Deep learning operators and mathematics compute library|Provide corresponding computation implementations by device and framework version|
| OpenVINO Runtime |Loading model, compilation map and passed device plug-in execution|Model and operator verification by CPU/GPU/NPU target|
| OpenVINO GenAI |Runtime-based generated model pipelines|Tokenization, generating, KV and Multimodal Capabilities|

```text
GGUF → llama.cpp SYCL backend → SYCL runtime / Level Zero → Intel GPU
IR and supporting files → OpenVINO GenAI → Runtime device plugins → CPU/GPU/NPU
```

Vulkan is another GPU computing route; The PyTorch XPU also has its own package, operator and backend requirements. These routes have different artifact, memory management and timing boundaries and cannot be interchanged only by device brand.

## Selection and optimization first

Local text pre-selects the model for completeness, output the correct backend, and then compares the load, initial token, decode and resources. When you need an NPU, check the model graph, shape and compilation constraints first. Don't decide the entire link with just TOP's or low power advertising.

Both integrated GPUs and NPUs can be used with CPU shared memory, image, audio preprocessing, and multiple pipelines. Mixed execution should record the actual device use of each module, and end-to-end results include preprocessing, execution and postprocessing.

Basic information: [oneAPI](https://www.intel.com/content/www/us/en/developer/tools/oneapi/overview.html) · [OpenVINO](https://docs.openvino.ai/).

## Deployment procedures and examples

The following is a list of devices, three GPU backend and NPU pipeline interpretation checks. See full history [Arc GPU, NPU and ASR/TTS](../../engineering/intel-arc-npu.md).

## One, three common routes

llama.cpp Vulkan uses the Vulkan driver to execute supported GGUF; SYCL route dependency oneAPI with corresponding runtime; OpenVINO GenAI uses supporting IR and device plugins. XPU framework routes also require verification of specific models and kernels.

|Routes|The main artifact|Check first.|
| --- | --- | --- |
| Vulkan | GGUF |device, driver, shader and offloading|
| SYCL | GGUF |OneAPI, Level Zero and frame architecture|
| OpenVINO GenAI |IR and supporting documents|Pipeline, plugins, models, charts and precision|

The same name as OpenVINO can't be omitted from the executor. llama.cpp OpenVINO+GGUF, with GenAI+IR, is a different link.

## Second, the environment.

The author tested the device for Core Ultra 7 256V, Arc Lunar Lake, 16GB of unified memory, Ubuntu 24.04.4; Mesa26.1.4,oneAPI2026.1.0,OpenVINO2026.2.1,GenAI/Tokenizers2026.2.1.0.

```bash
vulkaninfo --summary
sycl-ls
icpx --version
```

These commands are used in environments that have installed the corresponding software stack and retain the actual device and version. Additional plugins when using OpenVINO:

```python
import openvino as ov
core = ov.Core()
print(ov.__version__)
for device in core.available_devices:
    print(device, core.get_property(device, 'FULL_DEVICE_NAME'))
```

The listing only proves that the device can be found, and the next step is to load the matching IR and actually generate the token.

## Three, choose an entrance to complete a task.

In the original design, the GenAI GPU completed short generations of the Int4 and Int8 of Qwen 3.5-9B; The NPU INT4 is in compilation phase failure, and the INT8 compilation exits 124 after 420 seconds. It is possible to continue testing the complete answer using the passed GPU route while maintaining the NPU failure condition.

Another llama.cpp OpenVINO attempt could be constructed and listed, but encountered problems such as CPY/cache_r in GGUF. It cannot be successfully covered by the GenAI GPU.

## Four, 16GB of resources

The Vulkan/SYCL recording uses GPU 23 layer, CPU 10 layer, and is a mixed execution. Host memory, swap and device allocation should be observed simultaneously. The memory and timing of IR routes vary and require a separate baseline.

In the original record, the Vulkan engine generated 11.54±0.13 tokens/s, while the SyCL was 10.22±0.19; OpenVINO INT4 pipeline 21.1599 tokens/s The latter uses different artifacts and timing boundaries, which cannot be directly distinguished from the claimed frame acceleration.

## Five, get into full operation.

According to [OpenVINO IR is fully operational](../frameworks/openvino.md) Preparing independent environments, fixed revision, downloading files, uploading GPUs, warm-up, generating and storing indicators. The instruction manual writes the CPU/GPU/NPU target clearly and by default along the original recorded GPU input.

After completion, the length and quality of the business will be prepared. The original 19 inputs/128 outputs were recorded at the limit at the reasoning stage, so complete response quality still needs separate acceptance testing.

## Six, Complete Contrast: How to measure Vulkan with SYCL

The original GGUF was Qwen 3.5-9B Q4_K_M, about 5.23GiB, 8.95B parameter; There are 33 offloading layers of GPU 23 and CPU 10. This distribution is important: the speed in the table belongs to the mixed execution, and cannot be labeled as a full CPU.

Vulkan and SYCL use separate build directories to avoid synchronizing CMake cache with dynamic libraries. First fix the same source code, snapshot, model summary, thread number and offloading, then compilation respectively. There's no first shot.`.git` Only the information in version 0.16.0 is known, so the historical commit remains unknown; New experiments should complement source code commits, rather than date guessing versions.

```bash
cmake -S . -B build-vulkan -DGGML_VULKAN=ON -DCMAKE_BUILD_TYPE=Release
cmake --build build-vulkan --target llama-bench llama-server -j 4

source /opt/intel/oneapi/setvars.sh
sycl-ls
cmake -S . -B build-sycl -DGGML_SYCL=ON \
  -DCMAKE_C_COMPILER=icx -DCMAKE_CXX_COMPILER=icpx \
  -DCMAKE_BUILD_TYPE=Release
cmake --build build-sycl --target llama-bench llama-server -j 4
```

Specifically build dependency prepared in the fixed llama.cpp version. Vulkan requires matching headers, loaders and shader compilation tools, while SYCL requires a compiler and runtime. After creating the pass, the short request verifies the output of the two routes and then enters the same pp/tg benchmark.

```bash
./build-vulkan/bin/llama-bench -m "$QWEN_GGUF" \
  -ngl 23 -t 8 -fa on -p 512 -n 128 -r 3

export ONEAPI_DEVICE_SELECTOR=level_zero:0
export ZES_ENABLE_SYSMAN=1
./build-sycl/bin/llama-bench -m "$QWEN_GGUF" \
  -ngl 23 -t 8 -fa on -p 512 -n 128 -r 3
```

0 should be checked in the device selector `sycl-ls` It is not possible to assume that on multiple Intel devices, 0 will always be expected to be a GPU. Start one route, measure the release, and then start another. The original data is as follows:

|Routes and boundaries|Input/generate|Prompt rate|Growth rate|
| --- | --- | --- | --- |
|SYCL engine, three wheels| pp512 / tg128 | 353.70±15.31token/s | 10.22±0.19token/s |
|Vulkan engine, Mesa 26.1.4, three wheels| pp512 / tg128 | 244.91±0.79token/s | 11.54±0.13token/s |
|SYCL HTTP short request| 16 / 128 | 11.67token/s | 9.21token/s |
|Vulkan HTTP short request| 22 / 128 | 10.53token/s | 11.38token/s |

SYCL's pp is higher and Vulkan's tg is higher. This is not contradictory: Long input processing is different from the form of computation generated per token. If the daily input is long and the answer is short, TTFT should be the focus. If the input is short, the output is long, the decode rate weights higher. The two HTTP requests had different input token counts, so the entire difference cannot be attributed to the backend.

### Mesa upgraded observation

The old Mesa 25.2.8 record generated about 7.76 tokens/s, 26.1.4 was 11.54±0.13, and the observed improvement was about 48.7%. The old baseline does not have the same complete repeat recording, which is suitable for historical observation after changes in the version of the driver; The new test should preserve the old/new driver, the same model, the same parameters and repeat rounds.

Driver upgrades also verify desktop, Vulkan, and target services, retaining recoverable software packages and configurations. Don't skip other applications and long-term stability checks just because one model gets faster.

## Windows IPEX-LLM and Ollama: Keeping the old route and correcting the default assumptions

Early engineering used the Python 3.11 independent conda environment.`ipex-llm [cpp]` Pre-release package, passed `init-ollama.bat` Prepare the Intel adapter and start Ollama. It can be read as a historically compatible path, but the dependency of the pre-release will change, and the current reconstruction will need to check the maintenance status of the project, support device and fixed package versions.

When the Ollama system is present in the directory at the same time as the adapted version, confirm which one is currently being executed:

```powershell
Get-Command ollama -All | Select-Object Source
ollama --version
Get-CimInstance Win32_VideoController | Select-Object Name, DriverVersion
```

Environmental variables included `ZES_ENABLE_SYSMAN=1 `, ` SYCL_CACHE_PERSISTENT=1 `and ` OLLAMA_NUM_GPU=999 `. 999 of them express an offloading request, which does not guarantee that all layers actually land on the GPU; It's still necessary to log in from the service and ` ollama ps `This is the latest version of the game, which has been updated several times. The Old ` SYCL_PI_LEVEL_ZERO_USE_IMMEDIATE_COMMANDLISTS=1`It is a testable option, which may improve or decrease performance, and cannot be unconditionally retained for all versions.

When importing a Modelfile from a local GGUF, confirm that the GGUF tokenizer and template are recognizable. Mistral in the original note `[INST]` The template cannot be used in Qwen or other architectures:

```text
FROM ./model.gguf
PARAMETER num_predict 256
```

Let the matched version read the model itself with the template, and set it to the model by default if necessary. Creating short subjects, multiple rounds, natural endings, resources, observing everything passed and then applying it; Ollama create successfully only indicates that the artifact has been registered.

## Eight, NPU shape fit: Why can't a model just change devices?

GPUs and CPUs are usually more adaptable to dynamic shapes; NPU compilation paths have their own requirements for shape boundaries, states, and operators. Exporting the model to IR requires only the conversion of the graph expressions, but also the ability of the target plugins to compile, execute, and maintain numerical significance.

The TTS project demonstrates this distinction well. The original Qwen3-TTS0.6B product included multiple graphics for Talker, Code Predictor, embedding/projection, and Speech Tokenizer. Directly `device=NPU` The first is the encoder failure; After skipping the unnecessary encoder, the decoder again fails due to infinite dynamic length failure; To keep Tokenizer in the CPU, just migrate Talker, and still encounter dynamic ShapeOf error. Three failures are positioned in a different subgraph.

```text
Upper bounds are not specified
Got negative shape dim bound: '-1'
to_shape was called on a dynamic shape
```

Properly tailored to list the input, output, dynamic dimension, state, precision and target device of each graph, then consider the fixed shape or multiple buckets. The bucket is not successful after arbitrary padding: the valid length, attention mask, location coding, KV location and EOS all remain in the original sense.

|Need to check|Why Does It Affect Correctness?|
| --- | --- |
|Text/token length|The padding area cannot be considered as an effective context|
|KV capacity and actual location|Writing/reading errors can be magnified after several steps|
|Upper bound of codec|It's not possible to pretend that the end is natural.|
|The output of the subtype|The accuracy and layout of the following diagrams must match|
| CPU fallback |Effects on real device allocation, latency and memory|

The identity of the compilation cache should also include model and graphics, plugins/drivers, precision and compilation options. After replacing the IR or bucket, the old cache cannot be automatically used as proof of compatibility.

## Nine: From a single model to a 16GB device.

LLM, ASR and TTS are tested on the same device. When the LLM occupies unified memory, voice compilation is competing with the operating system, so the original voice specialisation stops the LLM service. This condition must be maintained with the results, otherwise the exclusive test results cannot be directly committed to three models running simultaneously.

measured gives an explanatory division of labor candidate: LLM uses a passed GPU route; The NPU core RTF of the Whisper Base INT8 is about 0.0387; Kokoro's 48 RTF P95 CPUs are 0.189. They show that different tasks can be achieved on different device paths, but runtime memory and usage also need to be specifically replicated.

It was not selected because of the RTF0.723 NPU path of BabelVox: the group translated the audio with only one word, quality failure. Full parameter, three-round table, 48 Kokoro results and rollback process see [OpenVINO speech is live](../frameworks/openvino.md#seven-complete-engineering-record-cold-start-of-the-whisper-asr-and-heat-inference). Here, the selection basis is the correct output, resources and performance.

Source: Qwen3.5-9B Intel OpenVINO platform inference comparison of reports by Qwen, Intel Vision and IPEX/Ollama records, see [List of corresponding articles](../../evidence/chapter-sources.md).
