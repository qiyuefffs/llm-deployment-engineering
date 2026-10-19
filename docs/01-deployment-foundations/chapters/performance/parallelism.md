---
id: T37
title: "多卡与多节点：先解决容量，再验证通信和收益"
type: tutorial
volume: book
layer: 4
platform: "general"
device: "general"
status: historical
source_ids: []
updated: 2026-10-19
summary: "多设备部署通常有两种目标：单设备放不下，或单副本的服务容量不足。前者需要切分或卸载，后者可能适合多个副本。把目标说清，才能选择TP、PP、DP、EP或RPC，而不是先把所有设备连起来。"
---

# 多卡与多节点：先解决容量，再验证通信和收益

[总目录](../../SUMMARY.md) · [性能总章](../../02-capability-layers/04-memory-performance.md) · [通信冒烟脚本](../../examples/all_reduce_check.py)

## 本章概览

多设备部署通常有两种目标：单设备放不下，或单副本的服务容量不足。前者需要切分或卸载，后者可能适合多个副本。把目标说清，才能选择TP、PP、DP、EP或RPC，而不是先把所有设备连起来。

本章来自FlowUs的双RTX4080容器、多节点排障和AMD五机RPC记录。历史结果用于解释实际问题，不将“多机运行成功”自动写成“多机加速”。

## 1. 几种并行方式的区别

TP将层内张量计算切分到多设备，常在每层产生通信；PP把模型阶段分配到不同设备，阶段之间传递激活；DP部署多个可独立处理请求的副本；MoE的EP分布专家并涉及路由和通信。具体组合受模型、框架和设备支持约束。

TP不一定等于单机GPU数，PP也不一定等于节点数。这些是候选映射方式，最终要看单卡容量、层数、算子、互连带宽、负载与流水线气泡。端侧网络慢时，容量扩展可能成功，单请求延迟却更高。

两张16GB卡不能无条件当作一张32GB卡使用。权重、KV、工作区和通信缓冲需要按rank分别预算。单个无法切分的大张量、某个rank的额外开销或不均匀层分配，都可能先触发OOM。

## 2. 检查物理拓扑与单设备

NVIDIA先看`nvidia-smi topo -m`和实际PCIe连接；AMD看设备、RCCL与P2P条件；昇腾核对HCCL和芯片支持。双RTX4080没有NVLink，应按实际PCIe拓扑验证，不写安装NVLink桥的步骤。

每个设备先独立完成分配、计算与小模型生成。多节点还要统一程序版本、容器、模型revision与时间基准，确认地址可达和所需端口。公开文档使用`NODE_A`、`NODE_B`等占位符，私人节点地址不入仓库。

## 3. 先做最小通信正确性测试

仓库提供[all_reduce_check.py](../../examples/all_reduce_check.py)，在配套PyTorch/NCCL环境从仓库根目录运行：

```bash
torchrun --standalone --nproc-per-node=2 \
  docs/01-deployment-foundations/examples/all_reduce_check.py
```

脚本用于检查各rank的设备与归约值，属于正确性冒烟。它没有证明大消息带宽、通信稳定性或模型适配。本轮未在双GPU执行，运行记录应由实际设备测试生成。

多节点要再测节点间通信，并保存网卡、路由、通信库日志和消息大小。Ray节点显示alive只证明控制面的一部分，不证明NCCL/RCCL/HCCL链路和模型执行都通过。

## 4. 启动模型后按 rank 检查

确认模型与硬件支持TP后，可在同一节点的两个可见设备上使用说明模板：

```bash
CUDA_VISIBLE_DEVICES=0,1 vllm serve /srv/models/example-model \
  --served-model-name example-model \
  --host 127.0.0.1 --port 8001 \
  --tensor-parallel-size 2 \
  --max-model-len 4096 --max-num-seqs 1 \
  --gpu-memory-utilization 0.80
```

这是配置模板，不是已经跑过的通用模型命令。检查每个rank加载、KV分配、通信初始化与首次生成；某个worker退出时，保存最早的异常，不要只看主进程最后的超时。

短请求通过后增加长度，再增加并发。长输入失败与多rank初始化失败属于不同阶段，修复方向也不同。

