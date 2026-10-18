# Engineering sources and measured transcripts

[简体中文](../../01-deployment-foundations/evidence/README.md) | **English**

[Contents](../README.md) · [References](../appendices/references.md) · [Offline billing](../../01-deployment-foundations/examples/verify_records.py)

This directory focuses on the sources, conditions, and evidence gaps of true instances. deployment of technical articles in the author's FlowUs space; Public material only extracts the necessary fields of the project and does not publish the original space output, private page addresses or account information.

## 1. Organizing scope and methods

The whole project of the platform is focused on [Example matrix](../engineering/README.md). 50 technical articles retain complete technical text and code blocks; Routes, authentication and private node sanitization, technical errors marked the revision. Number of characters and code fences retained [List of source languages covered](../../01-deployment-foundations/evidence/source-coverage.json). Added 8060S single-machine Vulkan's CPU→GPU→parameter combination process, as well as full control of Q4/BF16.

This is based on spatial technology directories and models, deployment, compilation, inference, quantization, load testing and other topics. A large language model for deploying adaptive knowledge delivery system frameworks is a six-part, five-tiered structure for extracting specific engineering content from deployment, conversion, service and test records across platforms.

Knowledge frameworks are used to support organizational relationships, execute commands and output for supporting instances. Orders not equal to execution; Successful titles cannot cover subsequent failures. The recommendations in the article summarize the orders, early conclusions, failure log and measured judgments respectively.

Preserving the generic device model, version, model, parameter, numerical value and necessary errors; Accounts, credentials, private paths, node addresses, business samples and signature attachments are not transcribed. When the source note image does not have the complete material available to the public, it is not downloaded for storage or redrawn as a running snapshot.

## 2. Source number

The following technical titles are used to identify the author's records without providing a private space link; This is the most recent record of the merger.

