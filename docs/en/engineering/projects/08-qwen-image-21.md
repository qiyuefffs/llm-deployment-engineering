# Qwen-Image 2.1 Image Generation Deployment

[Project index](README.md) · [General methodology](../edge-llm-performance-methodology.md)

## 1. Problem

- Qwen-Image 2.1 stalled in VAE decoding and reset the gfx1151 device.
- MIOpen Find performed exhaustive search for new convolution shapes.
- Trial launch could trigger `unspecified launch failure` and a GPU ring timeout.

## 2. Repair

1. Upgrade to a version with MIOpen immediate-mode support.
2. Temporarily set `MIOPEN_SEARCH_CUTOFF=1`, enable `torch.backends.miopen.immediate=True`, and disable `cudnn.benchmark`.
3. Do not set `MIOPEN_FIND_MODE` or `MIOPEN_FIND_ENFORCE`.
4. Use stable-diffusion.cpp HIP to bypass MIOpen VAE convolution.

## 3. Minimum procedure

1. Pin DiT, Turbo DiT, VAE, text encoder, and hashes.
2. Build HIP `sd-cli` and `sd-server`.
3. Smoke 512×512, 4 steps.
4. Test formal 1024×1024, 20 steps.
5. Test Turbo 1024/1536, 8 steps, CFG 1.
6. Start HTTP service and validate sync and async jobs.

## 4. MIOpen A/B

| Path | Searches | 512×512 VAE time |
| --- | ---: | ---: |
| Default Find | 20 | 178.28 s |
| Immediate mode | 0 | 1.87 s |

The repair reduced VAE decode by about 95.3×.

## 5. Representative performance

| Test | Text s | Sampling s | VAE s | Total s |
| --- | ---: | ---: | ---: | ---: |
| 512×512 / 4 steps | 1.74 | 9.65 | 1.58 | 12.98 |
| 1024×1024 / 20 steps | 0.86 | 194.79 | 5.20 | 200.88 |
| Turbo Q8 1024 / 8 steps | 0.84 | 39.87 | 5.17 | 45.90 |
| Turbo Q8 1536 / 8 steps | 0.86 | 115.01 | 11.73 | 127.64 |

Turbo Q8 was only about 2.3% slower than Q4_K_M with lower distortion.

## 6. Boundary

- A slow first run may come from backend search, not corrupted weights.
- Turbo requires fixed 8 steps and CFG 1.
- The 4-step CFG-6 image is only an API smoke.
- Image success still requires semantic, artifact, resolution, and repeatability checks.
- Current results do not cover every resolution, step count, or long-running service.

