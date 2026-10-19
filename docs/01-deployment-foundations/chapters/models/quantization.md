---
id: T32
title: "量化选择：从放得下到用得好"
type: tutorial
volume: book
layer: 2
platform: "general"
device: "general"
status: historical
source_ids: []
updated: 2026-10-19
summary: "端侧内存有限，量化通常是第一个容量方案。它改变权重或中间状态的表示，减少存储与数据搬运，也会引入额外误差和计算处理。一个合适方案应同时满足容量、质量和服务性能，不能仅看文件从多少GB降到多少GB。"
---

# 量化选择：从放得下到用得好

[总目录](../../SUMMARY.md) · [所属总章](../../02-capability-layers/02-model-formats-quantization.md) · [上一章：GGUF转换](gguf-conversion.md)

## 本章概览

端侧内存有限，量化通常是第一个容量方案。它改变权重或中间状态的表示，减少存储与数据搬运，也会引入额外误差和计算处理。一个合适方案应同时满足容量、质量和服务性能，不能仅看文件从多少GB降到多少GB。

本章结合FlowUs中的GGUF量化、Intel IR INT4/INT8和GB10 AWQ对比记录，解释选择与验证过程。转换操作接续上一章；历史数字集中保存在[测量文件](../../evidence/measurements.json)。

**2026-10更新：** 本章后半新增当前量化工具、NVFP4/MXFP4、可执行GPTQ流程和KV精度实验。AutoAWQ库已弃用，新项目按LLM Compressor等维护中的工具准备；这不表示AWQ算法或已有AWQ权重全部失效。官方资料与固定提交见[核查清单](../../evidence/2026-10-refresh.md)。

## 1. 把格式、方法和位宽分开

GGUF、safetensors和OpenVINO IR是制品表示；AWQ、GPTQ是量化方法或相关部署路线；INT4、INT8、FP8描述数值位宽或类型；实际执行还取决于布局与kernel。这几项需要同时写清，不能只写“用了4bit”。

Q4_K_M属于llama.cpp的K-quant系列方案。名称中的K不按k-means解释，M也不表示模型参数规模。混合量化会对不同张量采用不同处理，元数据和缩放参数同样占空间，所以最终文件大小不会严格等于参数量乘4bit。

FP16与BF16本身也是有限精度浮点表示，通常在项目里作为基线精度。两者指数与尾数分配不同，不能默认在所有模型、设备和kernel上互换。FP8、MXFP4、NVFP4等还要确认具体格式和硬件支持，不能只按名字里的位数选型。

## 2. 先判断容量问题发生在哪里

若权重加载时就失败，先考虑更小模型、更低位宽权重、分片或卸载。若短请求正常、长上下文或并发才OOM，重点检查KV、工作区与活动序列。后一种问题可能需要调整上下文、并发或KV表示，继续压缩权重未必最有效。

以27B参数为纯教学算例，4bit权重的理想数据量约为13.5GB，即约12.57GiB。这还没有加上缩放参数、部分高精度张量、KV、工作区和运行余量。MoE模型即使每token只激活部分专家，总权重仍需存储；激活参数不等于应下载或加载的参数量。

## 3. 做一组可比较的候选

沿用上一章的F16源文件，在同一llama.cpp提交下生成Q4、Q5与Q8：

```bash
for scheme in Q4_K_M Q5_K_M Q8_0; do
  llama.cpp/build-cpu/bin/llama-quantize \
    artifacts/gguf/Qwen3-0.6B-F16.gguf \
    artifacts/gguf/Qwen3-0.6B-${scheme}.gguf "$scheme" \
    > "records/quantize-${scheme}.log" 2>&1 || exit 1
done
sha256sum artifacts/gguf/*.gguf > records/gguf-sha256.txt
```

这些是待测试候选。不要在量化脚本成功退出后立即选最小文件作为交付版本。若需要importance matrix或校准数据，应使用获得授权的代表样本，记录样本来源、预处理、数量与工具版本。测试集与校准集应分开，避免把为量化调过的样本当作独立质量验证。

## 4. 质量验证要覆盖真实任务

先用十几道简单题做冒烟，能快速发现模板、截断、输出格式和严重能力退化。随后准备固定的代表任务集，例如中文问答、长文信息提取、数字计算、JSON约束与工具调用。每条记录输入、期望或人工评分规则、原始输出、结束原因和实际token。

