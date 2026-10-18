# OpenVINO：用固定 IR 完成 Intel GPU 推理

[总目录](../../SUMMARY.md) · [Intel平台](../hardware/intel.md) · [量化验证](../models/quantization.md)

## 本章概览

OpenVINO路线通常从IR制品进入，而不是把GGUF直接交给GenAI。先核对IR与Pipeline，再确认GPU或NPU能编译、能生成、能给出完整答案。这三件事要逐步检查。

本章来自作者FlowUs的Qwen3.5-9B平台测试，按原记录整理成顺序教程。历史设备为Core Ultra7 256V、Arc Lunar Lake、16GB统一内存，Ubuntu24.04.4；OpenVINO2026.2.1、GenAI与Tokenizers2026.2.1.0。本轮未在该设备重跑。

## 1. 建立独立 Python 环境

先按Intel与发行版说明安装GPU驱动与运行时，确认当前用户可以访问设备。Python包安装不能代替系统驱动。原记录使用Mesa26.1.4，oneAPI2026.1.0用于另一条SYCL路线；仅运行GenAI不代表必须安装整套oneAPI编译工具。

```bash
python3.12 -m venv .venv-openvino
source .venv-openvino/bin/activate
python -m pip install \
  openvino==2026.2.1 \
  openvino-genai==2026.2.1.0 \
  openvino-tokenizers==2026.2.1.0 \
  huggingface-hub==0.36.0
python -m pip freeze > openvino-packages.txt
```

这是按历史版本组织的安装清单。包是否提供当前Python、系统与架构的wheel，需要先确认。安装后运行：

```bash
python - <<'PY'
import openvino as ov
core = ov.Core()
print('OpenVINO:', ov.__version__)
print('devices:', core.available_devices)
for device in core.available_devices:
    print(device, core.get_property(device, 'FULL_DEVICE_NAME'))
PY
```

设备可枚举，只能说明插件发现了设备。模型图、形状、精度和状态管理是否支持，仍要在Pipeline创建和生成时检查。

## 2. 下载两份固定 IR

```bash
mkdir -p artifacts/ir
python - <<'PY'
from huggingface_hub import snapshot_download
items = [
    ('OpenVINO/Qwen3.5-9B-int4-ov',
     '3f31fc1609edb0cbc8b131bc4c291f1b15cb0676', 'artifacts/ir/qwen35-int4'),
    ('OpenVINO/Qwen3.5-9B-int8-ov',
     '3054198f70b6d50b97fa17ae80314e590c57def0', 'artifacts/ir/qwen35-int8'),
]
for repo, revision, target in items:
    snapshot_download(repo_id=repo, revision=revision, local_dir=target)
PY
```

历史清单两份各24文件，INT4总计6129582094字节，INT8总计9457724353字节。先核对配置、tokenizer、IR图和权重是否完整；下载缓存与`.cache`元数据不应算进模型制品体积。模型许可与来源参见对应模型卡，下载不意味着可以忽略再分发条件。

16GB共享内存设备不要同时加载两份模型做比较。每个候选独立进程，记录加载前可用内存、峰值RSS与swap，给系统和驱动留出空间。

## 3. 保存并运行完整推理程序

将下面保存为`run_ir.py`。它记录冷加载、预热与正式生成，并把文本和性能分开保存：

```python
import argparse
import json
from pathlib import Path
import time
import openvino_genai as genai

parser = argparse.ArgumentParser()
parser.add_argument('--model', required=True)
parser.add_argument('--device', default='GPU')
parser.add_argument('--output', required=True, type=Path)
args = parser.parse_args()
args.output.mkdir(parents=True, exist_ok=True)
t0 = time.perf_counter()
pipe = genai.VLMPipeline(args.model, args.device)
load_s = time.perf_counter() - t0
pipe.generate('Hello', max_new_tokens=8, do_sample=False)
prompt = '请用中文简要说明人工智能推理加速的作用。'
t0 = time.perf_counter()
result = pipe.generate(prompt, max_new_tokens=128, do_sample=False)
wall_s = time.perf_counter() - t0
m = result.perf_metrics
summary = {
    'model': args.model, 'device': args.device, 'prompt': prompt,
    'load_s': load_s, 'generate_wall_s': wall_s,
    'input_tokens': m.get_num_input_tokens(),
    'generated_tokens': m.get_num_generated_tokens(),
    'ttft_ms': m.get_ttft().mean,
    'tpot_ms': m.get_tpot().mean,
    'throughput_token_s': m.get_throughput().mean,
}
(args.output / 'answer.txt').write_text('\n'.join(result.texts), encoding='utf-8')
(args.output / 'summary.json').write_text(
    json.dumps(summary, ensure_ascii=False, indent=2), encoding='utf-8')
print(json.dumps(summary, ensure_ascii=False, indent=2))
print('\n'.join(result.texts))
```

模型包含视觉能力，原工程使用`VLMPipeline`完成文本测试。这个选择不表示图片功能已经验证；图片输入还需要公开样本、processor和独立验收。

```bash
python run_ir.py --model artifacts/ir/qwen35-int4 \
  --device GPU --output results/int4-gpu
python run_ir.py --model artifacts/ir/qwen35-int8 \
  --device GPU --output results/int8-gpu
```

每次进程结束后释放模型，再运行下一份。这个程序是基于原片段补全的教学入口，未在本轮硬件执行；实际输出以读者复跑的文件为准。它使用Pipeline指标，不能直接当作HTTP服务的TTFT。

## 4. 怎样阅读历史输出？

| 项目 | INT4 GPU | INT8 GPU |
| --- | --- | --- |
| 输入/输出token | 19 / 128 | 19 / 128 |
| 加载时间 | 8.251s，另一次冷加载13.528s | 12.140s |
| TTFT | 184.02ms | 169.73ms |
| TPOT | 47.26ms/token | 98.96ms/token |
| 管线报告吞吐 | 21.1599token/s | 10.1047token/s |
| 完整答案 | 思考阶段达到上限 | 思考阶段达到上限 |

这组记录证明当前组合完成了生成，并给出短任务性能观察。它没有证明最终中文答案完整，也没有证明服务并发容量。应先检查`answer.txt`，必要时调整生成预算和模型支持的思考配置，再运行固定质量集。

比较Vulkan、SYCL和GenAI时，先统一输入、制品、卸载、输出与计时边界。原记录的llama-bench tg和GenAI Pipeline吞吐应分列，不能仅相除就宣布框架收益。

## 5. NPU 失败该怎样记录？

原工程INT4在NPU编译阶段出现重复名称校验错误；INT8编译420秒未结束，被超时终止，退出124。二者都没有进入token生成。超时与明确编译错误要分别写，也不能填NPU吞吐为零后与GPU绘成速度比较。

要复核NPU，单独进程设置时间上限，保留完整编译日志、IR revision与插件版本，先查该架构、精度和动态形状支持。不要在主服务启动流程里无限等待，也不要将失败扩展为“所有Intel NPU不能运行语言模型”。

## 6. 本章交付与后续工作

应保存依赖快照、模型清单、设备枚举、命令、加载日志、原始文本、性能JSON与质量检查。GPU文本通过后，再逐项加入完整答案、长输入、多轮、图片与HTTP服务，每次增加一个需要验证的能力。

端侧部署尤其要关注共享内存竞争：桌面程序、其他模型和编译缓存都会改变可用预算。记录冷启动和热运行，才能判断用户第一次打开应用与连续使用时各自的等待。
