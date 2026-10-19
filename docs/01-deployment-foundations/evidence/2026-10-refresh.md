---
id: EV02
title: "2026-10部署与推理优化更新"
type: evidence
volume: evidence
layer: 0
platform: "general"
device: "general"
status: historical
source_ids: []
updated: 2026-10-19
summary: "资料核查日期：2026-10-19。本次保留原六部分、五层能力框架，将新技术放到对应层；原硬件实测仍按当时设备、版本与负载阅读。"
---

# 2026-10部署与推理优化更新

[知识体系首页](../README.md) · [完整目录](../SUMMARY.md) · [参考资料](../appendices/references.md)

资料核查日期：**2026-10-19**。本次保留原六部分、五层能力框架，将新技术放到对应层；原硬件实测仍按当时设备、版本与负载阅读。

## 1. 更新内容放在哪里

| 能力层 | 内容 | 工程落点 |
| --- | --- | --- |
| 硬件与运行时 | [DGX Spark / GB10](../chapters/hardware/dgx-spark.md) | ARM64、UMA、带宽、镜像digest、原生低精度与fallback |
| 模型与量化 | [当前量化工程](../chapters/models/quantization.md) | W/A/KV、LLM Compressor、GPTQ、NVFP4/MXFP4、校准与加载 |
| 推理框架 | [当前引擎选型](../chapters/frameworks/serving-engines.md) | vLLM V1、SGLang、TensorRT-LLM与llama.cpp执行路径 |
| 性能优化 | [MTP与推测解码](../chapters/performance/speculative-decoding.md) | 原生头、assistant、动态K、草稿输出头与接受成本 |
| 性能优化 | [DSpark](../chapters/performance/dspark.md) | 半自回归草稿、置信度、llama.cpp完整操作、自适应验证 |
| 性能优化 | [PD与MoE](../chapters/performance/disaggregated-serving.md) | 状态传输、NIXL/Mooncake、router、EP与同资源验收 |
| 性能与交付 | [缓存调度](../chapters/performance/cache-scheduling.md) / [压测](../chapters/performance/benchmarking.md) | 缓存冷暖、混合状态、固定矩阵、SLO与真实输出 |
| 跨项目技能 | [通用性能优化测试方法论](../engineering/edge-llm-performance-methodology.md) / [项目文档索引](../engineering/projects/README.md) | 总章保留通用方法，8 个项目各自独立成文 |

## 2. 本次修订的关键判断

1. DSpark是推测解码方法，DGX Spark是硬件，名称分开使用。
2. AutoAWQ库弃用不等于AWQ算法失效，新量化工程采用维护中的工具。
3. MTP需要真实预测制品与引擎实现，不能只按训练论文添加推理开关。
4. 固定K、按batch选K、按置信度分配验证预算是不同策略。
5. NVFP4/MXFP4、W4A16 fallback与原生FP4不混为一谈，日志要记录实际kernel。
6. KV量化、prefix cache、KV offload与PD transfer分别测试。
7. 推测采样的分布目标是当前目标模型，不自动消除量化误差。
8. PD、EP与多GPU只在同资源、同任务和同SLO条件下判断收益。
9. 模型能加载、编译能力可用和端到端性能达标是三个不同关口。
10. 多机RPC、独立副本与P/D分离分别解决容量、请求并发和阶段资源问题，不能合并成一个“多机加速”。
11. 项目知识层只保留可复用技术判断，不上传内部主机名、地址、路径、凭据和原始日志。

## 3. 可追溯的源码快照

| 项目 | 文档/代码快照commit | 用途 |
| --- | --- | --- |
| llama.cpp | `5aeac37a35b44fde4bdffaec9159f2fcb253b622` | DSpark转换/参数、EAGLE/DFlash、后端采样说明 |
| vLLM | `2365177ddda7714502e4df7a1669cc79c0a4dfd0` | MTP、adaptive verification、量化、调度与benchmark CLI |
| DeepSpec | `005e03b81cec38b7da6399833d609ee89a2587f2` | 配套草稿、训练模式、评测与缓存资源要求 |
| LLM Compressor | `f15ac1d2243c3fd60cd745cf4e735e2814142d76` | GPTQ W4A16 API与导出 |

这些是检索时的源码锚点，不声明为最新稳定release。开发分支、stable站点与已安装wheel可能不同，所有执行记录以实际安装版本为准。部分网页只能提供动态入口，复现时需另外保存当时recipe、模型revision和镜像digest。

[机器可读的资料清单](2026-10-sources.json)包含下载过的源码文档URL及SHA256；它校验资料快照，不是GPU测试结果。

