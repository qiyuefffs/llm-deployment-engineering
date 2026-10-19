---
id: T46
title: "vLLM ROCm 文本与多模态部署"
type: tutorial
volume: book
layer: 4
platform: "AMD"
device: "Ryzen AI MAX+ 395 / gfx1151"
status: historical
source_ids: [E25, E26, E27, E28, E29]
updated: 2026-10-19
summary: "Docker/原生环境准入、确定性图文负载、Flash 双路径对照、流式计时、并发阶梯及 W4A16 TP1/TP2 实验。"
---

# vLLM ROCm 文本与多模态部署

[项目索引](README.md) · [通用性能优化测试方法论](../edge-llm-performance-methodology.md)

## 1. 把三个实验问题分开

本项目包含两类 VLM 基准和一类大模型文本 TP 对照，不能合成一个“vLLM
支持全部模型”的结论。

| 实验 | 模型与任务 | 主要证据 | 不能替代的验收 |
| --- | --- | --- | --- |
| Qwen3-VL-4B | 固定单图 + prompt，Flash on/off，并发阶梯 | E27 | 多图、视频、长图文和长期服务 |
| DeepSeek-VL2-Tiny | 同类单图请求，保留 attention 失败组 | E28 | 失败的 Flash 组不能用于算加速比 |
| DeepSeek V4 W4A16 | 180B 剪枝量化衍生模型，文本 TP1/TP2 | E29 | 不是官方完整权重，也不是 VLM |

前期模型筛选发现 DeepSeek V4 公开架构是纯文本，不能进入 VLM 矩阵；后续
W4A16 测试使用的是另一套衍生制品和文本请求。模型名称接近，不代表制品、
输入模态或内存预算相同。

## 2. 环境准入和内存预算

记录平台为 Ryzen AI MAX+ 395 / Radeon 8060S / `gfx1151`，Ubuntu
24.04.4，宿主 ROCm 7.2.4，系统可见约 123 GiB，TTM/GTT 上限约
117.19 GiB。宿主驱动与容器用户态分别记录，不能只写一个 ROCm 版本。

```bash
./scripts/preflight.sh
python3 scripts/create_test_image.py
```

以上脚本来自原始工程，需在原工程根目录运行；本书仓库不包含整套模型服务。
预检输出 `reports/preflight.json`，检查设备节点、用户组、ROCm、容器能力、
磁盘、GTT/TTM 和当前可用内存。可运行容量取“空闲 GTT”和
“MemAvailable 减主机保留量”中的较小值，再与模型运行预算比较。

APU 上的少量 firmware VRAM 不代表只能使用这么大的模型。资源采样必须
联合读取 sysfs VRAM、GTT、主机已用量、进程树 RSS 和 swap；也不能把这些
数简单相加，它们可能描述重叠的统一内存分配。

## 3. Docker 与原生部署各自固定什么

### 3.1 Docker 路线

原工程使用官方 `vllm/vllm-openai-rocm` 镜像路线，镜像提供 PyTorch、Triton、
ROCm 用户态和 vLLM。正式复测应将 `${VLLM_IMAGE}` 设为实际核验的镜像标识，
公开文档省略内部仓库名和 digest。

```bash
VLLM_IMAGE="${VLLM_IMAGE}" \
./scripts/run_benchmark.sh \
  --runtime docker --model qwen3_vl_4b_instruct \
  --attention-modes flash_on,flash_off
```

原容器将 `/dev/kfd`、`/dev/dri` 传入，使用配套设备组与 host IPC，并挂载同一
模型缓存。检查点是容器内能识别目标 GPU、实际 vLLM/PyTorch/ROCm 版本
被保存，以及第一次真实生成完成。容器启动或 `/health` 成功都不足以覆盖
后续 JIT 和模型推理。

Qwen 路线保留 `--enforce-eager`、0.5 memory fraction 和 262144 pixels
视觉 profile 上限。大权重模型的默认 memory fraction 为 0.7，模型级参数
优先于全局默认值；但同一模型的 Flash 两组必须保持相同参数。

### 3.2 原生隔离环境

```bash
VLLM_COMMIT="${VLLM_COMMIT}" \
VLLM_ROCM_VARIANT=rocm721 \
./scripts/setup_native.sh
source .venv/bin/activate
./scripts/run_benchmark.sh \
  --runtime native --model deepseek_vl2_tiny \
  --attention-modes flash_on,flash_off
```

该路线使用 Python 3.12 独立环境和指定 ROCm wheel。原工程特别避免在现有
Python 3.13 中直接安装，以免选到 CUDA wheel。原生方案的安装说明不能当成
所有模型都已完成原生实测；最终运行时以各报告的 manifest 为准。

当前固定组合在 gfx1151 上保留 `--enforce-eager`，用于规避已观察到的
compile GPU hang。它是特定组合的处理措施，不是 ROCm 所有版本的永久要求。

