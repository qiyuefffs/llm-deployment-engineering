# 第 2 层：模型格式与量化层

[总目录](../README.md) · [上一层：硬件后端](01-hardware-backends.md) · [下一层：推理框架](03-inference-frameworks.md)

## 2.1 这一层解决什么问题？

模型层负责准备一份目标引擎真正能使用的制品，同时在容量、速度和质量之间作选择。

```text
模型太大，怎样缩小？
当前框架能读什么文件？
需不需要转换？转换会不会丢失能力？
权重量化、激活精度、KV 量化有什么区别？
下载和转换后，怎样确认文件与质量正确？
```

部署制品不只有权重。Tokenizer、聊天模板、特殊 token、架构配置、量化配置、分片索引和多模态处理器都可能影响结果。

## 2.2 模型格式体系

```text
常见部署制品
├── Hugging Face 模型目录
│   ├── safetensors / 历史 PyTorch bin
│   ├── config、分片索引
│   └── tokenizer、聊天模板、多模态 processor
├── GGUF：张量与元数据容器
├── ONNX：计算图和权重
├── OpenVINO IR：模型图、权重与配套配置
├── TensorRT / TensorRT-LLM 对应制品
└── 厂商运行时要求的图、缓存或专用包
```

### HF 模型目录检查

典型结构如下，具体文件按架构而变：

```text
model/
├── config.json
├── model.safetensors.index.json
├── model-00001-of-0000N.safetensors
├── ...
├── tokenizer.json / tokenizer.model
├── tokenizer_config.json
├── chat_template.jinja           有些模型单独提供
├── generation_config.json
└── processor / vision 配置       多模态模型需要
```

有单文件权重的模型不一定有分片索引；索引存在时必须核对其中所有分片。不能通过“目录里有几个大文件”判断下载完整。

## 2.3 量化体系：把四个维度分开

原稿将格式、精度和量化方法放在同一列表。工程记录按下面四个维度填写：

| 维度 | 回答什么 | 示例 |
| --- | --- | --- |
| 容器 / 图格式 | 文件怎样组织 | safetensors、GGUF、OpenVINO IR |
| 数值精度 | 张量用什么数值表示 | BF16、FP16、FP8、INT8、INT4 |
| 量化方法 | 怎样确定量化与误差补偿 | AWQ、GPTQ、校准、重要性矩阵等 |
| 执行布局 / kernel | 后端怎样存储和计算这些张量 | 分组、缩放、打包、特定硬件 kernel |

文件名有 “4bit”，仍要查看配置和实际 kernel。两种 4bit 制品可能使用不同布局、额外数据和计算路径，速度与质量不能只靠位宽推断。

### 权重、激活和 KV 分开记录

- **权重量化：** 缩小常驻权重与部分读取成本。
- **激活精度：** 影响执行期间张量和计算路径。
- **KV 量化：** 缩小生成时保存的状态，主要影响上下文和并发容量。

`W4A16` 常表示权重 4bit、激活 16bit；它没有说明 KV Cache 精度，也不保证所有计算都以 4bit 执行。

## 2.4 常见格式与精度怎样选择

| 名称 | 适合考虑的场景 | 需要检查 |
| --- | --- | --- |
| FP16 / BF16 | 质量基线、受支持 GPU 常规推理 | 设备能力、容量、模型原始 dtype |
| FP8 | 有匹配硬件和 kernel 的低精度部署 | FP8 类型、缩放方式、模型与后端支持 |
| INT8 | 在压缩和质量之间建立候选 | 校准、分组、执行路径、任务质量 |
| INT4 | 容量受限或带宽敏感的候选 | 质量下降、解包成本、批量与 kernel |
| AWQ / GPTQ | 使用已有权重量化模型 | 配置、group size、后端和布局 |
| GGUF Q4/Q5/Q8 | llama.cpp 与支持的本地引擎 | 架构、张量类型、量化版本与后端 |
| OpenVINO IR | Intel 设备与相应管线 | 子图、tokenizer、GenAI 和设备插件 |
| MXFP4 / NVFP4 等 | 特定低精度执行路线 | 格式细节、缩放、硬件指令与 kernel |

低位宽通常减少部分存储和带宽开销，但也可能引入解包、反量化、额外缩放或 CPU 回退。因此要做“文件 → 实际内存 → 速度 → 质量”的完整检查。

## 2.5 vLLM 与 llama.cpp 的制品选择

| 已有条件 | 优先验证的选择 | 原因 |
| --- | --- | --- |
| 受支持 HF 模型，准备多请求 GPU 服务 | vLLM 支持的 HF / 量化制品 | 模型配置、kernel 与调度配套 |
| 已有 GGUF，目标为 CPU/GPU 混合或多后端 | llama.cpp | 直接使用匹配的 GGUF 与后端 |
| Intel OpenVINO GenAI | 配套 IR | GenAI 管线按 IR 和配套文件加载 |
| Apple MLX 路线 | 匹配 MLX 模型与配置 | 架构实现和量化布局要匹配 |

