# GLM-5.3-Flash Deployment and Performance

[Project index](README.md) · [General methodology](../edge-llm-performance-methodology.md)

## 1. Two quantization routes

| Item | BALANCED | HYBRID |
| --- | --- | --- |
| Size | About 71.8 GiB | About 98.3 GiB |
| Attention | Q3_K | ROCmFP4 |
| Experts | IQ1_M | IQ2_XXS |
| Draft | Q6_K | Q8_0 |
| Loading | Full GPU | `--n-cpu-moe 8` required |

## 2. Recommended route

- Use BALANCED as the normal single-device route.
- Use HYBRID only with CPU MoE offload.
- MTP default `n-max=4`; compare depth 4 and 6.
- Start at 64K context; use 131K for sweeps.

## 3. Minimum procedure

1. Pin model, shards, draft head, and runtime.
2. Confirm ROCmFP4 kernels and `glm5next`.
3. Load BALANCED full GPU.
4. Add `--n-cpu-moe 8` for HYBRID.
5. Sweep context with fresh prompts.
6. Record decode, prefill, acceptance, GTT, and output integrity.

## 4. Performance results

| Context | Decode tok/s | Prefill tok/s | MTP accept |
| ---: | ---: | ---: | ---: |
| 7.9K | 14.1 | 133.6 | 0.51 |
| 16.4K | 13.3 | 115.5 | 0.59 |
| 32.8K | 11.1 | 90.2 | 0.57 |
| 65.6K | 10.1 | 67.7 | 0.65 |
| 98.3K | 9.1 | 57.0 | 0.64 |
| 131.1K | 8.6 | 49.4 | 0.64 |

## 5. Quality

- Fixed execution-style code tasks repeated three times.
- BALANCED task median about 67; HYBRID about 73.
- Results vary substantially between repeated runs.
- Multithreaded code is a known weak area.

## 6. Boundary

- Loading near the driver limit does not prove stability.
- CPU MoE offload is a capacity method, not lossless acceleration.
- Long-context speed declines with filled context.
- One code-task profile does not represent all business quality.