## 4. 官方资料与适用范围

| 资料 | 支撑的内容 | 边界 |
| --- | --- | --- |
| [DeepSpec](https://github.com/deepseek-ai/DeepSpec/tree/005e03b81cec38b7da6399833d609ee89a2587f2) | DSpark/DFlash/EAGLE配对制品、训练与评测 | 训练模式与任务分布不能省略 |
| [DSpark论文](https://arxiv.org/abs/2607.05147) | 方法名称与半自回归/置信调度思路 | 论文速度不是本仓库设备成绩 |
| [llama.cpp推测文档](https://github.com/ggml-org/llama.cpp/blob/5aeac37a35b44fde4bdffaec9159f2fcb253b622/docs/speculative.md) | Qwen3 DSpark转换与server参数 | 其他backbone不按转换成功认定运行支持 |
| [vLLM MTP](https://github.com/vllm-project/vllm/blob/2365177ddda7714502e4df7a1669cc79c0a4dfd0/docs/features/speculative_decoding/mtp.md) | 原生MTP、Gemma assistant、draft lm_head | 不意味着每种模型与量化都支持 |
| [Adaptive verification](https://github.com/vllm-project/vllm/blob/2365177ddda7714502e4df7a1669cc79c0a4dfd0/docs/features/speculative_decoding/adaptive_verification.md) | 预算、FULL图、估计器与限制 | 详细页与概览支持描述有版本差异 |
| [Dynamic SD](https://github.com/vllm-project/vllm/blob/2365177ddda7714502e4df7a1669cc79c0a4dfd0/docs/features/speculative_decoding/dynamic_speculative_decoding.md) | batch区间选K及DP限制 | 不是自动学习最佳区间 |
| [量化方案选择](https://docs.vllm.ai/projects/llm-compressor/en/latest/steps/choosing-scheme/) | W/A方案、格式、设备条件 | 精确kernel覆盖按具体模型验证 |
| [AutoAWQ弃用](https://docs.vllm.ai/en/latest/features/quantization/auto_awq/) | 工具迁移方向 | 历史权重仍需独立验收 |
| [GPTQ源码示例](https://github.com/vllm-project/llm-compressor/blob/f15ac1d2243c3fd60cd745cf4e735e2814142d76/examples/quantization_w4a16/llama3_example.py) | GPTQModifier/oneshot/save_compressed | 本文改为本地校准文件，不下载未知业务数据 |
| [ModelOpt](https://github.com/vllm-project/vllm/blob/2365177ddda7714502e4df7a1669cc79c0a4dfd0/docs/features/quantization/modelopt.md) | 元数据、linear backend、fallback | 读取格式不代表原生加速 |
| [KV量化](https://github.com/vllm-project/vllm/blob/2365177ddda7714502e4df7a1669cc79c0a4dfd0/docs/features/quantization/quantized_kvcache.md) | scale、per-head、FA3与跳过层 | 长文质量仍需测试 |
| [vLLM优化](https://github.com/vllm-project/vllm/blob/2365177ddda7714502e4df7a1669cc79c0a4dfd0/docs/configuration/optimization.md) | V1调度、预算与并行 | 参数方向不是保证值 |
| [SGLang PD](https://docs.sglang.ai/advanced_features/pd_disaggregation.html) | 两实例、router、NIXL/Mooncake | 新增依赖、传输与异常验收 |
| [TensorRT-LLM quick start](https://nvidia.github.io/TensorRT-LLM/quick-start-guide.html) | serve与Python入口 | 按GPU、backend、模型配套 |
| [Spark硬件](https://docs.nvidia.com/dgx/dgx-spark/hardware.html) / [vLLM recipe](https://build.nvidia.com/spark/vllm/choose-recipe) | UMA、ARM64、带宽、官方部署组合 | 静态参数与标称峰值不是实测 |

## 5. 当前验证状态

- 原测量文件、CPU实际输出和硬件历史记录继续保留原身份。
- 新GPU流程依据官方资料整理，尚无本轮硬件运行结果。
- 矩阵脚本默认plan_only；只有显式execute才发送请求，保存真实benchmark日志与结果。
- 文档链接、Python/JSON语法、构建产物与脚本计划可以在本地检查；这些检查不替代GPU质量/性能验收。
- 通用性能优化测试方法论只归纳既有工程结果，不新增模型测试，也不替代原始证据。

新增实验结果应另建记录，填写环境、输入、版本、采样、冷暖、输出和原始日志，再纳入对应硬件实例。不要将本页日期当成历史测量发生日期。
