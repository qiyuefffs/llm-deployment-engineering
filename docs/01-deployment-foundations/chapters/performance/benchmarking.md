# 性能测试：把一次运行变成可比较的结果

[总目录](../../SUMMARY.md) · [所属总章：性能优化](../../02-capability-layers/04-memory-performance.md) · [完整CPU实跑](../../practice/first-service/README.md)

## 本章概览

性能测试首先要说清测什么：模型执行速度、单个用户等待，还是服务在多请求下的容量。同一个“token/s”，可能来自引擎、单请求decode或整个HTTP压测窗口。计时边界不同，数字就不能直接比较。

本章按FlowUs中的压测工具总文、GB10突发测试、oMLX并发测试，以及本书CPU实跑组织。先定义工作负载，再选择工具、保存明细、检查质量，最后解释吞吐和延迟的取舍。

## 1. 先写测试计划，再发请求

测试计划至少包含模型与制品、输入输出长度、并发或到达率、请求数、采样与思考设置、缓存状态、预热、测量范围、错误处理和通过标准。输入长度用匹配tokenizer计算；字符数不能直接代替token数。

例如，本书CPU实跑计划固定Qwen3-0.6B-Q8_0、4线程、纯CPU、两槽位，c1/c2各4请求、输出上限32。目标是检查脚本链路和观察并发效应，样本量不够支持稳定P99或生产容量结论。先说明目的，就不会把一份教学结果夸大为服务器选型报告。

性能任务可以固定输出长度以比较计算，但必须检查真实usage和结束原因。`ignore_eos`等选项只在服务支持时使用，并应注明它偏离自然结束的业务行为。用于质量的任务应让模型有机会完整回答，两类结果分别保存。

## 2. 三种测量边界

| 边界 | 工具示例 | 回答的问题 |
| --- | --- | --- |
| 引擎执行 | llama-bench、vLLM离线bench | 固定计算负载的基础性能 |
| 本地Pipeline | OpenVINO GenAI等 | 分词、生成等管线开销 |
| HTTP客户端 | vllm bench serve、EvalScope、自写客户端 | 接口、排队、流式和完整请求表现 |

引擎tg高、HTTP吞吐低，不一定是引擎有故障。HTTP增加了模板、请求调度、缓存、队列与客户端开销；负载也可能完全不同。先把边界写到表头，再解释差异。

## 3. 核心指标怎样计算？

设请求发送时间为`t0`，首个有效正文到达为`t1`，流结束为`t2`，输出token数为`N`。客户端TTFT约为`t1-t0`，E2E为`t2-t0`，在`N>1`时，按这种边界估算的TPOT为`(t2-t1)/(N-1)`。结束事件与传输也包含少量开销，应说明测量方式。

流式事件可能一次携带多个token，事件间隔不能无条件当作逐token ITL。本书小型客户端记录首正文与总耗时，不伪造逐token时间戳。正式工具应查清其ITL采样和聚合定义。

整个测试窗口的输出吞吐是成功请求实际输出token总数除以窗口总时间；请求吞吐是成功完成数除以窗口时间。它们都不同于“各请求token/s的平均数”。失败、超时和重试必须单列，否则快失败也可能让报告显得很好。

百分位必须说明样本量、样本对象和算法。请求级TTFT的P99与所有token间隔的P99不是一回事；4个请求算出的P99没有稳定容量意义。Goodput进一步限制只有同时满足质量和延迟目标的请求才计入有效产出，适合服务验收。

## 4. 先测单实例引擎基线

确认同设备没有另一个模型竞争后运行：

```bash
llama-bench -m artifacts/gguf/Qwen3-0.6B-Q4_K_M.gguf \
  -ngl 0 -t 4 -p 64 -n 32 -r 3 -o json > engine.json
```

保存程序提交、模型摘要、后端、线程、pp/tg长度与重复次数。本书实际Q8 CPU结果是pp64为319.08±17.26token/s，tg32为69.88±0.22token/s。它们属于不同阶段；不可把pp与tg求平均变成“模型综合速度”。

第一次加载、编译、图捕获和预热与稳定生成分开记录。端侧用户关心首次打开等待，服务工程师还关心长时间运行，两者都值得测。

## 5. 再测 HTTP 并发曲线

先完成正常、流式与异常API检查，再开始压测。vLLM服务示例接续[部署章](../frameworks/vllm-service.md)，保持同一别名、端口与tokenizer：