有明确答案的任务按固定规则判断；开放任务采用事先约定的人工维度，例如事实正确、关键信息完整和表达可用。不要只让另一个模型给一个总分，却没有评分准则和原始答案。困惑度可以帮助比较语言建模变化，但不能替代结构化接口、工具调用和业务任务验收。

本体系CPU实跑的Q8模型在“2+2”题返回了“2”，三道冒烟题只有两道通过。这是提醒：高位宽文件、模型成功加载和接口200都不能代替质量检查。该结果属于具体小模型、模板与参数组合，不能据此推导所有Q8模型的质量。

## 5. 性能测量先固定边界

对每个候选先测相同线程、相同卸载和长度的引擎pp/tg；再启动服务测相同请求集、并发、流式与采样。保存权重内存、KV预算、峰值内存和错误，不要只截最后一行tok/s。

低位宽可以减少带宽压力，但也可能需要解包与反量化；不同kernel的支持和优化程度不同。小批量decode、长输入prefill和高并发服务，瓶颈并不完全相同。把其中一个场景的速度推广为“量化后一定更快”，容易误选。

### Intel IR INT4/INT8 的历史观察

同一Core Ultra7 256V、16GB、OpenVINO2026.2.1记录中，INT4制品约6.13GB，INT8约9.46GB。相同19输入、128输出的管线测量分别为21.1599与10.1047token/s，INT4约为2.09倍；TTFT分别184.02与169.73ms。

INT4生成速率更高，INT8这次首token稍早，两者并不矛盾。TTFT和连续生成衡量不同阶段。两个输出均在思考阶段达到上限，完整任务质量还未通过，因此这些数字支持性能候选选择，不能单独支持最终上线。

### AWQ 4bit/8bit 的历史观察

作者GB10的同系列26B-A4B模型对比中，c2、200请求下4bit/8bit输出吞吐分别60.08与47.81token/s，平均TTFT为272.97与338.92ms。原记录缺模型revision、校准身份与质量结果，因此保留为整套部署组合观察。

这组结果不能回答“所有模型4bit都更快”，也不能将差异只归因于位宽。kernel、布局、模型制品与环境同样需要核对。

## 6. 权重量化与 KV 量化分开实验

权重量化解决模型常驻存储的一部分问题；KV量化降低历史状态占用，更容易影响长上下文和活动序列容量。下载FP8或INT4权重，并不代表KV自动采用相同表示。

实验时先保持权重不动，单独调整K/V表示，检查框架对量化类型、Flash Attention和后端的组合要求。质量集应增加长上下文检索、跨段引用和多轮任务；短问答通过不足以说明长上下文状态没有明显误差。

## 7. 最终如何选型？

用同一张结果表记录候选，不设一个脱离需求的“最佳量化”：

| 候选 | 峰值内存 | 质量通过率 | 目标负载吞吐 | TTFT/尾延迟 | 结论 |
| --- | --- | --- | --- | --- | --- |
| 原精度 | 实测 | 固定题集 | 同口径实测 | 同口径实测 | 质量基线 |
| Q8/INT8等 | 实测 | 与基线比较 | 同上 | 同上 | 保留或淘汰理由 |
| Q4/INT4等 | 实测 | 与基线比较 | 同上 | 同上 | 保留或淘汰理由 |

先剔除质量或容量不达标的候选，再在服务目标内比较速度与成本。若几个方案各有取舍，就明确默认方案、低内存方案与回退条件，并保存可恢复的制品摘要与配置。

## 八、完整工程：GB10的Gemma4 AWQ四组比较

FlowUs原记录不只有26B的一对数字，还包含26B-A4B与31B各自的AWQ4/8bit。四组均在GB10、128GB、Ubuntu24.04、vLLM0.19.0+cu130环境测试。这里把部署配置、负载和结果放在一起，便于核对。

### 8.1 先辨认制品与计算结构

26B-A4B与31B属于同系列，但一个是每步激活部分参数的结构，另一个计算结构不同，不能用总参数量接近就假设算量接近。4bit/8bit还需要查`quantization_config`、group size、对称方式、零点、层排除策略与实际kernel。

目录名包含AWQ并不足以确认每个张量都使用相同表示。原记录缺模型revision和校准身份，因此公开表定位为四套制品/服务组合的历史表现，不把位宽当成唯一影响因素。

