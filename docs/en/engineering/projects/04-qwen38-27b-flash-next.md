# Qwen3.8-27B and Flash-Next Deployment and Performance

[Project index](README.md) · [General methodology](../edge-llm-performance-methodology.md)

## 1. Two different models

| Item | 27B | Flash-Next |
| --- | --- | --- |
| Parameters | 27B class | About 176.94B MoE |
| Files | Q4 17.1 GB, Q8 29.0 GB | UD-Q4_K_XL about 104 GiB |
| Use | Single-device text | Large MoE |
| Default | Vulkan + MTP n=2 | Vulkan cooperative matrix + no-spec |

The two models cannot share performance conclusions.

## 2. Qwen3.8-27B

1. Pin Q4/Q8 weights, Vulkan/HIP, and context.
2. Use the embedded MTP head; do not attach another model's draft.
3. Sweep MTP `n-max` with 128/512 output.
4. Compare Q8 KV for long context.

Representative results:

- Q4 + Vulkan + MTP n=2: 20.90 tok/s fixed seed.
- Peak: 21.56 tok/s.
- 512-token output: 18.29 tok/s.
- n=1/2/3/4: 17.71/20.90/19.26/18.72 tok/s.
- 32K prompt with Q8 KV: 207.19 tok/s.

## 3. Flash-Next

1. Repair shader tooling and confirm `KHR_coopmat`.
2. Run same-binary cooperative-matrix ablation.
3. Use real sampling and fixed prompt/output.
4. Compare MTP3 with no-spec.
5. Validate P/D save, transfer, restore, and output consistency.
6. Stop at 2 GiB MemAvailable/SwapFree.

Representative results:

- 4K-prefix prefill: about 267.83 to 353.42 tok/s.
- TTFT: about 17.33 to 13.16 seconds.
- 128-token request: about 23.55 to 19.41 seconds.
- MTP3 decode +14.6%, but prefill slower and E2E almost unchanged.
- Four 8K requests: single 7.39, P/D 9.58, replicas 13.97 tok/s.

## 4. Boundary

- Build success is not a speedup.
- Integer-dot build did not show a stable gain.
- MTP decode gain may be cancelled by prefill.
- P/D helps a multi-request pipeline, not single-stream latency.
- Replicas outperform this P/D prototype on the same machines.