## 4. 图文负载和 Flash 实验怎样控制变量

### 4.1 固定输入

工程生成确定性 PNG，包含三色条、形状、色块及测试文字。两组使用同一张图、
同一 prompt、`temperature=0`、相同输出上限、dtype、上下文、模型缓存和
memory fraction。每个 attention 模式重新启动服务，warm-up 保存但不进入
正式汇总；并发阶梯为 `1,2,4,8,16,32`，每档请求数为 `concurrency × 2`。

固定单图可控制视觉编码成本，但只能验收该图文负载。要判断视觉正确性，
还必须核对回答与色块、形状等输入内容相符，而非只检查是否返回字符串。

### 4.2 “开关”实际切换了两条路径

| 模式 | 语言 decoder | RDNA 视觉 encoder |
| --- | --- | --- |
| `flash_on` | `TRITON_ATTN` | `FLASH_ATTENTION_TRITON_AMD_ENABLE=TRUE` |
| `flash_off` | `ROCM_ATTN` | `FALSE`，视觉塔回退 SDPA |

所以这不是只改变一个 kernel 的严格消融。报告要同时保存请求的模式和
`observed_attention_backend`，再用 server log 确认实际后端。指定路径
启动失败时整组记失败；不能自动回退后继续称其为 Flash on。

DeepSeek-VL2 的上下文固定为 4096，使用其自己的模型配置。Qwen 的视觉
processor 参数不能直接复制给 DeepSeek；即使文本测试通过，也要继续验收
真正的 `image_url` 请求。

## 5. 流式计时、吞吐和失败怎样统计

流式 `/v1/chat/completions` 从发出请求计时，读取 SSE 到结束。VLM harness
将第一个非空 content 或 reasoning delta 作为首输出；E29 文本专项则按
首个实际文本 token 计时。两种口径不完全相同，不能不加说明合并 TTFT。

```text
TTFT = 首个有效输出时刻 - 请求发出时刻
E2E = SSE 结束时刻 - 请求发出时刻
generation tok/s = (completion_tokens - 1) / (SSE 结束 - 首输出)
total tok/s = completion_tokens / E2E
并发输出吞吐 = 该档成功请求 completion_tokens 总和 / 该档墙钟
```

Token 优先用服务 usage。若只能按空白估算，工程标记
`token_count_source=estimated_whitespace`，不与精确 token 行做严格速度比较。
失败请求保留状态、原因和原始响应，不填成 0 tok/s。

最高成功并发另带状态：下一档已失败才是 `failure_boundary`；最后配置档
仍成功则为 `capped`，表示尚未测到极限。不能把 `32` 写成模型理论上限。

## 6. Qwen3-VL 与 DeepSeek-VL2 的实测结果

### 6.1 Qwen3-VL-4B

以下来自 E27。并发 1 行使用 concurrency phase，单请求 single phase
单独列出，避免把两轮测量混在一行。

| 阶段/并发 | Flash on 输出 tok/s | Flash off 输出 tok/s | Flash on 单路生成中位数 tok/s |
| --- | ---: | ---: | ---: |
| single / 1 | 25.656894 | 25.505319 | 25.881433 |
| concurrency / 1 | 25.585026 | 25.484744 | 25.832171 |
| concurrency / 2 | 44.051211 | 47.720960 | 24.586784 |
| concurrency / 4 | 97.159187 | 94.875991 | 24.858482 |
| concurrency / 8 | 132.333114 | 135.277753 | 16.851132 |
| concurrency / 16 | 236.335069 | 249.670867 | 15.981138 |
| concurrency / 32 | 469.318514 | 477.816585 | 15.210449 |

吞吐增长的同时，单路生成速度下降。并发 32 的聚合输出约 469 tok/s
不表示每个用户都有这一速度。该档 Flash on 比 off 低约 1.78%，这组数据
支持的是“本负载下没有观察到聚合吞吐优势”，不能写成开启必然更快。

E27 的加载到就绪分别为 388.385509 s / 360.369322 s，GTT 峰值分别为
58.803665 GiB / 58.947617 GiB。加载口径包含进程到 health/models，
可能包含下载，不能用它替代引擎内部权重加载时间。

### 6.2 DeepSeek-VL2-Tiny

E28 中 flash_off 成功，single phase 的 TTFT P50 为 0.028754 s，单路
generation P50 为 130.793109 tok/s。并发 32 的聚合输出为
1545.089313 tok/s，而单路 generation P50 为 73.280183 tok/s。
两项分别描述总产出与单路体验，不能互换。

flash_on 的 single phase 为 3/3 请求失败，首档 concurrency 为 2/2 失败，
因此没有有效的 Flash 加速比。正确处理是保留失败行、回看错误响应和后端日志，
不将成功的 off 组与另一套模型的 on 组比较。

