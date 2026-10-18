# 工程来源与实测转录

[总目录](../README.md) · [参考资料](../appendices/references.md) · [离线核算](../examples/verify_records.py)

本目录集中说明正文实例的来源、条件与证据缺口。来源为作者FlowUs空间中的部署技术文章；公开材料仅提取工程必要字段，不发布原始空间导出、私人页面地址或账号信息。

## 1. 整理范围与方法

本次依据空间技术目录和模型部署、编译、推理、量化、压测等主题检索，核对相关目录与多篇工程文章。原《大模型部署适配交付知识体系框架》决定六部分与五层结构，具体工程内容从各平台部署、转换、服务和测试记录提取。

知识框架用于组织关系，运行命令与输出用于支撑实例。有命令不等于已执行；有成功标题也不能覆盖后续明确失败。文章中的建议命令、早期结论、失败日志和实测汇总分别判断。

正文保留通用设备型号、版本、模型、参数、数值与必要错误；账号、凭据、私人路径、节点地址、业务样本和签名附件链接不转录。源笔记图片未取得适合公开的完整材料时，不下载转存或重绘成运行截图。

## 2. 来源编号

以下技术标题用于标识作者记录，不提供私有空间链接；相近记录合并说明。

| 编号 | 技术记录 | 正文采用内容 | 证据边界 |
| --- | --- | --- | --- |
| E01 | DGX Spark适配编译vLLM部署Qwen3.6-35B-A3B（BF16/FP8） | ARM64/CUDA配套、架构编译错误、FP8服务与200请求 | FP8有汇总；BF16只有命令，未作性能比较 |
| E02 | Qwen3.5-9B Intel OpenVINO平台推理对比报告 | IR revision、INT4/INT8、Vulkan/SYCL、NPU失败 | GPU输出在思考阶段截断；不同引擎计时不混用 |
| E03 | AMD Strix Halo 395五机HIP RPC部署Kimi-K2.5-Q2 | gfx/ROCm、GTT/TTM排障、小上下文RPC | 缺单机基线和长期API验收，未证明长上下文性能 |
| E04 | AMD 780M-GPU适配教程及配套配置记录 | Windows社区运行库、gfx、版本隔离与验证 | 历史社区路线，不作为所有新设备支持承诺 |
| E05 | Mac Metal编译与vllm-metal部署记录 | 特殊GGUF类型失败、文本与视觉能力区别 | 特定版本/制品组合，不推广为全平台结论 |
| E06 | oMLX推理框架性能测试报告与压测流程 | 并发1/2/4的延迟、TPOT与输出吞吐 | 样本小、请求数不一致、缓存状态与环境不全 |
| E07 | GB10 Gemma系列关闭/开启MTP推理加速两篇记录 | 并发分组、吞吐、TTFT/TPOT/ITL、接受率 | 缺原始逐请求文件和质量等价，剔除矛盾峰值字段 |
| E08 | GB10编译DFlash并集成vLLM | 两套服务参数与spec_bench汇总 | 多变量变化，观察比值不能单项归因 |
| E09 | GB10 Gemma-4 AWQ 4bit/8bit部署与压测 | 同26B-A4B系列的配置、token和性能 | 缺revision/校准/质量；峰值并发与配置冲突 |
| E10 | GB10 llama.cpp构建、Qwen转GGUF、量化与Ollama导入 | 转换链、构建目标、CURL依赖、格式检查 | 每种模型/转换器仍需独立验证 |
| E11 | 双RTX4080 vLLM Docker部署记录 | 容器、模型挂载、多卡和参数管理 | NVLink说法已修正；速度口径不完整，不作严谨收益表 |
| E12 | 昇腾310P部署与压测记录 | 芯片/插件/镜像配套、实际样本量检查 | 一条请求不证明配置的十并发；旧参数不是当前默认值 |
| E13 | RTX2060 Qwen3 Q6/Q5混合推理记录 | CPU/GPU卸载、主机内存和swap | 单次引擎观测，不当HTTP吞吐或稳定成绩 |
| E14 | Intel Windows OpenVINO视觉部署记录 | GPU驱动、IR与视觉功能单独验证 | 原图片样本无公开授权链，不转存或当质量真值 |

其他概念笔记包括KV、Prefill、Prefix Cache、ROCm/PyTorch、CUDA/Vulkan构建与环境封装，解释已按官方概念修订。没有形成完整公开记录的平台保留为适配方法，不补造运行成绩。

## 3. 可公开的测量字段