|Numbers|Technical records|Official content adoption|The boundaries of evidence|
| --- | --- | --- | --- |
| E01 |DGX Spark adapts compilation vLLM deployment to Qwen 3.6-35B-A3B ((BF16/FP8)|ARM64/CUDA support, architecture compilation errors, FP8 services and 200 requests|FP8 has a summary; BF16 only commands, not performance comparisons|
| E02 |Qwen 3.5-9B Intel OpenVINO platform inference comparison report|IR revision,INT4/INT8,Vulkan/SYCL,NPU failure|GPU output is interrupted at the reasoning stage; Engine timing is not mixed|
| E03 |Deploying Kimi-K2.5-Q2 across five AMD Strix Halo 395 nodes with HIP RPC|Gfx/ROCm, GTT/TTM barrier, small context RPC|Lack of single-machine baseline and long-term API acceptance testing, lack of proven context performance|
| E04 |AMD 780M-GPU adapter tutorials and supporting configuration records|Windows community libraries, gfx, version isolation and verification|Historical community routes, not as promises to support all new devices|
| E05 |Mac Metal compilation with vllm-metal deployment records|Specific GGUF type failures, text and visual differences|Conclusions of specific versions/artifact combinations not promoted to the full platform|
| E06 |oMLX inference framework performance Test reports and load testing processes|Latency, TPOT, and output throughput at concurrency 1/2/4|Small sample size, request inconsistency, cache status and environment|
| E07 |GB10 Gemma series off/off MTP inference Accelerate two records|Concurrency groups, throughput, TTFT/TPOT/ITL, and acceptance rate|Absence of original request-by-request documents and quality equivalents, eliminating conflict peak fields|
| E08 |GB10 compilation DFlash and integrated vLLM|Two sets of service parameters and spec_bench summarized|Multivariate variation and observation of ratios cannot be attributed to a single variable|
| E09 |GB10 Gemma-4 AWQ 4bit/8bit deployment and load testing|Configuration, tokens and performance of the 26B-A4B series|Lack of revision/classification/quality; Peak concurrency and configuration conflicts|
| E10 |GB10 llama.cpp builds, Qwen translates GGUF, quantizes and imports Ollama|Convert links, build targets, CURL dependency, format checks|Each model/converter still needs to be independently verified|
| E11 |The dual RTX4080 vLLM Docker deployment record|Container, model, upload, multi-GPU and parameter management|The NVLink claim has been corrected; The speed scale is incomplete and not a rigorous profit chart.|
| E12 |Ascend 310P deployment and load testing records|Chip/plug-in/image support, actual sample size checks|10 concurrency of a request that does not demonstrate configuration; The old parameter is not the current default|
| E13 |RTX2060 Qwen3 Q6/Q5 Mixed inference records|CPU/GPU offloading, host memory and swap|A single engine observation; not HTTP throughput or a stable benchmark result|
| E14 |Intel Windows OpenVINO visual deployment records|GPU drivers, IR and visual functionality verified separately|The original image sample has no public authorization chain, is not stored, or is of quality.|
| E15 |W7900 8-card DeepSeek-R1 AWQ with dual node 70B/671B recording|ROCm container, OpenAI input, Ray and TP/PP|Part of the old fragment conflict has been modified by character, with no complete throughput|
| E16 |MLX-VLM multi-visual model inference with API guidelines and APC operations|CLI/API, processor, cooling cache, tenants and KV quantization|APC source code patchcommit is missing and does not guarantee any upgrades|
| E17 |GB10 Qwen3-VL,Qwen3-Omni,granite-docling deployment|Original model / port / budget, image transfer and functionality|Unrealized model results not added to new public test cards|
| E18 |ASR/TTS, full NPU, Kokoro specifications reported by Intel|Three rounds of timing, shape, wrong audio, rollback, 48 CPU results|Original audio is not public, ASR assistive checks are not equivalent to general quality sets|
| E19 |IPEX-LLM quantization and imported Intel integrated GPU records from Ollama|Windows program source, SYCL variable, modelfile and offloading verification|Early pre-release routes with no fixed current support commitments|
| E20 |Qwen 3.6-35B-A3B deployment with inference, BF16 inference optimization|8060S Vulkan offloading, ctx/batch, Q4/BF16 with buffer table|Conflicts in RAM fields, lack of quality, and request-by- request files; The bandwidth limit conclusion has been revised|

Other concept notes include KV, Prefill, Prefix Cache, ROCm/PyTorch, CUDA/Vulkan build and environment packaging, interpretations have been revised according to the official concept. Platforms that do not form a complete public record are retained as an adaptation method, not as a replacement for operational performance.

## 3. Publicly available measurement fields

[measurements.json](../../01-deployment-foundations/evidence/measurements.json) Preserving 16 groups of structured historical transcripts. The numbers keep the source units, and the fields are hand-ordered by white list; The lack of data is not a complete guess.

|Key to data|Key conditions and outcomes|Reading Location|
| --- | --- | --- |
| `dgx_qwen_fp8` |GB10/128GB/CUDA13; 200 request Suddenly, 25600 output tokens/297.46s|Level 3 Service, Level 4 Emergency and queue|
| `intel_openvino` |16GB/OV2026.2.1; IR fixed revision; INT4/8 with backend observation|2nd layer artifact, 3rd layer pipeline, 4th layer comparison|
| `omlx_concurrency` |Input goal 128, output ceiling 256; c1/c2/c4|Level 4 of the concurrency balance|
| `gemma_mtp` |Input 512 and output limit 256; Three groups of concurrency on/off MTP|Layer 4: speculative decoding|
| `dflash_observation` |spec_bench,50 request ; Context / sequence / memory / eager to change at the same time|Level 4 control variables|
| `amd_rpc` |Five 395 nodes, ROCm 7.2.1, llama b9557; Memory and short-term memory|Level 1 Compatibility, Level 3 RPC, Level 4 Budget|
| `gemma_awq` |GB10/vLLM0.19.0; 200 request ,c2; AWQ4/8|Level 4 quantization combined observation|
| `gemma_awq_31b` |31B AWQ4/8 full latency of the same workload|Table of topics for quantization|
| `rtx2060_hybrid` |RTX2060 12GB,32GB RAM; Q6 Engine generated|NVIDIA Mixed inference Full case|
| `intel_whisper_asr` |4.4 seconds audio, three-wheeled NPU core and process timing|OpenVINO speech is live|
| `intel_babelvox_hybrid` |NPU+CPU, three-wheel, torque and report RTF|device boundaries between work and timing|
| `intel_babelvox_full_npu` |CP fixed shape, RTF standard, audio error, rollback|Quality Objections to the Performance Scheme|
| `intel_qwen_tts_cpu` |0.6B INT8, CPU output of 8 seconds of audio; NPU dynamic shape failure|Product IR is not equal to NPU-ready|
| `intel_kokoro_cpu` |8 tone x 6 text; P95 RTF 0.189, RSS about 3GiB|Clean background and multiple acceptance testing|
| `intel_kokoro_npuw` |First run >20 minutes; cached rerun timed out after 120 s; no WAV produced|Compilation unfinished, not reported NPU throughput|
| `amd_8060s_vulkan` | Q4 22.9→47.2→58.4token/s;BF16 10.8→10.1token/s |Single-machine Vulkan combined with multiple parameters, without claims of losslessness or theoretical limitations|

### E01 Full Conditions

vLLM `0.19.1rc1.dev337+g17d87168d.cu130`, ctx16184, batched8192, seqs4, memory0.80, FP8 KV, FlashInfer, prefix caching, and chunked prefill. Random input target 2048, output 128, 200 requests, rate of achievement, infseed 42. The actual input is 411678, the output is 25600, the average TTFT is 148430.70ms, and the P99 is 293115.24ms.

The source note has no model revision and no complete JSON results. These figures are billable and cannot promise precise reproduction in another environment; Sudden workload also does not represent a light workload interaction experience.

### E02 model and environment

Core Ultra7 256V、Arc Lunar Lake、16GB；Ubuntu24.04.4、Mesa26.1.4、oneAPI2026.1.0、OpenVINO2026.2.1、GenAI/Tokenizers2026.2.1.0。

- INT4: `OpenVINO/Qwen3.5-9B-int4-ov `,revision `3f31fc1609edb0cbc8b131bc4c291f1b15cb0676`; 24 files, 6129582094 bytes.
- INT8: `OpenVINO/Qwen3.5-9B-int8-ov `,revision `3054198f70b6d50b97fa17ae80314e590c57def0`; 24 files, 9457724353 bytes.
- GPU pipeline 19 input/128 output token; NPU INT4 compilation failure, with the INT8 exiting 124 in 420 seconds.
- Vulkan/SYCL is available for the pp512/tg128 tricycle, GPU23/CPU10 layer, llama.cpp precision commit is not fixed in the source snapshot.

### E03/E05 edition boundaries

E03 used 5 Ryzen AI Max+395/8060S machines, ROCm 7.2.1, HIP 7.2.53211-e1a6bc5663, kernel 6.17.0-35, llama.cpp b9557-0f7fada56, and gfx1151. 120000MiB is the total visible amount of the repaired device, not the physical/available memory of any machine.

E05's Metal failure combination is M3 Ultra512GB, macOS 26.3, specific branch commit9d36408; Vllm-metal is another combination of 0.2.0, vLLM0.21.0+cpu, MLX0.31.2 and Python 3.12.13. The two sets of results were recorded separately, not mixed into a single environment.

### E07/E08/E09 Restrictions on comparison

E07 image is labeled as `vllm/vllm-openai:gemma4-0505-cu130`; the digest was not saved; MTP used 3 candidate tokens. E08 simultaneously changesctx32768→8192→seqs1→8→memory 0.70→0.85, baseline, apparent eager, on the other hand not apparent configuration. The target output of E09 is 128 and the actual total output is 25696, calculated by the actual token; The error peak field is not used for derivation.

## 4. Offline inspection and verification in this round

Running from the repository root directory:

```bash
python docs/01-deployment-foundations/examples/verify_records.py
```

The script only reads the JSON of the directory, checks the partial success counts, tokens/time and records throughput, concurrency pairs and ratios; [Actual control panel output](../../01-deployment-foundations/examples/verified-output.txt) Save the text. It doesn't connect devices, download models or make inferences.

This round has been renewed and implemented [Full Windows CPU workout](../practice/first-service/README.md) Fixed downloads with summaries, service starts, three functionality queries, malformed JSON, eight flow requests, metrics, service stops and three-wheel engine benchmarks. Public 12 results files. Three functionality queries were passed. Two, malformed JSON returned 500 and total acceptance testing was false.

The history of the GPU/NPU has not been overturned. Offline checking of document relative links, code fences, Python grammar and historical algorithms; These checks do not replace device and quality verification.

## 5. How has the evidence been reconciled?

The new experiment preserves the entire environment and artifact identity, final commands, inputs, request response, errors, resources, sampling and statistical procedures. Quality and performance are separated by acceptance testing, fixed version and workload.

This is a new addition. [public visual test card](../../01-deployment-foundations/assets/vision-input/vision-card.png), [Expected fields](../../01-deployment-foundations/assets/vision-input/expected.json), [Production process](../../01-deployment-foundations/examples/make_vision_input.py) with [Flow client](../../01-deployment-foundations/examples/vision_client.py). The test card has generated and verified the size, content fields and summaries; It is public input, not as a GPU/NPU measured output.

Historical records of the original documents, which were not made public, can still be used as a reference for engineering knowledge, but not directly as a complete reproduction of the material. In the event of a real-world war, [List of engineering deliveries](../02-capability-layers/05-engineering-delivery.md) complete each missing item.