## 5. AMD 五机 RPC 记录怎样理解？

作者五台395设备使用ROCm7.2.1、HIP7.2.53211-e1a6bc5663、llama.cpp b9557和gfx1151。首次较大分配失败，与GTT/TTM限制有关；修复后设备可见容量从63215MiB变为120000MiB。这是驱动和内存预算问题，不是简单把系统物理内存数写进参数就能解决。

历史Kimi小上下文记录pp约19.3、tg约8.2token/s；Qwen冒烟约40.3/21.3token/s。模型、长度和工作负载不同，应分别保存。源文中的32768上下文命令属于建议，没有足够结果支持长上下文已验收。

RPC让主进程调用远端后端资源，并不自动等于vLLM的TP。需要确认切分策略、远端缓冲、网络传输和失败恢复。缺少同一模型同一负载的单机基线，就不能计算五机加速比；若单机根本放不下，可报告“容量扩展到可运行”，并单独说明延迟代价。

## 6. 多设备性能怎样比较？

先保留单设备或最小可运行配置的基线，再记录设备数、切分、总资源、输入输出、并发、实际token与质量。若模型精度也改变了，收益是整套配置变化，不能只归因于设备数。

在线服务还要比较多个单卡副本与一个多卡副本。模型能单卡放下时，DP可能提升总请求容量；模型放不下时先解决容量。但最终仍需看满足延迟目标的有效吞吐，而不是GPU总利用率。

## 7. 故障收束顺序

按单设备、同节点通信、跨节点通信、分片加载、单请求、长请求、负载和故障恢复逐层检查。卡住时先确认每个rank停在哪个阶段，并核对首次错误、版本、网卡、端口和超时。

交付时说明节点退出后的行为：请求失败、超时、重启还是可以转移。停止与回滚应针对自己管理的实例，模型文件和配置也要能恢复到已验证组合。

## 八、完整操作：W7900双节点怎样形成一个服务

作者旧笔记有两种模型规模：70B与671B。它们都使用ROCm/Ray/vLLM，但卡数、TP/PP和容量不同，不能把片段接成一个没有统一配置的启动脚本。下面先把节点、资源与启动顺序理清，再列原671B参数。

### 8.1 先建立节点配置表

两台机器的镜像、ROCm用户态库、Python依赖、模型revision与目录保持一致。容器能访问本机所有目标GPU，head和worker选择用于节点通信的同一路由网络。

| 项目 | Head | Worker |
| --- | --- | --- |
| 角色 | Ray head与一个API服务 | Ray worker |
| GPU | 本机8个W7900 | 本机8个W7900 |
| 模型路径 | `/srv/models/DeepSeek-R1-AWQ` | 相同逻辑路径、相同制品 |
| 通信地址 | `$HEAD_ADDRESS` | `$WORKER_ADDRESS` |
| 主要检查 | 本机枚举、Ray资源、API与worker分配 | 本机枚举、Ray加入、模型加载与通信 |

地址变量由当前实验环境填写，不在仓库保存私人节点IP。各节点独立验证GPU后，再继续集群。

### 8.2 先启动控制面

在head的配套容器中前台运行：

```bash
ray start --head --node-ip-address="$HEAD_ADDRESS" --port=6379 --block
```

在worker容器运行：

```bash
ray start --node-ip-address="$WORKER_ADDRESS" --address="${HEAD_ADDRESS}:6379" --block
```

在head另一终端查看`ray status`，确认两节点和预期GPU资源。端口6379只覆盖head入口，Ray与通信库还会使用其他端口；固定端口范围和访问规则应按当前Ray部署文档配置，不能只开放一个端口后把所有超时归给模型。

### 8.3 再验证通信数据面

Ray资源可见后，用匹配的PyTorch/RCCL环境测试跨节点归约，保存每rank结果与通信日志。先验证小消息正确性，再测目标消息大小与持续传输。需要选择网卡时，确认IP、路由和物理接口对应，避免控制面走一张网卡、集合通信选到不可达接口。

PyTorch的ROCm构建仍可能使用名为`nccl`的backend接口，实际底层为RCCL；应从构建信息和运行日志确认，不能因API名字出现nccl就认定安装了CUDA版torch。

