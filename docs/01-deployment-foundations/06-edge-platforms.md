# 06 把部署流程迁移到 AMD、Intel 和 Mac

[总目录](README.md) · [上一章](05-llama-cpp-practice.md) · [下一章：服务与调度](07-serving-and-scheduling.md)

**本章目标：** 保留同一套模型身份、功能测试和测量方法，按目标设备重新选择后端。迁移时先验证一条最小路线，再扩展并发和功能。

## 1. 迁移时哪些内容可以复用

| 可以复用 | 必须重新确认 |
| --- | --- |
| 任务说明、公开输入、质量评分规则 | 设备可用内存、驱动和工具链 |
| API 请求结构和错误检查 | 模型架构、量化制品和后端算子支持 |
| 指标定义、结果文件结构 | 实际上下文、并发、卸载层数 |
| 启停和回归检查的流程 | 冷启动、速度、功耗、温度和稳定性 |

模型制品也未必能复用。例如 GGUF 和 OpenVINO IR 的执行路线不同。不能只改一个设备参数就认为迁移完成。

## 2. AMD Windows：从 780M 旧流程学什么

FlowUs《AMD 780M-GPU 适配教程》记录过：安装 HIP SDK 与驱动、准备 `gfx1103` 社区库、使用 `ollama-for-amd`，再用 `ollama serve` 启动服务。记录引用过 `v0.5.1` 和配套 ROCm 库。

这是一条有版本条件的社区适配路线。旧版 DLL 与 SDK 不能随意混装，也不能因为 890M 笔记引用了同一下载页就认定两个设备已经验证等价。

现在重做这个流程，建议按下面顺序：

1. 用设备管理器或下方命令确认 GPU 与驱动。
2. 检查当前官方支持与社区版本说明，选择一套完整组合。
3. 把不同版本的程序、运行库和日志分目录保存。
4. 先启动服务，确认实际后端与 GPU 使用情况。
5. 用同一条短请求检查模板，再测实际业务长度。
6. 保留可恢复的上一套程序和配置，确认升级后还能回退。

PowerShell 只读检查：

```powershell
Get-CimInstance Win32_VideoController |
  Select-Object Name, DriverVersion
Get-ChildItem -LiteralPath '.\bin' -Filter '*.dll' |
  Select-Object Name, Length
```

**检查方法：** 程序日志显示的设备、后端与实际硬件一致。任务管理器观察计算引擎和内存仅作辅助，不用一张 GPU 百分比图代替实际推理结果。

## 3. AMD Linux：HIP 与 Vulkan 分开构建

FlowUs 中既有 ROCm/HIP，也有 Vulkan 路线。两种后端的运行库不同，不要混用构建目录或复制出来的 DLL/so。

```text
llama.cpp/
├── build-hip/       HIP 产物与配置
└── build-vulkan/    Vulkan 产物与配置
```

下面是支持相应 CMake 选项版本的**构建模板**。先准备该版本的 ROCm/HIP 或 Vulkan SDK 与驱动，再执行。`gfx1151` 来自已有 8060S 记录，其他设备使用自己的实测标识。

```bash
cmake -S . -B build-hip \
  -DGGML_HIP=ON -DAMDGPU_TARGETS=gfx1151 \
  -DCMAKE_BUILD_TYPE=Release
cmake --build build-hip --target llama-server llama-bench -j 4
```

```bash
vulkaninfo --summary
cmake -S . -B build-vulkan \
  -DGGML_VULKAN=ON -DCMAKE_BUILD_TYPE=Release
cmake --build build-vulkan --target llama-server llama-bench -j 4
```

一些旧版本使用不同变量或还需要显式指定 HIP 编译器。以固定源码的构建文档和 CMake 输出为准；出现“变量未使用”时应停下来核对，不能忽略后继续宣称开启成功。

