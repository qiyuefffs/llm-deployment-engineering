# vLLM ROCm Text and Multimodal Deployment

[Project index](README.md) · [General methodology](../edge-llm-performance-methodology.md)

## 1. Applicable scenario

- vLLM ROCm on Ryzen AI Max+ 395.
- OpenAI-compatible text or vision service.
- Qwen3-VL, DeepSeek-VL2, and W4A16 TP1/TP2 comparison.

## 2. Recommended route

- Use a pinned ROCm image or fixed native wheel.
- Keep `--enforce-eager` on gfx1151 for the tested compile-hang workaround.
- Fix Qwen3-VL vision profile and memory fraction.
- Pin DeepSeek-VL2 to 4096 context and disable AITER fused RoPE.
- W4A16 baseline uses BF16 compute, FP8 KV, and `max_num_seqs=1`.

## 3. Minimum procedure

1. Run preflight for ROCm, GTT/TTM, memory, container, and permissions.
2. Pass health, models, and real text generation.
3. Send a fixed image only after text passes.
4. Increase concurrency and keep failed requests.
5. Use the same request set for TP1/TP2.
6. Record TTFT, decode, output throughput, VRAM, GTT, RSS, and swap.

## 4. Qwen3-VL-4B results

| Concurrency | Flash on output tok/s | Flash off output tok/s |
| ---: | ---: | ---: |
| 1 | 25.66 | 25.51 |
| 4 | 97.16 | 94.88 |
| 16 | 236.34 | 249.67 |
| 32 | 469.32 | 477.82 |

At concurrency 32, Flash on/off differed by about -1.78%. The 32 level was a configured cap.

## 5. DeepSeek V4 W4A16

| Metric | TP1 | TP2 |
| --- | ---: | ---: |
| Weight load | 208.03 s | 103.61 s |
| Weight memory | 97.77 GiB | 50.13 GiB/node |
| KV tokens | 25,196 | 89,932 |
| 1K effective prefill | 291.1 | 335.6 tok/s |
| 3.5K effective prefill | 312.0 | 361.4 tok/s |
| Decode-32 | 4.683 | 4.723 tok/s |

TP2 mainly improves loading, TTFT, KV, and long-prompt prefill.

## 6. Boundary

- Framework support does not prove the current ROCm combination.
- Text success does not replace vision.
- Container startup does not replace quality acceptance.
- One image does not represent long multimodal or multi-user capacity.

