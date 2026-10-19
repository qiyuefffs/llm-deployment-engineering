---
id: T48
title: "Qwen-Image 2.1 图像生成部署"
type: tutorial
volume: book
layer: 4
platform: "AMD"
device: "Radeon 8060S / gfx1151"
status: historical
source_ids: [E31, E32]
updated: 2026-10-19
summary: "MIOpen 冷缓存 A/B、VAE 故障定位、HIP 构建、基础/Turbo 生成、量化取舍及异步 HTTP 验收。"
---

# Qwen-Image 2.1 图像生成部署

[项目索引](README.md) · [通用性能优化测试方法论](../edge-llm-performance-methodology.md)

## 1. 按失败阶段定位，而不是先改显存

原始故障发生在采样完成后的 VAE 解码阶段：GPU launch failure、驱动重启，
Linux 内核出现 `ring gfx_0.0.0 timeout`，Python 栈落在 Qwen-Image VAE 的
卷积和 `decode()`。现场曾调整 BIOS 显存划分和驱动超时，现象仍在。

关键日志链为：

```text
MIOpen(HIP): Error [EvaluateInvokers]
Error setting device 0: unspecified launch failure
at::cuda::miopen_convolution
autoencoder_kl_qwenimage21.py:decode
```

ROCm 的 PyTorch 也使用 `torch.cuda` 命名空间。旧版应用按 `cuda` 设备名
开启 `cudnn.benchmark`，会让 ROCm 走到 MIOpen 卷积搜索；因此不能因为栈里
写 `cuda` 就判断安装了 NVIDIA 后端。

本项目把“长时间停在 VAE”缩小为“首次形状的算法搜索”，再用同一 latent
做冷缓存 A/B。它复现了触发机制，没有故意在高分辨率持续运行到 GPU reset。
这是已有现场故障与本地复现的明确边界。

## 2. 固定环境和四类模型组件

| 项目 | 实测环境 |
| --- | --- |
| CPU / GPU | Ryzen AI MAX+ 395 / Radeon 8060S，gfx1151 |
| 内存 | 128 GB UMA；PyTorch 可见约 118 GiB |
| OS / Kernel | Ubuntu 24.04.4 / 7.0.0-38-generic |
| ROCm / HIP | 7.2.4 / 7.2.53211 |
| PyTorch / Diffusers | 2.10.0+rocm7.2.4 / 0.41.0 |
| stable-diffusion.cpp | `b13a48219d5cdf408edcb93da6cd69b612ed03d3` |
| ggml | `dc998771e700d49bbdf9a39cede22bb5b3311767` |

| 组件 | 文件 | 大小 |
| --- | --- | ---: |
| 基础 DiT Q8 | `qwen-image-2.1-Q8_0.gguf` | 7,640,860,384 bytes |
| Turbo DiT Q8 | `qwen-image-2.1-turbo-Q8_0.gguf` | 7,640,860,480 bytes |
| Turbo DiT Q4 | `qwen-image-2.1-turbo-Q4_K_M.gguf` | 4,199,565,120 bytes |
| BF16 VAE | `qwen_image_2.1_vae_bf16.safetensors` | 675,508,656 bytes |
| Qwen3-VL 8B 编码器 | `Qwen3-VL-8B-Instruct-UD-Q4_K_XL.gguf` | 5,148,699,488 bytes |

下载脚本对每个文件执行大小和整文件 SHA-256 校验。公开文档不保留内部
下载地址、用户目录和摘要值；本地复现用自己的 manifest。基础 DiT 和
Turbo DiT 体积相近但 checkpoint、采样 schedule 不同，不能互换名字使用。

## 3. MIOpen 问题怎样做有效 A/B

### 3.1 只测 VAE，避免混入扩散采样

使用实际 BF16 VAE 和同一个 512×512 latent，两组分别使用独立的冷缓存
目录。默认组 `miopen.immediate=False`、`cudnn.benchmark=True`、
`MIOPEN_SEARCH_CUTOFF=0`，开启 MIOpen logging；保护组切换到 immediate
路径与 cutoff=1。保存完整日志，计数 `exhaustiveSearch = 1`，同时记录
解码墙钟和输出是否有效。

| 路径 | exhaustive search 次数 | 512×512 解码 | 本地结果 |
| --- | ---: | ---: | --- |
| 默认 Find | 20 | 178.28 s | 完成，没有崩溃 |
| immediate | 0 | 1.87 s | 完成，没有崩溃 |

