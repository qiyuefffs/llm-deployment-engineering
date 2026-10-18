# FlowUs article and chapter tables

[简体中文](../../01-deployment-foundations/evidence/chapter-sources.md) | **English**

[List of knowledge systems](../SUMMARY.md) · [Historical data and conditions](README.md) · [This round of CPUs is complete.](../practice/first-service/README.md)

## 1. How are these materials used?

The basic large language model deploys an adaptive knowledge delivery system framework that determines the six parts, five layers and each layer's section numbering. The main framework is organized by component, parameter and engineering inspection; The full text of 50 related FlowUs technical articles [Device engineering examples](../engineering/README.md), preserving commands, tables, errors, and follow-up experiments. Private information and credentials have been sanitized. For the source inventory and retained content, see [List of source languages covered](../../01-deployment-foundations/evidence/source-coverage.json).

Examples of execution in platform themes use a unified public path; The full source text retains the technical parameters and replaces the private paths and nodes, historical listening configuration as originally identified. Examples of introduction supplement execution order and technical revisions. An unresolved recommendation order is still marked as an operation statement; Failure and success are retained. The new writing program is not a fake as a historical original.

## 2. What articles are mentioned in the Five Pillars of Scripture?

|General Chapter|FlowUs technical articles or record topics|Topics and content of the system|
| --- | --- | --- |
|Layer 1 1.1 to 1.4.|4090 CUDA, DGX Spark compilation, CUDA links are wrong| [NVIDIA](../chapters/hardware/nvidia.md) Driver/Toolkit/Wheel, SM and kernel|
|Layer 1 1.2 to 1.4|780M instruction, 395 five-machine HIP RPC, ROCm environment| [AMD](../chapters/hardware/amd.md) Gfx, version isolation, GTT/TTM|
|Layer 1 1.2 to 1.4|Qwen 3.5-9B Intel comparison with Windows Visual deployment| [Intel](../chapters/hardware/intel.md) backend: device separated from task|
|Layer 1 1.2 to 1.4|Mac Metal builds, vllm-metal, oMLX operates| [Apple](../chapters/hardware/apple.md) Artifact with text/visual support|
|Layer 1 1.2 to 1.4|Ascend 310P deployment, plug-in installation and load testing| [Ascend](../chapters/hardware/ascend.md) Chip/image support and actual request number|
|Level 2 2.1 to 2.6|GB10 llama.cpp,Qwen converts GGUF, quantization and Ollama is imported| [GGUF conversion](../chapters/models/gguf-conversion.md): full directory→ F16→ Q4→ loaded|
|Layer 2 2.3 to 2.6|GGUF quantization Intel IR INT4/INT8 Gemma AWQ comparison| [quantization](../chapters/models/quantization.md) Capacity, kernel, quality and performance|
|Layer 3 3.1 to 3.3|DGX Spark vLLM source code deployment of Qwen FP8, early vLLM installation| [VLLM services](../chapters/frameworks/vllm-service.md) Build, launch, API and sudden workload|
|Layer 3 3.4 and 3.5|CUDA/HIP/Vulkan/SYCL/Metal building and loading| [llama.cpp](../chapters/frameworks/llama-cpp.md) Independent building, services and benchmarks|
|Layer 3 3.1/3.6|Intel OpenVINO vs. IR deployment| [OpenVINO](../chapters/frameworks/openvino.md) Dependence, fixed artifact, pipeline and failure|
|Layer 4 4.1 and 4.6|Benchmarking tool overview, vLLM bench, EvalScope, and oMLX reports| [Performance testing](../chapters/performance/benchmarking.md) Workloads, boundaries, concurrency and indicators|
|Layer 4 4.2 and 4.6|KV, Prefill, Prefix Cache learning and verifying notes| [Cache and scheduling](../chapters/performance/cache-scheduling.md) Conceptual revision and experimental sequence|
|Layer 4 4.6|Multi-node, dual 4080, linear barrier, AMD five-machine RPC| [Multi-device](../chapters/performance/parallelism.md) Communication, closures, capacity and revenue|
|Layer 4 4.6|Gemma turns off/off MTP, GB10 integrated DFlash| [Speculative decoding](../chapters/performance/speculative-decoding.md) Coupled results with attribution of multiple variables|
|Layer 5 5.1 floor 5.3|Docker Runtime, dual-GPU container, Ascend image, Intel service disabled| [Environment and Transport](../chapters/delivery/environment-operations.md) Packaging, switching on and resetting|
|Layer 5 5.2 floor 5.3|OpenAI is compatible with interface, load testing and service monitoring| [API and monitoring](../chapters/delivery/api-monitoring.md) Contracts, indicators and acceptance testing|

