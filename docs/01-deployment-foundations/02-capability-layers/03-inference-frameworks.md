# 第3层：推理框架层

[总目录](../SUMMARY.md) · [vLLM流程](../chapters/frameworks/vllm-service.md) · [llama.cpp流程](../chapters/frameworks/llama-cpp.md) · [OpenVINO流程](../chapters/frameworks/openvino.md)

## 3.1 框架定位

推理引擎把模型文件变成可以执行的程序：加载权重、套用模板、管理KV、选择kernel、调度请求，再把token转换为输出。它与CUDA、ROCm等设备软件栈配合工作。

### 先区分框架、引擎和服务

| 层次 | 职责 | 例子 |
| --- | --- | --- |
| 张量/机器学习框架 | 数组、计算图、算子和设备执行 | PyTorch、MLX |
| 推理引擎或模型管线 | 模型实现、生成循环、KV、批处理和采样 | vLLM、llama.cpp、MLX-LM、OpenVINO GenAI |
| 模型服务 | 协议、请求校验、队列、流式输出和监控 | 引擎自带server、独立服务封装 |
| 应用层 | 对话界面、业务编排、知识检索、工具调用 | 桌面客户端、Web应用、业务API |

一个项目可能同时覆盖几层，例如vLLM既有引擎也提供HTTP服务。判断职责时看实际执行链，不按项目名称推断所有功能。

### 加载和生成不是同一个阶段

```text
启动：读取配置/权重 → 分配设备内存 → 编译或加载kernel/图
    → 分配缓存和工作区 → 预热 → ready
请求：模板与分词 → 排队 → prefill → decode/采样 → 输出 → 回收状态
```

加载时间、首请求时间和稳定生成时间要分别观察。模型端口已监听，不代表模型已ready；首个请求慢，也不一定代表每轮decode都慢。

### 常见引擎的定位

| 框架 | 主要工程对象 | 优先核对 |
| --- | --- | --- |
| vLLM | 多请求服务、KV调度、TP/PP/EP、OpenAI API | 模型/量化kernel、后端与调度参数 |
| llama.cpp | GGUF、CPU/GPU卸载、多后端、CLI/server | 张量类型、后端、内存、槽位 |
| TensorRT-LLM | NVIDIA配套编译与服务优化 | GPU代际、模型、执行制品与版本 |
| SGLang | 服务调度、缓存、结构化等 | 模型/后端、前缀管理与协议 |
| OpenVINO GenAI | Intel等支持设备的IR管线 | 模型导出、设备编译与shape |
| MLX-LM / MLX-VLM | 基于MLX的文本/视觉模型实现 | 模型制品、processor、模板与服务封装 |
| Ollama/LM Studio | 本地模型管理和接口 | 模板、实际后端与资源，UI可用不代替压测 |

## 3.2 vLLM 知识结构

```text
HTTP/API校验 → chat template/tokenizer → 等待队列
 → Scheduler → KV Block Manager/Prefix Cache
 → Model Executor → attention/matmul/MoE kernel
 → sampler → detokenize → SSE/JSON → 结束与资源回收
```

| 子系统 | 参数 / 数据 | 工程机制 |
| --- | --- | --- |
| 接入 | model、messages/prompt、max_tokens、stop | 参数、长度、模板和输入校验 |
| Prefill/Decode | 输入token、历史KV、当前token | prefill建状态，decode逐步生成 |
| KV管理 | block、dtype、引用、可用块 | 分块分配/回收，前缀可复用 |
| 调度 | max-num-seqs、max-num-batched-tokens | 活动序列数与每轮token预算，均不等于客户端请求数 |
| 长输入 | enable-chunked-prefill | 分块调度，影响prefill/decode干扰 |
| 重复前缀 | enable-prefix-caching | 同token前缀复用，缓存冷暖与租户要记录 |
| 模型并行 | tensor/pipeline parallel、expert parallel | rank映射、通信、每卡预算 |
| 图与执行 | enforce-eager、attention-backend | 预热/图捕获、工作区与kernel支持 |
| 输出 | reasoning/content、finish_reason、usage | EOS/stop/length/取消/错误分别记录 |

进程监听端口、模型ready、功能通过和负载通过是四种状态。原生扩展、torch、Triton/FlashInfer/设备库需成套；源码目录可遮蔽已安装模块，升级Python包后也可能仍加载旧so。

## 3.3 vLLM 常见启动模板

```bash
vllm serve /srv/models/example-model \
  --served-model-name example-model \
  --host 127.0.0.1 --port 8001 \
  --tensor-parallel-size 1 \
  --gpu-memory-utilization 0.80 \
  --max-model-len 4096 --max-num-seqs 1
```

这是小预算配置模板，模型和参数需按设备验证。`gpu-memory-utilization`是引擎内存预算，不是GPU算力利用率。`trust-remote-code`仅在固定模型确需并已审阅时使用。

