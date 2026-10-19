---
id: T30
title: "1.2.1 NVIDIA GPU与CUDA软件栈"
type: tutorial
volume: book
layer: 1
platform: "NVIDIA"
device: "general"
status: historical
source_ids: []
updated: 2026-10-19
summary: "NVIDIA GPU通过大量并行计算单元执行矩阵和向量运算。CUDA是调用这些设备进行通用计算的软件平台，既用于训练，也用于推理。"
---

# 1.2.1 NVIDIA GPU与CUDA软件栈

[总目录](../../SUMMARY.md) · [硬件与运行时总览](../../02-capability-layers/01-hardware-backends.md)

## 硬件基础

NVIDIA GPU通过大量并行计算单元执行矩阵和向量运算。CUDA是调用这些设备进行通用计算的软件平台，既用于训练，也用于推理。

| 硬件类别 | 常见部署特点 | 选型重点 |
| --- | --- | --- |
| GeForce RTX | 常用于个人工作站与本地推理，多为独立显存 | 显存、散热、实际精度支持、PCIe与供电 |
| RTX专业卡 | 面向专业工作站，具体型号提供不同容量与专业功能 | 容量、驱动、可靠性要求、实际互联 |
| 数据中心GPU | 面向服务器，部分型号采用HBM和高速互联 | 带宽、支持的低精度、多卡拓扑、服务器配套 |
| CPU/GPU集成平台 | CPU架构、内存组织和软件包可能与普通PC不同 | ARM/x86、共享内存、编译目标和平台支持 |

CUDA Core执行通用计算；Tensor Core加速支持的矩阵运算，支持哪些精度随架构变化。显卡“有Tensor Core”不代表任意INT4/FP8模型都能高效执行，还需要相应kernel、布局与形状。

`compute capability`是GPU的计算能力版本，`sm_XX`是设备代码目标，与显存容量和CUDA Toolkit版本不是同一个概念。相同容量的两代显卡，支持的指令与kernel也可能不同。

## CUDA各组件分别做什么

```text
模型/推理引擎 → PyTorch或引擎自带kernel
             → CUDA Runtime/Driver API ＋ 计算库
             → NVIDIA驱动 → GPU
```

| 组件 | 职责 | 部署时的含义 |
| --- | --- | --- |
| NVIDIA Driver | 管理设备并提供底层设备访问，包含CUDA Driver API支持 | 宿主必须有与硬件及程序兼容的驱动 |
| CUDA Runtime | 提供内存分配、执行流、kernel启动与同步等API | 常见库名`libcudart`；可能由软件包或运行环境提供 |
| CUDA Toolkit | 开发套件，包含`nvcc`、头文件、运行时、部分库和开发工具 | 编译CUDA程序或扩展时通常需要；运行现成程序未必需要完整套件 |
| cuBLAS / cuBLASLt | 向量、矩阵乘法；Lt提供更灵活的布局与算法选择 | 模型线性层可能使用，也可能使用引擎的专用kernel |
| cuDNN | 神经网络计算库，包含受支持的算子和图执行能力 | 按引擎依赖使用，不是所有LLM部署都必须单独安装 |
| NCCL | GPU间集合通信，如AllReduce、AllGather | 常用于多卡多机；通信效率还取决于拓扑和网络 |
| attention/量化kernel | 实现注意力、反量化、融合计算等 | FlashAttention等属于算子实现，不是显卡驱动 |

CUDA Runtime、cuBLAS、cuDNN、NCCL有各自的职责与版本；它们不一定随同一个安装包全部提供。PyTorch或容器携带的用户态依赖，也不能替代宿主驱动。

## 怎样选择与理解性能

先检查目标模型和引擎支持，再估算权重、KV和工作区。模型能全部常驻显存时，通常可以避免CPU卸载带来的额外数据路径；放不下时，再比较量化、小模型、卸载或多卡。

长输入prefill、大批量矩阵运算可能更依赖计算吞吐；低批量decode常受权重与KV读取影响。张量计算能力、显存带宽、启动开销和通信都可能成为瓶颈，不能只按显卡峰值TFLOPS选型。

有三种版本信息必须分开：`nvidia-smi`显示驱动及其CUDA兼容能力；`nvcc --version`显示当前编译工具链；`torch.version.cuda`显示该PyTorch构建对应的CUDA信息。它们不必完全相同，但必须满足兼容条件。

