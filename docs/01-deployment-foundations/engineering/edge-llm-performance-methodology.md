---
id: T40
title: "通用性能优化测试方法论"
type: tutorial
volume: book
layer: 4
platform: "general"
device: "general"
status: historical
source_ids: [R21, R22, E22, E26, E27, E28, E29, E30, E32]
updated: 2026-10-19
summary: "用既有项目说明环境准入、负载构造、计时采样、对照消融、失败判定与结果复算，保留真实操作闭环。"
---

# 通用性能优化测试方法论

[工程实例索引](../cases/README.md) · [项目文档索引](projects/README.md) · [知识体系首页](../README.md)

技术标签：`on-device / benchmark / ROCm / Vulkan / multimodal`

## 1. 适用范围

本页从当前设备保存的项目原始记录提炼操作顺序、指标口径、实验方法和验收规则。每个项目单独成文；实际运行、部署方案与制品作者报告分别标明，未执行的组合不写成已完成测试。

项目文档：

1. [MiniMax-M2.7 多机推理](projects/01-minimax-m27.md)
2. [DeepSeek V4 Flash](projects/02-deepseek-v4-flash.md)
3. [Qwen3.6-35B-A3B](projects/03-qwen36-35b-a3b.md)
4. [Qwen3.8-27B 与 Flash-Next](projects/04-qwen38-27b-flash-next.md)
5. [GLM-5.3-Flash](projects/05-glm-53-flash.md)
6. [vLLM ROCm 文本与多模态](projects/06-vllm-rocm.md)
7. [MiniMax-H3 视频/音频生成](projects/07-minimax-h3.md)
8. [Qwen-Image 2.1](projects/08-qwen-image-21.md)

## 2. 开始测试前，先写清本轮回答哪个问题

“部署成功”“更快”“支持长上下文”对应不同证据。下面只列既有项目实际
遇到的问题，参数和结果留在各自章节，避免同一个数字多处维护。

| 问题 | 已有工程入口 | 本轮应观察的量 |
| --- | --- | --- |
| 超大模型能否跨设备加载 | [MiniMax-M2.7](projects/01-minimax-m27.md) | 分片、RPC 传输、各节点 buffer、health、实际正文 |
| 后端与多机路线怎样选 | [DeepSeek V4](projects/02-deepseek-v4-flash.md) | 制品是否相同、Prefill/Decode、加载与资源 |
| 并发扩容用 RPC 还是副本 | [Qwen3.6](projects/03-qwen36-35b-a3b.md) | 总上下文、每路实际长度、聚合吞吐、最慢一路 |
| MTP/协作矩阵有没有收益 | [Qwen3.8](projects/04-qwen38-27b-flash-next.md) | 实际 kernel、采样、接受率、TTFT、E2E |
| 混合量化能否由目标引擎读取 | [GLM](projects/05-glm-53-flash.md) | 架构与类型识别、作者报告和本机实测边界 |
| 图文吞吐怎样统计 | [vLLM ROCm](projects/06-vllm-rocm.md) | 图像一致性、实际 attention backend、usage、SSE |
| 视频哪里慢、内存怎样降 | [MiniMax-H3](projects/07-minimax-h3.md) | 编码、采样、双 VAE、GTT、媒体内容 |
| VAE 卡住是模型还是后端问题 | [Qwen-Image](projects/08-qwen-image-21.md) | 冷缓存、搜索次数、单组件解码、完整生成 |

先选一个问题，再决定基线和改动。例如 H3 的 offload 对照固定模型和生成
规格，只比较内存与墙钟；基础图像模型换 Turbo 时同时改变 checkpoint 和
schedule，只能写成整套方案变化。后者不能冒充单参数消融。

## 3. 环境与制品准入：具体核对到哪一层

### 3.1 设备、后端和容量分别取证

参照 [C06](../cases/C06-radeon-8060s/README.md) 与
[vLLM 部署记录 E25](../evidence/records/E25.md)，记录以下四层：

1. 硬件与系统：设备架构、物理内存、系统可见量、内核、驱动和当前其他负载。
2. 实际可分配量：GTT/TTM、当前 MemAvailable、RSS、swap；APU 不只看 firmware VRAM。
3. 用户态：容器或原生环境中的 ROCm、PyTorch、Triton、编译器和依赖库。
4. 程序：实际二进制 revision、构建选项、运行时设备与真正选中的后端。

