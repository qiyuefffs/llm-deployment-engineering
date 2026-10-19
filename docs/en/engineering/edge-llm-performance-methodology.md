# General Performance Optimization and Testing Methodology

[中文](../../01-deployment-foundations/engineering/edge-llm-performance-methodology.md) | **English**

[Hardware examples](README.md) · [Project index](projects/README.md) · [Knowledge base home](../README.md)

Technical labels: `on-device / benchmark / ROCm / Vulkan / multimodal`

## 1. Scope

This page summarizes only on-device projects that were actually completed on the current devices. Each project has a separate document. This chapter keeps the reusable operating order, metric definitions, experiment rules, and acceptance gates.

Project documents:

1. [MiniMax-M2.7 multi-device inference](projects/01-minimax-m27.md)
2. [DeepSeek V4 Flash](projects/02-deepseek-v4-flash.md)
3. [Qwen3.6-35B-A3B](projects/03-qwen36-35b-a3b.md)
4. [Qwen3.8-27B and Flash-Next](projects/04-qwen38-27b-flash-next.md)
5. [GLM-5.3-Flash](projects/05-glm-53-flash.md)
6. [vLLM ROCm text and multimodal](projects/06-vllm-rocm.md)
7. [MiniMax-H3 video/audio](projects/07-minimax-h3.md)
8. [Qwen-Image 2.1](projects/08-qwen-image-21.md)

## 2. Operating order

```text
Task and SLO → environment admission → artifact verification → backend build
 → minimal service → single-request baseline → variable matrix
 → quality → resources → repeated statistics → operating point
 → delivery and rollback
```

### 2.1 Before testing

| Item | Must be fixed |
| --- | --- |
| Task | Text/image/video/audio; input, output, context, concurrency |
| Device | CPU, GPU architecture, unified memory, available memory, GTT/TTM |
| Software | Kernel, driver, ROCm/HIP, Vulkan/RADV, compiler, toolchain |
| Model | Revision, shards, quantization, tokenizer, template, processor, draft/VAE |
| Engine | Commit, build options, binary, device list, API alias |
| Workload | Input, output, sampling, seed, cache, warm-up, repeats |

### 2.2 Minimal service gates

1. Start with small context, one slot, short output, and cache off.
2. Check health, models, non-streaming, streaming, and shutdown.
3. Verify actual input/output tokens, stop reason, and complete content.
4. Confirm model, device, and backend identity.
5. Run performance tests only after the service path passes.

## 3. Metrics

| Metric | Collection | Use |
| --- | --- | --- |
| Prefill | Input tokens / prompt time, or engine pp | Long input and pre-first work |
| TTFT | Request start to first valid content token | First-response experience |
| Decode | Post-first tokens / duration, or engine tg | Sustained generation |
| TPOT | `(end - first) / (output_tokens - 1)` | Per-token generation cost |
| E2E | Request start to completion | Whole-request experience |
| Output throughput | Successful output tokens / wall time | Batch or concurrency output |
| Acceptance | Accepted drafts / drafted | MTP/DSpark |
| Resource peak | Device memory, GTT, RSS, swap, busy, temperature | OOM, paging, throttling |

Retain mean, standard deviation, P50, and P95; add P99 when sample size supports it. Separate cold start, warm-up, and steady state. Keep failures visible.

## 4. Workload matrix

| Workload | Example | Focus |
| --- | --- | --- |
| Short interaction | 1K input / 128-512 output | TTFT, decode |
| Standard Q&A | 4K input / 256-512 output | TPOT, E2E |
| Long text/RAG | 8K-16K input / short output | Prefill, KV |
| Very long context | 32K-250K input / short output | TTFT, peaks, correctness |
| Concurrency capacity | Fixed request, rising offered load | Aggregate throughput, slowest stream, P95 |
| Multi-device | Single, dual, triple | Capacity, prefill, decode, communication |
| Multimodal | Fixed image, resolution, frames, steps | Encoder, sampling, VAE, media quality |

Fixed-total-context tests must state per-request input; total context is not per-stream context.

## 5. Controlled comparison

1. Change only backend, quantization, context, concurrency, KV, MTP, or topology.
2. Build HIP and Vulkan separately and use the same model, input, and sampling.
3. Keep engine benchmark, server prefill, client decode, and HTTP E2E separate.
4. Disable cache by default; test cold, warm, and different-prefix groups separately.
5. Describe multi-variable changes as combined observations.
6. Treat compile success, reported device capability, and measured gain as separate gates.
7. Preserve failures, timeouts, and negative results.

## 6. Optimization decisions

| Optimization | Required checks |
| --- | --- |
| Quantization | File size, memory, quality, decode/prefill |
| FlashAttention | Same-binary on/off, TTFT, decode, resources |
| Cooperative matrix/integer dot | Device listing, correctness, same-workload A/B |
| MTP/DSpark | Acceptance, TTFT, decode, E2E, concurrency |
| Multi-device RPC | Single baseline, worker load, prefill, decode, recovery |
| Replicas | Active slots, queueing, slowest stream, tail latency |
| P/D | State correctness, transfer, single- and multi-request |
| CPU offload | Peak memory, total time, quality |

## 7. Acceptance and records

Each formal run should retain:

```text
environment / artifact-manifest / command / workload
requests / responses / resource / server-log / summary / acceptance
```

The conclusion states the recommended configuration, supported input/output and concurrency, quality, resource peak, failure boundary, unverified items, and rollback.

## Related reading

- [Project document index](projects/README.md)
- [Benchmarking](../chapters/performance/benchmarking.md)
- [Speculative decoding](../chapters/performance/speculative-decoding.md)
- [PD and MoE](../chapters/performance/disaggregated-serving.md)
- [Quantization](../chapters/models/quantization.md)
- [Hardware examples](README.md)

