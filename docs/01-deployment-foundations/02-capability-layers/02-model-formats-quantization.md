# 第2层：模型格式与量化层

## 本章概览

硬件路线确定以后，需要准备能够被引擎正确读取的模型。这里的“模型”是一组部署材料：权重、结构配置、tokenizer、聊天模板，以及任务需要的处理器和辅助权重。格式转换改变制品组织方式，量化改变部分数值表示；两者都需要重新检查加载和输出。

本章保留原框架的六节。先理解格式与量化，再学习制品选择；完整转换操作放在2.6的配套教程中。

## 2.1 这一层解决什么问题？

最常见的问题是模型太大、格式不兼容或量化后结果变化。解决时先确认目标引擎支持什么，再选择模型制品。直接寻找最小文件，可能得到当前后端无法执行的张量类型。

模型身份需要固定到仓库和revision。同名目录可能包含不同转换、量化与模板，只有模型名称无法追溯结果。下载后应保存文件清单与哈希，转换后再记录工具版本、命令和生成制品。

质量与性能分别验收。压缩后文件更小，不保证所有请求都更快；能够加载，也不保证多轮、结构化输出或视觉能力完整。应使用同一组任务检查实际输出，再决定是否采用。

## 2.2 模型格式体系

Hugging Face模型通常以一个目录分发。`config.json`说明结构；safetensors或历史bin保存张量；分片索引指出各张量所在文件；tokenizer与模板决定文本怎样变成模型输入。多模态还可能需要processor、图像编码器与投影相关材料。

GGUF把张量与必要元数据放在一套容器中，常用于llama.cpp。它可以保存高精度或多种量化张量，因此GGUF与4bit不能画等号。ONNX和OpenVINO IR则以图和权重等配套文件组织执行材料，加载路径与HF或GGUF不同。

```text
常见制品
├── HF目录：配置、权重、索引、tokenizer、模板、processor
├── GGUF：张量与元数据容器
├── ONNX：图与权重等配套材料
├── OpenVINO IR：图、权重、tokenizer与GenAI配置
├── TensorRT / TensorRT-LLM对应执行制品
└── 厂商运行时要求的图、缓存或专用包
```

### 怎样检查目录完整性

先读取模型说明和索引，再核对分片。单文件模型不一定有索引，多模态模型也不止语言权重。以下代码只检查分片是否存在，完整校验还需要来源清单或哈希。

```python
import json
from pathlib import Path
model_dir = Path('/srv/models/example-model')
config = json.loads((model_dir / 'config.json').read_text(encoding='utf-8'))
print('model_type:', config.get('model_type'))
index = model_dir / 'model.safetensors.index.json'
if index.exists():
    mapping = json.loads(index.read_text(encoding='utf-8'))['weight_map']
    missing = [name for name in set(mapping.values()) if not (model_dir/name).is_file()]
    print('missing:', missing)
    assert not missing
```

## 2.3 量化体系

讨论量化时，分清格式、数值精度、量化方法与执行布局。safetensors是存储格式，INT4是低位宽表示，AWQ/GPTQ是量化方法，具体分组、缩放与打包还要由后端kernel处理。它们处于不同层次。

FP16与BF16是常见16位浮点表示；FP8还要区分具体格式和缩放方式。INT8、INT4减少部分存储与搬运，但会引入量化误差及解包、尺度读取等成本。能否加速取决于硬件、kernel、batch与任务。

AWQ和GPTQ常用于权重量化。BitsAndBytes及在线量化是另外的工具或执行路线，使用时需要说明何时量化、哪些张量量化、是否使用校准数据及目标后端。不同制品的4bit标签不表示布局一致。

### 权重、激活与KV分别记录

权重通常常驻，激活在执行中产生，KV随上下文和活动序列增长。`W4A16`描述部分权重/激活表示，没有说明KV精度。服务采用FP8 KV时，还要检查后端支持和长上下文质量。

量化并不让所有层都变成同一位宽。尺度、元数据、敏感层与混合方案都会影响实际大小。GGUF的Q4_K_M属于K-quant混合方案，K不应解释为k-means。

更完整的量化判读与真实AWQ/IR对照见[量化制品怎样验证](../chapters/models/quantization.md)。

## 2.4 常见格式解释

| 项目 | 它是什么 | 工程上重点检查 |
| --- | --- | --- |
| FP16/BF16 | 常见浮点表示 | 设备支持、容量与基线质量 |
| FP8 | 更低位宽浮点路线 | 格式、缩放、kernel与模型支持 |
| INT8/INT4 | 低位宽整数表示 | 分组、校准、解包与任务质量 |
| AWQ/GPTQ | 权重量化方法 | 制品配置、后端布局和kernel |
| GGUF Q4/Q5/Q8 | GGUF内的量化系列 | 架构、张量类型与实际后端 |
| OpenVINO IR | 图与配套文件 | 设备编译、Pipeline和tokenizer |
| KV量化 | 缓存状态的低精度表示 | 长度、并发、资源与长上下文质量 |

选择时还要考虑模型来源。已有低精度源模型转存成FP16，只增加表示空间，不会自动恢复丢失的信息。任意FP8模型也不能保证直接转换成GGUF，转换器需要认识其结构和张量布局。

## 2.5 vLLM 与 llama.cpp 的格式选择

vLLM服务通常选择其明确支持的HF模型和量化实现。检查模型架构后，再确认目标设备上的精度与kernel。GGUF支持需按版本、模型和功能核对，不能假定与llama.cpp等价。

llama.cpp优先使用受支持的GGUF。端侧常见的Q4/Q5/Q8只是候选，实际选择要看容量、速度和质量。部分卸载时，还需要把CPU、设备内存和转移成本一起纳入预算。

Intel OpenVINO与Apple MLX各有配套制品与运行方式。为它们选择原生支持的材料，通常比拿另一条路线的目录反复尝试更容易定位问题。

| 已确定的执行路线 | 先准备什么 |
| --- | --- |
| vLLM | 固定HF/量化制品、tokenizer与模板 |
| llama.cpp | 兼容GGUF及必要辅助模型 |
| OpenVINO GenAI | 完整IR与GenAI/tokenizer配置 |
| MLX-LM/MLX-VLM | 对应实现支持的MLX制品与processor |

## 2.6 格式选择

完整选择顺序是：任务和设备→支持的引擎→可用制品→资源预算→最小加载→固定任务质量→目标负载性能。高精度基线可容纳时，先保留它；低精度候选的收益与代价才有参照。

第一次动手可以使用[CPU演练的固定GGUF](../practice/first-service/README.md)。模型、revision、文件大小与SHA256已经给出，适合先理解制品身份和校验。它的三道功能题结果也说明，小文件和高速度不能代替答案检查。

需要自行转换时，按[HF→GGUF→量化→Ollama完整教程](../chapters/models/gguf-conversion.md)执行。该教程来自作者转换与导入笔记，统一源模型、输出文件和目录，说明依赖、资源、命令、检查与常见错误。

本层最终留下模型清单、完整文件、转换记录和质量结果。下一章使用这些材料建立推理服务。