[measurements.json](measurements.json)保存七组结构化历史转录。数字保持源单位，字段按白名单手工整理；缺失数据不猜测补全。

| 数据键 | 关键条件与结果 | 阅读位置 |
| --- | --- | --- |
| `dgx_qwen_fp8` | GB10/128GB/CUDA13；200请求突发，25600输出token/297.46s | 第3层服务，第4层突发与排队 |
| `intel_openvino` | 16GB/OV2026.2.1；IR固定revision；INT4/8与后端观察 | 第2层制品，第3层管线，第4层比较 |
| `omlx_concurrency` | 输入目标128、输出上限256；c1/c2/c4 | 第4层并发权衡 |
| `gemma_mtp` | 输入512、输出上限256；三组并发开/关MTP | 第4层推测解码 |
| `dflash_observation` | spec_bench、50请求；上下文/序列/内存/eager同时改变 | 第4层控制变量 |
| `amd_rpc` | 五机395、ROCm7.2.1、llama b9557；内存与短测 | 第1层兼容，第3层RPC，第4层预算 |
| `gemma_awq` | GB10/vLLM0.19.0；200请求、c2；AWQ4/8 | 第4层量化组合观察 |

### E01 完整条件

vLLM `0.19.1rc1.dev337+g17d87168d.cu130`，ctx16184、batched8192、seqs4、内存0.80、FP8 KV、FlashInfer、prefix与chunked prefill。随机输入目标2048、输出128、200请求、到达率inf、seed42。实际输入411678、输出25600，平均TTFT148430.70ms，P99为293115.24ms。

源笔记没有模型revision和完整结果JSON。这些数字可核算，不能承诺另一环境精确复现；突发负载也不代表轻负载交互体验。

### E02 模型与环境

Core Ultra7 256V、Arc Lunar Lake、16GB；Ubuntu24.04.4、Mesa26.1.4、oneAPI2026.1.0、OpenVINO2026.2.1、GenAI/Tokenizers2026.2.1.0。

- INT4：`OpenVINO/Qwen3.5-9B-int4-ov`，revision `3f31fc1609edb0cbc8b131bc4c291f1b15cb0676`，24文件，6129582094字节。
- INT8：`OpenVINO/Qwen3.5-9B-int8-ov`，revision `3054198f70b6d50b97fa17ae80314e590c57def0`，24文件，9457724353字节。
- GPU管线19输入/128输出token；NPU INT4编译失败，INT8在420秒超时退出124。
- Vulkan/SYCL为pp512/tg128三轮、GPU23/CPU10层，llama.cpp精确commit未在源快照固定。

### E03/E05 版本边界

E03为5台Ryzen AI Max+395/8060S，ROCm7.2.1、HIP7.2.53211-e1a6bc5663、内核6.17.0-35、llama.cpp b9557-0f7fada56、gfx1151。120000MiB是修复后的设备可见总量，不是任意机器的物理/可用内存。

E05的Metal失败组合为M3 Ultra512GB、macOS26.3、特定分支commit9d36408；vllm-metal另一个组合为0.2.0、vLLM0.21.0+cpu、MLX0.31.2、Python3.12.13。两套结果分别记录，不混为单一环境。

### E07/E08/E09 比较的限制

E07镜像标签为`vllm/vllm-openai:gemma4-0505-cu130`，digest未保存，MTP候选数3。E08同时改变ctx32768→8192、seqs1→8、内存0.70→0.85，基线显式eager、另一边未显式配置。E09目标输出128而实际总输出25696，按实际token核算；异常峰值字段不用于推导。

## 4. 离线检查与本轮验证

从仓库根目录运行：

```bash
python docs/01-deployment-foundations/examples/verify_records.py
```

脚本只读取本目录JSON，检查部分成功计数、token/时间与记录吞吐、并发组配对和比值；[实际控制台输出](../examples/verified-output.txt)随文保存。它不连接设备、下载模型或发起推理。

本轮还检查文档相对链接、代码围栏与Python语法，并查看目录、代表章节与图片的渲染。通过这些检查说明公开材料内部一致，不证明历史记录的所有质量、稳定性或跨设备复现要求已满足。

## 5. 后续怎样补齐证据？

新实验保存完整环境与制品身份、最终命令、输入、逐请求响应、错误、资源采样和统计程序。把质量与性能分开验收，固定版本和负载后再做对照。

原始文件未公开的历史笔记仍可作为工程知识参考，但不直接当作材料齐全的完整复现实战。需要提交实战时，按[工程交付清单](../02-capability-layers/05-engineering-delivery.md)逐项补齐。