The third part explains the ten original concepts; Section Four records the organization of engineering materials in ten projects; Section 5 retains eight original directories as indexes; Part Six extracts the check-in from the above real failures.

### This is an expansion of what engineering processes are used.

|Subjects of the article|The official opening location|Direct use of materials|
| --- | --- | --- |
|RTX2060 Qwen3 Q6/Q5 mixed inference|NVIDIA 7th season|i5/32GB/12GB, original parameter, 9/182 tokens with timing, resources, observation, concurrency, evidence range|
|395 five aircraft HIP RPC Kimi-K2.5-Q2|Section 6 of AMD|BIOS 2GB, GTT/TTM numbers, DKMS modules, repair, build, RPC, split, loading and monitoring|
|W7900 eight-card and dual-node 70B/671B|AMD 7th, multi-device 8th, and 9th|ROCm container, OpenAI input fixes, Ray roles, TP8×PP2, resources and communication checks|
|Mac Metal source code to build|Apple Seventh|Xcode/clang/CMake/Ninja, library and shader, 9d36408, hc_head_base/type42|
|vllm-metal compilation with text/visual|Section 8 of Apple|Full dependency tables,_rs import locations, template/sample, encoder not implemented with EngineDead|
|MLX-VLM multi-visual model with API|Apple Section 9, vLLM image links|Metal checks, CLI/server, image fields, processor resolution and chip parameters|
|oMLX operation and performance|Apple 10th, load testing 10th|Parent directory detection, load processes, memory, snapshots, three levels of complete latency and throughput|
| MLX-VLM APC |Cache Section 8 and 9|Original environment variables, block/disk budgets, tenant, stats/reset, and incompatibility with KV quantization|
|Intel GPU comparison|Part 6 of Intel: OpenVINO main course|pp/tg, 23/10 layers, Mesa 25.2.8 and 26.1.4, and HTTP/Pipeline timing boundaries|
|Intel Speech Specials|OpenVINO 7th and 12th episodes|Whisper tricycle, BabelVox device split/tricycle, CP shape and quality failure, Qwen TTS, Kokoro 48|
| GB10 VL/Omni/docling |NVIDIA Episode 8, VLLM Episode 7 and 8.|image, original port and budget, base64/SSE process, functionality|
| Gemma4 AWQ4/8 |Quantization Section 8|26B-A4B/31B four groups, 200 requests, actual tokens, TFT/TPOT/ITL/E2E full table|
|Gemma4 MTP turned on and off|Speculative decoding, sections VI–VII|Principal/assistant, service budget, three-tier matching, acceptance of counts and flow analysis|
|GB10 DFlash compilation and testing|Speculative decoding, sections VIII–IX|2cc008e7b, CUDA/torch, drafter, two sets of configurations with full latency|
|Intel IPEX-LLM and Ollama|Intel 7 and GGUF input nodes|Python 3.11 history routes, program sources, SYCL variables and templates Modified|

The above parameters and numeric values retain engineering meaning, private paths and nodes are changed to public. Public Visual Graphics, client and ARIA2 list generators are included in this supplemented instructional material, without pretending to be historical originals.

## 3. The full implementation of this new round

Windows CPU exercises actually download fixed official binary and Qwen3-0.6B-Q8_0, a post-nuclear model running service, three-way functionality questions, malformed JSON, eight streaming requests, metrics, and three-wheel engine benchmarks. The full input, code and 12 result files have been made public.

It is recorded separately from the historical works of FlowUs. This round has not re-run the GPU/NPU historical record, nor does it treat the expected output of the new code as an executed result. Total acceptance testing clear failure, see details [Practical Lessons](../practice/first-service/README.md).

## 4. How were the concepts and the old record revised?

Preserving useful versions, steps, errors, and data while revising format/quantisation, confusion, K-quant interpretation, CUDA version relationships, 4080 NVLink, Docker VRAM limitations and prefix cache implementation, and more. See revised list [Appendix B](../appendices/references.md).

Public materials do not include private page links, spatial exports, accounts, credentials, actual addresses of nodes and unauthorized business entries. The original framework diagram uses user-provided annexes; Other private note-taking images that were not transferred directly to this system were measured.

## 5. Complete technical correspondence to device instances

