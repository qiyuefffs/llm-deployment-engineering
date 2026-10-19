---
id: T41
title: "MiniMax-M2.7 多机推理"
type: tutorial
volume: book
layer: 4
platform: "AMD"
device: "Radeon 8060S / gfx1151"
status: historical
source_ids: [E21, E22]
updated: 2026-10-19
summary: "从 HIP 运行库分发、USB4 RPC 和分片加载，到 2/5 槽位验收、API timing 复算及加载观测。"
---

# MiniMax-M2.7 多机推理

[项目索引](README.md) · [通用性能优化测试方法论](../edge-llm-performance-methodology.md)

## 1. 任务、制品与记录边界

这个项目解决的是大模型跨设备加载和本地 API 服务。模型采用 MiniMax-M2.7
UD-Q4_K_M 四分片 GGUF，服务上报参数量 228,689,764,864，权重合计
140,161,616,896 bytes，约 130.57 GiB。入口是 `00001-of-00004.gguf`；
其余分片必须完整保留，不能把第一片当成独立模型。

本轮重新读到了两份双机原始记录，时间均为 2026-07-10，但服务配置不同。
后文分别称“2 槽位快照”和“5 槽位部署”，不把两份记录拼成同一轮运行。
三机数字仍保留为待回链历史摘要，见第 8 节。

| 项目 | 原记录内容 | 复现时的检查点 |
| --- | --- | --- |
| 计算设备 | Radeon 8060S，`gfx1151` | 两端都应由 HIP 原生识别 |
| 主机二进制 | `llama.cpp_b1294` 目录；版本输出 `1 (1ec44d1)` | 目录名不作为实际 commit 证据 |
| 编译器 | Clang 23.0.0，Linux | 保存实际 `--version` 和动态库依赖 |
| 远端 RPC | v4.0.1，TCP，`ROCm0` | 与主机程序和运行库配套 |
| 模型 | UD-Q4_K_M，四分片 | 核对分片名、大小、校验清单 |
| 互联 | Thunderbolt/USB4 直连 | 使用直连地址作为 RPC endpoint |
| 主机/从机身份 | 已脱敏 | 分别填写管理地址和推理直连地址 |

训练上下文 `196608` 是模型元数据；本项目服务实际设置的是总上下文
`8192`。二者不能互换，也不能据训练上限推断当前服务的可接收长度。

## 2. 先把设备、运行库和网络逐层验收

### 2.1 设备存在与当前会话权限

原从机刚接入时，网络可达，但 `amd-smi`、`rocm-smi` 不存在，USB4
接口也只有链路本地地址。处理顺序是先确认 PCI 设备、KFD/DRI 节点和用户组，
再安装诊断工具和配置推理链路。

```bash
rocminfo
amd-smi list
rocm-smi
```

检查点包括 `/dev/kfd`、`/dev/dri/renderD128`、`/dev/dri/card0`；当前会话
具有 `video`、`render` 访问权限；`rocminfo` 的 GPU agent 包含
`Name: gfx1151`、`Device Type: GPU`、`Wavefront Size: 32`。
修改用户组后原项目在新 SSH 会话中复核，不能仅凭组配置文件判断权限已生效。

### 2.2 分发的是配套运行环境

项目向从机复制了约 1.8 GB 的程序与运行库目录，包含 `rpc-server`、
`llama-server`、`libggml-hip.so.0`、`libggml-rpc.so.0`、HIP、hipBLAS、
rocBLAS 和 HSA 运行库。主机的依赖检查确认存在 HIP 库，未观察到 Vulkan 库；
从机的 RPC 初始化日志也明确列出 `ROCm0`。

因此“这次用了什么后端”的依据是动态依赖与设备初始化日志。只看到可执行文件
叫 `llama-server`，或机器安装过 ROCm，都不足以证明实际请求由 HIP 执行。

### 2.3 USB4 路由与 RPC 端口

原项目把推理接口设为静态地址，但不为直连接口配置默认网关，以保留原来的
上网路由。主机到从机的三次 ping 全部成功，平均 RTT 为 0.684 ms；端口探测通过。
这些是链路准入数据，不是模型推理加速比。

以下 `${RPC_NODE}` 是从机直连地址，`${ENGINE_ROOT}` 是配套二进制目录，
需要先按实际环境设置；文档不保留原节点和路径。

