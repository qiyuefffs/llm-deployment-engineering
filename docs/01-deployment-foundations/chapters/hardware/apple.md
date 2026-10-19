---
id: T26
title: "1.2.4 Mac硬件、Metal与MLX"
type: tutorial
volume: book
layer: 1
platform: "Apple"
device: "general"
status: historical
source_ids: []
updated: 2026-10-19
summary: "这里主要讨论Apple Silicon Mac。M系列SoC将CPU、GPU、Neural Engine等集成在同一平台，CPU与GPU共享物理内存。Intel Mac的软件与硬件条件不同，不能直接套用MLX/Apple Silicon部署"
---

# 1.2.4 Mac硬件、Metal与MLX

[总目录](../../SUMMARY.md) · [硬件与运行时总览](../../02-capability-layers/01-hardware-backends.md)

## 硬件基础

这里主要讨论Apple Silicon Mac。M系列SoC将CPU、GPU、Neural Engine等集成在同一平台，CPU与GPU共享物理内存。Intel Mac的软件与硬件条件不同，不能直接套用MLX/Apple Silicon部署路线。

| 硬件组成 | 在大模型部署中的作用 | 需要知道的限制 |
| --- | --- | --- |
| CPU | 分词、预处理、应用控制，以及CPU算子 | 也会与GPU争用内存带宽和系统资源 |
| GPU | 执行Metal/MLX等路线支持的矩阵与模型计算 | 算子、精度和模型实现由软件栈决定 |
| 统一内存 | 供CPU/GPU直接访问的共享物理内存 | 系统、应用、权重、KV和工作区共同占用 |
| Neural Engine | 专用神经网络加速单元 | MLX/Metal GPU推理不会自动使用它，需要相应执行路线与支持 |

选型除了看统一内存容量，还要看内存带宽、GPU能力与散热。能放下更大的模型，不意味着其decode速度与独立显卡相同；不同M系列芯片也不能只按内存容量比较。

## Metal、MLX、MLX-LM分别是什么

**Metal是GPU计算接口；MLX是数组与机器学习框架；MLX-LM是基于MLX实现文本模型加载、生成和量化等功能的软件包。**

```text
文本应用 → MLX-LM → MLX数组/模型计算 → Metal（GPU执行）→ Apple GPU
本地服务 → llama.cpp → GGML Metal后端 → Metal → Apple GPU
```

| 组件 | 软件层级与职责 | 常见使用方式 |
| --- | --- | --- |
| macOS驱动与Metal | GPU设备访问、命令提交、shader和计算执行 | 系统与开发工具提供，通常不单独安装CUDA式驱动包 |
| Accelerate | Apple的CPU向量、矩阵等计算库 | CPU计算与引擎的CPU路径 |
| MPS / MPSGraph | Metal上的高层计算组件 | 部分框架使用；PyTorch的`mps`是其设备后端名称 |
| MLX | 数组、自动微分、计算图与CPU/GPU执行 | Apple Silicon机器学习代码的基础框架 |
| MLX-LM / MLX-VLM | 在MLX上实现文本或视觉语言模型功能 | 模型加载、tokenizer/processor、生成和对应工具 |
| Core ML | 模型转换、优化与部署框架 | 在支持条件下使用CPU/GPU/Neural Engine等计算单元 |

MLX与PyTorch是不同框架，不能把`device='cuda'`改成一个字符串就完成迁移。llama.cpp Metal也不要求安装MLX；GGUF和MLX兼容模型是两种制品路线。

## 统一内存怎样影响部署

MLX利用共享内存，让支持的CPU/GPU运算访问同一数据池，减少显式跨设备拷贝需求。数据依赖、执行同步、内存带宽和工作区仍有成本；模型文件大小也不是峰值内存。

预算至少包括系统和桌面应用、权重、KV、预处理和临时空间。长上下文、多个并发请求和多模型常驻会继续增加需求。系统报告的memory pressure与swap比“总内存还有多少”更能说明运行是否已经受压。

MLX采用惰性求值：构造数组表达式时，计算可能尚未完成。做小算子计时时要在计时边界内触发求值，例如`mx.eval(result)`，并按当前API完成同步；只测Python提交时间会高估执行速度。

## 部署路线怎样选择

