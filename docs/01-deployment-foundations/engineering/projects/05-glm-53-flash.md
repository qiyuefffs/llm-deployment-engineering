---
id: T45
title: "GLM-5.3-Flash 部署与推理性能优化"
type: tutorial
volume: book
layer: 4
platform: "AMD"
device: "Strix Halo / gfx1151"
status: historical
source_ids: [E23, E24]
updated: 2026-10-19
summary: "依据随制品说明整理混合量化、引擎准入、MTP 上下文 sweep 和可执行质量验收，区分作者报告与本机未验证项。"
---

# GLM-5.3-Flash 部署与推理性能优化

[项目索引](README.md) · [通用性能优化测试方法论](../edge-llm-performance-methodology.md)

## 1. 当前掌握的材料与项目状态

本项目目录保存了 BALANCED / HYBRID 两份模型说明和下载进度材料。本轮没有
找到本机独立的 server 日志、请求级结果和质量执行记录。因此下文的速度、
质量分数和驱动故障都明确标为**制品作者报告**，不能计入个人已完成实测成果。

这两份说明仍能支撑具体的制品识别、引擎选择、启动参数和复测方法。它们回答
的是“怎样按已有记录搭建并验证”，不是“本机已经复现全部结果”。

## 2. 两种混合量化为什么要分开管理

| 组件 | BALANCED | HYBRID | 实际核对对象 |
| --- | --- | --- | --- |
| 文件与分片 | 71.8 GiB，单文件 | 98.3 GiB，5 分片 | 模型入口、全部分片、量化元数据 |
| Attention / indexer | Q3_K | `Q4_0_ROCMFP4_FAST` | 不是全模型统一 FP4 |
| MoE experts | IQ1_M，使用 imatrix | IQ2_XXS，使用 imatrix | 专家占权重主体 |
| MTP draft head | Q6_K，`blk.45` | Q8_0，`blk.45` | draft head 精度随制品变化 |
| Router / norms | FP32 | FP32 | 混合配方中的保留精度 |
| 作者加载配置 | 全 GPU | `--n-cpu-moe 8` | HYBRID 的 CPU 路径影响性能 |

不能把“ROCmFP4”当成所有张量的统一位宽，也不能仅凭文件名判断所需后端。
两份说明写明测试构建启用了 `GGML_VULKAN=ON`；格式名称里带 ROCm，不等于
这里已经验证过 HIP 构建。模型架构支持和量化类型支持是两个独立准入条件。

## 3. 引擎准入：先看架构，再看量化类型

E23/E24 指定的旧路线为 `guevae2/ROCmFPX` 的 `glm5next` 分支，提交
`3345156`；BALANCED 新版说明改用 `paoai-strix-engine` 的 `strix-main`，
提交 `4a8440f58`。新版上下文表来自后者，旧版 depth 对照来自前者，不能混算。

| 启动失败 | 说明中对应的组合 | 处理判断 |
| --- | --- | --- |
| `unknown model architecture: 'glm5next'` | stock llama.cpp | 架构尚未被该树识别 |
| `invalid ggml type 101. should be in [0, 43)` | 仅带 glm5next 的另一分支 | 架构识别了，但缺量化类型 |

这两种报错发生在真正推理之前，不应先调整 batch、上下文或 MTP。先确认二进制
来自配套源码树，并保存实际 revision、编译配置与设备枚举。说明没有提供完整
可复核的本机编译命令，本章不补造一套已执行构建过程。

## 4. 按来源保留的服务参数

下面是模型说明提供的运行命令，本轮未在本机执行。相对文件名应从模型所在
目录解析，服务参数仅适用于该说明匹配的引擎版本。

### 4.1 BALANCED

```bash
llama-server -m GLM-5.3-Flash-PaoAI-ROCmFP4-STRIX-BALANCED.gguf \
  --host 0.0.0.0 --port 8080 -ngl 999 -c 65536 --parallel 1 \
  --spec-type draft-mtp --spec-draft-n-max 4 \
  -fa on --cache-type-k q8_0 --cache-type-v q8_0 --lazy-mode off
```

检查点依次是架构和类型识别、模型完整加载、实际后端、上下文和单槽位、
q8_0 KV、MTP head 加载，最后才是真实输出。MTP 的 `n-max=4` 是草稿深度，
不是并发 4，也不是每轮必然接受 4 个 token。

### 4.2 HYBRID

```bash
llama-server -m GLM-5.3-Flash-PaoAI-ROCmFP4-STRIX-HYBRID-00001-of-00005.gguf \
  --host 0.0.0.0 --port 8080 -ngl 999 --n-cpu-moe 8 \
  -c 65536 --parallel 1 --spec-type draft-mtp --spec-draft-n-max 4 \
  -fa on --cache-type-k q8_0 --cache-type-v q8_0 --lazy-mode off
```

作者报告全 GPU 的大块 Vulkan 分配会使驱动进入不可终止的 D 状态，复现过三次；
因此 HYBRID 命令要求保留 `--n-cpu-moe 8`。该标志将部分层的专家留在 CPU，
是容量和驱动分配约束的处理方式，不能宣传为免费加速。