```bash
nc -vz -w 5 "${RPC_NODE}" 50053
```

检查点是端口可连接、请求实际走 USB4 路由。原记录中管理网络也能访问 RPC，
但服务明确使用直连 endpoint；管理网络连通不替代推理链路验收。

## 3. 启动 worker，再启动主模型

### 3.1 从机 RPC

```bash
cd "${ENGINE_ROOT}"
./rpc-server -H 0.0.0.0 -p 50053 -d ROCm0 -c
```

原日志的有效检查点是：RPC v4.0.1、监听 `50053`、设备为 Radeon 8060S /
`gfx1151`、`transport: TCP`。记录中的一次从机启动报告容量 98304 MiB，
可用 27764 MiB；这是当时的分配快照，不能当成机器永远有足够余量。
另一份快照中容量又不同，必须按每次实际启动日志重新预算。

### 3.2 主机 5 槽位配置

下面保留 E22 的实际参数。`${MODEL_ROOT}` 指向权重根目录，不能原样复制
尖括号占位符；必须先在 shell 中设置这些变量。

```bash
cd "${ENGINE_ROOT}"
./llama-server \
  --model "${MODEL_ROOT}/MiniMax-M2.7-GGUF/UD-Q4_K_M/MiniMax-M2.7-UD-Q4_K_M-00001-of-00004.gguf" \
  -ngl 999 \
  --rpc "${RPC_NODE}:50053" \
  --split-mode layer --tensor-split 45,55 --main-gpu 0 --fit off \
  --ctx-size 8192 --parallel 5 \
  --threads 16 --threads-batch 16 --threads-http 4 \
  --batch-size 2048 --ubatch-size 2048 \
  --flash-attn on --host 0.0.0.0 --port 8080 --temp 0.4 \
  --no-ui --metrics --no-mmap --log-timestamps --verbosity 1
```

`tensor-split 45,55` 是权重切分配置，不能解释成两台机器已经按此比例消耗
计算时间。验收还要看实际 buffer、远端传输、GPU 活动和 API 输出。
原启动脚本的文件名残留了另一个模型名，因此本项目以进程参数和 `/v1/models`
核对真正加载的模型，不以脚本名判断。

## 4. 加载、槽位与 API 的具体检查

### 4.1 监听不等于就绪

```bash
curl http://127.0.0.1:8080/health
curl http://127.0.0.1:8080/v1/models
curl http://127.0.0.1:8080/props
curl http://127.0.0.1:8080/metrics
```

加载期间端口已经监听，health 返回 `Loading model` / HTTP 503；同时 RPC
连接保持 `ESTAB`。E22 记录本地读取约 139.68 GB、向从机发送约 64.95 GB，
进程运行约 06:56 时 health 变为 `ok`。所以“约 7 分钟”是外部就绪观察，
不是引擎内部 `load_model` 精确计时。

E21 的 2 槽位快照则明确没有保留成功加载时间。服务存活约四小时不能替代
加载耗时；本章不把 E22 的约 7 分钟补填到 E21。

### 4.2 总上下文与每槽位上下文

| 来源 | 启动参数 | 服务实际报告 | 已验证含义 |
| --- | --- | --- | --- |
| E21 | `ctx-size=8192, parallel=2` | `total_slots=2, n_ctx=4096` | 总上下文在两个槽位间分配 |
| E22 | `ctx-size=8192, parallel=5` | `total_slots=5, n_ctx=1792` | 以服务实际报告为准，存在对齐行为 |

不能写成“五路各 8K”。也不能用 `8192 / 5` 的手算值替代 `/props`。
原文提出每路 8K 时重新增大总预算，但没有相应性能验收，本章不把该建议写成
已完成配置。`parallel=5` 只是配置的可用槽位，也不证明五路请求同时完成过测试。

### 4.3 使用真实正文验收

E22 的 chat 请求固定 `temperature=0.4`、`max_tokens=256`、`stream=false`，
要求模型不展示思考过程，最终只回复 `OK`。实际返回 `content: OK`、
`finish_reason: stop`，并产生 198 个 predicted token。

E21 的 `max_tokens=160` 探测可能把预算全部用在 `reasoning_content`，最终
正文为空。因此功能判据同时包含最终正文、结束原因和 token 用量，不能仅看
HTTP 200。OpenAI 客户端 Base URL 填到 `/v1`；直接 HTTP 才使用完整
`/v1/chat/completions` 路径。