vLLM 的 GGUF 支持按版本、模型和功能检查。不能把“能读取某个 GGUF”理解成与 llama.cpp 的所有量化和功能等价。

## 2.6 格式选择流程

```text
先确定任务与目标设备
 → 选择有支持依据的引擎与后端
 → 查看模型架构和可用制品
 → 估算权重、状态、缓冲与余量
 → 选择高精度基线和低精度候选
 → 实际加载与功能检查
 → 固定任务质量回归
 → 相同负载性能测试
 → 记录可发布制品
```

不要先随意找一个最小文件，再设法让任何引擎加载它。制品选择要受设备、后端、任务和质量共同约束。

## 2.7 获取模型与完整性核对

### 固定 revision 下载

Intel [E02](../evidence/README.md)保留的 INT4 制品是：

```text
Repository: OpenVINO/Qwen3.5-9B-int4-ov
Revision:   3f31fc1609edb0cbc8b131bc4c291f1b15cb0676
Files:      24
Bytes:      6,129,582,094
```

前提：已在下载环境安装提供 `hf` 命令的 `huggingface_hub`，有足够磁盘和网络。本体系统一使用可写的 `/srv/models`；如果改用其他目录，后续加载路径一起修改。公开模型不在示例中配置凭据。

```bash
mkdir -p /srv/models
hf download OpenVINO/Qwen3.5-9B-int4-ov \
  --revision 3f31fc1609edb0cbc8b131bc4c291f1b15cb0676 \
  --local-dir /srv/models/Qwen3.5-9B-int4-ov
```

记录工具版本、revision 和文件清单。下载器的 `.cache` 等元数据不计入模型制品总量；总量相同仍不能替代逐文件校验。

### aria2 并发下载单文件

有明确公开下载地址时，可以使用 aria2。先设置该模型文件对应的 `MODEL_URL`、文件名和保存目录：

```bash
# MODEL_URL 由模型页面中固定 revision 的文件地址设置
: "${MODEL_URL:?请先设置公开模型文件地址}"
aria2c -x 8 -s 8 -k 1M -c --file-allocation=none \
  -d /srv/models -o model.gguf "$MODEL_URL"
```

`-x` 限制每服务器连接数，`-s` 指定分段数，`-c` 用于服务端支持时断点续传。连接数不是越大越好；服务端限流、磁盘和网络都可能限制速度。

下载完成后用来源清单核对文件大小和哈希，不能只看进度 100%。

```bash
sha256sum /srv/models/model.gguf
```

### 检查 HF 配置与缺失分片

下面在模型已经下载后运行。修改 `model_dir` 为实际目录：

```python
import json
from pathlib import Path

model_dir = Path('/srv/models/example-model')
cfg = json.loads((model_dir / 'config.json').read_text(encoding='utf-8'))
text_cfg = cfg.get('text_config', cfg)
for key in ('model_type', 'architectures', 'quantization_config'):
    print(key, cfg.get(key, '未提供'))
for key in ('num_hidden_layers', 'num_attention_heads',
            'num_key_value_heads', 'hidden_size'):
    print(key, text_cfg.get(key, '未提供'))
index = model_dir / 'model.safetensors.index.json'
if index.exists():
    data = json.loads(index.read_text(encoding='utf-8'))
    shards = sorted(set(data['weight_map'].values()))
    missing = [name for name in shards if not (model_dir / name).is_file()]
    print('shards:', len(shards), 'missing:', missing)
    assert not missing, '分片缺失，先完成下载'
```

分片存在检查不包含哈希验证。Tokenizer、模板和视觉配置还要另查。

## 2.8 模型转换：从 HF 到 GGUF

FlowUs [E10](../evidence/README.md)包含 GB10 上 Qwen3-30B-A3B-Instruct-2507 转换，以及 GGUF 量化后导入 Ollama 的记录。提取出的稳定流程是：

```text
完整源模型 → 固定版本转换器 → 高精度 GGUF
 → 加载与输出核对 → 量化候选 → 再加载与质量回归
```

### 步骤一：准备转换环境

