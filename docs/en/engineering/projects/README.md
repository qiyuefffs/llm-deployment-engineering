# On-Device Model Project Index

[General performance methodology](../edge-llm-performance-methodology.md) · [Hardware examples](../README.md)

These eight documents separate completed on-device projects. Each keeps the recommended route, minimum operating procedure, performance-test method, representative results, and boundary. Private paths, host details, credentials, and raw logs are excluded.

| Document | Recommended route | Representative result |
| --- | --- | --- |
| [MiniMax-M2.7](01-minimax-m27.md) | HIP/ROCm + llama.cpp RPC | Triple pp512 94.46 tok/s; dual real generation 20.34 tok/s |
| [DeepSeek V4 Flash](02-deepseek-v4-flash.md) | DwarfStar, Lucebox, or vLLM by target | Short single decode about 16 tok/s; Lucebox about 23 tok/s |
| [Qwen3.6-35B-A3B](03-qwen36-35b-a3b.md) | HIP replicas for concurrency | 72 fixed-context scenarios; replicas scale request capacity |
| [Qwen3.8-27B / Flash-Next](04-qwen38-27b-flash-next.md) | Vulkan and cooperative matrix | 27B about 20.9 tok/s; Flash-Next prefill +32% at 4K |
| [GLM-5.3-Flash](05-glm-53-flash.md) | BALANCED full GPU; HYBRID CPU MoE | 7.9K-131K decode about 14.1-8.6 tok/s |
| [vLLM ROCm](06-vllm-rocm.md) | Docker/native vLLM | Qwen3-VL concurrency-32 output about 469 tok/s |
| [MiniMax-H3](07-minimax-h3.md) | HIP + FA + offload | Formal task 39:51, about 3:43 faster than ComfyUI |
| [Qwen-Image 2.1](08-qwen-image-21.md) | sd.cpp HIP or MIOpen immediate mode | VAE decode 178.28 s to 1.87 s |

## Reading order

1. Confirm the applicable scenario and recommended route.
2. Complete device, artifact, health, and real-generation gates.
3. Repeat the project test method rather than copying another machine's value.
4. Read the boundary before using a performance number.

## Shared rules

- Pin model revision, shards, quantization, engine, backend, and context.
- Pass health, models, real generation, and integrity before performance.
- Record prefill, decode, TTFT, E2E, and throughput separately.
- Keep failures and unsupported combinations out of averages.
- Validate MTP, P/D, RPC, and low-precision kernels through complete requests.
- Public documents exclude internal addresses, private paths, credentials, and raw logs.

