# MiniMax-H3 Video and Audio Deployment

[Project index](README.md) · [General methodology](../edge-llm-performance-methodology.md)

## 1. Model and route

- DiT: MiniMax-H3 FL2VA pruned Q4_K_M.
- Text encoder: Qwen3-VL 32B Q4_K_M.
- Separate video and audio VAE.
- Recommended: HIP/ROCm + `--diffusion-fa` + `--offload-to-cpu`.

## 2. Minimum procedure

1. Pin models, VAE, text encoder, source, and ggml commit.
2. Verify both GGUF files by SHA-256.
3. Release other model memory without restarting ComfyUI.
4. Smoke 608×352, 56 frames, 4 steps.
5. Check both video and audio.
6. Run the formal resolution/frame/step task.

## 3. Performance method

- Record text encoding, sampling, audio VAE, video VAE, wall time, GTT, and RSS.
- Compare HIP FA/no-FA, resident/offload, Vulkan, rocWMMA, EasyCache, and mmap.
- Use the same prompt, resolution, frames, steps, sampler, and seed as ComfyUI.
- Inspect container, codec, resolution, frame rate, duration, channels, and sample rate.
- Check first, middle, and late frames.

## 4. Representative results

| Configuration | Sampling s | s/step | Total s | Peak GTT GB |
| --- | ---: | ---: | ---: | ---: |
| ComfyUI | About 27.96 | 6.99 | 81.326 | About 54.1 |
| HIP FA + offload | 55.72 | 13.93 | 97.30 | 19.58 |
| HIP no-FA + offload | 94.91 | 23.73 | 136.36 | 19.39 |
| HIP FA + resident | 55.51 | 13.88 | 96.68 | 36.94 |
| Vulkan FA + offload | 66.85 | 16.71 | 116.03 | 43.33 |

The formal 864×480, 141-frame, 20-step task took about 39:51 versus about 43:35 for ComfyUI. Peak GTT was about 19.35 GB.

## 5. Findings

- HIP FA reduced sampling from 94.91 to 55.72 seconds.
- Offload added about 0.6% time while sharply reducing GTT.
- Vulkan was slower and used more memory.
- rocWMMA, default EasyCache, mmap, and direct-conv showed no clear gain.

## 6. Boundary

- Short smoke is only a chain check.
- The 4-step clip had visible noise and structural failure.
- Process success does not prove media correctness.
- The formal task remains far from a five-minute target.

