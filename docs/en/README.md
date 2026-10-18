# LLM Deployment Knowledge Base

[简体中文](../01-deployment-foundations/README.md) | **English**

![Five-layer LLM deployment framework](assets/framework.svg)

For LLM deployment, on-device inference, performance optimization, and service delivery. The material follows the six parts, five capability layers, and section numbers 1.1–5.3 of the original framework. General principles and selection criteria come first, followed by platform procedures and engineering examples.

**[Full contents](SUMMARY.md) · [Hardware examples](engineering/README.md) · [Environment and evidence conventions](00-preface.md) · [Standalone cases](../../cases/README.en.md) · [Repository home](../../README.en.md)**

## Hardware and compute software stacks

| Platform | How the hardware and software work together | Introduction |
| --- | --- | --- |
| NVIDIA | The GPU executes parallel computation; CUDA provides runtimes, tools, and compute libraries. | [GPUs, CUDA Runtime/Toolkit, cuBLAS, and NCCL](chapters/hardware/nvidia.md) |
| AMD | Radeon, Instinct, and integrated GPUs execute through ROCm/HIP or another supported backend. | [GPU architectures, ROCm, HIP, compute libraries, and RCCL](chapters/hardware/amd.md) |
| Mac | Apple Silicon shares physical memory. Metal exposes GPU computation; MLX provides machine learning operations on top. | [Unified memory, Metal, MLX, and MLX-LM](chapters/hardware/apple.md) |
| Intel | CPUs, GPUs, and NPUs use their corresponding toolchains, runtimes, and device plugins. | [oneAPI, SYCL, Level Zero, and OpenVINO](chapters/hardware/intel.md) |
| Ascend | AI accelerators execute through CANN and a compatible framework or serving engine. | [Hardware, runtimes, operators, HCCL, and framework plugins](chapters/hardware/ascend.md) |

Begin with [CPUs, GPUs, NPUs, memory, and software layers](02-capability-layers/01-hardware-backends.md), then choose a platform. CUDA and ROCm are compute software platforms; Metal is a GPU API; MLX is a machine learning framework. They occupy different layers and have different responsibilities.

## Engineering workflow

```text
Model selection → conversion/quantization → hardware backend setup
 → engine build and deployment → weights/KV/workspace budget
 → functional baseline → load testing → bottleneck analysis
 → controlled or combined optimization → API/monitoring → delivery/rollback
```

The knowledge base explains what each component is, why it matters, how to choose and use it, and how to assess its effects. Platform topics explain environment setup and commands; hardware examples preserve actual procedures and results. The learning sequence is hardware/software stacks → model artifacts → inference execution → performance bottlenecks → service delivery.

## 1. Knowledge framework

| Part | Entry point | Content |
| --- | --- | --- |
| Part I | [Overall knowledge map](01-knowledge-map.md) | Relationships between models, hardware, software stacks, and engines; the generation execution path |
| Part II | [Five capability layers](02-capability-layers/README.md) | Hardware, models, frameworks, performance, and delivery; detailed topics below |
| Part III | [Core concepts](03-core-concepts.md) | Ten mechanisms and their engineering implications |
| Part IV | [Project retrospective](04-project-review.md) | Ten records covering environment, deployment, troubleshooting, optimization, and acceptance |
| Part V | [Knowledge base organization](05-knowledge-base.md) | Eight topic directories and the organization of engineering materials |
| Part VI | [Troubleshooting reference](06-troubleshooting.md) | Locate failures by execution stage, verify causes, and run regression checks |

### Five layers and technical topics

| Layer | Focus | Detailed topics |
| --- | --- | --- |
| [1. Hardware and runtimes](02-capability-layers/01-hardware-backends.md) | CPUs/GPUs/NPUs, capacity, bandwidth, drivers, runtimes, and compute libraries | [NVIDIA](chapters/hardware/nvidia.md) / [AMD](chapters/hardware/amd.md) / [Intel](chapters/hardware/intel.md) / [Apple](chapters/hardware/apple.md) / [Ascend](chapters/hardware/ascend.md) |
| [2. Model formats and quantization](02-capability-layers/02-model-formats-quantization.md) | Artifact identity, HF/GGUF/IR, weight/activation/KV precision, and quality | [GGUF conversion](chapters/models/gguf-conversion.md) / [Quantization](chapters/models/quantization.md) / [Ollama](engineering/gguf-ollama.md) |
| [3. Inference frameworks](02-capability-layers/03-inference-frameworks.md) | Builds, loading, context, scheduling, and APIs | [vLLM](chapters/frameworks/vllm-service.md) / [llama.cpp](chapters/frameworks/llama-cpp.md) / [OpenVINO](chapters/frameworks/openvino.md) |
| [4. Memory and performance](02-capability-layers/04-memory-performance.md) | KV, prefill/decode, concurrency, latency, and throughput | [Benchmarking](chapters/performance/benchmarking.md) / [Caching and scheduling](chapters/performance/cache-scheduling.md) / [Parallelism](chapters/performance/parallelism.md) / [Speculative decoding](chapters/performance/speculative-decoding.md) |
| [5. Engineering delivery](02-capability-layers/05-engineering-delivery.md) | Environment packaging, APIs, monitoring, acceptance, and rollback | [Environment and operations](chapters/delivery/environment-operations.md) / [APIs and monitoring](chapters/delivery/api-monitoring.md) |

