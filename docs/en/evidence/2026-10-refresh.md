# October 2026 deployment and inference update

[简体中文](../../01-deployment-foundations/evidence/2026-10-refresh.md) | **English**

[Home](../README.md) · [Contents](../SUMMARY.md) · [References](../appendices/references.md)

**Sources checked: 2026-10-18.** The original six parts and five layers remain the organizing framework. Historical measurements retain their original hardware, versions, workload, and limitations.

## 1. Updated topics

| Layer | Topic | Engineering content |
| --- | --- | --- |
| Hardware | [DGX Spark](../chapters/hardware/dgx-spark.md) | ARM64, UMA, bandwidth, image digests, kernels |
| Models | [Quantization](../chapters/models/quantization.md) | W/A/KV, maintained tools, GPTQ, NVFP4/MXFP4, calibration |
| Engines | [Current selection](../chapters/frameworks/serving-engines.md) | vLLM V1, SGLang, TensorRT-LLM, llama.cpp |
| Performance | [MTP](../chapters/performance/speculative-decoding.md) | Native/assistant paths, dynamic K, draft heads |
| Performance | [DSpark](../chapters/performance/dspark.md) | Block drafting, confidence, local procedure, budgets |
| Performance | [PD/MoE](../chapters/performance/disaggregated-serving.md) | KV transfer, routers, NIXL/Mooncake, EP |
| Delivery | [Caching](../chapters/performance/cache-scheduling.md) / [Benchmarks](../chapters/performance/benchmarking.md) | Cache states, reproducible matrices, SLO accounting |

## 2. Corrections to older guidance

DSpark is an algorithm, DGX Spark hardware. AutoAWQ deprecation concerns a library, not the AWQ method. MTP inference requires published modules and engine support. Fixed K, batch-dependent K, and confidence/cost budgets are different policies.

Native FP4, W4A16 fallback, and FP4 artifact loading are different results. KV quantization, prefix reuse, offloading, and inter-instance transfer need separate experiments. Speculation preserves the selected target distribution when its implementation guarantees apply; it does not remove quantization error.

Compare PD, EP, and multiple GPUs with equal resources, tasks, and SLOs.

## 3. Pinned source snapshots

| Project | Commit | Scope |
| --- | --- | --- |
| llama.cpp | `5aeac37a35b44fde4bdffaec9159f2fcb253b622` | Conversion, speculation, flags |
| vLLM | `2365177ddda7714502e4df7a1669cc79c0a4dfd0` | MTP, verification, quantization, scheduling, CLI |
| DeepSpec | `005e03b81cec38b7da6399833d609ee89a2587f2` | Paired drafts, training, evaluation, resources |
| LLM Compressor | `f15ac1d2243c3fd60cd745cf4e735e2814142d76` | GPTQ/oneshot/export APIs |

These are source snapshots, not a declaration of the latest stable releases. Developer docs, stable docs, and installed wheels can differ. Record actual versions plus model revisions, recipe contents, and container digests.

The shared [source manifest](../../01-deployment-foundations/evidence/2026-10-sources.json) contains downloaded source URLs and SHA256 hashes. It identifies documentation, not GPU measurements. Detailed source links and limitations are also recorded in each topic.

## 4. Official reading list

- [DeepSpec](https://github.com/deepseek-ai/DeepSpec/tree/005e03b81cec38b7da6399833d609ee89a2587f2) and [DSpark paper](https://arxiv.org/abs/2607.05147): preserve training mode and task distribution.
- [llama.cpp](https://github.com/ggml-org/llama.cpp/blob/5aeac37a35b44fde4bdffaec9159f2fcb253b622/docs/speculative.md): conversion does not establish every backbone's runtime support.
- [vLLM MTP](https://github.com/vllm-project/vllm/blob/2365177ddda7714502e4df7a1669cc79c0a4dfd0/docs/features/speculative_decoding/mtp.md), [adaptive verification](https://github.com/vllm-project/vllm/blob/2365177ddda7714502e4df7a1669cc79c0a4dfd0/docs/features/speculative_decoding/adaptive_verification.md), and [Dynamic SD](https://github.com/vllm-project/vllm/blob/2365177ddda7714502e4df7a1669cc79c0a4dfd0/docs/features/speculative_decoding/dynamic_speculative_decoding.md): check exact runner, graphs, and parallel support.
- [Scheme selection](https://docs.vllm.ai/projects/llm-compressor/en/latest/steps/choosing-scheme/), [AutoAWQ deprecation](https://docs.vllm.ai/en/latest/features/quantization/auto_awq/), and [GPTQ example](https://github.com/vllm-project/llm-compressor/blob/f15ac1d2243c3fd60cd745cf4e735e2814142d76/examples/quantization_w4a16/llama3_example.py): methods, numerical schemes, and artifacts occupy different categories.
- [ModelOpt](https://github.com/vllm-project/vllm/blob/2365177ddda7714502e4df7a1669cc79c0a4dfd0/docs/features/quantization/modelopt.md), [KV quantization](https://github.com/vllm-project/vllm/blob/2365177ddda7714502e4df7a1669cc79c0a4dfd0/docs/features/quantization/quantized_kvcache.md), and [optimization](https://github.com/vllm-project/vllm/blob/2365177ddda7714502e4df7a1669cc79c0a4dfd0/docs/configuration/optimization.md): verify actual kernels, scales, and scheduling.
- [SGLang PD](https://docs.sglang.ai/advanced_features/pd_disaggregation.html) and [TensorRT-LLM quick start](https://nvidia.github.io/TensorRT-LLM/quick-start-guide.html): use matching complete environments.
- [Spark hardware](https://docs.nvidia.com/dgx/dgx-spark/hardware.html) and [recipes](https://build.nvidia.com/spark/vllm/choose-recipe): specifications and advertised peaks are not measurements.

## 5. Validation status

Historical artifacts and CPU outputs keep their identities. New GPU configurations are reference procedures without new local GPU results. The benchmark script defaults to plan_only and sends requests only with execute.

Local link, Python/JSON, HTML, and plan checks do not replace device quality/performance acceptance. Add new device results with complete environment, inputs, sampling, cache state, outputs, and logs. This review date is not the historical measurement date.