约 95.3 倍只适用于这次 VAE 冷缓存路径对比，不能写成整张图片生成加速
95.3 倍。两组都没有在该分辨率崩溃，因此该表也不能直接证明所有 GPU reset
都被本地复现过。

### 3.2 修复路径与确认方式

原工程优先升级到含 MIOpen immediate 修复的 Unsloth Studio；无法立即升级时，
使用保护启动脚本，在导入 PyTorch 时关闭 benchmark、打开 immediate。

```bash
unset MIOPEN_FIND_MODE
unset MIOPEN_FIND_ENFORCE
./scripts/start_unsloth_rocm.sh -H 0.0.0.0 -p 8888
```

该脚本设置 `MIOPEN_SEARCH_CUTOFF=1`，通过 `integrations/sitecustomize.py`
启用 `torch.backends.miopen.immediate=True`、
`torch.backends.cudnn.benchmark=False`。只设置 cutoff 而未确认应用实际
执行路径，不足以宣称修复完成。

原项目的确认命令为：

```bash
python - <<'PY'
import torch
print(torch.version.hip)
print(torch.backends.miopen.immediate)
PY
```

需在应用实际使用的环境执行，确认 HIP 版本和 immediate 为 True，再跑新
分辨率解码并检查搜索日志与内核错误。原记录中保护路径的 512×512 和
1024×1024 VAE 均完成，未出现 reset；不外推到所有形状。

## 4. 独立的 stable-diffusion.cpp HIP 路线

这条路径用 ggml/ROCm kernel 完成推理，绕开 PyTorch MIOpen 卷积。它既是
部署方案，也提供了与应用层修复相互独立的排障参照。

### 4.1 下载和编译

```bash
./scripts/download_qwen_image_2_1.sh
./scripts/build_sdcpp_hip.sh
./build-hip/bin/sd-cli --list-devices
```

脚本在原项目运行，默认每文件 16 路下载、支持续传，校验成功才使用最终文件。
遇到 429 时原工程将 `ARIA2_CONNECTIONS=8` 后重试；下载限流不能误判为
模型格式损坏。检查点是 `ROCm0` / gfx1151 和 CLI、server 均已生成。

构建脚本的主要配置为：

```text
Release / Ninja
SD_HIPBLAS=ON
GPU_TARGETS=gfx1151
AMDGPU_TARGETS=gfx1151
CMAKE_BUILD_WITH_INSTALL_RPATH=ON
CMAKE_POSITION_INDEPENDENT_CODE=ON
GGML_HIP_GRAPHS=ON
GGML_HIP_NO_VMM=ON
GGML_CUDA_FA=ON
targets: sd-cli sd-server
```

### 4.2 分开运行基础与 Turbo

基础脚本默认 1024×1024、20 步、CFG 6.0、Euler。Turbo 则必须配套
8 步、CFG 1.0 和 `qwen-image-2.1-turbo` sigma schedule。

```bash
./scripts/generate_qwen_image.sh
./scripts/generate_qwen_turbo.sh
WIDTH=1536 HEIGHT=1536 OUTPUT=output/turbo-1536.png \
  ./scripts/generate_qwen_turbo.sh
```

Turbo 脚本实际使用 Q8 DiT、BF16 VAE、Q4_K_XL 编码器，固定 seed 42，
保留 `--flash-attn off,diffusion=on` 与 `--offload-to-cpu`。这些是该
版本的语法；不能把另一个 sd.cpp 版本的 `--diffusion-fa` 机械搬过来。

固定 prompt、negative prompt 和 seed 后比较量化。若同时换基础 checkpoint、
Turbo、步数和 CFG，得到的是整套方案的变化，不能把收益归因给 Q8 或 Q4。

## 5. 阶段计时和实际结果

下表分别保留工程 README 的首次正式运行与后续部署文档的基础模型复跑。
它们不是互相覆盖的数据，也没有足够重复次数形成误差统计。

| 运行 | 分辨率 / 步数 | 编码 s | 采样 s | VAE s | 总耗时 s |
| --- | --- | ---: | ---: | ---: | ---: |
| CLI smoke | 512×512 / 4 | 1.74 | 9.65 | 1.58 | 12.98 |
| 基础 Q8 首次正式 | 1024×1024 / 20 | 0.86 | 194.79 | 5.20 | 200.88 |
| 基础 Q8 复跑 | 1024×1024 / 20 | 1.82 | 194.86 | 5.22 | 201.91 |
| Turbo Q4 | 1024×1024 / 8 | 0.82 | 38.89 | 5.16 | 44.88 |
| Turbo Q8 | 1024×1024 / 8 | 0.84 | 39.87 | 5.17 | 45.90 |
| Turbo Q8 | 1536×1536 / 8 | 0.86 | 115.01 | 11.73 | 127.64 |

