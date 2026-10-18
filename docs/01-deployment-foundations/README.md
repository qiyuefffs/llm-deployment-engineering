# 大模型部署适配基础知识体系：工程实践

这份知识体系围绕一个任务展开：**把指定模型部署到目标设备，测清它的性能与限制，交付别人能接手的服务。**

内容依据作者在 FlowUs 中保存的部署步骤、错误记录和性能测试整理。按实际操作顺序安排章节：先检查设备和模型，再运行服务；先建立基线，再优化。每章提供概念解释、操作或检查命令、实际实例、结果解读和验收点。

## 阅读路线

![从环境准备到服务交付的 13 章阅读路线](assets/deployment-workflow.png)

图注：四个阶段贯穿 13 章。排障可以随时进入第 10 章，遇到术语可查第 13 章。[查看 SVG](assets/deployment-workflow.svg)。

第一次阅读直接从第 01 章开始；已经在部署时，可按下表定位。另有[简短阅读指南](00-engineering-handbook.md)，说明命令前提和实例证据怎样使用。

| 阶段 | 章节 | 具体要做什么 | 留下什么 |
| --- | --- | --- | --- |
| 准备 | [01 明确部署目标](01-engineering-and-request.md) | 写清设备、任务、输入、输出和通过条件 | 部署任务单 |
| 准备 | [02 检查设备与环境](02-hardware-compatibility.md) | 区分驱动、编译工具链、框架后端，做最小设备运算 | 环境记录与兼容表 |
| 准备 | [03 准备模型制品](03-model-and-quantization.md) | 核对格式、量化、分片、模板、下载和哈希 | 模型清单与质量样例 |
| 准备 | [04 计算内存预算](04-memory-and-kv-cache.md) | 估算权重、KV、缓冲，理解上下文与并发 | 预算和实测资源记录 |
| 跑通 | [05 建立 llama.cpp 单机服务](05-llama-cpp-practice.md) | 构建、加载、调用 API、检查正常和异常请求 | 服务日志与功能结果 |
| 跑通 | [06 迁移到目标端侧设备](06-edge-platforms.md) | 对照 AMD、Intel、Mac、NPU 等记录选择路线 | 设备功能矩阵 |
| 跑通 | [07 配置服务与调度](07-serving-and-scheduling.md) | 核对容器路径、并发、批处理、前缀缓存 | 可追溯启动配置 |
| 验证 | [08 建立性能与质量基线](08-benchmark-and-quality.md) | 固定输入与负载，测 TTFT、吞吐、尾延迟及质量 | 分组结果与验收表 |
| 优化 | [09 开展性能优化实验](09-profiling-and-optimization.md) | 根据证据提出假设，对照 FA、量化、推测解码等 | 收益、代价和适用条件 |
| 排障 | [10 按阶段定位故障](10-troubleshooting.md) | 区分编译、加载、API、内存、慢请求和功能缺口 | 最小复现与修复验证 |
| 扩展 | [11 多设备与多机扩展](11-parallel-and-scaling.md) | 判断切分方式、通信条件、容量与速度 | 拓扑与扩展测试 |
| 交付 | [12 打包、启停、监控与恢复](12-delivery-and-learning.md) | 固定制品、干净复建、就绪、监控和回滚 | 七项交付材料 |
| 查阅 | [13 术语与资料来源](13-glossary-and-references.md) | 查概念、来源、旧知识修订和官方资料 | 可持续更新的参考索引 |

## 实际实例放在什么位置

| 实例 | 主要章节 | 可以看到什么 |
| --- | --- | --- |
| A10、llama.cpp b10430、27B Q4 | 02～05、08～10 | 公开输入、命令、原有操作截图、12 组汇总和 FA 对照 |
| DGX Spark GB10、Qwen FP8 | 02、07、08、10 | 编译错误、精确版本、200 请求负载、TTFT 与吞吐解读 |
| GB10、Gemma MTP 与 Qwen DFlash | 09 | 吞吐、TPOT、ITL 的不同表现；多变量比较的限制 |
| Intel Core Ultra / Arc、9B INT4/INT8 | 03、06、09、10 | 模型 revision、OpenVINO 指标、Vulkan/SYCL 与 NPU 失败 |
| Mac Metal、vllm-metal、oMLX | 06、08、10 | 版本相关能力、文本/视觉分开验收、并发与等待的取舍 |
| AMD 395 五机 HIP RPC | 02、10、11 | gfx、GTT/TTM 内存排查、小上下文结果与多机边界 |
| 双 RTX 4080、vLLM Docker | 07、11 | 模型挂载修正、并行配置、PCIe 拓扑 |

历史测试结果已经过可公开字段筛选，见[测量转录](evidence/measurements.json)。原有 A10 实战独立保存在 [Case 目录](../../cases/llama-cpp-flash-attention/README.md)，知识章节引用其图片和产物。

## 按当前问题查阅

| 你现在遇到的问题 | 从这里开始 |
| --- | --- |
| 不知道先装什么，设备是否支持 | 02 → 03 → 06 |
| 权重已经加载，请求一长就 OOM | 04 → 10 → 08 |
| 需要先跑通一份 HTTP 服务 | 05；已有 vLLM 模型则看 07 |
| 吞吐提高了，用户却觉得更慢 | 08 → 07 → 09 |
| 想证明量化、FA 或推测解码是否有效 | 08 固定测量 → 09 对照与回归 |
| 单机放不下，准备双卡或多机 | 04 → 11 → 08 |
| 要把程序和模型交给其他人使用 | 12 → 01 的通过条件 |

## 在本机核对一份已有记录

不需要 GPU。在仓库根目录执行：

```bash
python docs/01-deployment-foundations/examples/verify_records.py
```

它检查公开输入的 SHA256、样例和分组数量，并重新计算部分吞吐及提升比例。实际输出保存在 [verified-output.txt](examples/verified-output.txt)。这只是离线数据核对，具体模型实验须在相应设备重新运行。

## 作者提供的原始框架图

![大模型部署适配原始知识框架图](assets/edge-llm-deployment-framework-original.png)

图注：原图保留原样，便于对照学习范围和放大查看。[下载原图](assets/edge-llm-deployment-framework-original.png)。图中部分分类需要按正文理解：GGUF 是容器，AWQ/GPTQ 是量化方法；TTFT、TPOT、ITL 分开统计；框架支持具体到设备、版本、模型与功能。完整修订见[第 13 章](13-glossary-and-references.md)。这张图不是硬件实测支持矩阵。

## 材料与更新规则

更新日期：**2026-10-18**。本轮核对了空间目录并读取部署相关文章，公开内容以工程步骤和技术测量为范围。私人页面链接、凭据、内部地址、个人路径及签名附件未作为公开资料提交。[来源说明](evidence/README.md)列明历史记录与公开产物的边界。

正文中的“已有记录”是历史观察；“模板”需要按现场版本调整；“算例”是明确假设下的计算；“本轮离线核对”只校验文件与算术。本轮没有重新运行这些平台的 GPU 推理。

开始新项目时，可以使用[适配记录](templates/adaptation-record.md)、[实验记录](templates/experiment-record.md)和[部署复盘模板](../../templates/deployment-review.md)。
