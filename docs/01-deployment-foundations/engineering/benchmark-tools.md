# 压测工具工程记录：llama-bench、vLLM bench与EvalScope

[工程实例索引](README.md) · [知识体系总目录](../SUMMARY.md)

技术标签：`engine / HTTP / fixed load / raw results`

## 工程边界

| 工具 | 测量对象 | 必须固定 |
| --- | --- | --- |
| llama-bench | 引擎pp/tg | build、模型、后端、层数、线程、pp/tg和重复数 |
| vLLM bench serve | 服务端HTTP请求 | tokenizer、端点、输入输出、并发/到达率、缓存和实际token |
| EvalScope | 接口负载与分组报告 | API类型、数据集、number、parallel、采样和原始明细 |
| Locust/wrk/hey | HTTP压力与应用流程 | 自定义SSE/结束语义；普通req/s不代替token/s |

下方完整保留作者的工具说明、安装、命令和输出字段；涉及当前设备与框架的命令仍需固定到实际版本。统一统计定义与异常样例见[性能测试专题](../chapters/performance/benchmarking.md)。

## 完整技术记录的使用约定

以下直接保留相关FlowUs文章的技术正文、命令、表格、日志、失败和后续实验，不以摘要替代原过程。私人路径、节点、认证与附件地址脱敏；`<NODE_IP>`等占位符需要按当前环境填写。原建议或预测仍是建议或预测。上方执行顺序与技术修订用于解释历史记录中的冲突，历史GPU/NPU实验未在本轮重跑。

## R48 · llama.cpp 与 vLLM 推理性能评测工具2026年版本

[原笔记图片：图片.png；未公开转存]

#### 1. 总体选择

| 场景 | 推荐工具 | 说明 |
| --- | --- | --- |
| llama.cpp 本地裸跑性能 | llama-bench | 测 prompt processing / token generation，适合看 GGUF 在 CPU/GPU/Metal/CUDA/ROCm 后端的基础速度 |
| llama.cpp 困惑度 / 质量粗测 | llama-perplexity | 用文本集测 PPL，适合量化模型质量对比 |
| llama.cpp HTTP API 压测 | EvalScope / vLLM bench serve / 自写 wrk 脚本 | llama-server 支持 OpenAI 兼容 API，可以当服务压测 |
| vLLM 在线服务压测 | vllm bench serve | 重点看 TTFT、TPOT、ITL、E2E latency、吞吐、并发 |
| vLLM 离线吞吐测试 | vllm bench throughput | 不走 HTTP，测引擎离线批量推理能力 |
| vLLM 单批延迟测试 | vllm bench latency | 测固定 batch / 输入输出长度下的基础 latency |
| 生产级压测报告 | EvalScope / GuideLLM / Prometheus + Grafana | 更适合生成报告、并发曲线、SLA 分析 |