|Examples of documents|Full technical article|
| --- | --- |
| [nvidia-rtx2060](../engineering/nvidia-rtx2060.md) |R01 nvidai-llamacpp-qwen3:30-a3b-q6 test record; R02 nvidai-llamacpp-qwen3:30-a3b-q6 benchmark performance test record; R03 nvidai-llamacpp-qwen3:32B-q5 benchmark performance test records|
| [nvidia-dual-gpu](../engineering/nvidia-dual-gpu.md) |R04 servers: Nvidia GPU: Ubuntu 22.04+VLLM+Docker dual-GPU deployment Deepseek-r1:32B ((Int4)|
| [nvidia-gb10](../engineering/nvidia-gb10.md) |R05 NVIDIA GB10 ARM compilation llamacpp; R06 nvidia GB10 device (arm64 architecture ) compilation vllm; R07 DGX Spark is adapted to compilation vllm deployment of Qwen 3.6-35B-A3B model (bf16/fp8 precision); R08 NVIDIA GB10 deploys Qwen3-30B-A3B-Instruct-2507 and is equipped with the following: R09 DGX GB10 deploys the AWQ quantization model of the Gemma-4 series; R10 DGX Spark GB10 deploys the gemma-4 series model and shut down MTP inference acceleration; R11 DGX Spark GB10 deploys the gemma-4 series model and MTP inference acceleration; R12 DGX Spark GB10 compilation DFlash inference Acceleration modules integrated into vllm|
| [nvidia-gb10-multimodal](../engineering/nvidia-gb10-multimodal.md) |R13 GB10 deploys the Qwen 3-VL-8B model; R14 nvidia GB10 deployed Qwen 2.5-VL-7B; R15 GB10 deploys Qwen3-VL-30B-A3B; R16 NVIDIA GB10 version vllm deploys Qwen3‐Omni‐30B‐A3B‐Instruct; R17 NVIDIA GB10 vllm deployment of granite-docling-258M|
| [amd-780m](../engineering/amd-780m.md) |R18 AMD 780M-GPU adaptation tutorials; R19 AMD adaptive model (GPU-780M, CPU-8845HS); R20 AMD: using the Ollama framework to deploy Llama3.1 8b on AMD's GPU|
| [amd-8060s](../engineering/amd-8060s.md) |R21 Qwen 3.6-35B-A3B deployment and inference documentation; R22 Qwen 3.6-35B-A3B BF16 inference Optimized record|
| [amd-395-rpc](../engineering/amd-395-rpc.md) |The R23 AMD Strix Halo 395 five-speed HIP RPC series deploys the Kimi-K2.5-Q2 live combat documentation; R24 AMD 395 llamcpp+rpc compilation process; R25 AMD 395 llamacpp rpc service functionality Environmental testing script|
| [amd-w7900](../engineering/amd-w7900.md) |R26 single-node eight-card server ((W7900*8,48*8) deployment of DeepSeek-R1-AWQ-INT4; R27 W7900 dual-GPU deployment Qwen3:30b-A3b; R28 servers: AMD GPU:Ubuntu 22.04+VLLM+Docker dual-GPU deployment Deepseek-r1:32b/70b; R29 AMD single node four card DS-70B-fp16 test command; The R30 dual-node model deploys 70B verification; The R31 dual-node model deploys 70B-2.0 resources scheduling verification; R32 double node, again inference DS-70B; R33 Deepseek-R1-671b dual node deployment; R34 multi-node deployment barrier|
| [intel-arc-npu](../engineering/intel-arc-npu.md) |R35 Qwen 3.5-9B Intel openvino platform inference comparison report; R36 Qwen 3.5-9B INT4 IR multimodal visual inference test report; R37 usesipex-llm to quantize and produce ollama models deployed on Intel integrated GPUs. ; R38 Intel NPU makes model inference: deepseek-r1:1.5b, 7b, 8b|
| [apple-metal](../engineering/apple-metal.md) |R39 llama.cpp is a compilation guide on Mac Studio (Apple Silicon)|
| [apple-mlx](../engineering/apple-mlx.md) |R40 vllm-metal compilation with inference records; R41 mlx-vlm multi-visual model inference and API call guidance; R42 oMLX Mac inference operation process; R43 oMLX inference framework performance test reporting and load testing processes; R44 Mac device inference framework Classification summary|
| [ascend-310p](../engineering/ascend-310p.md) |R45 Huawei Ascend 310P3 inference Qwen3-32B; R46 Huawei Ascend 310p3: Qwen3-32b is tested with Qwen3-235b-a22b-2507; R47 Ascend 310P3 deploys Qwen3-32B benchmark records|
| [benchmark-tools](../engineering/benchmark-tools.md) |R48 llama.cpp with vLLM inference performance assessment tool 2026 edition; R49 large language model performance assessment framework set|
| [gguf-ollama](../engineering/gguf-ollama.md) |R50 uses llama.cpp for model conversion and quantization, and then uses ollama custom model.|