基础复跑到 Turbo Q8 的约 4.4 倍是整套 checkpoint/schedule/参数变化。
512×512 的 VAE 冷缓存 A/B 与这里 ggml 路线的 VAE 计时也不是同一后端，
不能串成一个连续优化倍率。

基础模型 1536×1536、40 步只记录了首步约 29.44 s；“约 20 分钟”是
外推估计，不是完整生成实测。它不进入正式对照表。

### 5.1 为什么默认选择 Turbo Q8

本机 Turbo Q8 的总耗时 45.90 s，Q4 为 44.88 s，时间代价约 2.3%。
模型卡给出的 LPIPS 为 Q8 0.036、Q4 0.153；这些质量值是上游报告，
不是本机重新计算的结果。项目据此选择 Q8，但不能宣称完成了本地 LPIPS
质量基准，更不能只凭该数断言所有提示词都同样改善。

本地还检查了相同 prompt/seed 的图像，1536 输出为 PNG RGBA，主体、
纹理与细节有效。这是具体样本的视觉验收，不是全量语义和审美测试。

## 6. HTTP 验收要完成整个异步任务

```bash
./scripts/start_sd_server.sh
curl -s http://127.0.0.1:18092/v1/models
curl -s http://127.0.0.1:18092/sdcpp/v1/capabilities
curl -s http://127.0.0.1:18092/sdcpp/v1/img_gen \
  -H 'Content-Type: application/json' \
  -d '{
    "prompt":"a blue ceramic cup on a wooden table",
    "width":512,"height":512,"seed":42,"output_format":"png"
  }'
```

该服务默认加载 Turbo Q8，使用配套 8 步、CFG 1 和 sigma schedule。
收到 job 后按响应的 `poll_url` 继续查询，直至成功或失败；再检查返回图像
存在、可解码、分辨率正确、内容匹配。返回 job ID 只代表任务已受理。

原服务提供 `/v1/images/generations` 兼容接口与 `/sdcpp/v1/img_gen`
异步接口。当前明确验收的证据重点是 models、capabilities 和异步生成；
不能把接口存在直接写成所有兼容客户端均已通过。

## 7. 故障复核和回归顺序

| 现象 | 先查什么 | 本项目依据 |
| --- | --- | --- |
| 采样结束后长期停顿 | `exhaustiveSearch`、`EvaluateInvokers` | MIOpen 冷缓存搜索 A/B |
| launch failure / ring timeout | VAE 栈、内核日志、实际 immediate 状态 | 现场故障 + 本地机制复现 |
| 4 步图模糊 | checkpoint、步数、CFG、schedule | 连通性 smoke 不代表正式质量 |
| Turbo 输出异常 | 是否仍用了基础模型 CFG/sigmas | Turbo 固定 8 步 / CFG 1 |
| 下载 429 | 总连接数、续传和校验结果 | 减少并发，不删除已校验文件 |
| HTTP 返回 job 但无图 | job 终态与错误内容 | 完成任务后再做功能验收 |

回归按“VAE 单组件 → CLI 小图 → 正式分辨率 → HTTP job → 内核日志”
推进。修复 VAE 后仍要跑完整采样，因为一个组件快不代表端到端质量或服务
稳定性已经合格。

## 8. 通用方法与未覆盖范围

这次排障的关键是把失败位置从“整个模型”缩到“后端算法搜索”，用同 latent、
独立冷缓存和搜索次数验证机制，再分别选择应用修复与独立 ggml 路线。
性能优化则把 VAE 修复、Turbo 方案和量化取舍分别统计，避免连乘不可比倍率。

原项目没有给出完整多次重复、并发容量、所有分辨率或长期 soak 的记录；
本轮也没有重新启动服务。公开文档去掉现场身份、地址和内部交付信息，保留
可复用的参数、失败栈、测量方法与验收过程。

来源：[E31 工程 README](../../evidence/records/E31.md)、
[E32 复现与部署报告](../../evidence/records/E32.md)。数据来源与边界见
[证据使用说明](../../meta/evidence-policy.md)。

