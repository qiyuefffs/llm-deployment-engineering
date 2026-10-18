# 技术记录来源与证据边界

[返回总目录](../README.md) · [术语与参考资料](../13-glossary-and-references.md)

本目录保存从作者部署技术笔记中筛选的可公开测量字段，供正文解释实际问题及离线核算。它不是原始 FlowUs 空间导出，也不是本轮重新执行各平台推理的结果。

## 1. 材料是怎样整理的

本次先核对空间目录并检索部署、编译、压测、推理等主题，再阅读相关目录与文章。文章中涉及具体设备、版本、命令、报错和输出的部分，用来组织 01～13 章。

公开时只转录需要的工程信息。私人页面地址、账号、个人目录、内部设备地址、凭据和签名附件地址未纳入仓库。没有将空间缓存、授权信息或整篇原始私有文章上传。

同一篇文章可能同时包含早期结论、后续失败和计划命令。正文优先采用能对应到具体版本与输出的证据；存在冲突时明确说明，不把标题或开头结论直接视为成功记录。

## 2. 主要来源与用法

以下使用技术笔记标题标识来源，不提供私人知识库页面链接。

| 技术笔记或记录 | 采用内容 | 正文章节 |
| --- | --- | --- |
| AMD 780M-GPU 适配教程、780M 配置与 890M 记录 | gfx、系统、运行库和后端条件 | 02、06、10 |
| ROCm 与 PyTorch 适配、AMD ROCm vLLM 编译 | PyTorch/HIP、源码编译与最小验证 | 02、06 |
| Linux CUDA、Flash Attention、CUDA/Vulkan 编译记录 | 驱动、Toolkit、wheel 与构建目录的区分 | 02、05、10 |
| 双 RTX 4080 vLLM Docker 部署记录 | 模型路径、容器挂载、双卡配置 | 07、11 |
| DGX Spark适配编译vllm部署Qwen3.6-35B-A3B模型（bf16/fp8精度） | GB10 编译错误、FP8 服务、200 请求输出 | 02、07、08、10 |
| DGX Spark GB10部署gemma-4系列模型及关闭MTP推理加速 | MTP 关闭时的并发分组 | 09 |
| DGX Spark GB10部署gemma-4系列模型及MTP推理加速 | MTP 打开时的吞吐、TPOT、ITL 与接受率 | 09 |
| DGX Spark GB10编译DFlash推理加速模块集成到vllm中 | 基线/DFlash 记录与服务参数差异 | 09 |
| Qwen3.5-9B Intel openvino 平台推理对比报告 | 模型 revision、INT4/INT8、Vulkan/SYCL、NPU 失败 | 03、06、09、10 |
| oMLX 推理框架性能测试报告与压测流程 | 并发 1/2/4 的吞吐与单请求延迟 | 08 |
| Mac Metal 编译、vllm-metal 和 MLX 记录 | 特定模型类型、文本/视觉能力与错误 | 06、10 |
| RTX 2060 Qwen3 Q6/Q5 混合推理记录 | 主机内存、交换、卸载与生成速度 | 04、10 |
| AMD Strix Halo 395 五机 HIP RPC 串联部署 Kimi-K2.5-Q2 实战文档 | 运行时内存、GTT/TTM、RPC 小上下文结果 | 10、11 |
| Prefill、Prefix Cache、KV Cache 学习记录 | 概念与工程检查，按官方实现修订 | 01、04、07 |
| Conda / PyInstaller 打包记录 | 环境与应用封装的边界 | 12 |

## 3. measurements.json 包含什么

[measurements.json](measurements.json)采用字段白名单转录，数值保持原单位；缺少的数据不补写。

| 数据项 | 保留内容 | 限制 |
| --- | --- | --- |
| `dgx_qwen_fp8` | 设备、版本、200 请求、输入/输出 token、TTFT 与吞吐 | 缺模型 revision 与原始逐请求文件；突发压力不能代表轻负载体验 |
| `intel_openvino` | 模型 revision、体积、INT4/INT8 指标、Vulkan/SYCL、NPU 错误 | 两组输出停在思考阶段；不同引擎计时边界不能混用 |
| `omlx_concurrency` | 并发 1/2/4、样本数、延迟与吞吐 | 样本少，缓存状态与完整环境不足；不能证明稳定 P99 |
| `gemma_mtp` | 各并发下开关 MTP 的指标与接受率 | 镜像 digest、逐请求数据和质量等价未补齐；未采用可疑峰值字段 |
| `dflash_observation` | 相同任务汇总与两边服务配置 | 同时改变上下文、活跃序列、内存比例和 eager 条件；2.03 倍观察比值不能归因于 DFlash 单项 |
| `amd_rpc` | HIP/内核/源码版本、内存错误、小上下文速度 | 无单机基线、长上下文服务负载和稳定性验收；不能计算多机加速比 |

## 4. A10 原有 Case 的公开证据

A10 资料继续保存在[独立 Case](../../../cases/llama-cpp-flash-attention/README.md)：

- [公开输入](../../../cases/llama-cpp-flash-attention/data/workload.jsonl)：8 条自制技术问题。
- [汇总 CSV](../../../cases/llama-cpp-flash-attention/results/observed-summary.csv)：12 组历史汇总转录。
- [8 张原有操作截图](../../../cases/llama-cpp-flash-attention/figures/00-workload-check.png)：从输入检查到最终报告，可从 Case 顺序查看。
- [脚本与步骤](../../../cases/llama-cpp-flash-attention/CASE.md)：下载、构建、服务、功能、压测和报告。

原有材料尚缺修正后完整成功构建日志、第二个干净实例复建记录和完整公开逐请求原始结果。知识章节引用这些产物，不补造缺失证据。

## 5. 本轮实际执行了什么

在本机运行了[离线核查脚本](../examples/verify_records.py)，检查公开输入哈希、样例数、分组数及部分算术关系；实际控制台输出保存在[verified-output.txt](../examples/verified-output.txt)。此外检查了文档链接、图片、代码语法与公开字段。

本轮没有重新下载和执行这些平台的模型，没有把源笔记转录当成本轮 GPU 测试日志。离线脚本通过，只说明它覆盖的计数与计算一致；不会自动证明源记录真实性、回答质量、性能稳定性或跨设备可复现性。

继续补实验时，应把新结果放在独立 run 目录，保存固定版本、完整启动配置、负载、逐请求记录和资源采样，再用同一套验收口径更新结论。