## 7. W4A16 TP1/TP2 文本专项

### 7.1 固定配置与有意保留的差异

E29 使用 180B W4A16 剪枝量化衍生制品，vLLM
`0.23.1rc1.dev1327+gf25953cc5`，BF16 计算、FP8 / `fp8_ds_mla` KV。
两组均 `--enforce-eager`、`--disable-custom-all-reduce`、4096 上下文、
`max_num_seqs=1`、`max_num_batched_tokens=2048`、关闭 prefix cache。

TP1 的 memory utilization 为 0.94，TP2 每节点为 0.75；双机使用 Ray +
Gloo，MLA Prefill 为 Torch SDPA 兼容回退。这是可运行配置之间的系统对照，
不是只改变 TP 数的单因素 kernel 消融。它也不是前面 VLM 的 Flash 专项。

### 7.2 请求矩阵与冷暖分组

六种场景每种三轮，共 18 个顺序正式请求。Decode 场景为 32-token 输入、
32/128-token 输出；Prefill 场景实际输入为 145、1041、2065、3505 tokens，
每次仅输出 3 tokens。R1 保留为新形状/JIT 冷态，主表用 R2/R3 中位数。

实际输入含模板等开销，因此“1K 场景”不是精确 1024-token 输入。
`effective_prompt_tps=prompt_tokens/TTFT` 包含调度和首 token 成本，
只能称有效 Prefill，不能当成纯引擎 pp 峰值。3-token 输出只有两个生成
间隔，其 Decode 不适合主对比。

### 7.3 加载与稳态结果

| 指标 | TP1 | TP2 | 解释 |
| --- | ---: | ---: | --- |
| 权重加载 | 208.03 s | 关键路径 103.61 s | 仅权重阶段约 2.01 倍 |
| 权重内存 | 97.77 GiB | 50.13 GiB/节点 | 总量不因此减半 |
| 日志规划 KV token 容量 | 25,196 | 89,932 | 不等于已测并发 |
| Decode-32 TTFT | 0.998 s | 0.583 s | HTTP 首文本口径 |
| Decode-32 E2E | 7.618 s | 7.146 s | 完整请求 |
| Decode-32 | 4.683 tok/s | 4.723 tok/s | 单路首 token 后 |
| Decode-128 | 4.524 tok/s | 4.693 tok/s | 单路首 token 后 |
| 1041-token 有效 Prefill | 291.1 tok/s | 335.6 tok/s | 输入/TTFT |
| 3505-token 有效 Prefill | 312.0 tok/s | 361.4 tok/s | 输入/TTFT |

双机主要改善权重加载、KV 余量、TTFT 和长输入处理；Decode 收益较小。
两组实际 `max_num_seqs=1`，不能根据 KV 规划器报告的容量声称已验证更多
并发。外部 health 就绪 301 s / 223 s 还包含不同初始化等待，不能套用
权重阶段的 2.01 倍到全服务启动。

### 7.4 JIT 与有限稳定性

单机 health-ready 到首个 4-token 验证请求结束约 82 s；双机也记录过一次
79.43 s warm-up。它们不进入稳态汇总，但必须保留为启动体验。原脚本因此
把真实生成 warm-up 纳入 ready 判定。

正式矩阵后单机追加 10 次顺序 Decode-32，成功 10/10，TTFT 中位数/P95
为 0.988/1.398 s，E2E 为 7.627/8.808 s，Decode 中位数 4.684 tok/s。
当时可用内存约 7.8 GiB，swap 已用 6.4 GiB。这是有限请求的稳定性观察，
不是长期 soak 或多用户验收。

## 8. 每轮需要保留的证据

| 文件 | 用途 |
| --- | --- |
| `manifest.json` | 启动参数、环境、模型与最终状态 |
| `inventory.json` | GPU、ROCm、内存和预检依据 |
| `raw_requests.csv` | warm-up、single、并发的逐请求时序与错误 |
| `summary.csv` | 同口径聚合，不掩盖失败和估算 token |
| `logs/*.log` | 实际 attention backend、JIT、加载、OOM 等 |
| `report.md` / 图表 | 从上述文件派生的阅读视图 |

可复用的完整方法是“模型与模态筛选 → 容量准入 → 固定图文输入 → 实际
后端核验 → 冷暖分组 → 并发吞吐与单路体验并看 → 失败边界”。TP 文本专项
则另建矩阵，避免把不同制品和输入模态混成一个数字。

来源：[E25](../../evidence/records/E25.md)、[E26](../../evidence/records/E26.md)、
[E27](../../evidence/records/E27.md)、[E28](../../evidence/records/E28.md)、
[E29](../../evidence/records/E29.md)。数据来源与边界见
[证据使用说明](../../meta/evidence-policy.md)。

