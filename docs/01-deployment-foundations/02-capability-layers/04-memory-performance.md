# 第4层：显存与性能优化层

[总目录](../SUMMARY.md) · [压测](../chapters/performance/benchmarking.md) · [缓存/调度](../chapters/performance/cache-scheduling.md) · [多卡多机](../chapters/performance/parallelism.md) · [MTP/DFlash](../chapters/performance/speculative-decoding.md)

## 4.1 核心问题

| 问题 | 分解 | 首先采集 |
| --- | --- | --- |
| 显存不足 | 权重、KV/循环状态、图、通信、prefill工作区 | 失败阶段、分项buffer、峰值 |
| TTFT高 | 排队、分词、prefill、编译/冷缓存、传输 | 客户端时间、队列、输入长度、冷暖 |
| TPOT高 | 权重/KV访问、kernel、batch、通信、主机卸载 | 引擎时间、GPU/CPU、带宽与拓扑 |
| 并发上不去 | 活动序列/token预算、KV容量、调度、请求长度 | waiting/running、块占用、尾延迟和错误 |

## 4.2 显存组成

```text
峰值设备内存 = 权重＋KV/循环状态＋图/Runtime
             ＋prefill/decode工作区＋通信buffer＋其他进程
```

| 分项 | 随什么变化 | 检查阶段 |
| --- | --- | --- |
| 权重 | 参数、dtype、scale/zero、布局、切分 | 加载完成 |
| KV/状态 | 架构、token、活动序列、dtype、共享/窗口 | 预分配及请求增长 |
| 图/Runtime | CUDA graph、编译、固定shape、allocator | warm-up/捕获 |
| 工作区 | batched tokens、ubatch、attention/量化kernel | 长prefill、decode峰值 |
| 通信 | TP/PP/EP、rank、collective | 多卡初始化与运行 |

UMA同时观察主机RSS、系统可用、设备预算、memory pressure与swap；这些计数可能重叠，不能简单相加。[395的GTT/TTM实例](../engineering/amd-395-rpc.md)说明物理容量、驱动预算与实际可分配量是三层。

## 4.3 粗略显存估算

```text
理想权重字节 ≈ 总参数量 × 位宽 / 8
7B×2 ≈ 14GB；32B×2 ≈ 64GB；70B×2 ≈ 140GB
```

以上为十进制原始权重数量级，不含scale、非量化层、对齐、KV与工作区。总MoE权重容量按总参数，计算量按激活路径；不能把激活3B理解为只需存3B权重。

以32B INT4为例，理想权重16GB约14.90GiB，实际制品可能更大，16GB显卡还需KV与工作区，不能据此认定单卡可部署。加载、warm-up、长输入与持续负载分别记录峰值。

## 4.4 KV Cache 为什么重要？

对纯attention、相同形状的层，理想化缓存预算：

```text
KV bytes ≈ 2 × attention层数 × KV heads × head_dim
          × 已缓存token数 × 活动序列数 × 每元素字节数
```

2来自K与V；GQA使用KV heads而非query heads。共享前缀、滑动窗口、块对齐、压缩、MLA、GDN/SSM循环状态与跨卡分配需按实现另算。

教学算例：32层、8个KV heads、head_dim128、FP16时，每token约128KiB；8192token约1GiB/序列，4条完全独立序列约4GiB，尚未计其他开销。不要用hidden size直接代替KV head结构。

| 优化 | 改变什么 | 验证 |
| --- | --- | --- |
| 限制ctx/活动序列 | 状态容量与任务范围 | 长输入、每槽上下文与峰值 |
| KV量化 | 状态字节数和读取/转换 | 后端支持、长上下文质量与ITL |
| Prefix Cache | 重复prefill，可能共享状态 | 同token前缀、冷暖、挤出、租户 |
| PagedAttention | 分块分配与引用 | 块占用、回收、碎片和调度 |
| Chunked Prefill | 调度粒度及瞬时prefill工作 | TTFT、ITL、总吞吐共同变化 |

## 4.5 性能指标体系

| 指标 | 定义 / 统计口径 | 必须注意 |
| --- | --- | --- |
| TTFT | 请求发出→首有效token或首正文，明确口径 | 空role事件不能自动算首正文；含排队与传输 |
| TPOT | 通常(末token时间−首token时间)/(输出token−1) | 单token与不足两token样本单独处理 |
| ITL | 相邻token/事件间隔，按工具实现 | 一个SSE事件可含多token，不等于TPOT分布 |
| 输出吞吐 | 实际输出token总数/测试墙钟时间 | 不能逐请求token/s直接相加 |
| 总token吞吐 | (输入＋输出token)/时间 | 必须标明，不能冒充输出吞吐 |
| req/s | 成功请求数/同窗口墙钟时间 | 请求长度差异影响比较 |
| p95/p99 | 相应样本分位数与计算方法 | 少量样本不能代表稳定尾部 |
| 有效吞吐 | 同时满足质量、错误与SLO的完成量/时间 | 应作为工作点选择依据 |

```text
对照必须固定：模型/revision、模板、输入/输出、采样、请求数
             并发/到达率、缓存、warm-up、工具版本、计时范围
```

[完整原压测文章与命令](../engineering/benchmark-tools.md)。引擎pp/tg、GenAI管线与HTTP不可直接排名；负载c4和到达率inf200请求也是不同实验。

## 4.6 常见瓶颈与优化方向

| 证据 / 瓶颈 | 优化变量 | 代价与验收 | 对应工程 |
| --- | --- | --- | --- |
| 权重超过设备 | 权重量化、offload、TP/PP | 质量、RAM、PCIe/通信与加载 | [2060](../engineering/nvidia-rtx2060.md)、[W7900](../engineering/amd-w7900.md) |
| 权重访问/CPU回退 | 实际卸载、kernel、精度 | 不以GPU利用率代替数据流证据 | [8060S](../engineering/amd-8060s.md) |
| KV/工作区OOM | ctx、seqs、batched、ubatch、KV dtype | 任务范围、长文本质量与峰值 | Intel16GB、395 |
| 重复长前缀 | Prefix Cache/APC | 冷暖分组、租户、命中、挤出 | [MLX APC](../engineering/apple-mlx.md) |
| 长prefill干扰 | chunked、token预算、长短请求分组 | TTFT与ITL权衡 | GB10、双4080 |
| decode计算/验证 | MTP、DFlash、草稿长度 | 接受率、验证成本、质量、显存 | [GB10推测解码](../engineering/nvidia-gb10.md) |
| 并发吞吐不足 | 活动序列、批处理、到达率 | 单流TPOT与尾延迟上升 | [oMLX c1/c2/c4](../engineering/apple-mlx.md) |
| 多卡通信 | TP/PP、网卡、collective、切分 | 每rank内存、拓扑、气泡和恢复 | W7900、HIP RPC |
| NPU快但内容错误 | shape/算子/精度修复或回滚 | 性能与质量双验收 | [Intel全NPU TTS](../engineering/intel-arc-npu.md) |

实验流程：基线→瓶颈证据→假设→变更→同负载复测→质量/资源→采用或回退。单变量可分析归因，多变量保留为组合观察。结果未改善也必须保存，例如8060S BF16放大batch后10.8→10.1token/s。
