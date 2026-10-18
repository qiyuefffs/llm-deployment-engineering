# DGX Spark / GB10: ARM64, unified memory, and low precision

[简体中文](../../../01-deployment-foundations/chapters/hardware/dgx-spark.md) | **English**

[Contents](../../SUMMARY.md) · [CUDA](nvidia.md) · [GB10 records](../../engineering/nvidia-gb10.md) · [Quantization](../models/quantization.md)

**Sources checked: 2026-10-18.** Current procedures are reference material; performance remains tied to the historical records.

## 1. Capacity, bandwidth, and compute

DGX Spark combines GB10 Grace Blackwell, a 20-core Arm CPU, and 128 GB shared LPDDR5x memory. Official bandwidth is 273 GB/s. It supports desktop development and larger local models, with different bandwidth and concurrency limits from server HBM GPUs.

Advertised FP4 peaks assume specific precision and sparsity. Fitting weights, executing kernels, and meeting latency are separate results.

Teaching calculation: reading 20 GB of weights per step at 273 GB/s gives approximately 13.65 steps/s before all other costs. This ignores caching, MoE activation, KV, unpacking, and runtime overhead and is not a model speed prediction.

## 2. Inspect ARM64

```bash
uname -m
cat /etc/os-release
nvidia-smi
free -h
docker version
```

Match ARM64/aarch64 packages. x86_64 wheels, extensions, and images cannot be copied merely because both use CUDA. Check driver, image architecture, runtime/PyTorch builds, and extensions.

Prefer the exact official recipe and keep its model, image, precision, environment, parsers, and flags together.

## 3. Pin the official vLLM route

At review time, the single-Spark example uses `nvidia/Qwen3.8-27B-NVFP4` and `vllm/vllm-openai:qwen38`. Record the digest because tags can move:

```bash
mkdir -p records/spark
docker pull vllm/vllm-openai:qwen38
docker image inspect vllm/vllm-openai:qwen38 \
  --format '{{json .RepoDigests}}' > records/spark/image-digests.json
docker image inspect vllm/vllm-openai:qwen38 \
  --format '{{.Architecture}}' > records/spark/image-architecture.txt
```

Save the matching launch script from [official instructions](https://build.nvidia.com/spark/vllm/instructions) and the model revision before starting. Avoid mixing unrelated recipe settings.

Validate actual NVFP4 backends/fallback, readiness and model ID, short answers, reasoning/content separation, and tools. Start at c1 before c2/c4 and record lengths, TTFT, TPOT, and memory pressure. Add supported drafting only afterward; the Spark hardware name does not enable DSpark.

## 4. Unified memory accounting

The 128 GB includes OS, CPU programs, weights, KV, workspace, and graphs. Engine memory fraction is not a weight-only reservation. RSS and GPU counters can overlap.

Some queried GPU memory fields may be N/A. Record plain `nvidia-smi`, `free -h`, RSS, engine buffers, and swap. Sustained swapping can ruin latency despite apparent capacity.

Historical drop_caches commands address specific pressure; they are not a default startup optimization. Diagnose page cache, residency, and allocations first.

## 5. Precise architecture and kernel support

Blackwell branding does not make all SM100 kernels compatible with GB10. Inspect `torch.cuda.get_device_capability()` and actual kernel coverage; do not rewrite capability to disguise the GPU.

NVFP4/MXFP4/FP8 differ in values, scales, activations, and layout. Native low precision, W4A16 fallback, and BF16 are different solutions.

Old patches belong to their original commits. Evaluate a current matching image first; preserve necessary diffs and validate generation and quality before benchmarking.

## 6. Two-device evaluation

Two Sparks have separate memory, not one transparent 256 GB GPU. Validate both control-plane and collective traffic with the official multi-node recipe.

If a model fits one device, compare independent replicas against cross-node TP. Otherwise report capacity expansion and its latency cost. Advertised model sizes do not cover all precisions and context budgets.

Use [parallelism checks](../performance/parallelism.md) for per-rank memory, effective bandwidth, tokens, and latency tails.

## 7. Official sources

- [Hardware](https://docs.nvidia.com/dgx/dgx-spark/hardware.html).
- [Porting](https://docs.nvidia.com/dgx/dgx-spark-porting-guide/overview.html).
- [Recipe selection](https://build.nvidia.com/spark/vllm/choose-recipe) · [instructions](https://build.nvidia.com/spark/vllm/instructions).
