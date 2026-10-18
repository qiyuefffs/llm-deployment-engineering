# 第3层：推理框架层

## 本章概览

推理框架将模型制品变成可执行计算，并管理内存、请求与输出。本章按原稿六节展开：先定位框架，再分别理解vLLM与llama.cpp，随后完成启动、构建和选型。

配套教程集中保存完整步骤：[vLLM服务](../chapters/frameworks/vllm-service.md)、[llama.cpp构建与服务](../chapters/frameworks/llama-cpp.md)、[OpenVINO完整运行](../chapters/frameworks/openvino.md)。

## 3.1 框架定位

vLLM常用于多请求服务，重点是模型执行、KV管理与调度。llama.cpp适合GGUF、本地与多种设备后端，也可以通过llama-server提供接口。两者都需要按实际模型和功能验证，不能把定位理解成排他的使用范围。

TensorRT-LLM偏向NVIDIA相应执行和优化路线；SGLang提供服务调度、缓存和结构化任务等能力；Ollama与LM Studio提供方便的本地使用入口。OpenVINO与MLX则需要对应的制品和平台支持。

选择框架先确认任务能够完成，再看性能和交付成本。一个接口看似一致的服务，视觉、工具、JSON约束、取消和错误处理也可能不同。应用会使用的能力应列成明确测试项。

## 3.2 vLLM 知识结构

一次聊天请求先经过HTTP与参数检查，再由模板与tokenizer形成模型输入。调度器安排prefill和decode，KV管理器分配历史状态，模型执行器调用设备kernel，最后将token转换成文本并返回客户端。

```text
API → 参数与模板 → Tokenizer → Scheduler
 → KV管理 / 缓存 → 模型执行器 / Kernel → 采样 → 文本与流式响应
```

### 请求的一生：接收、等待、执行与回收

一条请求可能先通过语法/长度校验，进入等待队列，随后执行prefill与多轮decode，最后因EOS、stop、长度上限、取消或错误结束。服务必须释放这条请求占用的活动槽位与KV引用，其他请求才能继续利用资源。

这些结束方式意义不同。EOS/stop通常对应生成策略；length可能截断答案；取消来自客户端或服务控制；错误说明本次没有完成。性能统计要保存这些状态，不能把“收到了一段文本”全部记成功。

服务进程可能已监听端口但模型仍在加载，模型ready也可能在一条视觉请求后因缺encoder退出。Apple的EngineDead记录正是例子。因此就绪检查、功能检查与持续健康都需要各自的证据。

### 推理阶段与内存

Prefill处理输入并形成初始状态；Decode在历史状态上逐步生成。长输入更容易增加prefill计算与工作区，长输出和多活动序列会持续占用KV。PagedAttention等机制改善KV组织，实际资源仍要按模型和负载预算。

### 调度与长上下文

Continuous Batching让不同请求在生成过程中加入或退出执行批次。`max-num-seqs`限制活动序列预算，`max-num-batched-tokens`控制每轮token预算，两者影响资源与请求之间的干扰。

Chunked Prefill将长输入分块调度；Prefix Caching复用相同token前缀的已计算状态；KV量化减少缓存存储。它们作用不同，应该分别验证。具体机制与实验见[缓存和调度专题](../chapters/performance/cache-scheduling.md)。

### 多设备与量化

TP分片层内张量，PP划分阶段，DP使用多个副本；MoE还可能使用EP。Ray可用于组织分布式worker，通信仍需要NCCL/RCCL等完成。量化制品也需要匹配设备kernel，不能只看框架是否认识模型名称。

### 压测与观测

启动日志说明加载、KV预算、编译和warm-up。服务运行后保存请求、错误、TTFT、TPOT/ITL、实际token与资源。框架内部指标和HTTP客户端指标一起看，才能区分计算慢与排队慢。

### 版本、依赖与编译产物是同一套组合

源码框架不只有Python。CUDA/HIP扩展、Triton、FlashInfer与原生库可能在安装或首次生成时构建。`pip install`成功后，还要查当前导入路径与实际设备执行；从源码目录启动可能遮蔽已安装包，torch升级也可能让旧扩展不再兼容。

GB10 DFlash工程为保持cu130版torch使用了特定源码与构建流程；另一份Qwen FP8工程使用不同commit和架构绕过。它们各自有条件，不能把两篇笔记的变量合并成“最新推荐配置”。每个实验保存独立环境和构建日志，升级时回归到目标模型。

## 3.3 vLLM 常见启动模板

启动前准备固定环境、模型目录和任务预算。磁盘路径供服务读取，模型别名供客户端调用，压测tokenizer指向匹配制品。三者需要明确区分。

下面是单设备服务的说明模板，资源参数需先按设备与模型预算：