## 5. 怎样从原始 timing 得到可比较的性能

### 5.1 单请求与累计 metrics 分开

E22 的请求级 timing 为：

```text
prompt_n: 51
prompt_ms: 837.125
prompt_per_second: 60.9228 tokens/s
predicted_n: 198
predicted_ms: 9734.168
predicted_per_second: 20.3407 tokens/s
```

复算分别使用 `51 / (837.125 / 1000)` 和 `198 / (9734.168 / 1000)`。
这些是服务端 timing，不含完整客户端排队、传输与收包开销，因此不能命名为
HTTP 墙钟吞吐或 TTFT。

| 记录 | Prompt tok/s（服务端） | Generation tok/s（服务端） | 限制 |
| --- | ---: | ---: | --- |
| E21，2 槽位单请求，24/160 tokens | 60.5232 | 20.0983 | 单次请求 |
| E21，测试前累计 metrics | 38.9045 | 16.8165 | 累计业务混合统计 |
| E22，5 槽位配置下单请求，51/198 tokens | 60.9228 | 20.3407 | 实际忙槽位指标为 1 |

E22 的 metrics 约 60.9319 / 20.3411 tok/s 与同次请求基本相符；E21
则是不同负载的累计值。不能把累计指标与单请求指标当成前后优化结果。

### 5.2 多机比较需要补齐哪些条件

比较单、双、三机时，应同时固定制品、KV 类型、总上下文、每槽上下文、
batch/ubatch、输入输出长度和采样。先测进程到就绪，再测请求级 Prompt/
Generation，最后另做实际并发请求。每个阶段分别记录主机和 worker 的资源。

现有双机记录没有同模型单机基线，也没有正式的并发阶梯和误差统计。因此它
能证明容量扩展与 API 可用，不能证明“多机线性加速”或五并发吞吐。

## 6. 排障和恢复检查

| 现象 | 原项目的定位依据 | 下一步 |
| --- | --- | --- |
| 从机可 SSH，RPC 不通 | 初始防火墙只放行 SSH | 核对 RPC 监听与主机来源规则 |
| 端口可连接，health 仍 503 | 加载中且 RPC 为 ESTAB | 继续对照传输、读取和加载日志 |
| 模型名与脚本名不一致 | 遗留脚本名含其他模型 | 以进程参数和 models 返回为准 |
| 200 成功但正文为空 | 输出预算被 reasoning 消耗 | 检查 content/reasoning 与 finish_reason |
| 停止后仍疑似占用 | E21 做过停止验收 | 核对无 HTTP listener、health 连接失败 |

RPC 缓存目录、访问身份和网络配置不在公开文档中给出。复建时应保存自己
任务的 worker 日志和停止结果，而不是仅记录主进程退出。

## 7. 从这个项目提炼的通用方法

这个项目最可迁移的操作链是“设备枚举 → 配套运行库 → 直连路由 → worker
设备日志 → 主机分片加载 → health → props → 真实正文 → 请求级 timing”。
其中每一步都能把失败缩小到一层：端口、加载、容量、模板和性能分别判断。

性能结论应至少带上“几台机器、几槽位、每槽实际上下文、请求长度、引擎或
HTTP 口径”。这些条件缺一项，下一轮都可能复现出不同数字而无法定位原因。

## 8. 未验证与待回链历史摘要

前次整理保留了三机 `30/35/35`、q8_0 KV、batch 512、ubatch 128、
4K 总上下文的摘要：`pp512=94.46 ± 1.16 tok/s`、`tg128=17.06 ± 0.01 tok/s`，
加载约 10 分 6 秒，长输出约 16.3–17.2 tok/s。当前重新读取的 E21/E22
均为双机记录，不能支撑这些三机数值；它们保留为历史线索，不参与本章对照排序。

同样，前次摘要中的固件不一致、接收窗口和 GPU 为零的排障过程，尚未在本章
两份原文中回链到具体日志，不能据此断言所有 RPC 卡顿都由固件导致。
待补材料是三机 benchmark 命令、每次采样、节点版本和对应故障日志。

本轮没有重新运行模型。数据来源与边界见[证据使用说明](../../meta/evidence-policy.md)；
具体原始过程见 [E21](../../evidence/records/E21.md) 和 [E22](../../evidence/records/E22.md)。

