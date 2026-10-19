---
id: C04
title: "NVIDIA GB10多模态：VL、Omni与文档模型的部署链路"
type: case
volume: cases
layer: 1
platform: "NVIDIA"
device: "DGX Spark / GB10"
status: historical
source_ids: [R13, R14, R15, R16, R17]
updated: 2026-10-19
summary: "技术标签：vLLM / processor / image / audio / SSE"
---

# NVIDIA GB10多模态：VL、Omni与文档模型的部署链路

[工程实例索引](../README.md) · [知识体系总目录](../../SUMMARY.md)

技术标签：`vLLM / processor / image / audio / SSE`

## 结论

R13–R17 保留了五类 GB10 多模态服务配置、图片请求代码和调用方式，但
没有统一图文性能表。Qwen3-VL-30B-A3B 曾配置 131072 或 100000 窗口，
这些是配置值，不是实际长图文验收结果。

## 适用边界

本文按视觉、Omni 与文档解析分支阅读；文本生成通过不能代替图片、音频或
DocTags 内容正确。各分支使用自己的模型目录、processor 和服务端口。

## 环境与制品

| 模型 | 原服务配置 | 独立验收项 |
| --- | --- | --- |
| Qwen3-VL-8B | memory0.8，端口8007 | 文本、单图、图像token、encoder、SSE |
| Qwen3-VL-30B-A3B | TP1/PP1、memory0.8；窗口131072，另有100000/batched4096 | 多图/长图输入与内存，不能从max-model-len推导已通过长度 |
| Qwen2.5-VL-7B | ARM64配套容器 | processor版本、图片字段与完整答案 |
| Qwen3-Omni-30B-A3B | memory0.9，端口8008 | 文本/图像/音频输入与输出分别测试 |
| granite-docling-258M | TP1/PP1、seqs512、batched8192 | DocTags、表格顺序、漏字，512不是已证明的有效并发 |

## 执行路径

先固定镜像与模型全目录，运行纯文本，再加入图片。图像应保存字节摘要、尺寸、预处理后token和期望内容；原私人图片不公开，复建改用[公开测试卡及完整客户端](../../chapters/frameworks/vllm-service.md#七从图片文件到流式答案的完整链路)。

优化按“图像分辨率/切片预算→encoder批处理→文本调度→并发”分项做对照。降低分辨率可能损失小字，缓存命中需要同一输入与processor，不能只看文本token/s。音频单独记录采样率、首音频延迟、持续RTF和内容正确性。

新增测试卡没有配上未执行的模型答案；模型具备的能力与当前服务入口支持的能力分别验收。

### 视觉服务和文档服务的原参数

以下是在模型已经挂载到 `/app/model` 的容器内执行的 R13 配置：

```bash
vllm serve /app/model --host 0.0.0.0 --port 8007 \
  --served-model-name qwen3-vl-8b-instruct --trust-remote-code \
  --tensor-parallel-size 1 --pipeline-parallel-size 1 \
  --gpu-memory-utilization 0.8
```

R17 的 granite-docling 则使用：

```bash
vllm serve /app/model --host 0.0.0.0 --port 8009 \
  --served-model-name granite-docling-258M --trust-remote-code \
  --tensor-parallel-size 1 --pipeline-parallel-size 1 \
  --max-num-seqs 512 --max-num-batched-tokens 8192 \
  --enable-chunked-prefill --gpu-memory-utilization 0.9
```

不能把 `max-num-seqs=512` 记作已通过 512 并发。验收先发送真实页面，
核对 DocTags、行序和表格，再单独构造并发负载。

### 从图片到完整响应的检查点

R13 客户端先读取图片字节并编码 base64，再用正确 MIME 组成 data URL，
在 `messages[].content` 中同时放 text 和 image_url，读取 SSE 的
`data:` 事件并组装回答。每一步都要保存实际模型 ID、图片尺寸、payload、
usage、结束原因和完整文本。中文小字或表格不能只用“生成了一段文字”验收。

Omni 分支的音频要另存输入格式与输出信号；服务端接收能力未验证时，不能
依据模型名称宣称该 API 已支持所有输入输出模态。

## 结果

| 来源 | 已有证据 | 性能口径缺项 |
| --- | --- | --- |
| R13/R14 | 模型部署、单图调用和流式客户端 | 无统一图片集和请求时序表 |
| R15 | 长窗口服务参数 | 无实际长输入 token 与质量验收表 |
| R16 | Omni 服务配置 | 模态逐项延迟、质量与完整音频记录未齐 |
| R17 | 文档模型部署配置 | 无已测并发与完整 DocTags 质量统计 |

保留这些实际操作材料，缺失的 TTFT、吞吐和容量不填估算数。

## 失败与修订

启动窗口和序列上限只描述配置。Qwen 视觉模型的 processor、Omni 的音频
路径、文档模型的专用输出均需独立验收；不能复用一个文本 curl 后称全部通过。
图片中的个人信息不随记录公开，改用公开测试素材后应重新记录结果。

## 证据

- [R13 完整技术正文](../../evidence/sources/R13.md)
- [R14 完整技术正文](../../evidence/sources/R14.md)
- [R15 完整技术正文](../../evidence/sources/R15.md)
- [R16 完整技术正文](../../evidence/sources/R16.md)
- [R17 完整技术正文](../../evidence/sources/R17.md)

## 未验证

多图、长图、超长上下文、音频输入输出、文档质量和长期并发没有统一验收。
原文没有的性能数字保持未记录；本页的后续优化顺序属于复测方法。

数据来源与边界见[证据使用说明](../../meta/evidence-policy.md)。
