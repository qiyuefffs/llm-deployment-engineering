---
id: C01
title: "NVIDIA RTX 2060 12GB：CUDA混合卸载与Qwen3量化推理"
type: case
volume: cases
layer: 1
platform: "NVIDIA"
device: "RTX 2060 12GB"
status: historical
source_ids: [R01, R02, R03]
updated: 2026-10-19
summary: "技术标签：CUDA / GGUF / CPU-GPU offload"
---

# NVIDIA RTX 2060 12GB：CUDA混合卸载与Qwen3量化推理

[工程实例索引](../README.md) · [知识体系总目录](../../SUMMARY.md)

技术标签：`CUDA / GGUF / CPU-GPU offload`

## 结论

R01 保存了一次 Qwen3-30B-A3B Q6 请求：9 个输入 token，182 个输出 token，
服务端 Prompt 9.04 tok/s、Decode 5.26 tok/s。R02/R03 保存了 EvalScope
命令，但附件明细未公开，不能补出完整并发成绩。

## 适用边界

这里是 RTX 2060 12GB 与 32GB 主机内存的 Windows CPU/GPU 混合路线。
Qwen3-30B-A3B 与 Qwen3-32B 是不同计算结构，后者不是前者只换量化精度。
历史配置中的 `parallel` 和 `tensor-split` 不能证明相应并发或分层实际生效。

## 环境与制品

| 项目 | 配置 |
| --- | --- |
| GPU / RAM | RTX 2060 12GB / 32GB主机内存 |
| 模型 | Qwen3-30B-A3B Q6；32B Q5作为容量对照 |
| 执行路径 | GGUF → llama.cpp CUDA → 部分层卸载 → OpenAI API |
| 主要约束 | 权重无法全部放入12GB；CPU端权重、KV和操作系统竞争32GB RAM |
| 原始测量 | Q6单次输入9token、输出182token；prefill约9.04token/s、decode约5.26token/s |

## 执行路径

1. `nvidia-smi`核对驱动与空闲显存；`free -h`、`vmstat 1`记录RAM与swap。该卡为Turing，不能按新卡假设具有原生FP8矩阵计算。
2. 按[CUDA构建说明](../../chapters/frameworks/llama-cpp.md)固定源码，构建`llama-server/llama-bench/llama-cli`。RTX2060可使用`-DCMAKE_CUDA_ARCHITECTURES=75`，核对实际日志。
3. 准备完整GGUF与SHA256。先以`-ngl 0 -c 2048 -np 1`验证CPU加载，再按16、24等档位增加卸载，直到保留足够设备工作区；不要把`-ngl 99`当作12GB卡必然可用的配置。
4. 相同prompt、输出预算、采样和线程下运行每档，保存`load time/prompt eval/eval/total`与CPU/GPU buffer。模型加载耗时与热生成分开。
5. 确定不发生swap抖动的配置后启动HTTP服务，检查模型列表、短题、长题、SSE和取消。原配置含parallel8，只能说明配置值；活动并发能力需另外压测。

```bash
./build-cuda/bin/llama-server \
  -m /srv/models/Qwen3-30B-A3B-Q6_K.gguf \
  --host 127.0.0.1 --port 8080 -c 2048 -np 1 -ngl 16
```

这是重新验证用的小预算入口，不是下方历史成绩的原始命令。最终卸载数按原记录与设备实测确定。

## 加速优化与验收

| 实验 | 固定条件 | 检查结果 |
| --- | --- | --- |
| 增加GPU卸载层 | 同制品、ctx、prompt、输出、线程 | decode、PCIe传输、CPU负载、显存余量 |
| Q6→Q5/Q4 | 同模型与任务；制品变化单独记录 | 内存下降、速度、答案质量；不能直接等价于无损 |
| 线程数调整 | 同卸载和输入 | CPU端耗时、上下文切换；线程越多不一定越快 |
| 槽位1→2 | 同长度与总样本 | 总吞吐、单请求TPOT、p95、失败率和RAM峰值 |

保留原来约5.26token/s的观测，不包装成稳定HTTP吞吐。合格配置必须完成目标任务，且RAM/swap、VRAM和尾延迟满足预先设定的预算。

### 历史实际参数和测试命令

R02 的 Q6 服务参数为 `top-k=1, ctx=2048, n=1000, tensor-split=0.9,0.1,
ngl=99, mlock, parallel=8`；R03 的 32B Q5 则为
`tensor-split=0.6,0.4, parallel=4`。它们是源记录中的命令，不代表本轮建议
对单卡照抄的切分配置。R01 另有可疑参数 `-ngld 99`，需以原版本帮助核对。

```text
evalscope perf --url http://127.0.0.1:8080/v1/chat/completions --model Qwen3-30B-A3B-Q6_K --api openai --parallel 8 --number 2 --stream
evalscope perf --url http://127.0.0.1:8080/v1/chat/completions --model Qwen3-32B-Q5_K_M --api openai --parallel 1 --number 5 --max-tokens 200 --stream
```

第一条只提交 2 个请求，即使 `parallel=8` 也不能形成八路有效压测；第二条
请求数更多但模型不同，不能与第一条算量化加速比。复测应先核对 models
中的实际模型 ID，保存每个请求的输入/输出 token、墙钟和失败信息。

## 结果

| R01 阶段 | 实际计数 | 服务端计时 | 复算口径 |
| --- | ---: | ---: | --- |
| Prompt | 9 tokens | 995.30 ms | 输入/Prompt 时间，约 9.04 tok/s |
| Eval | 182 tokens | 34,618.63 ms | 输出/Eval 时间，约 5.26 tok/s |
| 合计 | 191 tokens | 35,613.93 ms | 两阶段之和，不等于 HTTP TTFT |

资源观察还包括加载时主机 memory 82%–100%、运行时 85%–89%、GPU
98%–100%。原文“磁盘交换 100%”没有工具和采样定义，不能自行解释成
精确 swap 占用率或磁盘带宽饱和。

## 失败与修订

原文的高 memory、交换现象和配置并不能单独定位瓶颈。先核对实际卸载、
CPU/GPU buffer、分页和工作区，再调整层数；不能把 GPU utilization 高当成
延迟达标。Q6/Q5 对照又改变了模型结构，必须分组解释。

## 证据

- [R01 完整技术正文](../../evidence/sources/R01.md)
- [R02 完整技术正文](../../evidence/sources/R02.md)
- [R03 完整技术正文](../../evidence/sources/R03.md)

## 未验证

模型 revision、实际卸载层数、完整请求明细、质量对照和长时间稳定性未记录。
尚无受控的量化、线程、卸载层数单因素结果；本页提出的复测顺序不表示已经执行。

数据来源与边界见[证据使用说明](../../meta/evidence-policy.md)。
