# 1.2.3 Intel硬件、oneAPI与OpenVINO

[总目录](../../SUMMARY.md) · [硬件与运行时总览](../../02-capability-layers/01-hardware-backends.md)

## 硬件基础

Intel平台可能提供CPU、集成GPU、Arc独立GPU和NPU。CPU负责通用工作；GPU适合并行模型计算；NPU面向支持的神经网络工作负载。Core Ultra是处理器产品系列名称，不能单凭名称确定GPU/NPU代际或大模型支持范围。

| 设备 | 内存与计算特点 | 部署重点 |
| --- | --- | --- |
| CPU | 使用系统RAM，通过支持的向量/矩阵指令计算 | 指令集、线程、内存通道、NUMA与算子库 |
| 集成GPU | 使用共享系统内存 | 带宽、设备预算、CPU/GPU争用与驱动 |
| Arc独立GPU | 通常有独立显存 | 型号、显存、驱动、支持的kernel与精度 |
| NPU | 通常依赖专用编译与执行插件 | 模型图、shape、算子、精度和编译时间 |

GPU设备可用不表示NPU插件可用，NPU能执行某个语音模型也不表示能直接执行任意LLM。

## oneAPI、SYCL和OpenVINO是什么

| 组件 | 职责 | 与大模型部署的关系 |
| --- | --- | --- |
| oneAPI | 跨架构开发的软件规范与工具/库生态 | 提供编译器、计算库、分析工具等，不是单个运行时 |
| SYCL | 基于C++的异构并行编程标准 | llama.cpp SYCL等后端的开发与执行路线 |
| Level Zero | Intel GPU的底层设备访问与执行接口 | 常用于相应SYCL运行时的GPU路径 |
| oneDNN / oneMKL | 深度学习算子和数学计算库 | 按设备与框架版本提供相应计算实现 |
| OpenVINO Runtime | 加载模型、编译图并通过设备插件执行 | 按CPU/GPU/NPU目标验证模型与算子 |
| OpenVINO GenAI | 基于Runtime提供生成式模型管线 | 分词、生成、KV与对应多模态能力 |

```text
GGUF → llama.cpp SYCL后端 → SYCL运行时/Level Zero → Intel GPU
IR及配套文件 → OpenVINO GenAI → Runtime设备插件 → CPU/GPU/NPU
```

Vulkan是另一条GPU计算路线；PyTorch XPU也有自身的包、算子与后端要求。这些路线的制品、内存管理和计时边界不同，不能只根据设备品牌互换。

## 选型和优化先看什么

本地文本先选模型实现完整、输出正确的后端，再比较加载、首token、decode和资源。需要NPU时，先检查模型图、shape和编译约束；不要仅凭TOPS或低功耗宣传决定整条链路。

集成GPU和NPU都可能与CPU共享内存，图像、音频预处理与多个管线也会占用系统资源。混合执行应记录每个模块实际用的设备，端到端结果包含预处理、执行和后处理。