固定 llama.cpp commit；源码获取方法见[框架层](03-inference-frameworks.md#35-llamacpp构建单次运行与服务)。在源码根目录，按该版本转换脚本声明的依赖建立独立环境，并单独构建量化工具。下面要求源码中存在对应 requirements 文件；若该版本调整了文件组织，按其文档修改，不能跳过依赖安装。

```bash
python3 -m venv .venv-convert
source .venv-convert/bin/activate
python -m pip install -r requirements/requirements-convert_hf_to_gguf.txt
cmake -S . -B build-quant -DCMAKE_BUILD_TYPE=Release
cmake --build build-quant --target llama-quantize -j 4
```

查看两个入口的帮助：

```bash
python3 convert_hf_to_gguf.py --help
./build-quant/bin/llama-quantize --help
```

两条命令分别检查转换器和量化器入口。若对应架构不支持，要先处理转换器兼容性，不能仅改模型名。

### 步骤二：生成高精度 GGUF

以下路径是公开示例，源模型应完整且架构受支持：

```bash
python3 convert_hf_to_gguf.py \
  /srv/models/Qwen3-30B-A3B-Instruct-2507 \
  --outtype bf16 \
  --outfile /srv/models/qwen3-30b-a3b-bf16.gguf
```

选择 BF16/FP16 依原始制品、转换器和目标后端决定。把低精度源模型转存为 FP16 不会恢复原先丢失的精度；任意 FP8 模型也不能保证直接转换。

### 步骤三：从高精度基线生成候选

```bash
./build-quant/bin/llama-quantize \
  /srv/models/qwen3-30b-a3b-bf16.gguf \
  /srv/models/qwen3-30b-a3b-q5_k_m.gguf Q5_K_M
```

转换和量化需要额外磁盘、主机内存和耗时。保留源版本、工具 commit、命令、退出码、生成文件大小与 SHA256。

### 步骤四：先加载，再接应用

先用相同提示和模板完成短请求、多轮和停止条件检查。转换后能够加载，并不代表多模态、工具调用或模板语义都被保留。

若导入 Ollama，`Modelfile` 的 `FROM` 指向真实 GGUF；模板和参数以源模型要求及当前 Ollama 支持为准。不要因导入命令成功就跳过 API 与质量验收。

## 2.9 工程参考：Intel INT4 / INT8 IR

同一设备的记录如下：

| 项目 | INT4 | INT8 |
| --- | ---: | ---: |
| 文件数 | 24 | 24 |
| 制品总字节 | 6,129,582,094 | 9,457,724,353 |
| 输入 / 生成 token | 19 / 128 | 19 / 128 |
| TTFT ms | 184.02 | 169.73 |
| TPOT ms/token | 47.26 | 98.96 |
| 生成吞吐 token/s | 21.1599 | 10.1047 |

INT4 文件更小，该次连续生成也更快；TTFT 却略高。两边都在思考阶段触及长度上限，所以尚不能宣布完整答案质量等价。

这组记录用于说明：制品更小、生成更快、首字更快、答案更好，是四个需要分别判断的问题。

## 2.10 工程参考：GB10 Gemma AWQ 档位

[E09](../evidence/README.md)记录同一 GB10、vLLM `0.19.0+cu130`、客户端并发 2、200 请求、随机输入目标 1024、输出目标 128。26B-A4B 这组模型的结果：

| 制品标签 | 成功数 | 总时间 s | 实际输出 token | 输出吞吐 token/s | TTFT P95 ms |
| --- | ---: | ---: | ---: | ---: | ---: |
| AWQ-4bit | 200 | 427.70 | 25696 | 60.08 | 283.52 |
| AWQ-8bit | 200 | 537.49 | 25696 | 47.81 | 359.94 |

标签来自原记录，实际量化细节还应读各制品配置。两边 `gpu-memory-utilization=0.65`，笔记观察总占用约 81GB；这不表示两份权重一样大，因为引擎内存还包含 KV 池和其他预留。

原汇总存在最大客户端并发与某个峰值字段不一致的问题，目标输出数与实际计数也略有差别。因此这里只使用可对照的总计和分位数；固定 revision、原始逐请求输出和业务质量仍应补齐。

## 2.11 量化后的质量回归

准备固定任务集，用高精度或已验收版本作基线。至少包含：

| 类型 | 输入 | 检查 |
| --- | --- | --- |
| 基本问答 | 公开技术问题或业务样例 | 是否完成任务、是否出现循环或乱码 |
| 结构输出 | 要求固定 JSON 字段与类型 | JSON 可解析，字段和值符合规则 |
| 多轮 | 首轮给设备条件，后续追问 | 条件是否保留、角色是否正确 |
| 长输入 | 目标长度与上界附近样例 | 是否截断、位置影响和资源失败 |
| 不确定问题 | 材料不足或超出范围 | 是否明确说明不确定 |
| 多模态 | 有使用权的固定图片 | 视觉事实、文字、数量分别评分 |

固定模板、采样、思考模式和输出预算。若 `finish_reason=length`，先确认是否因上限不足而没写完，再判断质量。

每个版本同时记录质量、速度和资源。若低精度只在短提示上通过，不能省略长上下文回归；KV 量化尤其要测目标长度的检索和推理任务。

## 2.12 本层验收与模型清单

最终清单至少包含：仓库、revision、文件、哈希、架构、容器/图格式、权重精度、量化方法与布局、KV 设置、模板、许可证、质量输入与结果。

常见失败按以下方向处理：

| 现象 | 优先检查 |
| --- | --- |
| unknown architecture | 当前引擎与转换器是否认识结构 |
| missing tensor / shape 不符 | 权重、配置、分片和转换来源是否同一版本 |
| Q4 反而慢 | kernel、CPU 回退、反量化、批量和实际卸载 |
| 角色混乱或不停止 | tokenizer、模板、特殊 token 与 generation config |
| 图片失败而文字成功 | 视觉子图、processor 和当前后端功能 |

**本层产物：** 可追溯制品、完整文件清单、转换日志和固定质量回归。下一步进入[推理框架层](03-inference-frameworks.md)。
