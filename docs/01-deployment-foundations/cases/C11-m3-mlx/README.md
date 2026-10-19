---
id: C11
title: "Apple M3 Ultra：vllm-metal、MLX-VLM、APC与oMLX优化"
type: case
volume: cases
layer: 1
platform: "Apple"
device: "M3 Ultra"
status: historical
source_ids: [R40, R41, R42, R43, R44]
updated: 2026-10-19
summary: "技术标签：MLX / Metal / chat template / APC / batching"
---

# Apple M3 Ultra：vllm-metal、MLX-VLM、APC与oMLX优化

[工程实例索引](../README.md) · [知识体系总目录](../../SUMMARY.md)

技术标签：`MLX / Metal / chat template / APC / batching`

## 结论

oMLX 的实际并发1/2/4输出吞吐为29.38/41.11/55.15 tok/s，对应单路
Decode约29.21/21.04/14.32 tok/s。并发增加提升总产出，同时拉长单请求
延迟。vllm-metal 的文本与视觉结果分开，不能将文本可用写成视觉可用。

## 适用边界

M3 Ultra / 512GB 的多条框架路线；oMLX 基准使用 DeepSeek-V4-Flash-4bit，
EvalScope1.7.0、随机输入目标128、输出上限256、流式、温度0。缓存状态和
部分版本字段缺失，不将毫秒级 TTFT 当作所有冷请求表现。

## 环境与制品

| 分支 | 适配重点 | 已记录结果 |
| --- | --- | --- |
| vllm-metal | Python3.12.13、MLX0.31.2、vLLM0.21.0+cpu、插件0.2.0 | 文本与模板修复；视觉encoder失败 |
| MLX-VLM | 模型、processor、单图CLI、server协议 | 多视觉模型与完整调用代码 |
| APC | 块预算、磁盘缓存、tenant、冷暖缓存、KV量化互斥 | 自定义分支操作，无完整patch commit |
| oMLX | 父目录发现、模型加载、统一内存、连续批处理 | c1/c2/c4完整延迟与吞吐 |

## 执行路径

1. 记录macOS、芯片、物理/可用统一内存、Python/MLX与框架版本，各分支独立环境。
2. 检查原生扩展实际导入路径，避免当前源码目录遮蔽已安装`_rs`模块。
3. 文本先检查模板、reasoning/content与finish_reason，再进入图片。没有视觉encoder的服务应转支持路径，不能靠增大max_tokens修复HTTP500。
4. MLX-VLM使用其版本要求的图片schema；测试卡、base64和SSE客户端见[完整输入链路](../../chapters/frameworks/vllm-service.md#七从图片文件到流式答案的完整链路)。
5. oMLX检查模型父目录与模型ID，显式加载后再测试。APC按原变量设置并检查stats，先冷、再暖、再变前缀，再测挤出和租户隔离。

### oMLX 原服务参数

以下保留 R42 的配置，存储卷名替换为需预先设置的 `${DATA_ROOT}`。
`--model-dir` 填父目录，服务加载后还要确认返回的模型 ID。

```bash
omlx serve --model-dir "${DATA_ROOT}/models/mlx-community" \
  --host 127.0.0.1 --port 8000 \
  --max-model-memory disabled --max-process-memory disabled \
  --paged-ssd-cache-dir "${DATA_ROOT}/omlx-cache" \
  --paged-ssd-cache-max-size 100GB --hot-cache-max-size 8GB --log-level info
```

取消程序级内存限制不表示机器没有物理上限。原材料用 asitop 观察模型加载后
RAM约183.5/512GB、swap inactive；这是一次加载后的资源快照，不是压力测试峰值。

### 实际并发命令与统计文件

R43 在独立评测环境执行，认证值在公开文档中使用环境变量：

```bash
evalscope perf \
  --url http://127.0.0.1:8000/v1/chat/completions \
  --model DeepSeek-V4-Flash-4bit --api openai --api-key "${API_TOKEN}" \
  --dataset random --tokenizer-path "${DATA_ROOT}/models/mlx-community/DeepSeek-V4-Flash-4bit" \
  --parallel 1 1 2 4 --number 5 20 10 10 \
  --min-prompt-length 128 --max-prompt-length 128 --max-tokens 256 \
  --stream --temperature 0 --no-test-connection \
  --name omlx-dsv4-sweep --outputs-dir ./outputs
```

四组请求数不同，第一组是5条单并发观察，不与20条单并发合并冒充同一轮。
检查 `performance_summary.txt`、`benchmark_summary.json`、请求数据库，
核对实际生成 token 和每组墙钟。输出上限不是实际输出总数。

APC 的复测应另建冷、暖、改变前缀和挤出组，同时看 stats；原自定义分支
没有完整 patch commit，不能把所有缓存结果归因到可复现的公开版本。

## 结果

| 并发 | 请求数 | 总生成token/s | 单请求TPOT | 平均延迟 |
| --- | --- | --- | --- | --- |
| 1 | 20 | 29.38 | 34.2ms | 7.582s |
| 2 | 10 | 41.11 | 47.5ms | 10.257s |
| 4 | 10 | 55.15 | 69.8ms | 13.459s |

输入目标128、输出上限256；缓存和环境缺项照原记录标注。并发4总吞吐最高，但单请求更慢；工作点按交互或批处理目标选择。原首组c1/5请求也保留在全文，不从小样本推导稳定p99。

各框架的能力声明以固定版本功能验证为准，调研建议不自动记作实测。

这轮共生成9693 tokens、总窗口278.22 s。表中的 `Gen. tok/s` 是每组
聚合输出，`Decode tok/s` 描述单请求；不能取总吞吐的倒数当作单路 TPOT。
原表有 P99，但样本仅5/10/20，不能作为稳定尾延迟保证。

## 失败与修订

vllm-metal 的视觉 encoder 失败不能靠增大输出预算修复；应换到当时已支持
视觉输入的路线再验收。原生扩展 `_rs` 的导入还可能被当前源码目录遮蔽，
先查实际导入路径，再重装依赖，避免在错误环境反复操作。

## 证据

- [R40 完整技术正文](../../evidence/sources/R40.md)
- [R41 完整技术正文](../../evidence/sources/R41.md)
- [R42 完整技术正文](../../evidence/sources/R42.md)
- [R43 完整技术正文](../../evidence/sources/R43.md)
- [R44 完整技术正文](../../evidence/sources/R44.md)

## 未验证

完整 APC patch、冷暖缓存配对、模型 revision、长期并发和统一质量集未齐。
vllm-metal 视觉失败组不能继承 MLX-VLM 的成功状态；不同框架版本需独立复建。

数据来源与边界见[证据使用说明](../../meta/evidence-policy.md)。