基础资料：[oneAPI](https://www.intel.com/content/www/us/en/developer/tools/oneapi/overview.html) · [OpenVINO](https://docs.openvino.ai/)。

## 部署操作与工程参考

下面以设备枚举、三种GPU后端和NPU管线解释检查方法。完整历史记录见[Arc GPU、NPU与ASR/TTS](../../engineering/intel-arc-npu.md)。

## 一、三条常见路线

llama.cpp Vulkan使用Vulkan驱动执行受支持GGUF；SYCL路线依赖oneAPI与相应运行时；OpenVINO GenAI使用配套IR和设备插件。XPU框架路线也需要核对特定模型和kernel。

| 路线 | 主要制品 | 先检查 |
| --- | --- | --- |
| Vulkan | GGUF | 设备、驱动、shader与卸载 |
| SYCL | GGUF | oneAPI、Level Zero与框架构建 |
| OpenVINO GenAI | IR与配套文件 | Pipeline、插件、模型图和精度 |

同一个“OpenVINO”名称也不能省略执行器。llama.cpp OpenVINO＋GGUF，与GenAI＋IR，是不同链路。

## 二、环境采集

作者测试设备为Core Ultra7 256V、Arc Lunar Lake、16GB统一内存，Ubuntu24.04.4；Mesa26.1.4、oneAPI2026.1.0、OpenVINO2026.2.1、GenAI/Tokenizers2026.2.1.0。

```bash
vulkaninfo --summary
sycl-ls
icpx --version
```

这些命令用于已经安装对应软件栈的环境，保留实际设备与版本。使用OpenVINO时再枚举插件：

```python
import openvino as ov
core = ov.Core()
print(ov.__version__)
for device in core.available_devices:
    print(device, core.get_property(device, 'FULL_DEVICE_NAME'))
```

枚举只证明设备可发现，下一步应加载匹配IR并真正生成token。

## 三、先选择一个可完成任务的入口

原工程中，GenAI GPU完成了Qwen3.5-9B的INT4和INT8短生成；NPU INT4在编译阶段失败，INT8编译420秒后超时退出124。这里可以使用已通过的GPU路线继续测试完整答案，同时保留NPU失败条件。

另一条llama.cpp OpenVINO尝试可以构建和枚举，却在GGUF建图遇到CPY/cache_r等问题。它不能被GenAI GPU成功覆盖。

## 四、16GB资源怎样判断

Vulkan/SYCL记录采用GPU23层、CPU10层，属于混合执行。应同步观察主机内存、swap和设备分配。IR路线的内存组织和计时不同，需要单独建立基线。

原记录中Vulkan引擎生成11.54±0.13token/s，SYCL为10.22±0.19；OpenVINO INT4管线21.1599token/s。后者使用不同制品和计时边界，不能直接相除宣称框架加速。

## 五、进入完整操作

按[OpenVINO IR完整运行](../frameworks/openvino.md)准备独立环境、固定revision、下载文件、枚举GPU、预热、生成并保存指标。该教程把CPU/GPU/NPU目标写清楚，默认沿用原记录的GPU入口。

完成后再准备业务长度和质量集。原19输入/128输出记录在思考阶段到达上限，因此完整答案质量仍需单独验收。

## 六、完整对照：Vulkan与SYCL怎样测得清楚

原工程的GGUF为Qwen3.5-9B Q4_K_M，约5.23GiB，8.95B参数；33个可卸载层中GPU23、CPU10。这个分配很重要：表中的速度属于混合执行，不能标成“全部运行于GPU”。

Vulkan和SYCL使用独立构建目录，避免CMake缓存与动态库串用。先固定同一个源码快照、模型摘要、线程数与卸载，再分别编译。原快照没有`.git`，只有ggml0.16.0版本信息，所以历史commit仍记unknown；新实验应该补上源码commit，而不是凭日期猜版本。

```bash
cmake -S . -B build-vulkan -DGGML_VULKAN=ON -DCMAKE_BUILD_TYPE=Release
cmake --build build-vulkan --target llama-bench llama-server -j 4

source /opt/intel/oneapi/setvars.sh
sycl-ls
cmake -S . -B build-sycl -DGGML_SYCL=ON \
  -DCMAKE_C_COMPILER=icx -DCMAKE_CXX_COMPILER=icpx \
  -DCMAKE_BUILD_TYPE=Release
cmake --build build-sycl --target llama-bench llama-server -j 4
```

具体构建依赖按固定llama.cpp版本准备。Vulkan需要匹配的headers、loader及shader编译工具，SYCL需要编译器和运行时。构建通过后，先用短请求核对两条路线输出，再进入相同pp/tg基准。

```bash
./build-vulkan/bin/llama-bench -m "$QWEN_GGUF" \
  -ngl 23 -t 8 -fa on -p 512 -n 128 -r 3

export ONEAPI_DEVICE_SELECTOR=level_zero:0
export ZES_ENABLE_SYSMAN=1
./build-sycl/bin/llama-bench -m "$QWEN_GGUF" \
  -ngl 23 -t 8 -fa on -p 512 -n 128 -r 3
```

设备选择器中的0应核对`sycl-ls`，不能假定多Intel设备机器上0永远是期望GPU。比较时启动一条路线、测完释放，再启动另一条。原始数据如下：

| 路线与边界 | 输入/生成 | Prompt速率 | 生成速率 |
| --- | --- | --- | --- |
| SYCL引擎，三轮 | pp512 / tg128 | 353.70±15.31token/s | 10.22±0.19token/s |
| Vulkan引擎，Mesa26.1.4，三轮 | pp512 / tg128 | 244.91±0.79token/s | 11.54±0.13token/s |
| SYCL HTTP短请求 | 16 / 128 | 11.67token/s | 9.21token/s |
| Vulkan HTTP短请求 | 22 / 128 | 10.53token/s | 11.38token/s |

SYCL的pp更高，Vulkan的tg更高。这并不矛盾：长输入处理与逐token生成的计算形态不同。如果日常输入很长、回答很短，应重点测TTFT；如果输入短、输出长，decode速率权重更大。两条HTTP请求输入token不同，不能把差异全部归给后端。

### Mesa升级观察

旧Mesa25.2.8记录生成约7.76token/s，26.1.4为11.54±0.13，观察提升约48.7%。原旧基线没有同样完整的重复记录，适合写“驱动版本变化后的历史观察”；新测试应保存旧/新驱动、同模型、同参数和复测轮次。

驱动升级后还要验证桌面、Vulkan和目标服务，保留可恢复的软件包与配置。不要只因一个模型速度提升，就跳过其他应用和长期稳定性检查。

## 七、Windows IPEX-LLM与Ollama：保留旧路线，改正默认假设

早期工程采用Python3.11独立conda环境、`ipex-llm[cpp]`预发布包，通过`init-ollama.bat`准备Intel适配版程序，再启动Ollama。它可以作为历史兼容路径阅读，但预发布依赖会变化，当前复建要先查项目维护状态、支持设备和固定包版本。

目录中同时存在系统Ollama与适配版时，先确认当前执行的是哪一个：

```powershell
Get-Command ollama -All | Select-Object Source
ollama --version
Get-CimInstance Win32_VideoController | Select-Object Name, DriverVersion
```

原环境变量包含`ZES_ENABLE_SYSMAN=1`、`SYCL_CACHE_PERSISTENT=1`和`OLLAMA_NUM_GPU=999`。其中999表达卸载请求，不保证所有层实际落在GPU；仍需从服务日志和`ollama ps`等该版本提供的运行状态检查。旧`SYCL_PI_LEVEL_ZERO_USE_IMMEDIATE_COMMANDLISTS=1`属于可测试选项，可能改善或降低性能，不能无条件保留到所有版本。

Modelfile从本地GGUF导入时，先确认GGUF的tokenizer和模板可识别。原笔记中的Mistral `[INST]`模板不能原样用于Qwen或其他架构：

```text
FROM ./model.gguf
PARAMETER num_predict 256
```

先让匹配版本读取模型自带模板，必要时再按模型约定显式设置。创建、短题、多轮、自然结束、资源观察全部通过后再接应用；“ollama create成功”只表示制品已登记。

## 八、NPU形状适配：为什么一个模型不能只换device

GPU与CPU通常更容易接受动态shape；NPU编译路径对形状边界、状态和算子有自己的要求。把模型导出为IR只完成图表达转换，还需要目标插件能够编译、执行并保持数值语义。

TTS工程很好地显示了这个区别。原Qwen3-TTS0.6B成品包含Talker、Code Predictor、embedding/projection和Speech Tokenizer多个图。直接`device=NPU`先在Encoder失败；跳过不需要的Encoder后，Decoder又因无上界动态长度失败；把Tokenizer留在CPU、只迁移Talker，仍遇到动态ShapeOf错误。三个失败各自定位到不同子图。

```text
Upper bounds are not specified
Got negative shape dim bound: '-1'
to_shape was called on a dynamic shape
```

正确适配先列出每个图的输入、输出、动态维、状态、精度和目标设备，再考虑固定shape或多个bucket。bucket不是任意padding后就成功：有效长度、attention mask、位置编码、KV位置和EOS都要保持原语义。

| 需要检查 | 为什么影响正确性 |
| --- | --- |
| text/token长度 | padding区域不能当作有效上下文 |
| KV容量与实际位置 | 写入/读取错误会在多步后放大 |
| codec帧上限 | 到达上限不能假称自然结束 |
| 子图输出dtype | 后续图的精度和布局必须匹配 |
| CPU fallback | 影响真实设备分工、延迟和内存 |

编译缓存的身份也应包含模型与图形状、插件/驱动、精度和编译选项。换了IR或bucket后，旧cache不能自动作为兼容证据。

## 九、从单模型走到16GB设备上的任务分工

作者资料中LLM、ASR和TTS在同一设备测试。LLM占用统一内存时，语音编译与运行会受到竞争，因此原语音专项先停止LLM服务。这个条件必须随成绩保存，否则不能把独占测试成绩直接承诺为三模型同时运行表现。

实测给出了可解释的分工候选：LLM采用已通过的GPU路线；Whisper Base INT8的NPU核心RTF约0.0387；Kokoro CPU的48例RTF P95为0.189。它们说明不同任务可以在不同设备路径上取得结果，但同时运行时的内存与争用还需专门复测。

尤其不能因BabelVox全NPU路径RTF0.723就选它：那组音频回译只有一个字，质量失败。完整参数、三轮表、48例Kokoro结果和回滚过程见[OpenVINO语音实战](../frameworks/openvino.md#七完整工程记录whisper-asr的冷启动与热推理)。这里的选型依据是正确输出、资源与性能一起成立。

来源：作者《Qwen3.5-9B Intel OpenVINO平台推理对比报告》、Intel视觉与IPEX/Ollama记录，见[文章对应表](../../evidence/chapter-sources.md)。