```bash
for c in 1 2 4; do
  vllm bench serve \
    --backend openai-chat --base-url http://127.0.0.1:8001 \
    --endpoint /v1/chat/completions \
    --model Qwen3.6-35B-A3B-FP8 \
    --tokenizer /srv/models/Qwen3.6-35B-A3B-FP8 \
    --dataset-name random --random-input-len 2048 \
    --random-output-len 128 --num-prompts 100 \
    --max-concurrency "$c" --request-rate inf --seed 42 \
    --save-result --save-detailed --result-dir "results/c${c}"
done
```

这是新增测试计划，没有补造运行成绩。先从小并发运行，错误或资源压力出现时停止扩展，检查日志与容量。各档使用相同样本量与任务，正式比较还应多轮运行，控制热状态并观察方差。

vLLM bench的模型别名用于请求，tokenizer路径用于构造和计数，两者用途不同。使用某版本参数前先保存`vllm bench serve --help`；旧`benchmark_serving.py`脚本与新CLI不能随意混搭。

### 使用 EvalScope 的同类测试

作者oMLX工程使用EvalScope1.7.0。同一工具也能测兼容HTTP服务。独立环境安装`evalscope[perf]==1.7.0`后，先查看perf帮助；示例仍接上述服务：

```bash
evalscope perf \
  --parallel 1 2 4 --number 100 100 100 \
  --url http://127.0.0.1:8001/v1/chat/completions \
  --model Qwen3.6-35B-A3B-FP8 --api openai \
  --dataset random --min-prompt-length 2048 --max-prompt-length 2048 \
  --min-tokens 128 --max-tokens 128 \
  --tokenizer-path /srv/models/Qwen3.6-35B-A3B-FP8 --stream
```

工具默认采样、输出目录与参数以该安装版本为准，运行前保存完整配置。不要用两种工具各自默认的数据集和计时方式比较框架优劣。

## 6. 并发与到达率是不同实验

固定并发通常采用闭环：一个请求结束再补上一个。开放到达率则按计划时间发起请求，服务落后时队列可能持续增长。到达率inf表达尽快发起，结合客户端并发上限决定实际发出方式；没有上限时会形成突发。

作者GB10历史200请求突发平均TTFT约148秒，说明该负载的排队很重。它不代表模型计算首token要148秒，也不能据此估计轻载延迟。应补充有限并发和逐步到达率，再观察队列是否稳定。

## 7. 两组真实并发结果怎样分析？

本书CPU结果如下。每组4请求、128输出token，原始文件见[HTTP汇总](../../practice/first-service/results/2026-10-18-windows-cpu/http-summary.json)：

| 客户端并发 | HTTP成功 | 输出吞吐 | 平均TTFT | 平均E2E |
| --- | --- | --- | --- | --- |
| 1 | 4/4 | 53.18token/s | 131.16ms | 601.56ms |
| 2 | 4/4 | 82.12token/s | 217.49ms | 778.99ms |

并发2增加了总产出，同时平均请求等待变长。这就是需要画吞吐与延迟两条曲线的原因。该小样本只说明本次观察，不能说明长时间稳定性或所有并发趋势。

oMLX历史测试也出现相同方向：c1/c2/c4输出吞吐29.38/41.11/55.15token/s，平均请求延迟7.582/10.257/13.459秒。但请求数分别20/10/10，缓存与原始文件不全，只能保留为历史参考，不能与CPU数据混排成硬件排名。

## 8. 同时观察资源与质量

NVIDIA可在独立终端按秒采样显存、计算利用率、温度和功耗，CPU与统一内存平台记录RSS、可用内存、swap、频率和热状态。进程结束时停止自己启动的采样器，标明采样频率；一秒采样可能漏掉很短的峰值。

服务指标补充活动请求、排队请求、KV占用、命中、抢占/重算、错误和引擎运行状态。客户端TTFT高而计算利用率低时，还要排查客户端、tokenizer、网络和队列，不能立即增加GPU预算。

质量检查至少确认完整答案、JSON合法性和典型任务。速度提高却输出乱码、错误或只剩思考，应判为质量未达标。性能报告的通过标准由项目目标决定，不由这次最快结果倒推。

## 9. 一份能复查的结果目录

```text
results/run-id/
├── environment.json
├── model-manifest.json
├── server-command.txt
├── workload.json
├── requests.jsonl
├── responses.jsonl
├── resource.csv
├── server.log
├── summary.json
└── acceptance.md
```

保留工具原始文件，汇总从原始数据计算。最终结论写清负载、质量、延迟、容量和失败边界，推荐一个满足需求的工作点；不要只写“提升了多少百分比”。
