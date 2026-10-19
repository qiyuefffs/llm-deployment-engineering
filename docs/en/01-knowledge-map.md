# Part I: overall knowledge map

[简体中文](../01-deployment-foundations/01-knowledge-map.md) | **English**

[Contents](SUMMARY.md) · [Platform instance matrix](engineering/README.md)

## Four types of deployment components

|Component|What is it?|Common names|
| --- | --- | --- |
|Hardware|Device that actually stores data and performs computations| CPU,NVIDIA/AMD/Intel GPU,Apple Silicon,NPU |
|compute software stack|Submit the program computation to the device and provide the operator with the development tools.| CUDA,ROCm/HIP,Metal,oneAPI,CANN |
|model artifact|Weights, architecture, tokenizer, template and preprocessing configuration|HF directories, GGUF, OpenVINO IR, and MLX compatible models|
|inference engine|Loading models, managing caches, executing, scheduling and output| vLLM,llama.cpp,MLX-LM,OpenVINO GenAI |

MLX is a machine learning framework; MLX-LM implements text-model inference on top of it; Metal provides the Apple GPU compute interface. CUDA/ROCm and MLX occupy different software layers. For the complete relationship, see [Hardware and runtime](02-capability-layers/01-hardware-backends.md).

### The steps in one generation request

```text
User question → apply template/tokenize → token sequence
        → prefill: process input and establish KV and other state
        → decode: compute the next token and update state
        → sampling/stopping checks → detokenize → JSON or streaming output
```

The model is loaded into the CPU/GPU and other executable devices. the inference engine calls the runtime, compute library or kernel to perform the above calculations; Multi-GPUs also need to exchange intermediate results. The image and audio tasks add preprocessing, encoder or decoder respectively.

### Learning sequence

|Order|Need to Understand|Questions Answered|
| --- | --- | --- |
| 1 |Hardware, memory, bandwidth, drivers and runtime|What route does this device take to run the model?|
| 2 |Model architecture, formatting, precision, quantization and templates|Which files are needed, will they fit, and what does conversion change?|
| 3 |Prefill/decode, KV, kernel and request scheduling|How does the engine run and what configurations affect capacity and latency?|
| 4 |Baseline, indicators, workload and bottlenecks|Which stage is slow, and which setting should change?|
| 5 |API, deployment environment, monitoring, recovery and acceptance testing|How do we turn a runnable model into a maintainable service?|

Platform examples are used to observe the performance of these mechanisms in specific devices. The following tables describe general engineering modules and their inputs and outputs. Follow the example links for commands and historical results.

## 1. The deployment workflow

```text
Complete delivery workflow from model to service
```

|Engineering module|Input|Core operations|Output / verification gate|
| --- | --- | --- | --- |
|1. Hardware backend adaptation|Device, OS, driver, and framework|Identify arch/gfx and compatible runtimes, builds, operators, and communication|Actual computation completed on the device; Supported target models|
|2. Model formats and quantization|Original models, engine support, resources|Pin revision; convert, quantize, configure templates, and verify|Loadable artifacts, hashes, and quality baseline|
|3. Inference framework selection|Artifact, device, API and mission|kernel, KV/scheduling, boot, and protocol verification|A callable service that completes generation|
|4. VRAM and KV Cache|Model structure, dtype, length and sequence of activities|Budget weights, KV, status, graphs, workspace|Startup, execution, and load-test peaks, plus safety margin|
|5. Load testing and optimization|Fixed input, SLO, baseline|Controlled access rate/ concurrency, resources, sampling, individual comparisons|Raw records, statistics, quality checks, and conclusions|
|6. Multi-GPU / multi-node|Single-machine baseline, topology, and communication libraries|TP/PP/DP/EP/RPC, rank and device mapping|Changes in capacity, communication costs, speed and recovery|
|7. Serving and delivery|Verified operating combinations|API/SSE, monitoring, rate limiting, environment, and rollback|Seven deliverables and execution entry points|

### 1.1 Define task constraints before parameters

```yaml
task: text_generation
input: public-prompts.jsonl
model_revision: REQUIRED
input_tokens: 2048
max_output_tokens: 128
load:
  mode: controlled_concurrency
  concurrency: [1, 2, 4]
  requests_per_group: 200
acceptance:
  quality: REQUIRED
  ttft_p95_ms: DEFINE_BEFORE_TEST
  e2e_p99_ms: DEFINE_BEFORE_TEST
  error_rate: DEFINE_BEFORE_TEST
  memory_peak: DEFINE_BEFORE_TEST
```

This is a task template, not a running data. The performance threshold is determined and the threshold cannot be modified after measurement. Long input, long output, sudden and stable flow build workloads respectively.

## 2. Five capability layers

```text
Layer 1 — Hardware: device / driver / runtime / builds / communication
Layer 2 — Artifacts: architecture / format / numeric representation / template / verification
Layer 3 — Engines: loading / KV management / scheduling / kernels / APIs
Layer 4 — Performance: capacity / workloads / metrics / bottlenecks / experiments
Layer 5 — Delivery: environments / interfaces / monitoring / acceptance / rollback
```

|Interfaces between layers|Materials that must be delivered|
| --- | --- |
|Hardware→ artifact|Supported architecture, dtype/quantisation kernel, available capacity|
|Artifact → Engine|Complete model, list, tokenizer/template, quantization and processor configuration|
|Engine→ load testing|Final command, valid parameters, health/functionality/error results|
|Load testing → optimization|Data, resources, samples, failure samples, SLO gaps by request|
|Optimized→ Delivery|Parameters of acceptance testing, benefits and costs, known boundaries, restored inputs|

### 2.1 Find the relevant layer

|Issue|First layer to check|Evidence|
| --- | --- | --- |
|GPU visible but kernel failure|Layer 1|Arch, actual kernel, toolchain and the first error|
|tensor / shard / template error|Layer 2|List, index, GGUF metadata, tokenizer/template|
|No correctness, SSE/Error canceled|Layer 3|Primary response, end cause, API and engine log|
|OOM, TTFT/TPOT, concurrency is poor|Layer 4|memory segments, rows, each request, time and resources|
|Failure to rebuild after upgrading|Layer 5|Run combinations, digest, import paths, rollback records|

### 2.2 Engineering examples

[Matrix of GPU instances](engineering/README.md) Access to full adaptation and optimization records by specific device. Common mechanisms are developed in the five-layer main framework definitions, platform differences, commands and data in the original records of each device.

### 2.3 Skills extracted from on-device projects

The [General Performance Optimization and Testing Methodology](engineering/edge-llm-performance-methodology.md) keeps shared operations and test rules. The eight projects live in the [project index](engineering/projects/README.md), one document per project. Choose a project first, then review its recommended route, minimum procedure, test methods, representative results, and boundary.

Keep four cross-project boundaries: a model that loads is not automatically performant; multiple devices first address capacity or long prefill; independent replicas and RPC layer splitting are different scaling designs; speculation, P/D, and low-precision kernels all require complete-request, correctness, and resource acceptance.