| 需求 | 候选路线 | 首先核对 |
| --- | --- | --- |
| 已有GGUF、需要本地CLI/API | llama.cpp Metal或其上层应用 | GGUF张量类型、Metal kernel、模板与实际卸载 |
| MLX生态模型与Python开发 | MLX-LM；视觉任务检查MLX-VLM | 架构实现、量化配置、processor与模型版本 |
| PyTorch应用迁移 | 支持任务的PyTorch MPS | 算子、dtype、回退和应用代码兼容性 |
| 原生应用、专用加速器部署 | 支持该模型的Core ML路线 | 转换、shape、compute units和实际执行设备 |

以上是候选关系，不是速度排名。先验证任务、制品和资源，再用同一负载比较。

基础资料：[Metal](https://developer.apple.com/metal/) · [MLX](https://ml-explore.github.io/mlx/build/html/index.html) · [统一内存](https://ml-explore.github.io/mlx/build/html/usage/unified_memory.html) · [MLX-LM](https://github.com/ml-explore/mlx-lm)。

## 部署操作与工程参考

后续分别讲GGUF＋Metal构建、MLX服务和模型能力验证。实例：[M3 Ultra Metal构建与GGUF排错](../../cases/C10-m3-metal/README.md) · [MLX、APC与oMLX完整部署优化](../../cases/C11-m3-mlx/README.md)。

## 一、先区分模型路线

llama.cpp使用GGUF与Metal kernel。MLX-LM使用对应文本模型实现，MLX-VLM还涉及视觉processor与encoder。oMLX等服务层在引擎上提供模型发现、调度与接口；vllm-metal属于另一套插件组合。

这些路线不能只靠相同模型名称互换文件。先检查模型制品和当前版本支持，再连接应用。

## 二、检查系统与开发工具

```bash
sw_vers
uname -m
xcode-select -p
clang --version
cmake --version
```

源码构建需要Xcode命令行工具与相应CMake。准备好后，固定llama.cpp提交，以独立目录构建Metal与Accelerate：

```bash
cmake -S . -B build-metal   -DGGML_METAL=ON -DGGML_ACCELERATE=ON   -DCMAKE_BUILD_TYPE=Release
cmake --build build-metal --target llama-cli llama-server llama-bench -j 4
./build-metal/bin/llama-server --version
```

小模型准备与服务请求复用[llama.cpp教程](../frameworks/llama-cpp.md)。检查Metal设备与实际层分配，再看生成内容和结束原因。

## 三、统一内存需要怎样观察

模型、KV、运行时、应用和系统共享容量。先测加载与短输入，再增加长度与并发；同步看系统内存压力、swap与持续速度。短时间能够生成，不保证长时间运行没有换页或温度影响。

不以取消系统保护或无上限分配作为默认步骤。应先建立预算，在可接受资源内比较模型与配置。

## 四、实例：引擎编译通过，特定模型仍失败

作者M3 Ultra512GB、macOS26.3记录使用特殊llama.cpp分支commit9d36408。后续执行特定FP4/FP8 GGUF时出现`Asserting on type 42`，涉及尚未实现的Metal MoE路径。

这项结论限定到该分支、制品和功能。排查先看张量类型与kernel，不把编译通过当成模型通过，也不扩大为所有Metal低精度模型失败。

## 五、实例：文本成功，视觉尚未接通

另一份记录使用Python3.12.13、vllm-metal0.2.0、vLLM0.21.0+cpu、MLX0.31.2。文本请求可用，图片请求报多模态encoder尚未接通。

因此文本、图片、工具调用和结构化输出应分别记录。增加内存和上下文不能补齐缺失的encoder，应该选择支持所需任务的实现或版本。

## 六、oMLX模型发现与服务检查

原操作记录中的`--model-dir`指向模型父目录，服务从中发现模型。启动后先看模型列表，确认应用使用的别名，再检查普通与流式请求。路径正确后才进入并发。

oMLX的历史并发结果放在[压测专题](../performance/benchmarking.md)，此处只确认模型发现与功能链路。缓存状态、环境和样本量限制会在结果旁说明。

## 七、完整操作：Metal构建应该怎样验收

原构建设备为M3 Ultra，8E＋24P CPU、80核GPU、512GB统一内存，macOS26.3；工具链为Xcode26.3、Apple clang17.0.0、CMake4.3.2、Ninja1.13.2。这里的系统要求来自特定分支，不应推导为所有llama.cpp版本都必须使用macOS26。

### 7.1 配置、编译、链接、执行分成四次检查

`cmake -S ... -B ...`只生成构建配置，看到`Generating done`还没有产出程序。首次使用时，应在一套固定源码下完成配置与build，再检查动态库与设备初始化。

```bash
cmake -S . -B build-metal -G Ninja \
  -DCMAKE_BUILD_TYPE=Release \
  -DGGML_METAL=ON -DGGML_ACCELERATE=ON \
  -DGGML_METAL_EMBED_LIBRARY=ON
cmake --build build-metal --target llama-cli llama-server llama-bench llama-gguf-split -j 4
rg '^GGML_METAL|^GGML_ACCELERATE|^CMAKE_BUILD_TYPE' build-metal/CMakeCache.txt
otool -L build-metal/bin/llama-server
./build-metal/bin/llama-cli --list-devices
```

嵌入Metal library可以减少部署时漏带shader资源的机会，但共享动态库仍要配套。`otool -L`用于检查程序依赖，不保证所有后端都静态链接或列在主程序上；采用动态加载的版本还要看运行日志。

运行时重点核对Apple设备名称、Metal后端、统一内存标志与working set提示。`--version`是否触发设备初始化随版本变化，必要时用`--list-devices`或一次短模型加载验证。不要因为某版本的version输出没有Metal行，就断言编译选项一定为OFF。

### 7.2 为什么分支和GGUF必须成套

原工程为支持特殊模型，采用`nisparks/llama.cpp`的`wip/deepseek-v4-support`分支、commit`9d36408`。该组合遇到两类不同错误：

| 错误 | 所处阶段 | 排查重点 |
| --- | --- | --- |
| `missing tensor 'hc_head_base'` | 权重/张量命名匹配 | GGUF转换来源、模型实现、fork约定 |
| `Asserting on type 42`与`mul_mm_id_map0` | warm-up进入Metal算子 | 当前类型的MoE kernel是否实现 |

第一类错误不适合靠增加内存处理；第二类也不是把ctx从64K降到4K就能补齐kernel。应先列出模型架构、GGUF来源、量化类型、fork与commit，再寻找已支持的匹配组合。

原FP4/FP8制品含365个`f8_e4m3_b128`专家张量，约145GiB。该分支Metal MoE路径失败，可以得出“这套制品在这个commit没有通过”；不能扩展成“Mac所有FP8都不可用”。同样，64/64层卸载日志只说明权重分配，随后的空跑仍可能失败。

### 7.3 模型加载与系统观察

在支持的GGUF上先做小上下文、短输出。记录实际offload层数、Metal model buffer、KV和compute buffer，再同步观察`memory_pressure`、`vm_stat`以及Activity Monitor。512GB也需要预算，不能把全部内存交给权重。

切分支时使用新的构建目录，避免旧CMakeCache和shader产物混入。切换回已验证版本时，程序与共享库一起恢复。需要模型转换时另建Python环境，C++构建成功不代表transformers转换依赖已经满足。

## 八、完整操作：vllm-metal文本服务与模板排错

这份2026-05-18记录包含一条很有价值的完整链路：本地安装成功，原生扩展可导入，模型文本可生成，随后遇到模板和视觉支持问题。把每个阶段分开，就能避免反复重装。

### 8.1 固定环境与原生扩展

| 组件 | 记录版本 |
| --- | --- |
| Python | 3.12.13 |
| vllm-metal | 0.2.0 |
| vLLM | 0.21.0+cpu |
| mlx / mlx-metal | 0.31.2 / 0.31.2 |
| mlx-lm / mlx-vlm | 0.31.3 / 0.4.4 |
| torch / transformers | 2.11.0 / 5.8.1 |
| nanobind | 2.10.2 |

原安装运行项目的`./install.sh`，创建`.venv-vllm-metal`，准备vLLM源码并构建Rust扩展`_rs.cpython-312-darwin.so`。复建先固定项目commit、检查安装脚本与依赖，不把一张pip版本表当成全部构建锁。

检查扩展时先离开源码根目录：

```bash
cd /private/tmp
# 在此之前激活已安装vllm-metal的虚拟环境
python - <<'PY'
import vllm
import vllm_metal
import vllm_metal._rs
print(vllm.__version__)
print(vllm_metal.__file__)
print(vllm_metal._rs.__file__)
PY
```

源码目录中的`vllm_metal/`可能遮蔽site-packages，造成`ModuleNotFoundError: No module named 'vllm_metal._rs'`。先看`__file__`，再决定是否重编；没有必要在每次导入失败时都删除环境。

安装下载曾出现curl16 HTTP/2和curl56连接中断。可对公开下载改用HTTP/1.1、重试和断点续传，但完成后仍要核对制品。依赖解析失败应检查可信索引、包版本和Python支持，不直接放宽所有索引的选择规则。

### 8.2 恢复原文本服务参数

模型目录统一写作`/srv/models/Qwen3.6-35B-A3B-bf16`，端口18092。以下环境变量和选项属于上述固定版本，升级后应重新核对：

```bash
export VLLM_METAL_USE_MLX=1
export VLLM_MLX_DEVICE=gpu
export VLLM_METAL_USE_PAGED_ATTENTION=1
export VLLM_METAL_MEMORY_FRACTION=0.90
export VLLM_METAL_GDN_LAZY_DECODE=1
export VLLM_METAL_MULTIMODAL_MODE=auto
export VLLM_METAL_PREFIX_CACHE=1
export VLLM_METAL_PREFIX_CACHE_FRACTION=0.05
export VLLM_WORKER_MULTIPROC_METHOD=spawn
export TOKENIZERS_PARALLELISM=false

vllm serve /srv/models/Qwen3.6-35B-A3B-bf16 \
  --host 127.0.0.1 --port 18092 \
  --served-model-name qwen36-bf16 \
  --dtype bfloat16 --kv-cache-dtype bfloat16 \
  --max-model-len 8192 --max-num-seqs 16 \
  --max-num-batched-tokens 32768 --block-size 16 \
  --enable-prefix-caching \
  --chat-template /srv/models/Qwen3.6-35B-A3B-bf16/chat_template.jinja \
  --default-chat-template-kwargs '{"enable_thinking":false}' \
  --generation-config vllm \
  --override-generation-config '{"do_sample":false,"temperature":0,"top_p":1}' \
  --scheduler-reserve-full-isl
```

原模型的远程代码选项应在固定来源且审阅后按需启用，本体系不将它作为所有服务的默认。0.90内存比例和16条序列是历史服务参数，不是512GB上能承诺的16并发SLO；新环境先以更小预算冒烟。

### 8.3 从“只输出思考”定位到模板

故障响应出现`Here's a thinking process`，128个输出token后`finish_reason=length`。原检查发现`tokenizer_config.json`中的chat_template为None，实际模板保存在独立的`chat_template.jinja`；默认生成前缀会引入`<think>`。

处理要同时核对三层：服务加载了哪个模板、模板是否支持`enable_thinking`、最终请求使用什么参数。仅在system里写“不要思考”，不能替代模型约定的模板控制。

```bash
curl --fail-with-body http://127.0.0.1:18092/v1/chat/completions \
  -H 'Content-Type: application/json' \
  -d '{"model":"qwen36-bf16","messages":[{"role":"user","content":"用三句话介绍统一内存。"}],"temperature":0,"max_tokens":128,"chat_template_kwargs":{"enable_thinking":false},"stream":false}' \
  -o text-response.json
```

原模型generation_config另有`do_sample=true、temperature=1.0、top_p=0.95`。服务默认配置和请求覆盖共同决定最终采样，不能只改一处就假定所有请求一致。修复后保存模板摘要、命令与响应，验收正文是否完整，而不是只检查思考文本消失。

### 8.4 图片请求为什么需要换路线

同一服务收到图片时，前端已经产生`mm_features、pixel_values、image_grid_thw`，但runner抛出：

```text
NotImplementedError: Multimodal encoder execution is not wired on Metal yet.
```

这说明请求解析和视觉执行位于不同环节。错误随后引发`EngineDeadError`，需要重启该实例，文本成功也不能覆盖这次图片失败。增加显存、延长HTTP超时或继续提交相同图片，不能补上没有连接的encoder。

适合的处理是保留文本服务记录，视觉改走该模型已支持的mlx-vlm实现，重新进行功能与性能验收。升级插件后也要重测同一张公开图，不能把旧失败自动改写成新版本成功。

## 九、MLX-VLM：从单图命令行到API

原空间中的多视觉模型指南覆盖MiniCPM-V-4.6、Qwen3.6-35B-A3B与Gemma4。先检查`mlx_vlm.__file__`和源码commit，确认实际导入了目标环境，再检查Metal设备：

```bash
python - <<'PY'
import mlx.core as mx
import mlx_vlm
print(mlx_vlm.__file__)
print(mx.default_device())
print(mx.device_info())
PY
```

最短链路先用命令行，不先叠加HTTP与并发：

```bash
python -m mlx_vlm.generate \
  --model /srv/models/Qwen3.6-35B-A3B-bf16 \
  --image ./inputs/vision-card.png \
  --prompt '逐行读出图片中的文字，再描述图形，不补充图片外的信息。' \
  --max-tokens 512 --temperature 0
```

公开图片的生成见[vLLM多模态实例](../frameworks/vllm-service.md#七从图片文件到流式答案的完整链路)。换用同一张图，便于区分模型、processor和服务封装差异；不能拿私人工作截图作为默认输入。

命令行通过后再启动服务。原Qwen稳定配置为max-tokens4096、max-kv-size32768、prefill-step-size2048、vision-cache-size32，端口8081：

```bash
python -m mlx_vlm.server \
  --model /srv/models/Qwen3.6-35B-A3B-bf16 \
  --host 127.0.0.1 --port 8081 \
  --max-tokens 4096 --max-kv-size 32768 \
  --prefill-step-size 2048 --vision-cache-size 32 --log-level INFO
```

先保存`python -m mlx_vlm.server --help`，确认当前版本支持这些选项。该server在启动时由`--model`加载模型，不能直接套用oMLX的`/v1/models/{id}/load`接口。请求的图片结构也要按固定server版本检查，不能把所有“OpenAI风格”端点视为字段完全一致。

原指南为MiniCPM尝试`downsample_mode=4x、max_slice_nums=36`，为Qwen尝试`max_pixels=3211264`。这些属于特定processor的参数。提高分辨率/切片数可能让小字更清楚，也会增加视觉token、prefill与内存，应使用同一图分别保存识别结果和资源，不用“大图参数已设置”替代OCR准确率。

## 十、oMLX：模型发现、加载与内存预算

oMLX与mlx-vlm独立server采用不同的模型管理流程。原`omlx serve --model-dir`指向包含多个模型子目录的父目录，服务启动后先列出可发现模型，再对目标模型加载和请求。

```bash
omlx serve --help
omlx serve --model-dir /srv/models --host 127.0.0.1 --port 8000
curl --fail-with-body http://127.0.0.1:8000/v1/models
```

模型ID以列表返回值为准。原记录随后使用对应版本的`POST /v1/models/{id}/load`，再调用chat端点。是否支持运行时load、如何提供body，应按当前版本API检查，避免把文档中一个目录名当成所有版本的模型ID。

原512GB设备加载DeepSeek-V4-Flash-4bit后，内存快照为183.5/512GB、swap inactive。空闲时GPU约3%、683MHz等只是加载后的状态，不作为推理功耗和持续频率成绩。

历史启动记录曾将max-model-memory与max-process-memory设为disabled，SSD paged cache100GB、hot cache8GB。它说明当时如何运行，不宜作为交付默认：应先给模型常驻、进程、系统与磁盘分别留预算，记录缓存位置和剩余空间，再提高上限。模型父目录中的文件大小，也不能直接加总成所有模型同时加载的RAM占用。

该模型的EvalScope成绩接到[并发测试](../performance/benchmarking.md#十omlx完整并发结果与工作点选择)，包括TTFT、TPOT、平均与P99延迟。APC的另一路MLX-VLM配置接到[缓存专题](../performance/cache-scheduling.md#八mlx-vlm-apc从配置到冷暖缓存实验)。硬件、引擎、服务管理和缓存各有角色，这样阅读不会把三个程序混成一套。

## 十一、Apple部署的验收清单

最终至少保留：工具链与commit、模型制品身份、原生扩展来源、模板与采样、实际Metal分配、文本/视觉分项结果、加载与热推理、统一内存压力、swap和持续负载。发现缺kernel就处理版本/制品匹配，发现模板错就检查token化路径，发现系统换页再处理预算。

来源：作者Mac Metal、vllm-metal、MLX-VLM及oMLX工程文章，见[文章对应表](../../evidence/chapter-sources.md)。
