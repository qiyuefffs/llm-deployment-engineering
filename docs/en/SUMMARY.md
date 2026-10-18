# LLM Deployment Knowledge Base: Contents

[简体中文](../01-deployment-foundations/SUMMARY.md) | **English**

This edition follows the original six parts, five capability layers, and section numbering. Start with hardware, runtimes, and model fundamentals, then move into engine execution, performance optimization, and service delivery. Platform procedures and complete engineering records show how these concepts apply to specific devices.

## Overview and entry points

- [Knowledge base home and framework diagram](README.md)
- [Environment and evidence conventions](00-preface.md)
- [Hardware deployment and optimization matrix](engineering/README.md)
- [CPU walkthrough: fixed artifacts, complete service, and actual acceptance results](practice/first-service/README.md)

## Part I: overall knowledge map

- [Models, hardware, software stacks, engines, and engineering modules](01-knowledge-map.md)

## Part II: five capability layers

- [Five-layer overview](02-capability-layers/README.md)
- [Layer 1: hardware, runtimes, and compute backends (1.1–1.4)](02-capability-layers/01-hardware-backends.md)
  - [NVIDIA: GPUs, CUDA, compute libraries, and deployment](chapters/hardware/nvidia.md)
    - [DGX Spark / GB10: current ARM64/UMA deployment](chapters/hardware/dgx-spark.md)
    - [RTX 2060: mixed offloading and quantized Qwen3 inference](engineering/nvidia-rtx2060.md)
    - [RTX 4080 / A6000: dual-GPU deployment and tuning](engineering/nvidia-dual-gpu.md)
    - [GB10: ARM64, FP8, AWQ, MTP, and DFlash](engineering/nvidia-gb10.md)
    - [GB10 multimodal: VL, Omni, and Docling](engineering/nvidia-gb10-multimodal.md)
  - [AMD: GPUs, ROCm, HIP, compute libraries, and deployment](chapters/hardware/amd.md)
    - [780M: Windows HIP and Ollama compatibility](engineering/amd-780m.md)
    - [8060S: Vulkan offloading and Q4/BF16 optimization](engineering/amd-8060s.md)
    - [Five-node 395: HIP RPC and GTT troubleshooting](engineering/amd-395-rpc.md)
    - [W7900: multi-GPU, Ray, and TP/PP](engineering/amd-w7900.md)
  - [Intel: hardware, oneAPI, OpenVINO, and deployment](chapters/hardware/intel.md)
    - [Arc/NPU: three GPU backends and complete ASR/TTS measurements](engineering/intel-arc-npu.md)
  - [Mac: unified memory, Metal, MLX, and deployment](chapters/hardware/apple.md)
    - [M3 Ultra: Metal builds and GGUF compatibility errors](engineering/apple-metal.md)
    - [M3 Ultra: MLX, APC, and oMLX concurrency](engineering/apple-mlx.md)
  - [Ascend: hardware, CANN, plugins, and testing](chapters/hardware/ascend.md)
    - [310P3: deployment, load testing, and failure records](engineering/ascend-310p.md)
  - [MUSA: deployment and optimization validation procedure](engineering/musa.md)
- [Layer 2: model formats and quantization (2.1–2.6)](02-capability-layers/02-model-formats-quantization.md)
  - [HF → GGUF → quantization: complete workflow](chapters/models/gguf-conversion.md)
  - [Quantization engineering: W/A/KV, calibration, deployment, and AWQ measurements](chapters/models/quantization.md)
  - [Model conversion and Ollama: complete technical records](engineering/gguf-ollama.md)
- [Layer 3: inference frameworks (3.1–3.6)](02-capability-layers/03-inference-frameworks.md)
  - [Current engines: vLLM V1, SGLang, TensorRT-LLM](chapters/frameworks/serving-engines.md)
  - [vLLM: complete service and multimodal input](chapters/frameworks/vllm-service.md)
  - [llama.cpp: build, loading, APIs, and shutdown](chapters/frameworks/llama-cpp.md)
  - [OpenVINO: IR, GPU/NPU, and speech pipelines](chapters/frameworks/openvino.md)
- [Layer 4: memory and performance optimization (4.1–4.6)](02-capability-layers/04-memory-performance.md)
  - [Benchmarking: workloads, metrics, and operating points](chapters/performance/benchmarking.md)
  - [KV, caching, and scheduling](chapters/performance/cache-scheduling.md)
  - [Multi-GPU and multi-node: capacity, communication, and benefits](chapters/performance/parallelism.md)
  - [Speculative decoding: MTP, DFlash, dynamic strategies, and measurements](chapters/performance/speculative-decoding.md)
  - [DSpark: complete local deployment and verification budgets](chapters/performance/dspark.md)
  - [PD, KV transfer, and MoE expert parallelism](chapters/performance/disaggregated-serving.md)
  - [Benchmarking tools and complete commands](engineering/benchmark-tools.md)
- [Layer 5: engineering delivery (5.1–5.3)](02-capability-layers/05-engineering-delivery.md)
  - [Environment packaging, start/stop, and rollback](chapters/delivery/environment-operations.md)
  - [APIs, monitoring, and acceptance](chapters/delivery/api-monitoring.md)

## Part III: core concepts

- [Ten core mechanisms: definitions, engineering implications, and parameters](03-core-concepts.md)

## Part IV: project retrospective

- [Ten project records and multi-hardware templates](04-project-review.md)
- [Adaptation record template](templates/adaptation-record.md)
- [Experiment record template](templates/experiment-record.md)

## Part V: knowledge base organization

- [Eight topic directories and engineering material organization](05-knowledge-base.md)

## Part VI: troubleshooting reference

- [Locate failures by stage and verify the fix](06-troubleshooting.md)

## Appendices and evidence

- [Appendix A: common commands](appendices/commands.md)
- [Appendix B: references and technical corrections](appendices/references.md)
- [October 2026 sources, snapshots, and validation](evidence/2026-10-refresh.md)
- [Article, example, and framework mapping](evidence/chapter-sources.md)
- [Historical test conditions and measurement notes](evidence/README.md)

The [source inventory](../01-deployment-foundations/evidence/source-coverage.json) lists 50 technical records and their code-fence counts. Hardware, models, parameters, and historical measurements retain their original conditions. Private information and credentials have been sanitized. MUSA remains marked as awaiting device tests.

The [offline reader](../01-deployment-foundations/book.html) is the **Chinese edition**. It supports the framework contents, full-text search, in-page navigation, and chapter navigation. Rebuild it from the repository root with `python tools/build_deployment_book.py`; see the [build instructions](../../tools/README.en.md).
