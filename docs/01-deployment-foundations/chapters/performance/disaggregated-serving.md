# 分离式推理：PD分离、KV传输与MoE并行

[总目录](../../SUMMARY.md) · [缓存与调度](cache-scheduling.md) · [多卡并行](parallelism.md) · [当前引擎选型](../frameworks/serving-engines.md)

**资料核查：2026-10-18。** 本章命令根据官方文档整理，尚未在本仓库的多GPU环境执行。PD分离属于需要额外设备、网络和运维验证的服务架构。

## 1. 从单引擎的两个阶段看问题

Prefill批量处理输入，建立生成所需的状态；decode利用已有状态继续生成。长输入prefill插入正在decode的batch时，可能拉长流式输出间隔。chunked prefill通过分块调度减轻干扰，但两个阶段仍共享同一组设备。

PD分离将prefill和decode放到不同实例。prefill完成后，将相应KV和必要元数据交给decode实例。这样可以分别调整两侧设备、batch、并行与容量，代价是新增KV传输、路由、等待队列和故障处理。

```text
客户端 → Router → Prefill实例 → KV传输/状态映射 → Decode实例 → SSE
                   ↑                 ↑                 ↑
              输入token/模板     块表/位置/身份      采样/取消/回收
```

它首先解决阶段干扰和资源分工。是否提高吞吐取决于原瓶颈和新增成本，不能将“分离”直接写为加速。端侧只有一块GPU时，先做好chunked prefill、prefix cache、token预算和量化，通常更容易获得可解释的结果。

## 2. 三种容易混淆的KV机制

| 机制 | 复用或搬运什么 | 主要目标 | 额外成本 |
| --- | --- | --- | --- |
| Prefix cache | 已算过且匹配的输入前缀状态 | 减少重复prefill | 驻留空间、索引、挤出 |
| KV offload | GPU状态与CPU内存/其他介质之间搬运 | 扩大状态容量或保留更多前缀 | 主机内存、链路、搬运延迟 |
| PD KV transfer | 将一个实例生成的状态送到另一实例 | 阶段分工 | 网络、格式映射、跨实例生命周期 |

NIXL是传输库，Mooncake提供KV相关存储与传输能力；具体引擎通过connector/transfer backend接入。安装这些包只解决依赖，不会自动得到完整的PD系统。

## 3. 先算传输是否值得

对普通GQA架构，可用下面的理想公式估算一次独立长输入的KV数据量：

```text
KV字节 = 2 × 层数 × KV heads × head_dim × 输入token × 元素字节
传输时间下界 ≈ 需传输的实际字节 / 有效链路带宽
```

教学算例：32层、8个KV heads、head_dim128、BF16、8192输入token，约产生1GiB的KV。10GbE的理论线速为1.25GB/s，完整传输1GiB即约0.86秒，尚未计协议与调度；若实测有效带宽只有1GB/s，则约1.07秒。这不是设备实测，也不是所有模型都传1GiB。

分页、MLA、滑动窗口、量化、层间流水与缓存命中会改变实际字节。先记录实际传输量，再比较原prefill/decode干扰损失；不能用网卡标称带宽掩盖小包、内存注册和CPU协议开销。

## 4. SGLang两GPU最小流程

本例使用同机两块GPU，分别能容纳完整的Llama-3.1-8B-Instruct实例和所需缓存。模型需先取得访问许可，并放到本地完整目录。按官方配套环境准备SGLang、router和NIXL，固定版本并保存依赖清单；不要将不配套的最新wheel混装进旧环境。

### 4.1 检查当前环境和参数

```bash
mkdir -p records/pd
python -m pip show sglang sglang-router nixl > records/pd/packages.txt
python -m pip freeze > records/pd/requirements-resolved.txt
python -m sglang.launch_server --help > records/pd/server-help.txt
python -m sglang_router.launch_router --help > records/pd/router-help.txt
nvidia-smi topo -m > records/pd/topology.txt
```

确认帮助包含`--disaggregation-mode`与`--disaggregation-transfer-backend`。先用一个普通SGLang实例验证模型、模板、精度、输入长度和质量集，保存同设备资源下的对照。

### 4.2 启动prefill实例

在终端P运行：

```bash
CUDA_VISIBLE_DEVICES=0 python -m sglang.launch_server \
  --model-path /srv/models/Llama-3.1-8B-Instruct \
  --disaggregation-mode prefill \
  --disaggregation-transfer-backend nixl \
  --host 127.0.0.1 --port 30000 \
  > records/pd/prefill.log 2>&1
```

### 4.3 启动decode实例

在终端D运行：