vLLM 官方当前把 benchmark 统一放到了 CLI 里：`vllm bench latency` 用于单批延迟，`vllm bench serve` 用于在线服务吞吐，`vllm bench throughput` 用于离线吞吐。使用 bench 命令需要安装 `vllm[bench]`。([vLLM](https://docs.vllm.ai/en/latest/cli/))

---

#### 2. llama.cpp 的评测方式

##### 2.1 llama.cpp 自带工具

现在写 llama.cpp 评测，不能再说“llama.cpp 本身不自带 benchmark 工具”。更准确的说法是：

**llama.cpp 自带基础性能测试工具，但如果要做 API 压测、并发压测、报告分析，可以结合 EvalScope。**

llama.cpp 官方 README 里列出了 `llama-bench`，用于 benchmark inference performance；也列出了 `llama-perplexity`，用于测 perplexity 和其他质量指标。([GitHub](https://github.com/ggml-org/llama.cpp))

##### 2.2 本地性能测试：`llama-bench`

```text
# 基础测试
llama-bench -m /path/to/model.gguf
```

常见输出里会看到两类核心指标：

| 指标 | 含义 |
| --- | --- |
| pp512 | prompt processing，提示词预填充阶段速度 |
| tg128 | token generation，解码生成阶段速度 |
| t/s | tokens/s，吞吐速度 |
| backend | 当前使用的后端，例如 CUDA、Metal、BLAS、ROCm 等 |

示例：

```text
llama-bench \
  -m /models/Qwen3-32B-Q5_K_M.gguf \
  -ngl 99 \
  -t 16
```

说明：

| 参数 | 作用 |
| --- | --- |
| -m | GGUF 模型路径 |
| -ngl | GPU offload 层数，常用 99 表示尽量全部 offload |
| -t | CPU 线程数 |
| -p | prompt token 数，部分版本支持 |
| -n | generation token 数，部分版本支持 |

---

##### 2.3 llama.cpp 服务压测：`llama-server + EvalScope`

llama.cpp 的 `llama-server` 是 OpenAI API 兼容 HTTP server，支持 `/v1/chat/completions`，也支持并行解码、多用户、continuous batching、OpenAI-compatible responses / embeddings、function calling、speculative decoding、Prometheus metrics 等能力。([GitHub](https://github.com/ggml-org/llama.cpp))

启动服务：

```text
llama-server \
  -m /models/Qwen3-32B-Q5_K_M.gguf \
  --host 0.0.0.0 \
  --port 8080 \
  -c 32768 \
  -np 4 \
  -ngl 99 \
  --metrics
```

参数解释：

| 参数 | 含义 |
| --- | --- |
| -c 32768 | 上下文长度 |
| -np 4 | 并行 slot 数，影响同时处理请求数量 |
| -ngl 99 | 尽量将模型层 offload 到 GPU |
| --metrics | 开启 Prometheus /metrics 指标 |

开启 `--metrics` 后，llama.cpp server 支持 Prometheus 兼容指标，例如 prompt tokens、generation tokens、平均 prompt 吞吐、平均 generation 吞吐、处理中请求数、排队请求数等。([GitHub](https://github.com/ggml-org/llama.cpp/blob/master/tools/server/README.md))

---

#### 3. EvalScope：通用 API 压测与质量评测

EvalScope 现在更适合定位为：

**通用大模型评测框架，既能做模型能力评估，也能做 OpenAI API 兼容服务压测。**

EvalScope 官方说明它支持模型能力评估、推理性能压测和结果可视化，并支持 LLM、VLM、Embedding、Reranker、AIGC 等模型类型。它的性能测试指标包括 TTFT、TPOT 等。([GitHub](https://github.com/modelscope/evalscope))

安装：

```text
pip install evalscope[perf] -U
```

官方 stress test 文档说明，EvalScope 支持 OpenAI API 格式服务和多种数据集格式；`parallel` 表示并发请求数，`number` 表示每个并发档位下的总请求数，`tokenizer-path` 用于计算 token 数，尤其是 random dataset 时很重要。([EvalScope](https://evalscope.readthedocs.io/en/latest/user_guides/stress_test/quick_start.html))

##### 3.1 压测 llama.cpp OpenAI API

```text
evalscope perf \
  --parallel 1 2 4 \
  --number 3 6 12 \
  --url http://127.0.0.1:8080/v1/chat/completions \
  --model qwen3-32b-q5 \
  --api openai \
  --dataset random \
  --min-prompt-length 1024 \
  --max-prompt-length 1024 \
  --min-tokens 512 \
  --max-tokens 512 \
  --tokenizer-path /models/Qwen3-32B-tokenizer \
  --extra-args '{"ignore_eos": true}' \
  --stream
```

你原来的 `speed_benchmark` 建议改成 `random`。新版 EvalScope 官方 quick start 里用的是 `--dataset random`，并通过 `min/max prompt length` 和 `min/max tokens` 固定输入输出长度。([EvalScope](https://evalscope.readthedocs.io/en/latest/user_guides/stress_test/quick_start.html))

##### 3.2 压测 vLLM OpenAI API

```text
evalscope perf \
  --parallel 1 10 50 100 \
  --number 10 100 500 1000 \
  --url http://127.0.0.1:8000/v1/chat/completions \
  --model qwen3-32b \
  --api openai \
  --dataset random \
  --min-prompt-length 1024 \
  --max-prompt-length 1024 \
  --min-tokens 512 \
  --max-tokens 512 \
  --tokenizer-path /models/Qwen3-32B \
  --extra-args '{"ignore_eos": true}' \
  --stream
```

EvalScope 输出会包含 total/success/failed、request throughput、avg latency、TTFT、TPOT、ITL、output throughput、total throughput 等指标，也会输出不同百分位结果。([EvalScope](https://evalscope.readthedocs.io/en/latest/user_guides/stress_test/quick_start.html))

---

#### 4. vLLM 官方 benchmark：新版写法

你去年的写法里还是 `benchmark_serving.py` 和 `benchmark_throughput.py`，现在建议改成：

```text
vllm bench serve
vllm bench throughput
vllm bench latency
```

vLLM 的 `benchmarks/README.md` 已经说明，原来的 benchmark 脚本目录现在主要指向 Benchmark CLI 文档；`benchmark_throughput.py` 文件本身也直接打印 deprecated，并提示使用 `vllm bench throughput`。([GitHub](https://github.com/vllm-project/vllm/blob/main/benchmarks/README.md))

---

##### 4.1 在线服务压测：`vllm bench serve`

适合测试已经启动好的 vLLM OpenAI API 服务。

先启动模型：

```text
vllm serve /models/Qwen3-32B \
  --host 0.0.0.0 \
  --port 8000 \
  --served-model-name qwen3-32b \
  --tensor-parallel-size 1 \
  --gpu-memory-utilization 0.9 \
  --max-model-len 32768
```

再压测：

```text
vllm bench serve \
  --backend openai-chat \
  --host 127.0.0.1 \
  --port 8000 \
  --endpoint /v1/chat/completions \
  --model qwen3-32b \
  --dataset-name random \
  --num-prompts 100 \
  --max-concurrency 8 \
  --request-rate inf \
  --random-input-len 1024 \
  --random-output-len 512 \
  --ignore-eos \
  --percentile-metrics ttft,tpot,itl,e2el \
  --metric-percentiles 50,90,95,99 \
  --save-result \
  --save-detailed
```

核心参数：

| 参数 | 含义 |
| --- | --- |
| --backend openai-chat | 使用 OpenAI Chat Completions 协议 |
| --endpoint /v1/chat/completions | 对应 vLLM OpenAI API |
| --model | 必须和 --served-model-name 对齐 |
| --num-prompts | 总请求数 |
| --max-concurrency | 最大并发数 |
| --request-rate | 请求到达速率，inf 表示一开始尽量全部打过去 |
| --random-input-len | 随机数据集输入长度 |
| --random-output-len | 随机数据集输出长度 |
| --ignore-eos | 忽略 EOS，尽量生成到指定长度 |
| --percentile-metrics | 统计 TTFT、TPOT、ITL、E2E 等百分位 |
| --metric-percentiles | 统计 P50/P90/P95/P99 |
| --save-detailed | 保存每个请求的详细结果 |

`vllm bench serve` 的文档明确说明，`--max-concurrency` 控制最大并发，`--request-rate` 控制请求发起速率；当服务处理不过来时，实际 request rate 可能低于设定值。它还支持 `ttft`、`tpot`、`itl`、`e2el` 等百分位指标，以及 ramp-up 压测。([vLLM](https://docs.vllm.ai/en/stable/cli/bench/serve/))

---

##### 4.2 离线吞吐测试：`vllm bench throughput`

适合不走 HTTP，直接测 vLLM engine 的极限吞吐。

```text
vllm bench throughput \
  --model /models/Qwen3-32B \
  --dataset-name random \
  --num-prompts 100 \
  --input-len 1024 \
  --output-len 512 \
  --tensor-parallel-size 1 \
  --gpu-memory-utilization 0.9 \
  --max-model-len 32768
```

适用场景：

| 场景 | 是否适合 |
| --- | --- |
| 看 GPU 理论推理吞吐 | 适合 |
| 对比不同量化精度 | 适合 |
| 对比 TP / PP 参数 | 适合 |
| 模拟真实 HTTP 用户并发 | 不适合 |
| 测 TTFT / 网络延迟 | 不适合 |

---

##### 4.3 单批延迟测试：`vllm bench latency`

```text
vllm bench latency \
  --model /models/Qwen3-32B \
  --input-len 1024 \
  --output-len 128 \
  --tensor-parallel-size 1 \
  --gpu-memory-utilization 0.9
```

适合回答这类问题：

| 问题 | 适合用什么 |
| --- | --- |
| 单请求延迟有多低？ | vllm bench latency |
| 服务并发能力如何？ | vllm bench serve |
| 离线最大 tokens/s 多少？ | vllm bench throughput |
| 真实生产 API 稳不稳？ | EvalScope + Prometheus + Grafana |

---

#### 5. 核心指标解释

| 指标 | 中文解释 | 怎么看 |
| --- | --- | --- |
| TTFT | Time To First Token，首 token 延迟 | 用户体感响应速度，越低越好 |
| TPOT | Time Per Output Token，平均每个输出 token 耗时，不含首 token | 解码速度核心指标，越低越好 |
| ITL | Inter-token Latency，token 间隔 | 流式输出是否顺滑 |
| E2EL | End-to-End Latency，端到端总延迟 | 一次请求完整耗时 |
| Req Throughput | requests/s，每秒完成请求数 | 服务请求吞吐 |
| Output Throughput | output tok/s，每秒生成 token 数 | 解码吞吐 |
| Total Throughput | input + output tok/s | 总处理吞吐，包含 prefill |
| Concurrency | 并发请求数 | 同时处理多少请求 |
| Request Rate | 请求到达速率 | 模拟用户流量进入速度 |
| Goodput | 满足 SLA 的有效吞吐 | 生产环境更有意义 |

EvalScope 文档对 TTFT、TPOT、ITL、Output Throughput、Total Throughput 都有明确指标解释；其中 TTFT 是从发送请求到收到第一个响应 token 的平均时间，TPOT 是排除首 token 后每个输出 token 的平均生成时间，ITL 是 token 间平均间隔。([EvalScope](https://evalscope.readthedocs.io/en/latest/user_guides/stress_test/quick_start.html))

---

#### 6. 推荐标准测试流程

##### 第一组：单请求基础速度

目标：看模型在当前硬件上的基础生成速度。

```text
vllm bench serve \
  --backend openai-chat \
  --host 127.0.0.1 \
  --port 8000 \
  --endpoint /v1/chat/completions \
  --model qwen3-32b \
  --dataset-name random \
  --num-prompts 5 \
  --max-concurrency 1 \
  --random-input-len 1024 \
  --random-output-len 512 \
  --ignore-eos
```

重点看：

```Markdown
Mean TTFT
Mean TPOT
Output token throughput
Total token throughput
```

---

##### 第二组：并发曲线测试

目标：看并发从小到大时，吞吐是否上升、延迟是否爆炸。

```text
for c in 1 2 4 8 16 32; do
  vllm bench serve \
    --backend openai-chat \
    --host 127.0.0.1 \
    --port 8000 \
    --endpoint /v1/chat/completions \
    --model qwen3-32b \
    --dataset-name random \
    --num-prompts 100 \
    --max-concurrency $c \
    --random-input-len 1024 \
    --random-output-len 512 \
    --ignore-eos \
    --save-result \
    --result-dir ./bench-results \
    --metadata concurrency=$c
done
```

判断方式：

| 现象 | 说明 |
| --- | --- |
| 并发升高，output tok/s 明显升高 | batching 生效 |
| 并发升高，TTFT 小幅升高 | 正常 |
| 并发升高，TTFT / E2E 暴涨 | 达到服务瓶颈 |
| failed requests 增加 | 上下文、显存、服务错误或超时 |
| output tok/s 不再提升 | GPU 或调度已经打满 |

---

##### 第三组：长上下文测试

目标：验证 32K / 64K / 128K 上下文下的稳定性。

```text
vllm bench serve \
  --backend openai-chat \
  --host 127.0.0.1 \
  --port 8000 \
  --endpoint /v1/chat/completions \
  --model qwen3-32b \
  --dataset-name random \
  --num-prompts 20 \
  --max-concurrency 2 \
  --random-input-len 32768 \
  --random-output-len 512 \
  --ignore-eos \
  --percentile-metrics ttft,tpot,itl,e2el \
  --metric-percentiles 50,90,95,99
```

长上下文重点看：

| 指标 | 关注点 |
| --- | --- |
| TTFT | prefill 压力会明显变大 |
| GPU 显存 | KV Cache 是否撑爆 |
| failed requests | 是否超过 max_model_len |
| total throughput | 长 prompt 下 prefill 性能 |
| output throughput | decode 是否受影响 |

---

#### 7. llama.cpp 与 vLLM 压测对比

| 对比项 | llama.cpp | vLLM |
| --- | --- | --- |
| 主要模型格式 | GGUF | HF Transformers / safetensors / 量化格式 |
| 典型部署场景 | 端侧、本地、小服务器、CPU/GPU 混合 | 服务端、高并发、多卡推理 |
| 自带 benchmark | llama-bench、llama-perplexity | vllm bench latency/serve/throughput |
| API 服务 | llama-server | vllm serve |
| OpenAI API 兼容 | 支持 | 支持 |
| 并发能力 | 支持 -np、parallel decoding、continuous batching | 强项，continuous batching / PagedAttention |
| 监控 | --metrics 暴露 /metrics | /metrics + Prometheus/Grafana |
| 最适合测什么 | GGUF 量化速度、端侧推理速度 | 服务端吞吐、TTFT、TPOT、并发曲线 |
| 推荐压测工具 | llama-bench + EvalScope | vllm bench serve + EvalScope |

---

#### 8. 最终建议

现在这部分可以这么讲：

**如果是 llama.cpp，我会先用 `llama-bench` 测本地 GGUF 模型的基础推理速度，重点看 prompt processing 和 token generation 的 tokens/s；如果模型以 `llama-server` 方式对外提供 OpenAI API，我会再用 EvalScope 做并发压测，观察 TTFT、TPOT、ITL、请求成功率和吞吐曲线。**

**如果是 vLLM，我优先使用官方新版 `vllm bench` 命令。`vllm bench serve` 用来测在线服务并发能力，`vllm bench throughput` 用来测离线极限吞吐，`vllm bench latency` 用来测单批延迟。生产环境里，我会配合 Prometheus/Grafana 观察 KV Cache、请求队列、GPU 利用率和服务端指标，避免只看单次 tokens/s。**

## R49 · 大模型性能评估框架集合

下面把“性能”分成两类：**推理服务性能压测**，看吞吐、延迟、并发、TTFT/ITL/TPOT；以及**模型能力评测**，看 MMLU、C-Eval、GSM8K、RAG、Agent、多模态等任务效果。

#### 1. vLLM 相关压测工具

| 工具 | 适合场景 | 主要指标/能力 | 备注 |
| --- | --- | --- | --- |
| vllm bench serve | 在线服务压测，压 vLLM OpenAI-compatible API | request throughput、output token throughput、total token throughput、TTFT、TPOT、ITL、P99 等 | 旧的 benchmark_serving.py 已废弃，官方提示改用 vllm bench serve。(GitHub) |
| vllm bench throughput | 离线批量推理吞吐测试 | requests/s、total tokens/s、output tokens/s | 适合比较模型、batch、并行策略、量化、spec decoding 对离线吞吐的影响。(vLLM) |
| vllm bench latency | 单模型/本地推理延迟测试 | 延迟类指标 | vLLM 当前 CLI 明确提供 latency / serve / throughput 三类 bench 入口。(GitHub) |
| vLLM specialized benchmarks | 特性专项压测 | structured output、prefix caching、long document QA、多模态、embedding、reranker 等 | 用来验证某个 vLLM 功能开关或回归，而不是完整生产流量模拟。(vLLM) |
| GuideLLM | 生产级 vLLM 服务压测 | 负载模式、实时进度、报告、延迟分布、吞吐行为 | vLLM 官方文档明确说：vLLM 自带 benchmark 更偏特性/回归测试；生产 vLLM server 压测推荐 GuideLLM，因为数据集加载、请求格式、workload pattern 更灵活。(vLLM) |

`vllm bench serve` 常用形态大概是：

```text
vllm serve Qwen/Qwen2.5-7B-Instruct --host 0.0.0.0 --port 8000

vllm bench serve \
  --backend vllm \
  --model Qwen/Qwen2.5-7B-Instruct \
  --endpoint /v1/chat/completions \
  --dataset-name sharegpt \
  --dataset-path /path/to/sharegpt.json \
  --num-prompts 1000 \
  --request-rate inf \
  --max-concurrency 64 \
  --save-result
```

压测时重点调 `--request-rate`、`--burstiness`、`--max-concurrency`：官方说明 `request-rate=inf` 适合最大吞吐，有限 RPS 更像真实流量；`burstiness` 可模拟突发或均匀流量；`max-concurrency` 用来模拟网关/负载均衡的并发上限。([vLLM](https://docs.vllm.ai/en/latest/benchmarking/cli/))

#### 2. 通用开源推理性能压测框架

| 框架 | 类型 | 适合用法 |
| --- | --- | --- |
| GuideLLM | LLM 服务性能压测 | 推荐用于生产 vLLM 服务容量评估、并发扫描、报告输出；支持 rate-based load、HTML/JSON/CSV 报告。(GitHub) |
| NVIDIA GenAI-Perf | 推理服务 benchmark | 支持 LLM、多模态、Embedding、Reranking、LoRA 等；输出 CSV/JSON，可测 TTFT、ITL、TPS、RPS；支持 OpenAI API 规范服务，因此可压 vLLM endpoint。(NVIDIA Docs) |
| Ray LLMPerf | LLM API 压测 | 通过并发请求测 inter-token latency 和 generation throughput，也带简单 correctness test；适合横向比较不同 API/服务端。(GitHub) |
| Kubernetes SIGs Inference Perf | 生产/K8s 推理压测 | 面向生产级 GenAI inference deployment，model-server agnostic，适合在 K8s 环境做不同后端的 apples-to-apples 比较。(GitHub) |
| EvalScope | 评测 + 压测一体 | ModelScope 社区的框架，既能做通用能力评测、多模型比较，也支持 stress test；覆盖 LLM、VLM、Embedding、Reranker、AIGC 等。(GitHub) |

#### 3. 开源模型能力评估框架

| 框架 | 更适合评什么 | 特点 |
| --- | --- | --- |
| lm-evaluation-harness | 学术/通用 NLP benchmark | EleutherAI 维护，统一评测大量生成式语言模型任务，支持 60+ 标准 academic benchmarks、vLLM、Transformers、API 模型，也被 Hugging Face Open LLM Leaderboard 使用。(GitHub) |
| OpenCompass | 中文 + 通用大模型能力 | 国内常用，强调公平、全面评估；支持丰富数据集、模型、榜单，适合 C-Eval、CMMLU、MMLU、数学、代码、长上下文、中文任务等。(GitHub) |
| EvalScope | 一站式模型评测 | 支持通用能力、多模型比较、压测；内置 MMLU、C-Eval、GSM8K 等，并集成 OpenCompass、VLMEvalKit、RAGEval 等后端。(GitHub) |
| HELM | 可复现、透明、整体性评估 | Stanford CRFM 开源框架，关注 holistic evaluation，除准确率外还覆盖 efficiency、bias、toxicity 等维度，并有 leaderboard 和 Web UI；不过项目说明 2026-06-01 起进入维护模式。(GitHub) |
| LightEval | Hugging Face 生态评测 | HF Leaderboard/Evals 团队维护，强调快速、灵活、多 backend 评测，近期也持续适配 vLLM。(GitHub) |
| VLMEvalKit | 多模态/VLM 评测 | OpenCompass 系列，多模态大模型一键评测工具，适合图文、多模态 benchmark。(GitHub) |
| DeepEval | LLM 应用单测/回归评估 | 类似 pytest 的 LLM app 测试框架，适合 RAG、Agent、chatbot、应用级指标和 CI 回归。(GitHub) |
| Ragas | RAG 应用评估 | 专注 RAG/LLM application 评测，提供 metrics、合成测试集和开发/生产质量监控工作流。(ragas.io) |

#### 选型建议

做 **vLLM 服务上线前容量评估**：优先 `GuideLLM` 或 `vllm bench serve`。前者更适合生产流量模式和报告，后者更轻量、贴近 vLLM 自身。

做 **模型/部署参数对比**：用 `vllm bench throughput` 比较离线吞吐，用 `vllm bench serve` 或 GenAI-Perf 比较在线 TTFT、ITL、P99、tokens/s、并发上限。

做 **中文/通用能力评测**：优先 OpenCompass 或 EvalScope；英文/学术 benchmark 对齐用 lm-evaluation-harness；多模态用 VLMEvalKit；RAG/Agent 应用质量用 Ragas 或 DeepEval。

大模型质量评估框架集合（私人页面链接不公开）
