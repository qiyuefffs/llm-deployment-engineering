---
id: C08
title: "AMD W7900：单机多卡、双节点Ray与TP/PP部署"
type: case
volume: cases
layer: 1
platform: "AMD"
device: "Radeon W7900"
status: historical
source_ids: [R26, R27, R28, R29, R30, R31, R32, R33, R34]
updated: 2026-10-19
summary: "技术标签：ROCm / RCCL / Ray / TP / PP / DeepSeek"
---

# AMD W7900：单机多卡、双节点Ray与TP/PP部署

[工程实例索引](../README.md) · [知识体系总目录](../../SUMMARY.md)

技术标签：`ROCm / RCCL / Ray / TP / PP / DeepSeek`

## 结论

本章保存 W7900 双卡、四卡、八卡与双节点的多条部署记录。单节点八卡
每卡48GB，双节点 TP8×PP2 对应16个 rank；Ray 注册成功不代表这些 rank
已完成集合通信或模型生成。现有材料没有统一可比较的吞吐表。

## 适用边界

R26–R34 的模型、精度、卡数和引擎版本不同，按独立实验复建。尤其 671B
AWQ 的 safetensors 路线和 GGUF 路线由不同引擎执行，不能混用启动参数。

## 环境与制品

| 实例 | 设备 / 模型 | 执行路线 |
| --- | --- | --- |
| 单机双卡 | W7900，Qwen3-30B-A3B / DeepSeek32B/70B | ROCm vLLM、TP2 |
| 单机四卡 | DeepSeek70B FP16 | TP4，原c1/c2/c4配置分组 |
| 单机八卡 | W7900×8、每卡48GB；DeepSeek-R1 AWQ INT4 | ROCm容器、TP8、量化kernel |
| 双节点 | 每节点8GPU的记录 | Ray组织worker；TP8×PP2表示16rank，不是8卡配置 |

## 执行路径

1. 每节点记录`rocminfo/rocm-smi`、驱动、ROCm、torch HIP、容器digest与GPU拓扑。两台节点保持同模型文件和版本。
2. 容器先接入`/dev/kfd`和目标`/dev/dri`；在容器内完成小矩阵计算，随后单GPU模型、单机TP，再进入Ray。
3. 分别验证节点间连通、Ray资源注册、RCCL集合通信与模型rank映射。Ray ready只能说明控制面可用，不能代替GPU通信或目标模型执行。
4. 主节点与worker分别执行其角色命令。`ray start --head`只用于head，worker使用`--address`加入；IP、网卡和端口按本地部署配置。
5. 基础模型请求正确后，按目标ctx/seqs加载；保存每rank内存、KV块、通信错误与API输出。

### 单节点八卡的历史模型加载入口

R26 在配套 ROCm 容器中给出下面的 AWQ 配置：

```bash
python3 -m vllm.entrypoints.api_server \
  --model /app/models/DeepSeek-R1-awq --served-model-name DeepSeek-R1 \
  --tensor-parallel-size 8 --max-model-len 4096 --max-num-seqs 8 \
  --max-num-batched-tokens 2048 --gpu-memory-utilization 0.95 \
  --enforce-eager --quantization awq --dtype bfloat16 \
  --trust-remote-code --port 8000
```

该入口为原版本的 native `api_server`，不能默认具有 OpenAI chat schema。
R26 另列 OpenAI server 和 llama.cpp 验证命令，复测必须让端点、payload
与所选入口一致。命令存在不等于八卡目标模型的性能和质量已完整验收。

### 双节点先验证控制面，再验证数据面

先核对两端镜像、模型文件和 GPU runtime；head 只启动一次，worker 加入
同一 Ray 集群。读取 Ray 报告的总 GPU 与每节点资源，确认 rank 分配实际
覆盖预期设备，再观察 RCCL 日志、网络接口和模型加载。

R30–R34 中资源调度和模型启动反复修订，不能把最后的启动语句套回前一轮
资源状态。TP/PP 的乘积要与可用 GPU 对应；发现调度等待时先查 worker
注册和资源申请，不先调高 `gpu-memory-utilization`。

### 性能测试怎样保持可比

固定总卡数、模型、精度、输入输出和请求集，分别记录权重加载、首请求、
稳态 Prefill/Decode、每卡内存和通信错误。不同卡数的系统比较还要写总资源，
不把容量增加直接算作算力收益。

## 结果

对比TP/PP时固定总卡数、模型、精度、输入输出与负载。TP增加层内通信，PP引入阶段流水与气泡；不能只因总显存增加就推导速度增加。角色与资源解释见[多设备专题](../../chapters/performance/parallelism.md)。

没有完整吞吐数字的实验不补填数字。新实验至少提供单机/多机的成功请求、实际token、时长、TTFT/TPOT、每rank资源和错误；配置项中的最大并发并非实际并发结果。

| 来源组 | 保存的工程内容 | 结果解释范围 |
| --- | --- | --- |
| R26/R27 | 八卡 AWQ/GGUF 与双卡 Qwen 部署 | 独立模型路径，不构成速度对照 |
| R28/R29 | 双卡及四卡蒸馏模型配置 | 卡数、精度、并发均需单独固定 |
| R30–R34 | Ray、TP/PP、调度与排障迭代 | 可定位启动过程，缺统一性能矩阵 |

## 失败与修订

Ray ready 只覆盖控制面；RCCL 连接、rank 映射和目标模型请求分别留证。
原容器中出现过 `HSA_OVERRIDE_GFX_VERSION` 和后端环境变量，它们属于
当时适配组合，不宜未经验证复制到新版本。`--shm-size` 设置值也不代表
物理 GPU 内存已经增加。

## 证据

- [R26 完整技术正文](../../evidence/sources/R26.md)
- [R27 完整技术正文](../../evidence/sources/R27.md)
- [R28 完整技术正文](../../evidence/sources/R28.md)
- [R29 完整技术正文](../../evidence/sources/R29.md)
- [R30 完整技术正文](../../evidence/sources/R30.md)
- [R31 完整技术正文](../../evidence/sources/R31.md)
- [R32 完整技术正文](../../evidence/sources/R32.md)
- [R33 完整技术正文](../../evidence/sources/R33.md)
- [R34 完整技术正文](../../evidence/sources/R34.md)

## 未验证

统一同负载吞吐、单机/双机加速比、每 rank 资源峰值、质量与长时间通信
恢复仍缺完整证据。未记录模型 revision 的分支需先补齐制品身份。

数据来源与边界见[证据使用说明](../../meta/evidence-policy.md)。