例如 MiniMax 从动态依赖确认主机使用 HIP，从 worker 初始化确认远端设备；
H3 的 Vulkan 输出列出 KHR_coopmat，但工具链缺少较新的 shader 扩展。
“机器装过 ROCm”“编译成功”“能力位显示支持”都不能替代请求实际走到该路径。

### 3.2 制品 manifest 不只写模型名

参照 [Qwen-Image 组件清单](projects/08-qwen-image-21.md)，保留主模型、
量化格式、分片、tokenizer/模板、视觉 processor、draft head、VAE 及源码版本。
以大小和摘要核对下载完整性；摘要值保留在本地 manifest，公开文本使用占位符。

DeepSeek 的 GGUF 与 W4A16 safetensors 是不同路线，GLM 还要求引擎同时
支持 `glm5next` 架构和特殊量化类型。制品不相同就先分组，不直接排名 token/s。

检查点是“这些文件能由这一个已记录二进制正确读取”。不在此时调整所有
性能开关，否则格式、设备和性能问题会混在一起。

## 4. 建立能真实生成的最小服务

参照 [MiniMax 的加载与 API 检查](projects/01-minimax-m27.md)，按下面顺序
逐项记录，而不是只截一张端口已监听的图：

```text
进程启动
 → 端口监听，加载期间可能仍返回 503
 → health / models 成功，核对模型身份
 → props 核对总槽位和每槽实际上下文
 → 真实请求，核对正文、reasoning、usage、finish_reason
 → 需要时验证 SSE 到正常结束
 → 停止，确认本任务监听与资源释放
```

MiniMax 短输出可能全部消耗在 reasoning，最终 content 为空；W4A16 在
health-ready 后首个真实请求仍触发 JIT。因此 ready 至少要区分“HTTP 就绪”
和“真实生成预热完成”。加载时间、首次请求和稳态时间分别报告。

功能验收失败应先保留结果。[C14 Windows CPU](../cases/C14-windows-cpu/README.md)
有可执行记录和未通过验收项，不能因为服务能返回文本就把整体结论写为通过。

## 5. 从实际 token 构造负载矩阵

### 5.1 四个长度字段分开

| 字段 | 怎样获得 | 真实项目中容易出现的误读 |
| --- | --- | --- |
| 模型训练上下文 | 模型元数据 | 当作当前服务已经分配的窗口 |
| 服务总上下文 | 启动参数与服务属性 | 当作每个并发请求可独占的长度 |
| 每槽位上下文 | 服务实际报告 | 只用总量/并发手算，忽略对齐 |
| 请求实际输入/输出 | usage / timings / tokenizer | 把“1K 场景”当成恰好 1024 tokens |

[Qwen3.6 的固定总上下文矩阵](projects/03-qwen36-35b-a3b.md)要求并发和
总上下文一起解释；[W4A16 文本专项](projects/06-vllm-rocm.md)也保存了模板后
实际 token。正式比较使用这些真实计数，不用字符数或文件大小代替。

### 5.2 根据瓶颈构造输入输出

长输入、短输出用于观察 Prefill/TTFT；短输入、足够长输出用于观察持续生成。
W4A16 的 Prefill 场景只输出很少 token，该行 Decode 的采样间隔不足，
不应作为主结论。对照时用它自己的 Decode 专项。

长上下文测试还需实际填充窗口并验证回答，而不是只增大启动参数。
[GLM 的上下文说明](projects/05-glm-53-flash.md)展示了“启动窗口”和“实际
填充长度”如何配对；其中作者数据仍不能当成本机复跑。

图像、视频实验固定 prompt、negative prompt、seed、RNG、分辨率、帧数、
步数、sampler 和 scheduler。改变任一项就记录为新负载，不能从小规格
线性推算正式任务结果。H3 的小规格与正式规格就出现过后端排序变化。

## 6. 计时必须保留原始事件

完整定义集中在[指标口径](../meta/metrics.md)。本节说明实际采集位置与
复算方式，避免在同一表中混用引擎和客户端值。

### 6.1 引擎 timing

MiniMax 记录了 `prompt_n/prompt_ms` 与 `predicted_n/predicted_ms`；先核对
计数，再除以秒数，得到服务端 Prompt/Generation tok/s。该时间不覆盖
完整 HTTP 传输与排队，不能改名为客户端吞吐。