### 8.2 保存统一服务配置

原四组共用ctx16384、seqs2、batched4096、memory0.65、prefix caching、eager，文本测试禁用图像/视频。各候选分别启动并释放，不在同一设备同时常驻比较。

```bash
vllm serve /srv/models/gemma-4-26B-A4B-it-AWQ-4bit \
  --served-model-name gemma26-awq4 \
  --host 127.0.0.1 --port 8003 \
  --dtype auto --gpu-memory-utilization 0.65 \
  --max-model-len 16384 --max-num-seqs 2 \
  --max-num-batched-tokens 4096 \
  --enable-prefix-caching --enforce-eager \
  --limit-mm-per-prompt '{"image":0,"video":0}'
```

其余三组换成对应模型目录与别名，其他参数相同。量化后端由该版本读取制品配置选择，启动日志应保存实际kernel；不能在没有支持的情况下给所有模型强行加同一个量化backend名称。

原文写四组“显存占用均为81GB，GPU限制均为0.65”。它更接近引擎共同预算/内存池观察，**不能推出四组权重大小相同**。模型权重、KV池和整体设备占用应在不同字段保存；没有原始资源采样，就不为四组补造峰值权重表。

### 8.3 用同一负载测量

共同负载为200请求、并发2、随机输入目标1024、输出上限128、随机长度比例0.1、10条warmup、temperature0。命令整理如下：

```bash
vllm bench serve \
  --backend openai-chat \
  --base-url http://127.0.0.1:8003 \
  --endpoint /v1/chat/completions \
  --model gemma26-awq4 \
  --tokenizer /srv/models/gemma-4-26B-A4B-it-AWQ-4bit \
  --dataset-name random --num-prompts 200 --max-concurrency 2 \
  --random-input-len 1024 --random-output-len 128 \
  --random-range-ratio 0.1 --request-rate inf --num-warmups 10 \
  --percentile-metrics ttft,tpot,itl,e2el --metric-percentiles 50,95,99 \
  --extra-body '{"max_tokens":128,"temperature":0.0}' \
  --save-result --save-detailed --result-dir results/gemma26-awq4
```

模型别名与tokenizer是不同参数，别名用于HTTP路由，tokenizer用于构造/计数。新运行应补固定seed、输入清单与源码版本；若需要严格同输入，不仅固定目标长度，还应保存生成的请求数据。

### 8.4 四组实际结果

四组均为200成功、0失败，实际输入206139token、输出25696token。输出超过200×128的表面预算，说明工具/服务报告口径还需用逐请求usage复核；本体系按原实际总数核算吞吐，不替原记录把它改成25600。

| 指标 | 26B-A4B AWQ4 | 26B-A4B AWQ8 | 31B AWQ4 | 31B AWQ8 |
| --- | --- | --- | --- | --- |
| 总时间s | 427.70 | 537.49 | 1550.23 | 2587.60 |
| 输出吞吐token/s | 60.08 | 47.81 | 16.58 | 9.93 |
| 请求吞吐req/s | 0.47 | 0.37 | 0.13 | 0.08 |
| TTFT mean ms | 272.97 | 338.92 | 1554.39 | 2879.26 |
| TTFT P50 ms | 264.55 | 335.99 | 1537.91 | 2846.44 |
| TTFT P95 ms | 283.52 | 359.94 | 1660.53 | 3027.51 |
| TTFT P99 ms | 418.72 | 504.80 | 2448.72 | 4703.69 |
| TPOT mean ms | 31.32 | 39.39 | 109.12 | 179.92 |
| TPOT P95 ms | 31.85 | 40.11 | 111.02 | 183.70 |
| ITL mean ms | 31.07 | 39.08 | 108.24 | 178.48 |
| ITL P99 ms | 94.44 | 118.89 | 405.37 | 737.11 |
| E2E mean ms | 4264.87 | 5360.53 | 15461.46 | 25809.91 |
| E2E P95 ms | 4626.35 | 5838.26 | 16744.49 | 27932.55 |
| E2E P99 ms | 4759.75 | 5889.24 | 17295.65 | 29163.73 |

源工具另报告“peak concurrent requests4”，与配置的最大并发2冲突；该字段定义没有解释，所以不用于声称四路同时执行。其余数值保留为历史报告，后续应通过原始请求时间重建统计。