```bash
vllm serve /srv/models/example-model   --served-model-name example-model   --host 127.0.0.1 --port 8001   --tensor-parallel-size 1   --max-model-len 4096   --max-num-seqs 1   --gpu-memory-utilization 0.80
```

本机先检查`/health`与`/v1/models`，再发一条短请求。`trust-remote-code`只在模型确需并且已审阅固定仓库代码时使用，不应作为所有模型的默认选项。

作者GB10工程的实际配置、启动、请求和200请求结果，在[vLLM服务完整讲解](../chapters/frameworks/vllm-service.md)中按顺序展开。其历史依赖锁与模型revision有缺口，文末说明了需要补齐的材料。

压测放在正常、流式与异常请求检查之后。完整工具选择、负载与结果保存见[压测教程](../chapters/performance/benchmarking.md)。

## 3.4 llama.cpp 知识结构

llama.cpp先解析GGUF与模型结构，借助GGML后端构建和执行计算。权重、KV与临时缓冲按后端分配，生成过程负责采样与文本转换。CLI、benchmark和server是围绕执行核心提供的不同入口。

`llama-cli`适合单次生成；`llama-bench`测引擎的pp与tg；`llama-server`处理HTTP、槽位和调度；`llama-quantize`生成量化候选；RPC可调用远端后端资源。每个工具回答的问题不同。

### 后端与卸载

CPU、CUDA、HIP、Vulkan、SYCL、Metal等后端有各自依赖。`-ngl`提出卸载层数请求，实际层放置与缓冲分配以日志为准。CPU/GPU混合执行时，速度受到双方计算与数据传递的共同影响。

### 上下文与服务槽位

`-c`与`-np`影响上下文和并行请求。不同版本的KV分配和上下文语义可能不同，启动后查看总预算与每槽位可用长度。服务收到的HTTP请求数也可能大于活动槽位数，多余请求需要等待。

入门演练固定`-c 2048`、`-np 2`、`-t 4`和`-ngl 0`。它的两组HTTP请求展示了吞吐上升同时单请求等待增加的现象，后续性能章节会解释这些数字。

### batch、ubatch和槽位不是同一件事

逻辑batch规定一次处理的token预算，物理ubatch影响实际切块与临时工作区；服务槽位描述同时管理的活动序列，上下文又描述历史容量。它们可能相互影响，但不能只因为名字中有batch就都填成并发数。

AMD五机首次验证用`-c512 -b32 -ub8 -fa off`，先降低工作区与上下文压力；RTX2060原服务设置parallel8，但缺完整并发结果。前者是小预算验证，后者是配置意图，均不能单凭参数推导正式服务容量。

改变`-c/-np`后检查每槽位上下文，确认系统提示、历史、当前输入和预期输出都放得下。多轮应用尤其要处理旧历史增长与截断规则，不应等到生产请求超长才发现每槽位预算不足。

## 3.5 llama.cpp 常见构建模板

源码构建包含配置与构建两个阶段。`cmake -S . -B build-xxx`检查依赖并生成工程，`cmake --build`才编译产物。后端或工具链改变时分目录构建，避免旧缓存继续引用错误路径。

```bash
# 选择一条与本机配套的路线执行
cmake -S . -B build-cpu -DCMAKE_BUILD_TYPE=Release
cmake --build build-cpu --target llama-server llama-bench llama-cli -j 4
```

CUDA、HIP、Vulkan和Metal的完整依赖与命令见[构建与服务教程](../chapters/frameworks/llama-cpp.md)。教程固定源码提交，先检查程序版本，再加载模型，最后测试API与停止方式。

Windows读者可以先使用[固定官方CPU二进制演练](../practice/first-service/README.md)。其中下载、SHA256、服务参数、功能输入和实际结果都已公开，适合先完成一次链路，再学习源码构建。

## 3.6 vLLM vs llama.cpp 选型表

| 需求 | 优先验证的候选 | 判断依据 |
| --- | --- | --- |
| 多请求GPU服务 | vLLM等 | 模型/kernel、活动序列、延迟与交付 |
| GGUF、本地、CPU/GPU混合 | llama.cpp | 架构、后端、卸载与资源 |
| Intel端侧 | OpenVINO及支持的SYCL/Vulkan等 | IR、GPU/NPU、任务与内存 |
| Apple本地 | MLX或Metal路线 | 制品、文本/视觉与统一内存 |
| 多卡/多机容量扩展 | 支持该模型的分布式路线 | 切分、互连、通信与恢复 |
| 特定NVIDIA优化 | TensorRT-LLM等 | 支持范围、构建与运维成本 |

先筛掉无法完成任务的组合，再在同样输入、质量和计时边界下比较。最终选型记录应包含选择理由、基线、资源和功能范围。下一章分析这些服务在目标负载下的内存与性能。