`llama-bench` 的 pp/tg 又属于独立引擎负载。[C06](../cases/C06-radeon-8060s/README.md)
的历史 Decode 也应保留原口径，不能与 VLM 的并发输出吞吐放在一列排名。

### 6.2 HTTP / SSE timing

按 [E26](../evidence/records/E26.md) 记录请求发出、首个有效输出、SSE
结束三个时刻，以及服务 usage 和结束原因。使用相邻生成间隔时，分子为
`completion_tokens - 1`；使用完整墙钟时，分子为全部 completion tokens。
正文和 reasoning 的首输出规则也必须写在报告中。

E26 的 VLM harness 接受首个非空 content/reasoning delta，E29 的文本
专项按首个实际文本 token。未经统一，不能把它们的 TTFT 汇总成一条曲线。
没有 usage 而使用空白估算的行保留估算标记，不与精确 token 行严格比较。

### 6.3 冷态、形状首次运行和稳态

按 [E29](../evidence/records/E29.md) 将首轮新形状/JIT 单列，稳态按后续
重复请求统计。不要静默删除首次长尾；读者需要同时知道冷启动体验与稳态。
缓存是否预下载、Ray 是否已运行、模型是否常驻，也随该行一起保存。

均值、标准差、中位数和分位数只有在相应样本存在时才报告。两次稳态样本
不能包装成可靠 P99；单次生成结果就写单次观察，不补造误差条。

## 7. 对照与消融：从项目中保留可执行判据

### 7.1 后端、Flash 和矩阵能力

[H3](projects/07-minimax-h3.md)固定同一规格，对 HIP 的 FA 开关做对照，
分别记录采样与双 VAE。[vLLM](projects/06-vllm-rocm.md)的 Flash on/off
则同时切换 decoder 和视觉 encoder 路径，只能视为两套配置比较。

[Qwen3.8](projects/04-qwen38-27b-flash-next.md)要求新 Vulkan 构建实际
识别 KHR_coopmat，再保持输入、采样与输出一致复测。仅出现能力字符串
不证明端到端更快；构建成功也不能覆盖输出正确性。

### 7.2 MTP / DSpark

先建立 target-only 基线，再固定同一目标制品、实际 prompt、输出上限、
温度和 seed，对草稿深度/策略单独对照。保存 drafted、accepted、接受率、
TTFT、Decode、E2E、资源和输出完整性。

接受率提高不保证端到端更快：draft 成本、verify 成本和前处理仍然存在。
[Qwen3.8](projects/04-qwen38-27b-flash-next.md)的贪心历史组与真实采样组
分开；[DeepSeek](projects/02-deepseek-v4-flash.md)也把 quality、speed
profile 分开。不能跨采样模式和精度路线挑选最快数字拼成推荐配置。

### 7.3 缓存

先构造冷请求，再复用相同前缀并改变后缀，最后换不同前缀；同时看 server
实际 eval 的 prompt token 是否减少。只看 TTFT 变短，无法排除 JIT、负载
和不同输入长度。

[Qwen3.8 的 Prefix Cache 实验](projects/04-qwen38-27b-flash-next.md)
用实际评估 token 证明前缀命中；H3 的 EasyCache 则明确没有跳步。开了
参数却无命中时必须保留为无收益结果，也不能把缓存 TTFT 收益写成 Decode 加速。

## 8. 多机、并发和资源怎样一并判断

### 8.1 三种拓扑分别回答问题

| 路线 | 该项目里解决什么 | 验收时不能省略 |
| --- | --- | --- |
| RPC / TP | 分摊权重、计算与容量 | 各节点实际参与、通信、总资源、同模型基线 |
| 独立副本 | 多请求同时服务 | 各副本忙槽、排队、聚合吞吐与最慢一路 |
| P/D 分离 | 阶段分工与状态迁移 | 状态正确性、迁移耗时、单请求与流水线 |

参照 [MiniMax](projects/01-minimax-m27.md)、[Qwen3.6](projects/03-qwen36-35b-a3b.md)
和 [Qwen3.8](projects/04-qwen38-27b-flash-next.md)。能加载模型证明容量，
要证明加速还需同模型同负载基线；增加设备后总吞吐上升，也需同时写总资源。

### 8.2 并发阶梯的实际做法

E26 按固定 worker 数同时发请求，每档保留全部请求和该档起止墙钟，汇总
成功输出总量、单路延迟/速度和错误。并发总吞吐不能用单路 tok/s 简单相加，
HTTP 连接数也不等于实际执行中的模型槽位。