### 8.5 如何得出有用的工程结论

同26B系列，AWQ4输出吞吐约为AWQ8的1.257倍；同31B系列约为1.670倍。二者都是这套环境与制品的观察。26B与31B之间还跨越结构和计算量，不能把差异解释成单纯“多5B参数慢了多少”。

如果教学需求设为TTFT P95低于500ms、平均TPOT低于50ms，那么两套26B配置满足这两个性能条件，两套31B不满足。这里是示范怎样套用验收门槛，不代表原项目正式SLO，更没有替四组补齐质量通过结论。

下一步在26B的两个性能候选间做固定质量集：数字、长文、结构化输出、工具调用和多轮。只有质量差异可接受且资源稳定，才能选择AWQ4；如果某类任务退化明显，就保留AWQ8或原精度路线，并清楚说明适用任务。

## 九、量化后出现问题，先按阶段定位

加载报未知量化类型，先检查框架/转换器与制品布局；kernel找不到，核对目标架构、编译产物和支持矩阵；能生成但乱码，先对照tokenizer与模板，再比较量化误差；短题正常、长上下文退化，检查KV表示、位置/窗口与长文质量。

可以在原精度、候选量化、相同输入三个条件下建立逐步对照。先不同时引入推测解码、前缀缓存或新采样，以免输出差异无法归因。遇到NaN或异常中止保留最早日志和最小输入，而不是只保存最后一段HTTP错误。

## 十、量化产物如何登记和回退

每份制品保存源模型revision、转换/量化工具commit、命令、量化配置、校准数据说明、文件摘要、许可和验收结果。名称写清系列、大小、量化类型和版本，不用含糊的final、new、best作为唯一身份。

服务配置引用一个明确版本目录，更新通过验收后再切默认。发生质量退化时恢复对应模型、tokenizer、模板和引擎配置，不能只换回权重文件，却保留新模板和不兼容缓存。

## 11. 当前量化选型：先分清W、A和KV

W是权重，A是激活，KV是生成历史状态。W4A16表示4bit权重和16bit激活，不代表所有运算、累加与KV都是4bit。W8A8也要区分INT8、FP8、每tensor/每channel/每token scale及实际kernel。

| 路线 | 主要压缩对象 | 优先使用场景 | 需要核对 |
| --- | --- | --- | --- |
| GGUF K/I-quant等 | 按张量类型保存量化权重 | llama.cpp、多后端、CPU/GPU混合 | 目标架构、量化类型、后端kernel |
| GPTQ/AWQ W4A16 | 分组整数权重 | 低batch带宽与模型容量 | group size、zero point、排列与Marlin等kernel |
| FP8 W8A8 | 浮点权重与激活 | 具有相应执行路径的现代GPU | E4M3/E5M2、scale粒度、dynamic/static |
| MXFP4 | FP4值及microscaling元数据 | 支持该制品和kernel的设备 | 块结构、scale、布局、激活路径 |
| NVFP4 | NVIDIA FP4方案及分级scale | 支持原生路径的Blackwell设备 | 精确架构、ModelOpt/其他导出格式、kernel |
| FP8等KV量化 | K/V状态 | 长上下文和并发容量受限 | attention后端、scale、长文质量 |

MXFP4与NVFP4的缩放组织和序列化并不相同，不能改一个文件名或dtype字段就互转。量化值之外还有scale、对齐与保留高精度层，4bit制品不应按严格4倍缩小验收。

### 11.1 不再从AutoAWQ旧环境开始新工程

vLLM官方已提示AutoAWQ库弃用，并指向LLM Compressor中的AWQ流程。保留旧AWQ环境可以复现历史制品，新工程则使用维护中的工具，并固定工具commit、PyTorch与导出格式。

GPTQ/AWQ是优化方法，NVFP4/FP8是数值方案，compressed-tensors/ModelOpt是制品约定；这些概念可以组合。不要按“用了GPTQ，所以肯定是INT4”推断最终文件。

### 11.2 原生低精度与fallback区别

当前vLLM的ModelOpt路径通过`hf_quant_config.json`识别量化方案。NVFP4制品可以选择不同linear backend；某些设备没有受支持的原生FP4 GEMM时，会在可支持的组合下使用Marlin等W4A16执行并记录警告。