基础资料：[CUDA平台](https://docs.nvidia.com/cuda/cuda-programming-guide/01-introduction/cuda-platform.html) · [兼容性](https://docs.nvidia.com/deploy/cuda-compatibility/) · [cuBLAS](https://docs.nvidia.com/cuda/cublas/index.html) · [NCCL](https://docs.nvidia.com/deeplearning/nccl/user-guide/docs/overview.html)。

## 部署操作与工程参考

下面从环境检查、源码构建和模型运行继续展开。历史设备只用于解释具体问题，版本与参数按该记录阅读。

实例：[RTX2060混合卸载](../../cases/C01-rtx2060/README.md) · [RTX4080/A6000双卡](../../cases/C02-dual-4080/README.md) · [GB10量化与推测解码](../../cases/C03-gb10/README.md) · [GB10多模态](../../cases/C04-gb10-multimodal/README.md)。

## 一、先建立环境记录

RTX4090记录使用Ubuntu22.04、32GB主机内存、24GB设备内存与CUDA Toolkit12.9。GB10记录使用Ubuntu24.04 ARM64、128GB与CUDA13。两个环境的CPU架构和设备目标不同，软件包不能直接互换。

```bash
uname -m
nvidia-smi
nvcc --version
ptxas --version
nvidia-smi --query-gpu=name,compute_cap --format=csv
```

`nvidia-smi`中的CUDA字段反映驱动兼容能力，`nvcc`与`ptxas`属于当前工具链，`torch.version.cuda`反映PyTorch构建信息。数字不必完全一致，但组合应受支持。源码扩展还需要核对PyTorch ABI与构建依赖。

如果系统没有`nvcc`，先检查是否真的安装Toolkit，以及PATH指向哪里；不要只凭`nvidia-smi`推断完整编译环境已经存在。

## 二、安装与配置遵循什么顺序

先按操作系统和设备的官方支持准备驱动，重启要求按安装器说明完成；随后准备框架需要的Runtime或Toolkit。已有环境先记录，避免一次同时替换驱动、编译器和框架。

以已经安装在`/usr/local/cuda-12.9`的Toolkit为例，可在当前实验shell设置：

```bash
export CUDA_HOME=/usr/local/cuda-12.9
export PATH="$CUDA_HOME/bin:$PATH"
export LD_LIBRARY_PATH="$CUDA_HOME/lib64:${LD_LIBRARY_PATH:-}"
command -v nvcc
nvcc --version
```

这里先在当前终端验证，成功后再决定是否持久配置。多个Toolkit共存时，记录实际路径，防止构建与运行分别读到不同版本。

## 三、完成一次CUDA框架检查

PyTorch环境可以执行第1章的最小张量计算。llama.cpp路线则进入[构建与服务教程](../frameworks/llama-cpp.md)，使用`-DGGML_CUDA=ON`，通过日志确认设备和实际卸载，再运行小模型。

```bash
cmake -S . -B build-cuda   -DGGML_CUDA=ON -DCMAKE_BUILD_TYPE=Release
cmake --build build-cuda --target llama-server llama-bench llama-cli -j 4
```

先让CMake识别设备目标。需要显式架构时使用本机检查值：原4090记录为89，GB10需要按其实际支持组合核对。编译成功后保存版本与CMakeCache，再做生成。

## 四、实例：找到了nvcc，为什么还在链接时报错？

作者4090记录出现：

```text
No rule to make target '/usr/lib/x86_64-linux-gnu/libcudart.so'
```

错误指向构建缓存引用的库路径。该机器的库实际在Toolkit目录下。此时应检查安装文件和CMake配置，而不是把其他机器的动态库复制过来。

```bash
ls -l /usr/local/cuda-12.9/lib64/libcudart.so*
cmake -S . -B build-cuda-clean   -DGGML_CUDA=ON   -DCMAKE_CUDA_COMPILER=/usr/local/cuda-12.9/bin/nvcc   -DCMAKE_BUILD_TYPE=Release
cmake --build build-cuda-clean --target llama-server -j 4
```

新目录避免旧缓存继续保留错误路径。具体结果以本机配置和构建日志为准；原笔记没有保存可用于本轮完整复建的依赖锁。

## 五、实例：GB10的架构与低精度kernel

GB10工程的vLLM提交`17d87168d`遇到`cvt with .e2m1x2`不支持`sm_121`的错误。它说明框架构建涉及了不适用于该目标的指令路径。原记录曾用12.0目标进行特定尝试，不能把这个值设为所有GB10项目的默认值。

先定位失败kernel、精度和目标，再核对源码修复与CUDA要求。CPU架构正确、设备被识别、普通张量成功，都不足以证明所有低精度路径可用。

## 六、容器与多卡再增加哪些检查

宿主GPU正常而容器看不到设备时，检查NVIDIA Container Toolkit和Docker GPU接入。容器保存用户态环境，仍依赖宿主驱动。完整流程见[环境与容器](../delivery/environment-operations.md)。

多卡先检查`nvidia-smi topo -m`，再验证集合通信。RTX4080不支持NVLink，旧笔记中的桥接建议已修正。双卡总容量也不能直接当作单设备容量，切分与通信需要框架支持。

## 七、完整工程实例：RTX 2060 12GB 怎样运行大于显存的模型？

这份记录适合回答一个常见端侧问题：显存放不下全部权重时，怎样判断混合推理是否还有使用价值？原设备为i5-12400F、32GB系统内存、RTX 2060 **12GB版**，使用Windows CUDA版llama.cpp。不要套用到6GB版2060；容量差异会改变可以卸载的层数和主机压力。

记录中的主模型是`Qwen3-30B-A3B-Q6_K.gguf`。30B表示总参数规模，A3B表示每token的激活规模；未激活专家仍属于模型资产。把它当成一个只需存放3B权重的小模型，会从容量估算开始出错。

### 7.1 先把三类内存分开

加载前先记录模型文件字节数、可用系统内存、专用显存和当前页面文件活动。权重可以分布在CPU与GPU，执行还需要KV和临时缓冲。任务管理器的“共享GPU内存”也不能直接视为与显卡本地显存等速的存储。

```powershell
Get-CimInstance Win32_Processor | Select-Object Name, NumberOfCores, NumberOfLogicalProcessors
Get-CimInstance Win32_OperatingSystem | Select-Object TotalVisibleMemorySize, FreePhysicalMemory
Get-Item -LiteralPath '.\models\Qwen3-30B-A3B-Q6_K.gguf' | Select-Object Name, Length
nvidia-smi --query-gpu=name,memory.total,memory.used --format=csv
.\llama-server.exe --version
.\llama-server.exe --list-devices
```

先确认二进制来自同一发行包，CUDA依赖与程序匹配。日志需要出现CUDA后端及RTX 2060，而不是只有CPU。接着查看模型加载日志中的实际卸载层数、CPU/GPU缓冲与KV大小；这些才是分配结果。

### 7.2 怎样阅读原配置

原笔记使用`--top-k 1 -c 2048 -n 1000 -ngl 99 --mlock --parallel 8`等参数。它们描述不同事情：

| 参数 | 工程含义 | 本例应检查什么 |
| --- | --- | --- |
| `-ngl 99` | 请求尽量卸载较多层 | 实际卸载日志、显存和加载是否成功 |
| `-c 2048` | 此版本的上下文预算 | 启动日志中的总上下文与每槽位上下文 |
| `--parallel 8` | 配置服务槽位 | 每槽位容量、同时活跃请求和KV占用 |
| `-n 1000` | 默认生成上限 | 请求端是否另设上限、是否自然结束 |
| `--top-k 1` | 把候选限制为最高项 | 模型模板与质量是否正常 |
| `--mlock` | 尝试锁住映射内存 | 系统权限、实际是否成功、其他进程余量 |

`-ngl 99`不代表“显存不够时一定自动得到最佳混合方案”。有些版本会在分配阶段直接失败，另一些组合有自动适配行为。公开教程应从可以解释的较小卸载量起步，按日志调整。

原记录还出现`--tensor-split 0.9,0.1`。这个选项用于后端设备之间的分配，**不是CPU/GPU各占10%/90%的通用开关**。单CUDA设备的混合执行主要先用层卸载建立基线；多设备切分另见[多卡专题](../performance/parallelism.md)。

### 7.3 重新组织为可检查的运行顺序

以下是依据原工程整理的检查配置，先用单槽位、短输出，便于定位容量；它与历史成绩的完整配置不同，不给它配上旧性能数字。

```powershell
.\llama-server.exe -m .\models\Qwen3-30B-A3B-Q6_K.gguf `
  --alias qwen30b-q6 -ngl 20 -c 2048 --parallel 1 `
  --host 127.0.0.1 --port 8081
```

前台启动后，在另一终端提交`你好`和一条有明确答案的短题。检查完整响应、结束原因、实际prompt/eval token数。加载失败先减少卸载或换更小制品；短题正常后，再以固定输入分别尝试更多卸载层。每次重启前保存命令、加载日志和空闲资源，不把多次配置的资源截图拼成一组结果。

卸载层数提高后，GPU常驻权重增加、CPU侧权重与执行负担可能变化，但模型结构、缓冲和映射使内存不会严格按层数线性变化。一次尝试只有在功能正确、没有持续换页且速度收益可见时，才值得保留。

### 7.4 原记录的一次真实生成

Q6记录中，“你好”这次生成留下了完整引擎计时：

| 阶段 | token数 | 时间 | 速率 |
| --- | --- | --- | --- |
| Prompt eval | 9 | 995.30ms | 9.04token/s |
| Eval | 182 | 34618.63ms | 5.26token/s |
| 两项时间合计 | 191 | 35613.93ms | 不把两阶段平均成decode速度 |

按原始时间核算，prompt约110.59ms/token，eval约190.21ms/token。这里的182是实际生成数，不是配置的1000。该表是引擎观察，不包含一套完整HTTP并发测试，也不说明长输入下仍有相同速度。

同时观察到CPU约21%、系统内存85%—89%、GPU98%—100%。GPU高利用率与生成只有约5.26token/s可以同时成立：大模型的带宽、CPU/GPU数据路径和每步工作量都影响速度，利用率不是用户体验分数。

原笔记用“磁盘交换100%”描述了压力现象，但没有保存可确认是页面文件、磁盘活动时间还是另一统计项的完整上下文，因此本体系不替它补写监控定义。要进一步判断，应同步采集页面读入、磁盘吞吐、进程工作集和TTFT/TPOT。

### 7.5 并发为什么要最后增加

原Q6压测命令有EvalScope `parallel=8、number=2`，另一个Q5记录为`Qwen3-32B-Q5_K_M.gguf`、服务槽位4、测试`parallel=1、number=5、max-tokens=200`。记录没有可读的完整请求成绩，不能填“8并发通过”或给Q5补上速度。

增加槽位会影响上下文分配与KV，也会让多个请求竞争同一内存带宽。正确扩展顺序是：单请求完成目标输入输出长度，再测c1、c2，观察总吞吐是否增加以及每个请求的等待是否可接受。系统内存已经持续接近耗尽时，先降低模型/上下文/并发压力。

### 7.6 这个实例可以得到什么结论

在这套32GB RAM＋12GB显存配置下，大于显存的Q6模型完成了一次混合生成，留下约5.26token/s的decode观察。是否适合日常使用还要由完整答案、目标长度、持续换页和交互等待共同决定。若目标是流畅交互，较小模型全GPU与大模型混合执行应作为两个独立候选比较，不能预先认定参数量更大的方案更好。

## 八、GB10的视觉部署：文本端点之后还要验证哪些环节？

作者的GB10资料包含Qwen3-VL、Qwen3-Omni和granite-docling。它们共享设备，不共享全部运行边界。视觉需要processor、图像encoder和图文拼接；Omni还可能涉及音频编码、输出头和流式协议。一个`/v1/models`成功响应只能证明服务可访问。

原工程使用`nvcr.io/nvidia/vllm:25.12-py3`配套环境。模型与主要参数如下，作为部署记录保留，表内较大上限不等于已做过同长度验收：

| 模型 | 原端口 | 主要配置 | 要单独验收的内容 |
| --- | --- | --- | --- |
| Qwen3-VL-30B-A3B | 8006 | TP1、PP1、memory0.8、batched4096；ctx曾设100000/131072 | 多图、图像尺寸、长输入实际token |
| Qwen3-VL-8B | 8007 | 单设备、memory0.8 | 图像解析、正文、流式结束 |
| Qwen3-Omni-30B-A3B | 8008 | TP1、PP1、memory0.9 | 文本、图像、音频输入和音频输出分别测试 |
| granite-docling-258M | 8009 | TP1、PP1、seqs512、batched8192、chunked prefill、memory0.9 | 文档转写结构、顺序和内容准确性 |

这些端口属于不同次实验，不能据此判断所有模型同时常驻。16/128GB设备的统一内存中，图像预处理、视觉token、KV和多模态缓存同样占预算。新部署先以单模型、单图、单请求完成链路，再逐步恢复原预算。

完整图像输入生成、base64请求、SSE客户端和验证过程接续[vLLM服务章](../frameworks/vllm-service.md#七从图片文件到流式答案的完整链路)。

## 本节完成检查

环境记录能区分驱动、Toolkit和框架；最小计算完成；实际模型使用目标后端；构建与错误能追溯到固定版本。随后进入模型与服务章节。

来源：作者《linux编译llama.cpp-CUDA版本》《DGX Spark适配编译vLLM部署Qwen3.6-35B-A3B》及双卡部署记录，见[文章对应表](../../evidence/chapter-sources.md)。