Qwen3-VL 的高并发组聚合吞吐提高但单路速度下降；最终工作点应按真实任务
对延迟和产出的要求选择，不把最高吞吐档自动称为“最佳配置”。最高配置档
仍全部成功时注明 capped，不宣称测到了失败极限。

### 8.3 资源采样与容量取舍

H3 用每秒 sysfs TSV 和 `/usr/bin/time -v` 同时保存 GTT/VRAM 与最大 RSS；
W4A16 又记录 MemAvailable 和 swap，说明模型可运行与宿主余量充足是不同
判断。不同内存视角不相加，也不拿 firmware VRAM 一项代替 APU 全部资源。

offload 比较保持任务和质量不变，先看峰值变化，再看完整墙钟。H3 的结果
能支持本负载的内存折中；GLM HYBRID 的 CPU MoE 则只有作者记录，尚不
支持本机同样的速度与边界。

## 9. 失败和质量进入同一份验收

[E28](../evidence/records/E28.md)保留了 DeepSeek-VL2 的失败 Flash 组；
[Qwen3.8](projects/04-qwen38-27b-flash-next.md)保留超长上下文与不完整轮次；
[C14](../cases/C14-windows-cpu/README.md)保留未通过的 API 验收。它们都不能
作为 0 tok/s 混入成功均值，也不能删除后声称矩阵全部成功。

质量检查随任务变化：文本核对正文、结束原因和可执行任务；图文核对回答与
输入对应；图像检查文件、语义和伪影；视频检查首中末帧与运动；音频检查
声道、采样率和有效信号。H3 的媒体验证和 Qwen-Image 的 job 终态都提供了
具体流程。进程退出码为零只证明程序完成，不证明内容正确。

未隔离的原因写“原因未确定”。Qwen-Image 的本地证据是同 latent 冷缓存
搜索路径的对照，不能扩大成所有驱动超时都来自 MIOpen；MiniMax 未回链的
固件线索也不能替代具体故障日志。

## 10. 一个可以照着检查的闭环

以 [C06 Radeon 8060S](../cases/C06-radeon-8060s/README.md)为例，先固定
Qwen3.6 GGUF 与请求，保留 CPU 和 Vulkan 两份实际启动配置；通过模型
加载日志检查 `offloaded 41/41` 和 GPU buffer，再读取 prompt/eval timing。
CPU→GPU 的结果与后续 ctx/batch/线程组合分别标记，不把组合收益归因给
其中一项。BF16 加大工作区仍未提高 Decode 的记录同样保留。

若照此方法做新一轮，应先恢复原始配置，再逐项改变变量；这是复测方案，
不是声称历史所有参数都已经逐项消融。最后把输出、性能和资源放在同一个
验收记录里：

| 检查项 | 从哪里取证 | 未满足时怎样写 |
| --- | --- | --- |
| 模型与二进制一致 | manifest、version、加载日志 | 未记录具体 revision |
| 负载相同 | 实际 token、采样、缓存、输入文件 | 只能做组合观察 |
| 后端真正在算 | 设备日志、buffer、后端选择 | 仅编译或仅枚举通过 |
| 数字可复算 | timing / SSE / usage / 墙钟 | 缺原始计时，保留历史观察 |
| 输出正确 | 正文、执行结果或媒体文件 | 功能验收失败，不纳入成功推荐 |
| 资源与停止完成 | TSV、RSS、swap、监听状态 | 资源边界或停止结果未验证 |

项目记录保存环境、制品、命令、workload、逐请求响应、资源、server log、
汇总与 acceptance。原始结果不覆盖，派生表可以重算；公开版只替换路径、
节点、凭据和业务素材，不删除关键参数、失败现象及测量条件。

本章没有新增模型测试。数据来源与边界见[证据使用说明](../meta/evidence-policy.md)，
补充记录入口见[端侧项目证据索引](../evidence/records/projects.md)。

## 相关阅读

- [项目文档索引](projects/README.md)
- [性能测试专题](../chapters/performance/benchmarking.md)
- [推测解码](../chapters/performance/speculative-decoding.md)
- [PD 分离与 MoE](../chapters/performance/disaggregated-serving.md)
- [量化工程](../chapters/models/quantization.md)
- [工程实例索引](../cases/README.md)