这类fallback可以解决可运行性，但计算密集prefill的收益不等同原生FP4。也不能由“能读取NVFP4文件”推断任意旧GPU均可部署。查看实际kernel、非量化层、预处理与显存，再测prefill和decode。

当前配置使用`--linear-backend`，旧`VLLM_NVFP4_GEMM_BACKEND`已弃用。起步用auto并保存日志，只有明确需要验证某后端时才固定它。SM100、SM120/121等平台的具体覆盖应分别查，不能只写Blackwell全支持。

## 12. 完整W4A16流程：本地校准、GPTQ、导出和加载

以下为根据LLM Compressor官方API整理的参考实验，未在本仓库GPU执行。选择较小的`Qwen3-0.6B`降低首次验证成本，不将小模型的质量结论推广到其他模型。

### 12.1 固定工具与输入

量化最好使用单独环境，避免与已有推理服务互相修改依赖。先按目标硬件配置配套PyTorch，再安装固定LLM Compressor源码：

```bash
git clone https://github.com/vllm-project/llm-compressor.git
git -C llm-compressor checkout f15ac1d2243c3fd60cd745cf4e735e2814142d76
python -m pip install ./llm-compressor datasets huggingface_hub
mkdir -p records/quant artifacts
python -m pip freeze > records/quant/packages.txt
```

源模型先按[DSpark下载步骤](../performance/dspark.md)相同的revision方法准备到`/srv/models/Qwen3-0.6B`。准备本地UTF-8 `calibration.jsonl`，每行一个对象：

```json
{"messages":[{"role":"user","content":"说明模型权重和KV缓存的区别。"},{"role":"assistant","content":"权重是模型固定参数，KV缓存保存当前输入及生成历史对应的注意力状态。"}]}
```

正式校准从有公开/使用权限的代表样本中选取，建议从512条、最大2048token起步；记录来源、数量、截断、语言和任务分布。上面一行仅说明schema，不能复制512次冒充代表数据。校准集不混入独立验收题。

### 12.2 保存并运行quantize_w4a16.py

```python
import hashlib
import json
from pathlib import Path
from datasets import load_dataset
from transformers import AutoModelForCausalLM, AutoTokenizer
from llmcompressor import oneshot
from llmcompressor.modifiers.gptq import GPTQModifier

source = "/srv/models/Qwen3-0.6B"
calibration = Path("calibration.jsonl")
output = Path("artifacts/Qwen3-0.6B-W4A16")
if output.exists():
    raise FileExistsError("Choose a new artifact directory")
tokenizer = AutoTokenizer.from_pretrained(source, local_files_only=True)
model = AutoModelForCausalLM.from_pretrained(
    source, local_files_only=True, torch_dtype="auto")
dataset = load_dataset("json", data_files=str(calibration), split="train")
if len(dataset) < 512:
    raise ValueError("Provide at least 512 representative calibration samples")
dataset = dataset.shuffle(seed=42).select(range(512))

def encode(row):
    text = tokenizer.apply_chat_template(
        row["messages"], tokenize=False, add_generation_prompt=False,
        enable_thinking=False)
    return tokenizer(text, max_length=2048, truncation=True,
                     padding=False, add_special_tokens=False)

dataset = dataset.map(encode, remove_columns=dataset.column_names)
recipe = GPTQModifier(targets="Linear", scheme="W4A16", ignore=["lm_head"])
oneshot(model=model, dataset=dataset, recipe=recipe,
        max_seq_length=2048, num_calibration_samples=512)
model.save_pretrained(output, save_compressed=True)
tokenizer.save_pretrained(output)
Path("records/quant/calibration.json").write_text(json.dumps({
    "file_sha256": hashlib.sha256(calibration.read_bytes()).hexdigest(),
    "samples": 512, "max_seq_length": 2048, "seed": 42,
    "source": source, "artifact": str(output), "scheme": "W4A16",
    "ignored": ["lm_head"], "enable_thinking": False,
}, indent=2), encoding="utf-8")
```

```bash
python quantize_w4a16.py > records/quant/quantize.log 2>&1
find artifacts/Qwen3-0.6B-W4A16 -type f -exec sha256sum {} \; \
  > records/quant/artifact-sha256.txt
```