### 8.4 一个head API调度整套资源

原671B路线使用TP8×PP2，共16个rank。head启动一个OpenAI API入口，由Ray组织分布式worker；worker节点只加入资源池，不再独立启动另一份相同API来假装“共同推理”。

```bash
python -m vllm.entrypoints.openai.api_server \
  --model /srv/models/DeepSeek-R1-AWQ \
  --served-model-name deepseek-r1-awq \
  --host 127.0.0.1 --port 8001 \
  --distributed-executor-backend ray \
  --tensor-parallel-size 8 --pipeline-parallel-size 2 \
  --max-model-len 4096 --max-num-seqs 16 \
  --max-num-batched-tokens 4096 \
  --gpu-memory-utilization 0.85 \
  --disable-custom-all-reduce
```

这些是原路线关键参数的顺序整理。量化格式、模型结构及该版本对AWQ/TP/PP的支持都要先确认，不能把16卡总容量算够就当成加载保证。源中没有完整性能结果，本节不为它填写吞吐。

70B旧笔记混有TP2/PP2、TP4等不同方案，应该先按真实卡数与容量选定一个组合，生成独立配置，不能从每段各选一个参数。TP×PP给出rank规模，但具体落在哪些GPU、是否跨节点，还要核对实际placement和通信。

## 九、控制面成功、模型失败时怎样逐步缩小范围

### 9.1 资源不够还是worker没注册

先比较预期GPU与Ray可用资源，核对容器环境的可见设备和worker日志。一个节点只注册了CPU时，继续降低模型长度不会让GPU自动出现。资源表正确再看placement是否等待，以及是否有另一个作业占用。

### 9.2 模型路径是否相同

head进程能读模型不代表远端worker也能读。检查每节点挂载、文件权限、分片索引与摘要。safetensors拆成多个文件只改变磁盘组织，TP/PP运行时仍需要从完整逻辑模型中读取各自张量。

### 9.3 环境变量是否传到worker

在head终端设置的变量不一定进入已经启动的远端Ray进程。设备选择、通信网卡和库路径应在各worker的启动环境或受控runtime配置中明确。检查实际worker环境时只输出必要技术字段，避免整份环境转储带入凭据。

### 9.4 用dummy load只能验证哪一段

固定版本支持dummy load时，可以暂时绕过真实权重I/O，帮助判断初始化、图与通信是否仍失败。但它没有验证模型文件、真实权重精度或任务质量。dummy通过后换回真实加载，继续单请求验收，不能把dummy吞吐作为模型成绩。

### 9.5 看第一条worker异常

API最终显示EngineDead或超时，通常是上游worker已先失败。按时间检查每个rank的第一条错误，区分权重分配、通信初始化、warmup/kernel与输入执行。保存错误前后的版本、rank、设备和输入，才能构造最小复现。

## 十、RPC与Ray/TP/PP分别怎样观察网络

AMD五机RPC的A负责读分片、向远端发送张量，加载阶段可能按设备顺序传输；Ray/vLLM路径则包含worker资源管理、模型分片加载和集合通信。两者网络曲线的解释不同，不能只看到一个连接忙就套同一种判断。

读盘主导时观察`/proc/PID/io`与磁盘延迟；传输主导时看bytes_acked、重传、RTT和实际接口吞吐；通信计算重叠不佳时再结合Profiler。网络标称速率不等于有效模型速度，短小RPC频次、同步等待和消息大小都可能成为限制。

多节点最后要做一次受控故障：在专用测试服务中让一个worker退出，记录正在运行请求的返回、主服务健康变化、资源释放与恢复步骤。不能承诺框架自动迁移正在执行的KV，除非对应机制已实际验证。

## 十一、什么时候优先多个副本

模型能在单设备正确运行时，多副本可以让请求彼此独立，并降低某些跨设备通信需求；代价是复制权重与各自KV。模型单设备放不下时，先做容量切分，必要时再多副本扩容。

比较“2个单卡副本”与“1个双卡副本”，要用相同总硬件、同质量模型、同输入输出和相同SLO。总GPU利用率、单请求最低延迟与服务有效吞吐可能指向不同方案。结论应回到项目约束，而不是把设备串联数量当成优化程度。
