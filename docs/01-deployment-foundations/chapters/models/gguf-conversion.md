# 从原始权重到可加载的 GGUF

[总目录](../../SUMMARY.md) · [所属总章：模型格式与量化](../../02-capability-layers/02-model-formats-quantization.md) · [下一篇：量化选择与验证](quantization.md)

## 本章概览

拿到模型以后，先确认运行框架能够读取什么制品。llama.cpp通常读取GGUF；从Hugging Face下载的safetensors目录不能仅靠改扩展名变成GGUF。转换程序要读懂模型结构、张量名称、tokenizer和配置，才能写出执行器能够使用的文件。

本章依据作者FlowUs中的GB10构建与Qwen转换、量化记录整理。原笔记包含从FP8转F16的命令，但转换不会恢复FP8已经损失的信息。下面的教学操作改用小型原始模型，先转换为F16，再进入量化，步骤更容易检查。本轮未执行这组转换；已实际运行的成品GGUF演练见[第一个本地服务](../../practice/first-service/README.md)。

## 1. 转换之前，先看清模型目录

一份完整模型不只有权重。`config.json`描述模型结构；`tokenizer.json`和词表把文本转为token；`tokenizer_config.json`可能保存聊天模板；权重分片由索引关联。缺少这些文件，转换可能失败，也可能出现模型能加载、对话格式却错误的情况。

先回答四个问题：转换器支持这个架构吗？支持当前权重表示吗？文本与视觉组件是否分开处理？目标引擎版本是否支持转换后的GGUF类型？作者Mac笔记中的特殊GGUF类型失败，正说明“文件已下载”和“执行器能够读取”是两个检查关口。

本例只处理文本模型，不涉及视觉投影器、LoRA合并或自定义远程代码。目录统一使用当前工作目录下的`artifacts/`，避免把机器上的私人路径复制进教程。

## 2. 准备固定版本与模型

以下以Linux、Python3.12、Git、CMake和C++编译器为例。先准备至少8GiB空闲内存和约6GiB空闲磁盘；这是小模型练习的预留建议，转换峰值仍以实际监测为准。大模型要同时容纳源文件、F16中间文件、量化文件和转换工作区，不能只按最终Q4文件大小准备空间。

```bash
mkdir -p deployment-conversion
cd deployment-conversion
git clone --branch b9557 --depth 1 https://github.com/ggml-org/llama.cpp.git
git -C llama.cpp rev-parse HEAD
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -r llama.cpp/requirements/requirements-convert_hf_to_gguf.txt
python -m pip install huggingface-hub==0.36.0
python -m pip freeze > conversion-packages.txt
mkdir -p artifacts/source artifacts/gguf records
```

`b9557`对应本体系CPU演练使用的引擎系列，短提交为`0f7fada56`。安装依赖后保存的`conversion-packages.txt`是该次转换环境快照；若要长期重复相同构建，应将经过验证的依赖快照、Python版本与wheel一并归档。源码tag固定，并不自动固定所有下载依赖。

下载原始Qwen3-0.6B到固定目录。模型revision是公开仓库的具体提交，与CPU演练的成品GGUF revision分别记录：

```bash
python - <<'PY'
from huggingface_hub import snapshot_download
snapshot_download(
    repo_id="Qwen/Qwen3-0.6B",
    revision="c1899de289a04d12100db370d81485cdf75e47ca",
    local_dir="artifacts/source/Qwen3-0.6B",
)
PY
```