```bash
curl --fail-with-body http://127.0.0.1:8001/health
curl --fail-with-body http://127.0.0.1:8001/v1/models
curl --fail-with-body http://127.0.0.1:8001/v1/chat/completions \
  -H 'Content-Type: application/json' \
  -d '{"model":"example-model","messages":[{"role":"user","content":"计算12乘13，只输出数字。"}],"temperature":0,"max_tokens":128}'
```

先验收功能、SSE、异常和取消，再用固定tokenizer压测。启动、KV预算、热身和真实200请求数据见[GB10完整实例](../engineering/nvidia-gb10.md)。

## 3.4 llama.cpp 知识结构

```text
GGUF读取/架构识别 → Tensor与GGML graph → CPU/设备后端
 → 权重/KV/循环状态/工作区 → prefill/decode → 采样/模板
工具：llama-cli / llama-bench / llama-server / llama-quantize
```

| 参数 | 作用 | 观察对象 |
| --- | --- | --- |
| -ngl / --n-gpu-layers | 请求卸载层数 | 实际offloaded层、每backend buffer |
| -c / --ctx-size | 上下文预算 | 总ctx、每槽ctx、KV/状态与长输入 |
| -np / --parallel | 并行槽位预算 | 活动序列、等待请求、每槽长度 |
| -b / --batch-size | 逻辑token batch | prefill吞吐、调度与工作区 |
| -ub / --ubatch-size | 物理微批 | 临时buffer峰值和kernel效率 |
| -t / --threads | CPU执行线程 | CPU负载与decode耗时 |
| --threads-batch | prefill侧线程 | pp耗时、调度与争用 |
| -fa | Attention实现选择 | 后端支持、KV dtype、正确性与速度 |
| tensor-split / split-mode | 设备分配与切分 | 每设备权重、KV、通信 |

ctx与parallel的语义按固定版本启动日志核对，不能只按一个通用除法估算。CPU/GPU混合还受双方计算、数据传输与RAM影响。GDN/SSM等结构有循环状态，不能只套纯attention KV模型。

## 3.5 llama.cpp 常见构建模板

同一源码、各后端独立build目录。先记录commit、编译器、Runtime与目标arch，配置后检查CMakeCache里实际启用项。

```bash
# 选择当前设备的一条路线；依赖按平台实例准备
cmake -S . -B build-cpu -DCMAKE_BUILD_TYPE=Release
cmake -S . -B build-cuda -DGGML_CUDA=ON -DCMAKE_BUILD_TYPE=Release
cmake -S . -B build-hip -DGGML_HIP=ON -DCMAKE_BUILD_TYPE=Release
cmake -S . -B build-vulkan -DGGML_VULKAN=ON -DCMAKE_BUILD_TYPE=Release
cmake -S . -B build-metal -DGGML_METAL=ON -DCMAKE_BUILD_TYPE=Release
```

```bash
# 示例：已经配置CUDA目录后
cmake --build build-cuda --target llama-server llama-bench llama-cli -j 4
./build-cuda/bin/llama-cli --version
./build-cuda/bin/llama-cli --list-devices
./build-cuda/bin/llama-server \
  -m /srv/models/model.Q4_K_M.gguf -ngl 99 -c 4096 -np 1 \
  --host 127.0.0.1 --port 8080
```

SYCL、MUSA、CANN按对应提交和厂商工具链单独准备，未知CMake变量可能被忽略，不能据此认定后端已启用。平台完整步骤见[实例矩阵](../engineering/README.md)。

## 3.6 vLLM vs llama.cpp 选型表

| 约束 | 优先候选 | 决策证据 |
| --- | --- | --- |
| GGUF、低显存、混合卸载 | llama.cpp | 支持架构、RAM/VRAM、卸载与质量 |
| 多请求服务、模型并行 | vLLM等服务引擎 | kernel、调度、目标SLO下有效吞吐 |
| Intel端侧 | IR/GenAI、SYCL/Vulkan | 图/shape、设备编译、完整输出 |
| Apple统一内存 | Metal或MLX路线 | 制品、文本/视觉、缓存与并发 |
| 特定NVIDIA深度优化 | TensorRT-LLM等 | 模型支持、构建成本、实际性能 |
| 快速本地管理 | Ollama/LM Studio | 后端、模板、API与维护成本 |

先通过硬件、制品、功能三个筛选，再比较同任务质量、延迟、资源与交付成本。完整FlowUs框架/服务文章写入各设备实例，不用选型表替代部署步骤。

## 2026-10 工程更新

[当前引擎选型](../chapters/frameworks/serving-engines.md)补充V1调度、SGLang、TensorRT-LLM入口、混合模型状态与版本配套。
