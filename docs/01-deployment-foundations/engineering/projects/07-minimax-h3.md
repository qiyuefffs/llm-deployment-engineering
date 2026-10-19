---
id: T47
title: "MiniMax-H3 视频/音频生成部署"
type: tutorial
volume: book
layer: 4
platform: "AMD"
device: "Radeon 8060S / gfx1151"
status: historical
source_ids: [E30]
updated: 2026-10-19
summary: "从 HIP/Vulkan 构建与组件校验，到小规格消融、阶段计时、GTT/RSS 采样和正式音视频内容验收。"
---

# MiniMax-H3 视频/音频生成部署

[项目索引](README.md) · [通用性能优化测试方法论](../edge-llm-performance-methodology.md)

## 1. 要验证的是完整音视频链路

项目在 2026-08-06 比较 stable-diffusion.cpp 的 HIP、Vulkan 与 ComfyUI。
同一次任务包含文本编码、扩散采样、音频 VAE、视频 VAE 和媒体输出；只看
采样器秒/步会遗漏 VAE 与装载开销。最终选用 HIP/ROCm +
`--diffusion-fa` + `--offload-to-cpu`。

原报告把它称为“无损最优”，其实际含义是在本轮没有开启跳步和近似缓存的
配置中耗时与内存较合适；没有逐像素/逐样本一致性实验，不能延伸为数值无损。

## 2. 固定源码、组件和构建

### 2.1 制品清单

| 组件 | 制品 | 大小 | 作用 |
| --- | --- | ---: | --- |
| DiT | `minimax_h3_fl2va_pruned-Q4_K_M.gguf` | 11,420,663,904 bytes | FL2VA pruned 扩散模型 |
| 文本编码器 | `qwen3vl_32b_minimax_h3-Q4_K_M.gguf` | 18,218,065,024 bytes | Qwen3-VL 32B |
| 视频 VAE | `minimax_h3_video_vae_fp16.safetensors` | 5,207,808,496 bytes | 视频解码 |
| 音频 VAE | `minimax_h3_audio_vae_fp32.safetensors` | 605,254,808 bytes | 音频解码 |

两个 GGUF 均按官方整文件 SHA-256 校验过。公开文档省略摘要值和本机目录，
复现时使用自己的下载 manifest，不能用文件名相同替代完整性检查。
VAE 复用已有文件，但音频和视频路径分别传入，不能互换。

源码为 stable-diffusion.cpp `c6beeef35526c6dc94b74a7fb69f9d2e6a2a7a12`，
ggml 为 `eced84c86f8b012c752c016f7fe789adea168e1e`。记录中因获取源码不稳定，
曾按 Git blob 校验 raw 文件，结果 189 个匹配、0 个不匹配；这只证明源码
快照一致，不证明模型输出质量。

### 2.2 独立构建目录和能力检查

| 构建 | 原记录中的关键项 | 验收点 |
| --- | --- | --- |
| HIP 基线 | `SD_HIPBLAS=ON`、`CMAKE_HIP_ARCHITECTURES=gfx1151`、`GGML_HIP_GRAPHS=ON`、`GGML_HIP_NO_VMM=ON`、`GGML_CUDA_FA=ON` | ROCm 7.2.4，gfx1151，wave 32 |
| HIP 基线 | `GGML_HIP_ROCWMMA_FATTN=OFF` | 与 rocWMMA 实验分开 |
| Vulkan | `SD_VULKAN=ON` | RADV GFX1151，UMA=1，KHR_coopmat |
| rocWMMA 实验 | 独立目录启用 `GGML_HIP_ROCWMMA_FATTN=ON` | 编译成功后继续实测 |

Vulkan 构建使用本地依赖，glslc 为 shaderc 2023.8，不能编译较新的 integer-dot /
bfloat16 shader。该结果只能代表当时可运行的 Vulkan 基线，不是所有 SDK
版本的性能上限。HIP 与 Vulkan 各自保留二进制和依赖，不混用。

测试前通过已有服务的 `/free` 卸载其他模型；ComfyUI 服务保持运行。本项目
资源比较的前提是没有另一套已加载大模型争用 UMA，不能仅看进程是否存在。

