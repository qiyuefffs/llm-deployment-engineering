# MiniMax-M2.7 Multi-Device Inference

[Project index](README.md) · [General methodology](../edge-llm-performance-methodology.md)

## 1. Applicable scenario

- About 228.69B parameters, UD-Q4_K_M four-shard GGUF.
- One device lacks capacity, so layer splitting across devices is required.
- Target is a local OpenAI-compatible service, not single-stream decode scaling.

## 2. Recommended route

```text
HIP/ROCm + llama.cpp RPC + USB4/Thunderbolt + layer split
```

The triple-device stage used a 30/35/35 split and 4K total context. The dual-device stage used 45/55, 8K total context, and five slots.

## 3. Minimum procedure

1. Verify all shards and node versions.
2. Check ROCm, GPU permissions, RPC ports, and direct-link routing.
3. Release old model processes and confirm memory cleanup.
4. Start HIP `rpc-server` on every worker.
5. Start `llama-server` with RPC, layer split, and tensor split.
6. Check health, models, completion, chat, and long output.
7. Record loading, worker transfer, host RSS, GPU/memory, and shutdown.

## 4. Performance method

| Test | Method |
| --- | --- |
| Loading | Start to health; per-worker transfer and host RSS |
| Engine | `llama-bench`, pp512, tg128, r=3 |
| API | Fixed prompt/output/sampling; prompt and generation tok/s |
| Multi-device | Confirm every worker participates |
| Concurrency | Record actual slots, not HTTP connections |

The triple benchmark used q8 KV, batch 512, ubatch 128, and layer 30/35/35.

## 5. Representative results

| Metric | Result |
| --- | ---: |
| Triple pp512 | 94.46 ± 1.16 tok/s |
| Triple tg128 | 17.06 ± 0.01 tok/s |
| Triple load | About 10:06 |
| Dual load | About 7 minutes |
| Dual chat prompt | 60.93 tok/s |
| Dual chat generation | 20.34 tok/s |
| Triple long-output decode | About 16.3-17.2 tok/s |

## 6. Problems and boundary

- One RPC stall came from inconsistent worker firmware.
- `8K context + 5 slots` means 8K total, not 8K per stream.
- Triple benchmark and dual chat are not the same measurement.
- No same-model single-device baseline, so no speedup ratio is claimed.

