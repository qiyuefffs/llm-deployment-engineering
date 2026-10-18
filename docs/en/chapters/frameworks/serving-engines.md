# Choosing a current inference engine

[简体中文](../../../01-deployment-foundations/chapters/frameworks/serving-engines.md) | **English**

[Contents](../../SUMMARY.md) · [Framework layer](../../02-capability-layers/03-inference-frameworks.md) · [Quantization](../models/quantization.md) · [PD](../performance/disaggregated-serving.md)

**Sources checked: 2026-10-18.** Exact support depends on the model, hardware, and engine version.

## 1. Match six parts of execution

```text
Architecture → weight format/quantization metadata → hardware/kernel
             → KV/state → scheduling/parallelism → API/parsers
```

“Supports Qwen” is insufficient: a family may include dense, MoE, hybrid attention, vision, audio, and MTP variants. Check the exact architecture, quantization, drafter, parsers, and inputs.

| Route | Evaluate for | Verify |
| --- | --- | --- |
| llama.cpp | GGUF, local inference, CPU/GPU offload, multiple backends | Architecture, placement, tensor types, slots, drafts |
| vLLM | Concurrent serving, batching, parallelism, speculation | Attention/linear/MoE backends, runner, version |
| SGLang | Prefix reuse, structured serving, PD/MoE | RadixAttention, scheduler, transfer, router |
| TensorRT-LLM | Integrated NVIDIA kernels, quantization, serving | GPU, backend, artifacts, container |
| MLX-LM/VLM | Apple text and vision | Version, formats, processors, cache |
| OpenVINO GenAI | Intel CPU/GPU/NPU | IR, plugins, shapes, coverage |

Fitting a model does not establish the best engine. Compare identical tasks, token accounting, resource budgets, and SLOs.

## 2. vLLM: revise V0 tuning habits

V1 enables chunked prefill by default where supported. It generally schedules decodes first, then prefills within the remaining token budget. `max-num-batched-tokens` is a per-step token limit; `max-num-seqs` is an active-sequence limit. Neither equals client concurrency.

```bash
vllm serve /srv/models/example-model \
  --served-model-name serving-lab \
  --host 127.0.0.1 --port 8000 \
  --max-model-len 8192 --max-num-seqs 8 \
  --max-num-batched-tokens 2048 \
  --enable-chunked-prefill --enable-prefix-caching \
  --gpu-memory-utilization 0.80
```

This parameter template requires a validated artifact. Sweep batched tokens 2048/4096/8192 with everything else fixed. A smaller budget may reduce decode interference; a larger one may finish prefill earlier. Measure mixed traffic.

Do not add `--enforce-eager` universally. It isolates graph/compilation issues but changes steady-state performance and conflicts with some newer features. Compare graphs, compilation time, and graph memory after ordinary generation works.

## 3. SGLang: separate caching, execution, and routing

RadixAttention manages reusable prefixes; batching schedules requests; kernels execute them; routers choose ordinary or PD instances.

In an officially prepared environment:

```bash
python -m sglang.launch_server \
  --model-path /srv/models/example-model \
  --host 127.0.0.1 --port 30000
```

Validate IDs, normal/streaming requests, and cancellation. Keep prefixes stable, change only the final question, and use a different-prefix control to separate caching from process warmup. Save this version's help rather than copying vLLM flags.

PD requires a compatible router and NIXL/Mooncake setup; see the [complete procedure](../performance/disaggregated-serving.md). Without phase-interference evidence, first tune chunks and queues.

## 4. TensorRT-LLM has more than offline engine builds

Older tutorials emphasize conversion, engine building, and executors. The current quick start also has `trtllm-serve` and a Python `LLM` API for supported HF/ModelOpt artifacts. Some backends still build engines offline.

Inside a matching official NVIDIA container:

```bash
trtllm-serve "TinyLlama/TinyLlama-1.1B-Chat-v1.0"
```

The guide also shows `nvidia/Qwen3-8B-FP8`. Check hardware/kernel support first. A simple entry point still has compilation, warmup, workspace, and graph costs.

NVFP4 on one engine versus BF16 on another compares deployment solutions, not engines alone. Use equivalent artifacts where possible and report each solution's quality.

## 5. llama.cpp speculation

Current documentation includes drafts, EAGLE-3, DFlash, DSpark, and n-gram routes, each with specific conversions and flags. `-md` supplies a file; `--spec-type` and model support define its role.

DSpark currently documents Qwen3-backbone runtime support. Conversion success alone does not prove another model can run. See the [Qwen3-4B procedure](../performance/dspark.md).

GGUF tensor formats do not imply equal CPU/CUDA/HIP/Vulkan/Metal efficiency. Check offloading, KV, graphs, and actual kernels.

## 6. Architecture changes the optimization

| Structure | Change | Check |
| --- | --- | --- |
| GQA/MQA | Fewer KV heads | KV budget and TP replication |
| MLA | Compressed state | Layout, attention, parallel support |
| Window/sparse attention | Selected history | Residency, index cost, long-context quality |
| Hybrid GDN/SSM | Recurrent state | Checkpoints, rollback, caches, speculation |
| MoE | Selected experts | Total weights, routing, EP/all-to-all |
| Multimodal | Processor/encoder work | Input budgets, caches, protocol |

Do not apply a pure-attention KV formula to all layers or force one unsupported attention backend.

## 7. Upgrade with a recoverable environment

Record device/driver, CPU architecture, image digest or wheels, PyTorch/runtime builds, extensions, commit, and local diff. Developer documentation may describe options absent from a stable package.

Before changing the default, pass loading, short prompts, maximum target input, SSE, cancellation, quality, three comparable performance rounds, and sustained operation. Diagnose against a known working combination.

## 8. Official sources

- [Pinned vLLM optimization](https://github.com/vllm-project/vllm/blob/2365177ddda7714502e4df7a1669cc79c0a4dfd0/docs/configuration/optimization.md).
- [SGLang](https://docs.sglang.ai/) · [source](https://github.com/sgl-project/sglang).
- [TensorRT-LLM quick start](https://nvidia.github.io/TensorRT-LLM/quick-start-guide.html).
- [Pinned llama.cpp speculation](https://github.com/ggml-org/llama.cpp/blob/5aeac37a35b44fde4bdffaec9159f2fcb253b622/docs/speculative.md).