约 98 GB 的故障描述来自特定驱动与分配组合，不是所有 gfx1151 的统一硬件
上限。也不能拿文件 GiB 数和 GPU 分配 GB 数直接相减得出安全余量。
本机是否存在同样边界，仍缺独立证据。

## 5. 上下文 sweep 怎样设计

### 5.1 区分窗口上限和真实填充长度

作者的旧版实验每个 arm 独立启动一次服务，配置 `-c 131072`，再分五档填充
上下文；每档使用新 prompt，输出 300 tokens，避免 prefix cache 复用。
两组分别测试 draft depth 4 和 6，FlashAttention 与 q8_0 KV 保持一致。

复测时必须同时记下启动窗口、实际 prompt token、实际输出 token、draft
深度和 cache 状态。仅把服务开到 131072 后发送短 prompt，不能写成完成了
131K 长上下文测试。

### 5.2 作者新版结果

以下是 E23 标为 2026-09-21、`4a8440f58` 的结果；`n=4` 表示 draft
depth 4，不表示重复次数。README 没有提供可回收的逐请求原始文件。

| 实际填充上下文 | Decode tok/s | Prefill tok/s | MTP accept |
| ---: | ---: | ---: | ---: |
| 7.9K | 14.1 | 133.6 | 0.51 |
| 16.4K | 13.3 | 115.5 | 0.59 |
| 32.8K | 11.1 | 90.2 | 0.57 |
| 65.6K | 10.1 | 67.7 | 0.65 |
| 98.3K | 9.1 | 57.0 | 0.64 |
| 131.1K | 8.6 | 49.4 | 0.64 |

这些值反映该作者的长上下文曲线，不能作为本机稳态保证值。原说明的 131.1K
为近似写法；缺原始计数时，不把近似 K 单位反推成精确整数。

### 5.3 旧版 depth 4/6 消融

| 实际填充上下文 | Depth 4 Decode tok/s | Depth 6 Decode tok/s | Prefill tok/s | GTT |
| ---: | ---: | ---: | ---: | ---: |
| 7.7K | 13.7 | 12.6 | 134.8 | 82.3 GB |
| 30.6K | 11.5 | 10.4 | 100.0 | 82.3 GB |
| 61.2K | 10.8 | 9.2 | 82.5 | 82.4 GB |
| 91.8K | 8.4 | 6.8 | 71.8 | 82.4 GB |
| 122.4K | 6.5 | 7.1 | 64.7 | 82.5 GB |

旧版短上下文中 depth 6 更慢，最高档略快。作者仍默认 depth 4，并指出接受率
单次波动；这组材料不能支持“增大深度总是加速”。新版表只有 depth 4，
因此也不能用它证明新版 depth 6 的收益。

GTT 接近平坦不自动证明整个系统无换页；本机复测仍需采样 MemAvailable、
RSS 与 swap。制品说明里的资源结论不能替代缺失的宿主记录。

## 6. 代码质量怎样验收

作者使用按执行结果评分的 chain test，而不是只读生成文本。任务包括：
读取带误导的代码并定位错误、实现新状态机并核对精确轨迹，以及线程安全
ring buffer 的 5000 操作压力测试。每种模型三轮，保留单次分数与中位数。

| 作者记录 | Automaton | Hunt | Ring buffer | 总体记录 |
| --- | --- | --- | --- | --- |
| BALANCED 初版 | 100 / 100 / 40 | 60 / 100 / 60 | 20 / 20 / 100 | 文中任务汇总 67/100 |
| HYBRID | 40 / 100 / 100 | 60 / 60 / 100 | 100 / 100 / 20 | 文中任务汇总 73/100 |
| BALANCED 新引擎复跑 | 中位数降到 40 | 60 | 20 | 文中任务汇总 40，原因未隔离 |

这些分数必须和引擎版本一起保存。旧文“状态机可靠”的结论已受到新版复跑
反例限制；不能只引用旧的 100 分，也不能把汇总分当成通用代码能力排行榜。
两份说明没有附完整题目、评分器与逐次生成文件，本机独立复现仍需这些材料。

## 7. 可复用的方法与当前缺项

本项目资料能提炼三条具体方法：先分别验证模型架构和量化类型；把 MTP
深度实验与实际填充上下文配对；引擎升级后同时复跑速度和可执行质量题。
更快的 Decode 不能抵消质量回退，也不能替代整段代码实际运行。

当前待完成的是本机模型完整性、实际引擎构建与加载日志、固定请求的流式
计时、长上下文资源采样和 chain test 的原始执行文件。HYBRID 的 CPU 路径
需单独测量，不能直接继承作者给出的耗时。

资料来源：[E23 BALANCED](../../evidence/records/E23.md)、
[E24 HYBRID](../../evidence/records/E24.md)。数据来源与边界见
[证据使用说明](../../meta/evidence-policy.md)。

