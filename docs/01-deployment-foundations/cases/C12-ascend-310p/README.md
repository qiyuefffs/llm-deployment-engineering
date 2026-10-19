---
id: C12
title: "昇腾310P3：CANN容器、Qwen3部署与性能验收"
type: case
volume: cases
layer: 1
platform: "Ascend"
device: "Ascend 310P3"
status: historical
source_ids: [R45, R46, R47]
updated: 2026-10-19
summary: "技术标签：CANN / torchnpu / vLLM Ascend / TP2 / EvalScope"
---

# 昇腾310P3：CANN容器、Qwen3部署与性能验收

[工程实例索引](../README.md) · [知识体系总目录](../../SUMMARY.md)

技术标签：`CANN / torch_npu / vLLM Ascend / TP2 / EvalScope`

## 结论

R47 的一次请求输出14336 tokens、耗时3120.88 s，输出吞吐4.5936 tok/s；
同文另有5请求组。并发参数写10或30不代表实际已跑满10或30路，请求数和
完整时序必须一并查看。

## 适用边界

昇腾310P3双设备的特定 CANN/torch_npu/vLLM Ascend 组合。32B的有效
float16路径与235B/bfloat16尝试分开，不能套用910系列支持表或另一镜像的结论。

## 环境与制品

| 项目 | 原记录 |
| --- | --- |
| 设备 | 昇腾310P3，双设备 |
| 模型 | Qwen3-32B；Qwen3-235B-A22B作为另一配置探索 |
| 镜像 | quay.io/ascend/vllm-ascend:v0.10.0rc1-310p |
| 32B有效路线 | float16、TP2、mp、eager、block64、swap16 |
| 历史长输出 | 1请求、14336输出token、3120.88s、约4.5936token/s |

## 执行路径

1. `npu-smi info`核对芯片、驱动/固件，固定CANN、torch_npu、插件和镜像配套。310P的支持不能套用910系列。
2. 准备HF完整模型目录，显式挂载`davinci0/1`、manager、svm和驱动库。原文多种镜像、MindIE与插件版本属于不同实验分支，分别复建。
3. 进入容器先检查设备，再运行下方float16的32B路径。源材料另有bfloat16/235B命令，它们是尝试配置，不等于在双310P完成容量和算子验收。
4. 从可工作的目录启动，记录模块导入位置与`VLLM_USE_V1`的最终值；定位源码遮蔽后再切换执行模式。
5. 端点与字段匹配后做单请求、流式和长度验收，再进入EvalScope。原`parallel10/number1`实际上只提交一个请求。

### 原32B服务入口

在设备节点、驱动库和模型已挂载的配套容器内，R45给出：

```bash
python -m vllm.entrypoints.openai.api_server \
  --model /data/models/Qwen3-32B --served-model-name Qwen3-32B \
  --host 0.0.0.0 --port 8000 --tensor-parallel-size 2 --dtype float16 \
  --max-model-len 32768 --gpu-memory-utilization 0.95 \
  --distributed-executor-backend mp --enforce-eager --trust-remote-code \
  --block-size 64 --swap-space 16
```

检查点是两设备均可见、模型rank初始化、float16算子路径、API短生成与
长输出。`VLLM_USE_V1` 在不同尝试中设置过或unset过，记录最终环境值，
不把两种分支的启动日志合成同一次成功。

### 历史长输出测试命令

```bash
evalscope perf --url http://127.0.0.1:8000/v1/completions \
  --model Qwen3-32B --api openai --dataset openqa \
  --parallel 10 --number 1 --max-tokens 14336 --min-tokens 1024 \
  --stream --connect-timeout 60 --read-timeout 120 \
  --log-every-n-query 1 --name Qwen3-32B
```

这是completion端点，不应改发chat的messages字段。另开监控采集
`npu-smi info`，保留请求、token、墙钟与错误。输出上限很大时，read timeout
与单次请求总时长不同，不能只看命令中的120就判定总任务不可能超过120秒。

## 结果

先保证float16算子路径、TP2通信和短请求正确；再对ctx、活动序列、block、eager/图模式及插件支持的算子优化做分项实验。每次保存实际生效参数、NPU内存/利用率、输出token和墙钟时间。

现有14336token长生成只证明该样例，不能证明十并发或稳定p99。新并发测试应固定长度、足够请求数，检查超时、结束原因与质量。

| R47组别 | 实际请求 | 输出与时间 | 可解释范围 |
| --- | ---: | --- | --- |
| parallel10 / number1 | 1/1成功 | 14336 tokens，3120.88 s，4.5936 tok/s | 单请求长输出 |
| parallel10 / number5 | 5/5成功 | 平均输出3574.4 tokens，总窗口1816.71 s，聚合9.8376 tok/s | 5请求混合长度 |
| parallel30 / number5 | 5/5成功 | 总窗口1817.25 s，聚合9.8346 tok/s | 没有30个请求，不证明30并发 |

首组TTFT0.2364 s，TPOT0.2177 s/token。单请求的各分位数反复相同不能
代表稳定P99；五请求组长度差异大，也不能只用平均延迟比较调度能力。

## 失败与修订

原记录包含源码目录运行导致模块导入问题、V1设置反复调整和不同镜像尝试。
先核对工作目录、模块路径和实际版本，再定位算子与资源。235B命令只保存
尝试配置，没有足够材料证明双310P完成容量、质量和服务验收。

## 证据

- [R45 完整技术正文](../../evidence/sources/R45.md)
- [R46 完整技术正文](../../evidence/sources/R46.md)
- [R47 完整技术正文](../../evidence/sources/R47.md)

## 未验证

足够请求数的固定长度并发矩阵、同资源调优消融、长期稳定性和完整质量题集
仍未完成。MindIE、不同插件及大模型尝试不继承32B路径的成功状态。

数据来源与边界见[证据使用说明](../../meta/evidence-policy.md)。