## 3. 先用小规格验证参数和媒体链路

### 3.1 固定兼容性负载

| 参数 | 实际值 |
| --- | --- |
| 分辨率 / 帧数 | 608×352 / 56 帧 |
| 帧率 / 步数 | 24 FPS / 4 步 |
| Sampler / scheduler | `res_multistep` / `simple` |
| Seed / RNG | 314159265 / CPU |
| CFG | 1.0 |
| 提示内容 | 桌面纸风车旋转、窗外树叶、镜头靠近，并包含环境声与立体声要求 |

原始完整 prompt 保存在 E30。它同时包含主体、运动、镜头和声音条件，适合
检查链路中是否有模态缺失。所有后端对照保持 prompt 与参数相同。

### 3.2 项目脚本的复现入口

```bash
./run_benchmark.sh \
  hip \
  hip_fa_offload_608x352_56f_4step_repeat \
  --diffusion-fa \
  --offload-to-cpu
```

这是原项目脚本的入口；它内部固定权重、VAE 和小规格参数。移植时先修改
本地路径和 GPU sysfs 节点，再运行，不能在本书目录直接调用。
需要核对脚本实际展开的命令，而不是只保留调用这一行。

原脚本的核心调用如下，路径改为需预先设置的变量，`PROMPT` 对应固定原文。

```bash
"${SD_CLI}" -M vid_gen --backend ROCm0 \
  --diffusion-model "${DIT}" --vae "${VIDEO_VAE}" \
  --audio-vae "${AUDIO_VAE}" --llm "${LLM}" \
  -p "${PROMPT}" --cfg-scale 1.0 -W 608 -H 352 \
  --video-frames 56 --fps 24 --steps 4 \
  --sampling-method res_multistep --scheduler simple \
  --seed 314159265 --rng cpu --output "${OUTPUT}" -v \
  --diffusion-fa --offload-to-cpu
```

检查点是四个组件均加载、采样正常结束、视频与音频解码均完成，以及 WebM
包含有效双轨。只保存首帧不能证明视频运动和音频正确。

## 4. 怎样采集时间和资源

脚本保存开始/结束时间、实际命令、退出码、完整 CLI 日志和媒体输出；
用 `/usr/bin/time -v` 记录最大 RSS，每秒读取目标 GPU 的
`mem_info_gtt_used`、`mem_info_vram_used`，输出独立 TSV，再取峰值。
单任务超时为 7200 s，退出后清理采样进程。

采集点分为文本编码、扩散采样、音频 VAE、视频 VAE、引擎生成总时间与外部
墙钟。各阶段相加不必严格等于墙钟，因为还有装载、媒体封装和其他开销。
sysfs 的 GB 采用十进制，进程 RSS 原记录为 KiB，不混用单位。

本轮对照按问题分组：HIP FA/no-FA 看注意力；HIP 常驻/offload 看容量代价；
HIP/Vulkan 看整套后端；rocWMMA、EasyCache、mmap、direct-conv 分别保留
负结果。不同后端可能使用不同内核，不能将全量差值归因给单个 kernel。

## 5. 小规格实验结果与取舍

以下均为 608×352、56 帧、4 步；时间单位 s，GTT 单位 GB。

| 配置 | 文本编码 | 采样 | 秒/步 | 音频 VAE | 视频 VAE | 总墙钟 | 峰值 GTT |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| ComfyUI | 未拆分 | 约 27.96 | 6.99 | 未拆分 | 未拆分 | 81.326 | 先前观察约 54.1 |
| HIP FA + offload | 2.83 | 55.72 | 13.93 | 6.89 | 30.63 | 97.30 | 19.58 |
| HIP no-FA + offload | 2.73 | 94.91 | 23.73 | 6.91 | 30.59 | 136.36 | 19.39 |
| HIP FA + 常驻 | 2.37 | 55.51 | 13.88 | 6.87 | 30.67 | 96.68 | 36.94 |
| Vulkan FA + offload | 4.87 | 66.85 | 16.71 | 1.00 | 42.06 | 116.03 | 43.33 |
| Vulkan no-FA + offload | 4.95 | 77.86 | 19.47 | 0.98 | 42.21 | 127.29 | 46.42 |
| HIP rocWMMA FA + offload | 2.82 | 56.31 | 14.08 | 6.94 | 31.56 | 98.88 | 19.59 |
| HIP FA + offload + EasyCache | 2.80 | 56.22 | 14.06 | 6.91 | 31.43 | 98.61 | 19.40 |
| HIP FA + offload + mmap | 3.00 | 56.13 | 14.03 | 6.90 | 31.38 | 98.85 | 19.60 |