## 2. Hardware deployment and optimization examples

See the [example matrix](engineering/README.md) for full test conditions and evidence status. Each entry brings together deployment, parameter changes, measured results, and limitations for a platform.

| Platform | Example | Engineering focus |
| --- | --- | --- |
| NVIDIA | [RTX 2060](engineering/nvidia-rtx2060.md) | CUDA, quantized artifacts, and mixed CPU/GPU offloading |
| NVIDIA | [Dual RTX 4080 / A6000](engineering/nvidia-dual-gpu.md) | Tensor parallelism, PCIe, memory budgets, and serving parameters |
| NVIDIA | [GB10 text inference](engineering/nvidia-gb10.md) | ARM64 builds, FP8, AWQ, MTP, and DFlash |
| NVIDIA | [GB10 multimodal inference](engineering/nvidia-gb10-multimodal.md) | VL, Omni, Docling, and input budgets |
| AMD | [Radeon 780M](engineering/amd-780m.md) | Windows HIP, Ollama, fallback, and shared memory |
| AMD | [Radeon 8060S](engineering/amd-8060s.md) | Vulkan, Q4/BF16, CPU-to-GPU comparisons, and tuning |
| AMD | [Five-node Ryzen AI Max+ 395 RPC](engineering/amd-395-rpc.md) | HIP RPC, GTT/TTM, build distribution, and model splitting |
| AMD | [Multi-GPU and multi-node W7900](engineering/amd-w7900.md) | ROCm/RCCL, Ray, TP/PP, and communication troubleshooting |
| Intel | [Arc GPU / NPU](engineering/intel-arc-npu.md) | Vulkan/SYCL/IR comparisons, ASR/TTS, and device assignment |
| Apple | [M3 Ultra Metal](engineering/apple-metal.md) | GGUF, Metal builds, and artifact compatibility |
| Apple | [M3 Ultra MLX / oMLX](engineering/apple-mlx.md) | Templates, APC, vision, and concurrency |
| Ascend | [310P3](engineering/ascend-310p.md) | CANN, model plugins, FP16/TP2, and load testing |
| MUSA | [Adaptation and optimization procedure](engineering/musa.md) | Toolkit, builds, GPU offloading, and APIs; device tests pending |
| CPU | [Windows walkthrough](practice/first-service/README.md) | Fixed artifacts, complete service, functional/error/performance acceptance |

## 3. Commands, templates, and evidence

| Purpose | Entry point |
| --- | --- |
| Before execution | [Environment and evidence conventions](00-preface.md) |
| Command reference | [Common commands](appendices/commands.md) / [Benchmarking tools and complete commands](engineering/benchmark-tools.md) |
| Engineering records | [Adaptation template](templates/adaptation-record.md) / [Experiment template](templates/experiment-record.md) / [Retrospective template](templates/deployment-review.md) |
| Historical data | [Conditions and notes](evidence/README.md) / [Measurement JSON](../01-deployment-foundations/evidence/measurements.json) |
| Arithmetic checks | [Verification program](../01-deployment-foundations/examples/verify_records.py) / [Verification output](../01-deployment-foundations/examples/verified-output.txt) |
| Source traceability | [Article-to-chapter mapping](evidence/chapter-sources.md) / [Inventory of 50 technical records](../01-deployment-foundations/evidence/source-coverage.json) |
| References | [Official documentation and technical corrections](appendices/references.md) |

## 4. Directory layout and reading options

```text
docs/en/
├── README.md               English home
├── SUMMARY.md              Detailed contents
├── 00-preface.md            Environment and evidence conventions
├── 01-knowledge-map.md      Engineering knowledge map
├── 02-capability-layers/    Five capability layers
├── 03–06-*.md              Concepts, retrospectives, organization, troubleshooting
├── chapters/               Technical topics
├── engineering/            Complete hardware engineering records
├── practice/               Walkthrough documentation
├── templates/              Adaptation, experiment, and retrospective templates
├── evidence/               Source and measurement documentation
├── assets/                 English framework diagram
└── appendices/             Commands and references
```

Read the English edition on GitHub using this page and the [full contents](SUMMARY.md). Source code, data files, screenshots, and raw measurements are shared with the Chinese edition. Original Chinese prompts, expected answers, comments, and logs are retained where they are part of the reproducible inputs or evidence.

The downloadable [offline reader](../01-deployment-foundations/book.html) is currently the Chinese edition. Build instructions are available in [English](../../tools/README.en.md).

Standalone case tutorials, scripts, inputs, screenshots, and results are stored under [`cases/`](../../cases/README.en.md).

## Evidence status

The 50 technical records preserve public procedures, versions, parameters, logs, and test tables. Private paths, node addresses, and credentials have been sanitized. Historical GPU/NPU measurements retain their original conditions; failures and missing evidence remain explicit. MUSA has no measured device results yet. Read the [technical corrections](appendices/references.md) alongside the framework diagram.

Source edition updated: **2026-10-18**.