`ignore=lm_head`只指定保留该输出层，最终还需检查导出的quantization_config，确认实际targets、group size和非量化张量。主机/设备内存必须容纳量化过程中的原权重、校准激活和算法工作区；最终4bit模型能放下不代表量化过程同样能放下。

### 12.3 在独立推理环境加载

```bash
vllm serve artifacts/Qwen3-0.6B-W4A16 \
  --served-model-name qwen-quant-lab \
  --host 127.0.0.1 --port 8000 \
  --max-model-len 4096 --max-num-seqs 4 \
  --gpu-memory-utilization 0.80
```

检查日志识别到compressed-tensors及实际kernel。不要强行加`--quantization awq`，因为本例导出的是GPTQ计算得到的compressed-tensors制品。

依次运行短题、固定质量集、512输入/256输出和长输入负载。原精度基线使用相同模型源、模板、thinking、采样与请求集；量化引起的kernel变化属于方案的一部分，但不能再同时改变并发、上下文和图模式。

## 13. FP8与FP4实验怎么展开

FP8_DYNAMIC的常见配置为权重按channel、激活按token动态量化；这种特定流程可以不使用激活校准数据，不表示全部FP8方法都无需校准。静态scale与KV scale仍可能需要代表数据。

NVFP4/MXFP4先选择官方配套预量化模型，确认目标GPU上能生成。需要自行量化时，使用当前LLM Compressor/ModelOpt对应模型的完整示例，保存变换、校准、保留层和导出配置；不要用一段通用`FP8_DEFAULT_CFG`代码宣称完成了任意FP4模型适配。

对同一个模型建立W/A候选表：BF16、W4A16、FP8、目标设备支持的FP4。每个候选都需要独立的文件摘要、加载日志、峰值内存、prefill/decode/HTTP结果和质量评分。某候选不受支持时保留“未运行/不支持”原因，不给它填零性能。

## 14. KV精度单独做四组实验

| 组别 | 权重 | KV | 比较目的 |
| --- | --- | --- | --- |
| A | 原精度 | 原精度 | 质量与资源基线 |
| B | 量化权重 | 原精度 | 权重方案差异 |
| C | 原精度 | FP8等候选 | KV方案差异 |
| D | 量化权重 | 同C的KV | 组合收益与质量 |

vLLM的`--kv-cache-dtype fp8`不等于完成scale校准。当前文档无校准路线使用默认scale1.0，推荐用LLM Compressor代表数据校准；某些per-head路径还限定attention后端。

FA3配合FP8 KV的路径中，attention还可能量化Q，所以“只改变存储、计算完全不变”并不准确。新版本提供`--kv-cache-dtype-skip-layers`，可以保留敏感层或sliding-window层的原精度，但必须先确认本版本支持。

长文验收至少覆盖：短上下文固定题、目标长度的信息检索、多跳关系、数字/代码以及接近最大长度的稳定性。记录实际KV字节、可用token块、最长成功输入和质量变化。总显存不会因为KV减半就减半。

## 15. 最终选型表怎么写

报告逐行填写：目标模型revision、工具commit、W/A/KV、scale粒度、格式、kernel、设备、长度/并发、实际输出、质量与性能。先列硬性门槛，再在通过候选里比较延迟、吞吐、内存与维护成本。

例如要求某任务集得分下降不超过事先约定范围、TTFT P95与TPOT P95低于目标、无持续OOM/错误，再选择资源占用较小或有效吞吐较高的候选。门槛由项目制定，不能把教学样例自动当成生产标准。

**当前资料：** [AutoAWQ弃用说明](https://docs.vllm.ai/en/latest/features/quantization/auto_awq/) · [LLM Compressor方案选型](https://docs.vllm.ai/projects/llm-compressor/en/latest/steps/choosing-scheme/) · [W4A16源码示例](https://github.com/vllm-project/llm-compressor/blob/f15ac1d2243c3fd60cd745cf4e735e2814142d76/examples/quantization_w4a16/llama3_example.py) · [ModelOpt加载与kernel](https://github.com/vllm-project/vllm/blob/2365177ddda7714502e4df7a1669cc79c0a4dfd0/docs/features/quantization/modelopt.md) · [KV量化](https://github.com/vllm-project/vllm/blob/2365177ddda7714502e4df7a1669cc79c0a4dfd0/docs/features/quantization/quantized_kvcache.md)。