FA 将 HIP 采样时间从 94.91 s 降到 55.72 s，耗时下降约 41.3%。这是
时间降幅，不能写成吞吐只增加 41.3%。常驻与 offload 的总墙钟几乎相同，
offload 峰值 GTT 从 36.94 GB 降到 19.58 GB，因此推荐这一容量折中。

小规格下 ComfyUI 更快，所以本轮小规格速度门槛没有通过。正式规格后来的
胜出不能倒过来抹掉这个负结果；小测试适合筛选路径，但不能预测大尺寸排序。

### 5.1 没有效果的优化也要留下

- EasyCache 明确打印 `completed without skipping steps`，不能宣称缓存命中。
- rocWMMA 构建和识别都成功，但采样 14.08 s/步略慢于基线 13.93 s/步。
- mmap 的最大 RSS 为 36,907,856 KiB，基线为 35,287,768 KiB，未改善本次预算。
- `--vae-conv-direct` 的视频 VAE 为 31.51 s，基线 30.63 s，没有收益。
- `--diffusion-conv-direct` 首步 15.30 s，与基线首步约 15 s 相近。

这些是当前负载的观察，缺重复误差条时不把细小差值写成稳定退化结论。
原报告说明 RDNA3/3.5 的 Q4_K 已自动走 MMQ；不能因为看到“强制某后端”
的选项就默认它比现有量化路径快。

## 6. 正式规格必须独立复测

正式任务与 ComfyUI 历史对照保持 864×480、141 帧、24 FPS、20 步、
`res_multistep`、`simple`、seed 314159265、CFG 1.0、CPU RNG，关闭
EasyCache/跳步，使用同一组模型组件与提示词。

| 阶段 | HIP FA + offload 实测 |
| --- | ---: |
| 文本编码 | 2.79 s |
| 20 步采样 | 2206.95 s |
| 平均每步 | 110.35 s |
| 音频 VAE | 39.08 s |
| 视频 VAE | 138.90 s |
| 引擎 generate_video | 2387.87 s |
| 外部总墙钟 | 2391.36 s，39 分 51.36 秒 |
| 峰值 GTT | 19,352,936,448 bytes，约 19.35 GB |
| 峰值 VRAM sysfs | 1,724,555,264 bytes |
| 最大进程 RSS | 36,539,572 KiB |

ComfyUI 对照总墙钟为 43 分 34.87 秒，采样约 122.56 s/步。正式规格下
sd.cpp 节省 3 分 43.51 秒，总墙钟降约 8.55%。对照为历史任务而非多轮
交替 A/B，仍缺长期重复统计；结果也远未达到五分钟生成目标。

## 7. 输出验收要覆盖容器、内容和音轨

推荐小规格输出实际为 Matroska/WebM，VP8，608×352，24 FPS，时长
2.291666748 s；音频为双声道 16-bit PCM，32000 Hz。
正式输出为 VP8、864×480、24 FPS，时长 5.833333496 s，同样含双声道音频。
不能按“帧数 / 帧率”的理想值替代媒体工具实际读出的时长。

正式任务按秒抽取七张不同 PNG，检查首帧、中间帧、末段帧的主体、运动、
结构稳定和镜头变化；左右声道均有有效信号。小规格 4 步只能确认链路，
存在噪点，不能替代正式质量。

本项目可迁移的方法是：用小规格筛掉不兼容路径，按阶段定位瓶颈，再按真实
规格复测排序；最后让性能表与可播放、可听的输出同时通过。暂未覆盖更长
视频、多用户服务、完整客观音视频质量评价和长期稳定性。

来源：[E30 完整报告](../../evidence/records/E30.md)。数据来源与边界见
[证据使用说明](../../meta/evidence-policy.md)。