**实际笔记的修订：** 同一批 395 材料曾出现 `gfx1152` 与 `gfx1151` 两种写法。本体系使用有设备记录支撑的 `gfx1151` 解释实例，实际目标仍由 `rocminfo` 等运行输出确认。不能靠复制笔记选择架构。

## 4. Intel 16GB 设备：用真实对比选择后端

2026-07-15 的 FlowUs 测试记录：Core Ultra 7 256V、Lunar Lake 核显、Intel NPU、16GB 统一内存；Ubuntu 24.04.4。主要环境为 Mesa 26.1.4、oneAPI 2026.1.0、OpenVINO 2026.2.1、GenAI/Tokenizers 2026.2.1.0。

| 路线 | 制品与测试 | 记录结果 | 怎样使用结论 |
| --- | --- | ---: | --- |
| llama.cpp Vulkan | Q4_K_M，GPU 23/CPU 10 层，pp512/tg128，3 轮 | 生成 11.54 ± 0.13 token/s | 引擎基准，另有 HTTP 记录 |
| llama.cpp SYCL | 同一 GGUF 与分层，pp512/tg128，3 轮 | 生成 10.22 ± 0.19 token/s | 同设备后端候选比较 |
| OpenVINO GenAI GPU | INT4 IR，19 输入/128 输出 token | 21.1599 token/s，TTFT 184.02ms | 管线内部指标，输出截断在思考阶段 |
| OpenVINO GenAI GPU | INT8 IR，同提示与生成设置 | 10.1047 token/s，TTFT 169.73ms | 可与上述 INT4 管线作有限对照 |
| OpenVINO NPU | INT4 IR | 编译失败 | 未获得推理吞吐 |
| OpenVINO NPU | INT8 IR | 420 秒编译超时 | 未进入生成，不能当成推理成功 |

不要用 `21.16 / 11.54` 直接宣称严格的框架加速比：两项的模型制品和计时边界不同。INT4/INT8 的 2.09 倍也是该短生成记录的比值，需要多轮、质量、内存与稳定性回归后才能发布业务结论。

### 4.1 复查 OpenVINO 路线

原记录的 INT4 模型为 `OpenVINO/Qwen3.5-9B-int4-ov`，revision 为 `3f31fc1609edb0cbc8b131bc4c291f1b15cb0676`，24 文件共 `6,129,582,094` 字节。

前提：模型已完整下载到 `/srv/models/Qwen3.5-9B-int4-ov`；使用与记录匹配、依赖可解析的独立环境。以下是记录中推理代码的公开路径改写，**本轮未在 Intel 设备重跑**。

```bash
python3 -m venv .venv-ov
source .venv-ov/bin/activate
python -m pip install openvino==2026.2.1 \
  openvino-genai==2026.2.1.0 openvino-tokenizers==2026.2.1.0
```

```python
import openvino as ov
import openvino_genai as genai

print('devices:', ov.Core().available_devices)
pipe = genai.VLMPipeline('/srv/models/Qwen3.5-9B-int4-ov', 'GPU')
pipe.generate('Hello', max_new_tokens=8, do_sample=False)  # 预热
result = pipe.generate(
    '请用中文简要说明人工智能推理加速的作用。',
    max_new_tokens=128, do_sample=False,
)
print(result)
m = result.perf_metrics
print('input tokens:', m.get_num_input_tokens())
print('generated tokens:', m.get_num_generated_tokens())
print('TTFT ms:', m.get_ttft().mean)
print('TPOT ms:', m.get_tpot().mean)
print('throughput token/s:', m.get_throughput().mean)
```

**检查：** 完成设备编译和生成，保存实际 token 数与输出；性能口径用 `PerfMetrics` 说明。设备枚举到 NPU 只证明可发现，不证明该模型能在 NPU 上执行。

旧 Intel 笔记还使用过 IPEX-LLM/Ollama 路线，它是历史流程参考，不能代替当前设备上的 OpenVINO/SYCL/Vulkan 实测。

## 5. Mac：先区分 llama.cpp、MLX 和插件