```bash
CUDA_VISIBLE_DEVICES=1 python -m sglang.launch_server \
  --model-path /srv/models/Llama-3.1-8B-Instruct \
  --disaggregation-mode decode \
  --disaggregation-transfer-backend nixl \
  --host 127.0.0.1 --port 30001 \
  > records/pd/decode.log 2>&1
```

每个进程只看见一块GPU，其本地编号均为0。不要再将decode设为本地GPU1。通过两侧日志确认加载和传输初始化完成。

### 4.4 启动router并发请求

终端R运行：

```bash
python -m sglang_router.launch_router \
  --pd-disaggregation \
  --prefill http://127.0.0.1:30000 \
  --decode http://127.0.0.1:30001 \
  --host 127.0.0.1 --port 8000 \
  > records/pd/router.log 2>&1
```

客户端只访问router：

```bash
curl --fail-with-body http://127.0.0.1:8000/v1/models
curl --fail-with-body http://127.0.0.1:8000/v1/chat/completions \
  -H 'Content-Type: application/json' \
  -d '{"model":"/srv/models/Llama-3.1-8B-Instruct","messages":[{"role":"user","content":"Explain prefill and decode in two sentences."}],"max_tokens":128,"temperature":0}'
```

模型字段以`/v1/models`返回的ID为准。应能在P侧看到prefill活动、D侧看到生成活动。随后增加公开长输入，保存双方日志和实际传输量。普通回答正确但未发生KV传输，不能判定PD验收通过。

### 4.5 vLLM的对应路线

vLLM通过`--kv-transfer-config`接入connector。当前NIXL示例使用：

```json
{"kv_connector":"NixlConnector","kv_role":"kv_both"}
```

两侧传输配置、路由程序、请求关联与运行入口必须使用同一版本的官方示例。只在两个server上加入这段JSON，没有调用关联协议，不能形成完整链路。该功能在官方文档中仍标为experimental；直接使用对应提交的端到端示例验证，再接入自己的服务入口。

## 5. MoE的EP与PD分别解决什么

EP将专家分布到多个设备，token根据router结果发往所需专家，再将结果合回。PD将生成的两个阶段分开。它们可以组合，但不是同一个开关。

| 组件 | 计算/通信特征 | 重点指标 |
| --- | --- | --- |
| Attention TP/DP | 注意力状态与各自请求分配 | 每rank KV、复制、同步时间 |
| MoE EP | dispatch/专家计算/combine | all-to-all耗时、负载偏斜 |
| Prefill池 | 较大的token批量 | 输入token/s、队列、TTFT |
| Decode池 | 持续小步生成 | TPOT、ITL、驻留状态、输出token/s |

vLLM的MoE层分片与TP×DP组合有关，不能按普通dense模型的“DP一定复制全部权重”直接推断每rank的专家分配。`--enable-expert-parallel`也不自动保证通信库、GPU拓扑与模型kernel匹配。

专家热门程度不均，会让某些rank忙、其他rank等待。要看每rank专家token数、通信等待和尾延迟，再评估EPLB等负载均衡；不能只增加GPU数。DeepEP等后端的高吞吐/低延迟路径有不同适用条件，按实际prefill/decode负载选择。

## 6. 架构验收和停止条件

先比较相同总设备数：两个独立普通副本、同一引擎的多卡副本、PD两侧分工。若只给PD多一倍GPU，不能把全部容量增长归因于架构。

验收记录至少包含：两侧模型与模板身份、KV dtype/layout、块大小、TP/DP/EP、有效链路、传输字节、prefill排队、decode排队、TTFT/TPOT尾部、吞吐、错误与峰值内存。不同TP布局还可能需要gather/scatter或staging buffer，必须确认引擎支持。

对自己管理的测试实例，单独停止一个decode worker，检查router如何报错、取消是否传到prefill、KV多久释放；恢复后重发固定输入。若请求超时后KV不释放，长压测可能比短跑更早出问题。

**回到普通服务的条件：** 传输成本抵消阶段隔离收益、节点恢复不稳定、质量或状态一致性未通过，或同资源普通副本已经满足SLO。

## 7. 官方资料

- [SGLang PD文档与NIXL/Mooncake示例](https://docs.sglang.ai/advanced_features/pd_disaggregation.html)。
- [vLLM PD固定提交文档](https://github.com/vllm-project/vllm/blob/2365177ddda7714502e4df7a1669cc79c0a4dfd0/docs/features/disagg_prefill.md)。
- [vLLM Expert Parallel部署](https://docs.vllm.ai/en/stable/serving/expert_parallel_deployment/)。
- [NIXL项目](https://github.com/ai-dynamo/nixl) · [Mooncake项目](https://github.com/kvcache-ai/Mooncake)。