本章使用的模型源为[Qwen/Qwen3-0.6B](https://huggingface.co/Qwen/Qwen3-0.6B)，许可证Apache-2.0。下载器与转换依赖均保存在同一环境，不要在不同终端混用系统Python与虚拟环境。

检查下载目录中有config、tokenizer、模板和权重文件。对权重及关键配置计算摘要，保存仓库、revision与文件清单；不要只保留下载进度截图。

## 3. 转换为 F16 GGUF

```bash
python llama.cpp/convert_hf_to_gguf.py \
  artifacts/source/Qwen3-0.6B \
  --outfile artifacts/gguf/Qwen3-0.6B-F16.gguf \
  --outtype f16 > records/convert-f16.log 2>&1
```

这里的输入是完整目录，输出是一个GGUF文件。`--outtype f16`规定输出张量表示；它不能保证源模型中每个张量都以同一种精度保存，也不能纠正错误的tokenizer或模板。转换器遇到未知架构、缺少分片、无法处理的量化表示时，应先检查输入，不要跳过报错继续量化。

检查方法是同时看退出状态、日志结尾、输出文件和后续加载。日志里识别的模型结构、层数、词表与源配置应对应。只有文件存在还不足够：被中断的进程也可能留下不完整文件。

## 4. 构建加载与量化工具

本章只需要CPU工具，能够先验证文件与文本链路：

```bash
cmake -S llama.cpp -B llama.cpp/build-cpu -DCMAKE_BUILD_TYPE=Release
cmake --build llama.cpp/build-cpu \
  --target llama-cli llama-server llama-quantize -j 4
llama.cpp/build-cpu/bin/llama-cli --version
```

如果配置阶段提示缺少CURL开发库，先按发行版安装`libcurl4-openssl-dev`等对应软件包；不用网络下载功能的构建也可按固定版本支持的选项关闭CURL。作者GB10记录中的失败发生在依赖发现阶段，不能把这类错误归因于GPU计算能力。

## 5. 先加载原精度制品，再量化

```bash
llama.cpp/build-cpu/bin/llama-cli \
  -m artifacts/gguf/Qwen3-0.6B-F16.gguf \
  -ngl 0 -c 2048 -t 4 -n 64 \
  -p '计算2+2。只输出一个数字。'
```

这条命令用于检查加载与一次生成，聊天任务仍应通过正确模板测试。检查日志中的架构、张量与tokenizer警告；再保存输出。如果原精度制品已经乱码、空输出或模板异常，先修复它，避免量化后无法判断问题从哪里引入。

然后生成一个Q4候选：

```bash
llama.cpp/build-cpu/bin/llama-quantize \
  artifacts/gguf/Qwen3-0.6B-F16.gguf \
  artifacts/gguf/Qwen3-0.6B-Q4_K_M.gguf Q4_K_M
sha256sum artifacts/gguf/*.gguf > records/gguf-sha256.txt
```

保留F16源文件、量化命令、日志、输出摘要和工具提交。后续要生成Q5或Q8时，从较高精度源生成，避免把低位宽文件反复再量化后仍当作同等来源。

## 6. 转换结果怎样验收？

第一步是制品验收：输入revision与输出摘要齐全，转换和加载无错误。第二步是功能验收：同一模板下检查中文、计算、JSON与实际业务任务。第三步才是性能验收：固定输入输出、线程、后端与缓存状态，分别测引擎和HTTP。

推荐把结果放进下面的结构。输入与转换日志留在一次记录中，避免过几周只剩一个不知道来源的GGUF：

```text
records/conversion-run/
├── source-manifest.json
├── conversion-packages.txt
├── convert-f16.log
├── quantize-command.txt
├── gguf-sha256.txt
├── functional-results.json
└── conclusion.md
```

遇到不支持的架构时，可选择支持该模型的固定转换器与执行器，或者回到原格式框架运行。修改架构名称、删除未知张量或强行套用其他模型模板，都需要结构级证据和回归，不能作为通用修复。

本章完成后应得到来源明确的F16和Q4候选，而不是已经证明质量达标的模型。下一章说明怎样决定保留哪个量化方案。

## 七、大模型下载工程：先列清单，再用aria2并发

FlowUs原模型下载记录包含SDK下载与多目录模型管理，实际部署中还需要处理中断、分片和磁盘余量。并发下载只改变传输效率，不替代制品完整性。模型下载完成的标准应是“固定revision的全部必要文件核对完成”，而不是“进度条到100%”。

### 7.1 什么时候用SDK，什么时候用aria2

SDK适合下载完整仓库、处理revision和文件过滤；aria2适合已经取得确定公开文件URL、需要断点续传与多连接的任务。带权限模型使用平台官方认证流程，凭据不写进命令清单或提交文件。

不要为提高速度把模型仓库URL直接交给aria2，仓库页面不是权重文件。也不要只下载safetensors而漏掉config、tokenizer和processor，之后再把转换错误归给引擎。

### 7.2 为公开源生成固定下载清单

下面沿用本章固定的Qwen3-0.6B revision，列出仓库文件并生成aria2清单。示例下载文件URL不含认证信息，使用前按模型卡确认许可。

```python
from pathlib import Path
from huggingface_hub import HfApi, hf_hub_url

repo = 'Qwen/Qwen3-0.6B'
revision = 'c1899de289a04d12100db370d81485cdf75e47ca'
target = Path('artifacts/source/Qwen3-0.6B').resolve()
lines = []
for name in sorted(HfApi().list_repo_files(repo_id=repo, revision=revision)):
    relative = Path(name)
    if relative.is_absolute() or '..' in relative.parts:
        raise ValueError('Unexpected file path')
    if name.startswith('.git/') or name.startswith('.cache/'):
        continue
    directory = target / relative.parent
    directory.mkdir(parents=True, exist_ok=True)
    lines.extend([
        hf_hub_url(repo_id=repo, filename=name, revision=revision),
        '  dir=' + str(directory),
        '  out=' + relative.name,
    ])
Path('records/aria2-public.txt').write_text('\n'.join(lines) + '\n', encoding='utf-8')
```

清单中每个URL后跟dir/out选项，避免所有分片重定向后被保存成同一个文件名。较大仓库可依据索引生成必要文件集合，但不要在尚不理解模型结构时随意排除辅助组件。

```bash
aria2c --input-file=records/aria2-public.txt \
  --continue=true --max-concurrent-downloads=2 \
  --max-connection-per-server=8 --split=8 \
  --min-split-size=16M --max-tries=5 --retry-wait=5
```

`-j`/max-concurrent-downloads限制同时下载文件数，`-x`限制每服务器连接数，`-s`请求分段。实际连接受服务器Range支持、带宽、限流与单文件大小影响，不能把8×2写成必然16倍加速。

先从2文件、每文件8连接观察吞吐和429/503；并发过高导致重试时降低连接。保留`.aria2`用于断点，下载失败先确认磁盘、网络与远端状态，避免误删已经完成的大分片。

### 7.3 完成后做四次检查

先核对文件清单和分片索引，再核对字节数/可信源摘要，随后解析模型配置与tokenizer，最后用目标转换器或执行器加载。自行计算SHA256可以追踪本地制品身份，但若没有可信上游值，单算一次摘要不构成来源完整性验证。

HF大文件有时使用LFS/Xet存储，元数据字段的摘要类型可能不同。不要将任意HTTP ETag一律当成文件SHA256。若使用SDK已提供的完整性逻辑，仍将最终文件清单和必要源元数据留档。

大模型需同时预算源模型、转换中间文件、量化候选、下载临时文件和缓存。350G级模型如果还需要一份中间制品，磁盘需求会明显大于350G。下载目录与服务模型目录分开，可以避免半成品被服务自动发现。

## 八、从GGUF进入Ollama：导入后还需要验证什么

原笔记包含“转换、量化、Modelfile、create、run”的端到端过程。可以沿本章的Q4文件创建模型，先确认当前Ollama版本支持它的架构与GGUF张量类型。

在GGUF文件同目录创建Modelfile：

```text
FROM ./Qwen3-0.6B-Q4_K_M.gguf
PARAMETER num_ctx 2048
PARAMETER num_predict 256
PARAMETER temperature 0
```

```bash
ollama create book-qwen-q4 -f Modelfile
ollama show book-qwen-q4 --modelfile
ollama run book-qwen-q4
```

先检查导入后的模板、参数和制品信息，再提交与llama.cpp相同的功能题。不要把Mistral的`[INST]`模板复制到Qwen，也不要把llama.cpp CLI原始prompt的结果与Ollama chat模板结果直接视为完全同输入。

导入可能产生独立blob或存储管理开销，删除源文件前确认交付与回退要求；清理时使用对应工具管理指定模型，避免删除共用模型库。Ollama运行层数与后端同样以实际日志和状态为准。

## 九、转换失败时怎样保留最小问题

未知架构、未知张量类型、缺分片和tokenizer不匹配应分别定位。保存固定源码、依赖、模型revision、命令和最早异常。若问题只涉及配置，可以先公开脱敏配置与堆栈；不要为了提问把整份私人工作目录上传。

源模型是低精度格式而转换器暂不支持时，先选支持该制品的引擎或官方转换路线。仅将config中的model_type改为相近名称，会让加载器按另一结构解释张量，不能作为安全的通用适配方法。

转换器完成后，还要通过tokenizer/模板和真实任务验收。Mac特定fork的`hc_head_base`错误与Metal type42失败分别说明：制品命名匹配与后端算子支持是两道独立关口，文件格式相同不会消除它们。