| 路线 | 输入制品 | 本次读到的记录 |
| --- | --- | --- |
| llama.cpp Metal | 匹配架构的 GGUF | M3 Ultra 编译、设备与特定模型失败记录 |
| MLX / oMLX | 对应 MLX 制品 | 本地服务与并发测试 |
| vllm-metal | 插件支持的模型和布局 | 特定版本文本可用、视觉 encoder 未接通 |

Mac 编译的基本顺序：准备 Xcode 工具链与 CMake，固定源码，新建构建目录，配置，构建，再运行检查。

```bash
xcode-select -p
clang --version
cmake -S . -B build-metal \
  -DGGML_METAL=ON -DGGML_ACCELERATE=ON -DCMAKE_BUILD_TYPE=Release
cmake --build build-metal --target llama-server llama-bench -j 4
./build-metal/bin/llama-server --help
```

**检查：** 运行日志出现 Metal 设备和实际卸载层数，再完成真实生成。`cmake -S ... -B ...` 只生成构建配置，还没有生成可执行文件。

### 5.1 编译成功而模型失败的实际记录

Mac Studio M3 Ultra、512GB、macOS 26.3 的笔记使用过 `nisparks/llama.cpp` 的 `wip/deepseek-v4-support`，commit `9d36408`。该记录后续明确写出：特定 FP4/FP8 GGUF 在 Metal 执行时出现 `Asserting on type 42`、相关 MoE kernel 未实现。

因此应记录为“引擎编译可用，但该版本与该模型制品组合失败”。笔记开头的早期成功描述不能覆盖后面的失败证据，也不能扩大成“Mac 不支持所有 FP8”。

### 5.2 文本成功，不代表多模态成功

2026-05-18 的 vllm-metal 记录包含：`vllm-metal 0.2.0`、`vllm 0.21.0+cpu`、`mlx 0.31.2`、Python 3.12.13。Qwen3.6 文本请求可用，图片请求报：

```text
NotImplementedError: Multimodal encoder execution is not wired on Metal yet.
```

这属于该版本能力缺口。应将文本、图片、工具调用分别验收，不能只因模型名含视觉能力就认为服务后端已接通视觉链路。

## 6. NPU、手机和嵌入式怎样继续

AMD NPU 笔记记录了 Ryzen AI OGA 的特定代际条件；Intel 笔记又显示同一 NPU 在某些语音模型可用、该 9B 模型失败。判断单位应是“设备 + SDK + 模型 + 精度 + 功能”，而不是一个 NPU 标签。

本轮读到的材料没有形成可公开的 Android/Jetson 完整性能记录，因此不补写成绩。迁移到这些设备仍按相同顺序：工具链 → 小模型 → 目标模型 → 应用调用 → 资源与温控回归。

## 7. 昇腾 310P3：插件、精度和压测入口一起核对

FlowUs 保存了 Qwen3-32B 的 vLLM Ascend 操作和 benchmark，使用过 `v0.10.0rc1-310p` 等历史镜像。部署前应核对芯片代际、驱动/固件、CANN、插件与 vLLM 的配套版本，以及当前模型精度的支持范围。

先用 `npu-smi info` 核对设备；再检查容器内所需设备与运行库、模型挂载、插件加载；完成小请求后再做双设备与目标上下文测试。旧容器中的高权限、全网络与整目录挂载不作为默认模板复制。

记录还存在“配置并发 10，但总请求只有 1”的测试。它只能证明那次请求完成，不能代表 10 路同时服务，也不能提供可靠 P95/P99。压测应实际提交足够请求，并核对工具报告的请求数、实际并发与输出长度。

MUSA 等其他路线按相同方法建立兼容与验收记录；本体系没有将框架图上的名字当作已公开验证的完整适配案例。

**本章交付：** 目标设备路线、版本、模型制品、功能矩阵和实际日志。接下来[配置服务与调度](07-serving-and-scheduling.md)。
