---
id: C03
title: "NVIDIA GB10：ARM64构建、FP8、AWQ、MTP与DFlash"
type: case
volume: cases
layer: 1
platform: "NVIDIA"
device: "DGX Spark / GB10"
status: historical
source_ids: [R05, R06, R07, R08, R09, R10, R11, R12]
updated: 2026-10-19
summary: "技术标签：CUDA 13 / ARM64 / vLLM / speculative decoding"
---

# NVIDIA GB10：ARM64构建、FP8、AWQ、MTP与DFlash

[工程实例索引](../README.md) · [知识体系总目录](../../SUMMARY.md)

技术标签：`CUDA 13 / ARM64 / vLLM / speculative decoding`

## 结论

Qwen FP8 的一轮 200 请求共输出 25600 tokens、用时 297.46 s，输出吞吐
86.06 tok/s；但平均 TTFT 达 148430.70 ms。这组结果说明必须同时看吞吐
和排队。MTP 与 DFlash 各有独立负载与版本，不能混为同一个加速实验。

## 适用边界

GB10 为 ARM64 统一内存平台。下列多个分支使用不同源码、torch 与扩展组合，
必须分环境复建。Qwen 构建中的 SM120 处理是该版本绕过特定 FP4 编译错误
的操作，不改变设备本身 SM121，也不是所有版本的编译准则。

## 环境与制品

| 分支 | 环境 / 模型 | 适配问题 | 性能数据入口 |
| --- | --- | --- | --- |
| 基础构建 | GB10、ARM64、128GB、CUDA13 | x86 wheel不可直接使用；SM12.1与特定kernel构建 | 源码、依赖与构建日志 |
| Qwen FP8 | vLLM commit17d87168d；Qwen3.6-35B-A3B FP8 | FP8 KV、FlashInfer、prefix/chunked | 200请求、25600输出token、297.46s、86.06token/s |
| Gemma AWQ | 26B-A4B与31B各4/8bit | 打包、量化kernel、模型计算结构 | 四组TTFT/TPOT/ITL/E2E |
| Gemma MTP | 主模型＋assistant，3个候选 | 接受率、验证成本、batch | c1/c2/c4配对 |
| DFlash | 自定义分支、drafter、CUDA扩展 | 多套torch/CUDA/源码需配套 | 原两配置观察约2.03倍，非单变量归因 |

## 执行路径

```text
ARM64/驱动/CUDA确认 → 固定源码及torch → 构建扩展
 → 小输入完成生成 → API与SSE → 无优化基线
 → AWQ或MTP或DFlash独立分支 → 同负载复测 → 质量及资源验收
```

1. 分别记录每个分支的`git rev-parse HEAD`、`pip freeze`、`torch.__version__`、`nvcc --version`与模板。下面多篇文章的环境不同，不能合并到一个虚拟环境再声称复现。
2. Qwen构建中曾把`TORCH_CUDA_ARCH_LIST`设为12.0绕过特定FP4 kernel错误；这不改变GB10计算能力12.1，也不是所有版本的默认编译参数。
3. 用[Qwen FP8完整服务步骤](../../chapters/frameworks/vllm-service.md)完成启动、请求和输出保存，之后恢复历史性能预算。
4. AWQ四组统一输入目标2048、输出128、200请求、c2；比较前确认各制品配置与实际输出。MTP使用自己的512/256负载，不与AWQ绝对吞吐交叉排名。
5. DFlash先检查drafter匹配与草稿接受统计，再看TTFT/TPOT和目标模型质量；原配置同时改变ctx、seqs、memory与eager，组合收益不能归因给单一模块。

### Qwen FP8 实际服务与压测参数

R07 固定 vLLM `17d87168d` / CUDA 13，原服务窗口为 `16184`，不是
手动改写成近似的 16K。下面保留关键命令，模型路径是公共约定位置。

```bash
vllm serve /srv/llm/models/Qwen3.6-35B-A3B-FP8 \
  --served-model-name Qwen3.6-35B-A3B-FP8 --host 0.0.0.0 --port 8001 \
  --max-model-len 16184 --max-num-batched-tokens 8192 --max-num-seqs 4 \
  --gpu-memory-utilization 0.80 --generation-config auto \
  --override-generation-config '{"temperature":0.6,"top_p":0.95,"top_k":20}' \
  --kv-cache-dtype fp8 --load-format auto --attention-backend flashinfer \
  --enable-prefix-caching --enable-chunked-prefill --trust-remote-code

vllm bench serve --backend openai-chat \
  --base-url http://127.0.0.1:8001 --endpoint /v1/chat/completions \
  --model Qwen3.6-35B-A3B-FP8 \
  --tokenizer /srv/llm/models/Qwen3.6-35B-A3B-FP8 \
  --dataset-name random --random-input-len 2048 --random-output-len 128 \
  --num-prompts 200 --request-rate inf --seed 42
```

这里的无限到达率会形成排队，不等于引擎同时执行 200 路。检查点是成功/
失败计数、实际输入总量、输出总量、测试窗口和 TTFT/TPOT；不能只摘最大
瞬时吞吐。模型与命令含 prefix/chunked 等多个机制，也不是单项消融。

### MTP 与 DFlash 单独建配对

R11 的 MTP 使用主模型配 assistant、`num_speculative_tokens=3`；输入
目标512、输出256，并发1/2/4分别20/40/80请求。对照同负载的 target-only
结果，保存 drafted、accepted 和每位置接受率，而非只看接受率一个数。

R12 的 DFlash 使用 spec_bench、50 prompts、输出256、并发1、seed42。
其 baseline 与 DFlash 服务还改变了窗口、seqs、memory 与 eager，所以
应保留为配置组合对照。相同任务不自动构成严格单变量实验。

## 结果

Qwen原200请求突发的平均TTFT为148430.70ms，P99为293115.24ms，吞吐86.06token/s并不代表交互体验好。验收应补有限到达率和并发，让TTFT与尾延迟达到目标。

MTP原吞吐增幅按c1/c2/c4约44.76%/32.68%/53.19%。保留原始数据，不把接受率或总吞吐当作质量等价证明。

| DFlash 组合对照 | Baseline | DFlash | 口径 |
| --- | ---: | ---: | --- |
| 50 请求用时 | 594.69 s | 292.62 s | spec_bench，总窗口 |
| 输出吞吐 | 21.52 tok/s | 43.74 tok/s | 12800 输出 token / 窗口 |
| Mean TPOT | 43.14 ms | 21.80 ms | 不含首 token |
| Mean ITL | 42.97 ms | 72.82 ms | 批量交付间隔，不能直接等同 TPOT |

输出吞吐约 2.03 倍只描述这一配置组合。推测一次交付多个 token 时，ITL
可能增加而 TPOT 减少；解释时必须说明计量事件。

## 失败与修订

R07 报 `cvt with .e2m1x2 not supported on .target sm_121`，对应特定 FP4
构建路径；先修源码/目标架构匹配，再做服务性能。R12 不能因草稿接受率
较好就声称质量和全部采样分布已验收。R09 的 AWQ 四组又有自己的负载，
不能与上述绝对 tok/s 交叉排名。

## 证据

- [R05 完整技术正文](../../evidence/sources/R05.md)
- [R06 完整技术正文](../../evidence/sources/R06.md)
- [R07 完整技术正文](../../evidence/sources/R07.md)
- [R08 完整技术正文](../../evidence/sources/R08.md)
- [R09 完整技术正文](../../evidence/sources/R09.md)
- [R10 完整技术正文](../../evidence/sources/R10.md)
- [R11 完整技术正文](../../evidence/sources/R11.md)
- [R12 完整技术正文](../../evidence/sources/R12.md)

## 未验证

各分支尚缺统一质量集、完全一致的服务参数消融、有限到达率下的 SLO 曲线
和长期稳定性。部分源码扩展需按原分支复建，不宜把跨版本说明拼为一个安装脚本。

数据来源与边界见[证据使用说明](../../meta/evidence-policy.md)。
