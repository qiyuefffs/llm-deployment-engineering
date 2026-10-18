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

## 七、完整工程记录：Whisper ASR的冷启动与热推理

本节继续使用Core Ultra7 256V、16GB统一内存和OpenVINO2026.2.1。测试日期2026-07-15，运行前停止LLM服务，减少统一内存与后台计算竞争。Whisper Base INT8模型约83MiB，目标设备为Intel AI Boost NPU。

### 7.1 输入、预处理和输出

原输入是一段4.400秒、24kHz、单声道PCM16音频。Pipeline前将音频重采样为16kHz，识别配置为中文transcribe。三轮输出一致，识别出一条中文短句。由于输入来自语音合成且内容本身存在截断，这组样本只证明此链路完成转写，不能计算通用ASR准确率。

公开复跑可换成获得授权的自录短句：提供参考文本、采样率、时长和文件摘要。新输入得到的新时间应另存，不沿用下表的历史成绩。

### 7.2 一份可以保存测量文件的ASR入口

把以下保存为`run_asr.py`。环境使用本章前面的OpenVINO版本，另安装并固定`librosa`、`soundfile`、NumPy的实际解析版本；记录`pip freeze`。模型目录必须是Whisper GenAI可加载的IR及其配套文件。

```python
import argparse
import json
from pathlib import Path
import time
import librosa
import openvino_genai as genai

p = argparse.ArgumentParser()
p.add_argument('--model', required=True)
p.add_argument('--audio', required=True)
p.add_argument('--device', default='NPU')
p.add_argument('--output', type=Path, required=True)
args = p.parse_args()
args.output.mkdir(parents=True, exist_ok=True)

start = time.perf_counter()
audio, sr = librosa.load(args.audio, sr=16000, mono=True)
prepare_s = time.perf_counter() - start
start = time.perf_counter()
pipe = genai.WhisperPipeline(args.model, args.device)
load_s = time.perf_counter() - start
start = time.perf_counter()
result = pipe.generate(audio.tolist(), language='<|zh|>', task='transcribe')
infer_s = time.perf_counter() - start
audio_s = len(audio) / sr
report = {
    'device': args.device, 'audio_s': audio_s,
    'prepare_s': prepare_s, 'pipeline_load_s': load_s,
    'infer_s': infer_s, 'rtf': infer_s / audio_s,
    'texts': result.texts,
}
(args.output / 'summary.json').write_text(
    json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
(args.output / 'transcript.txt').write_text('\n'.join(result.texts), encoding='utf-8')
print(json.dumps(report, ensure_ascii=False, indent=2))
```

```bash
/usr/bin/time -v -o results/asr-process-time.txt \
  python run_asr.py --model artifacts/ir/whisper-base-int8 \
  --audio inputs/short-zh.wav --device NPU --output results/asr-run1
```

这个教学入口补齐了结果保存，不是原私有脚本的逐字公开。进程外`time -v`包括Python导入、文件读取与退出，内部infer只包围generate；不要用内部计时替代冷启动体验。

### 7.3 三轮实测完整表

| 指标 | Run1 | Run2 | Run3 |
| --- | --- | --- | --- |
| 音频时长 | 4.400s | 4.400s | 4.400s |
| 核心infer | 0.173s | 0.169s | 0.172s |
| RTF，源报告四舍五入值 | 0.039 | 0.038 | 0.039 |
| 进程端到端 | 8.97s | 1.65s | 1.66s |
| 峰值RSS | 1277992KiB | 764444KiB | 764588KiB |
| Swap | 0 | 0 | 0 |

平均核心RTF约0.0387，核心处理约25.9倍实时。首轮新进程8.97秒，缓存后的新进程约1.66秒，二者对应不同用户等待。若将服务常驻，还应测“进程内第二条请求”；现有新进程热缓存成绩不能替它填写。

## 八、BabelVox TTS：混合设备分工与三轮结果

原模型为BabelVox OpenVINO INT8，约2.5GiB，编译缓存约1.8GiB。中文输入、`max_tokens=256`、Code Predictor KV cache开启，Talker使用64/128/256长度bucket。

虽然命令指定`device=NPU`，子图实际分布如下：Speaker encoder、Talker与Tokenizer decoder在NPU，Code Predictor prefill/decode和CP KV在CPU。设备参数只能说明Pipeline选择，不能覆盖源码中明确的CPU编译路径。

| 指标 | Run1 | Run2 | Run3 |
| --- | --- | --- | --- |
| 模型compile | 3.3s | 1.5s | 1.5s |
| 权重与tokenizer加载 | 1.5s | 0.6s | 0.6s |
| Codec frames | 42 | 42 | 55 |
| 核心生成 | 5.1s | 4.7s | 6.6s |
| 输出音频 | 3.36s | 3.36s | 4.40s |
| 框架报告RTF | 1.5 | 1.3 | 1.4 |
| 进程墙钟 | 15.18s | 11.30s | 12.61s |
| 峰值RSS | 4415732KiB | 4584960KiB | 4585956KiB |
| Swap | 0 | 0 | 0 |

这张表应保留框架RTF原值。源中“核心生成耗时”与“框架RTF”的计时边界/取整并未完整说明，逐项相除不完全相等，不能擅自修改其中一列。后续基准应在同一层明确RTF分子，并另记进程墙钟。

三轮输出帧数不同，说明随机生成改变了音频长度。直接拿Run2比Run3短1.9秒来评价性能，会混入工作量变化。正式比较固定文本、音色、种子与上限，保留自然EOS、帧数、音频时长和质量。

RTF均值约1.40，核心生成尚慢于实时音频播放。流式播放可以缩短用户感知首段等待，但并不会自动把持续生成的RTF改成小于1。

## 九、一次应当回滚的优化：全NPU Code Predictor

### 9.1 优化目标与图形状

目标是把Code Predictor也移到NPU，让RTF低于1。实验为CP prefill/decode建立固定shape，禁用CPU fallback，记录主要输入：

| 输入/状态 | 固定形状 |
| --- | --- |
| CP prefill inputs_embeds | `[1,2,1024]` |
| CP decode inputs_embeds | `[1,1,1024]` |
| CP decode attention_mask | `[1,1,1,20]` |
| past_keys / past_values | `[5,1,8,20,128]` |

日志确认CP编译到了NPU，不能就此认定适配完成。下一步是与CPU基线逐子图比较输出，再检查多步状态和最终音频。原实验使用seed20260715、max_tokens128，三轮生成文件摘要一致，说明错误可以稳定出现。

### 9.2 速度确实达标

| 指标 | Run1 | Run2 | Run3 |
| --- | --- | --- | --- |
| Pipeline load | 127.03s | 3.89s | 2.17s |
| 核心生成 | 7.572s | 7.421s | 7.381s |
| 音频时长 | 10.24s | 10.24s | 10.24s |
| RTF | 0.739 | 0.725 | 0.721 |
| 进程墙钟 | 138.41s | 14.94s | 12.52s |
| 峰值RSS | 5589676KiB | 4553232KiB | 4550872KiB |

Run2/3平均RTF0.723，已经快于实时。但三轮都撞到128帧上限，没有自然EOS；对原完整中文句子的音频做ASR回译，只得到“我”。这项性能变化无法作为可用优化成果交付。

### 9.3 排除“只是KV实现出错”的单一假设

实验随后关闭CP KV，采用完整Code Predictor，输入`[1,17,1024]`。结果cold load125.03秒、生成7.497秒、音频10.24秒、RTF0.732、峰值RSS5713012KiB；回译仍只有“我”。

它让排查范围从单一KV实现扩大到INT8 CP的数值、固定shape语义和NPU执行兼容性。没有逐层张量误差与上游定位，不能进一步断言某一个原因已确定。下一步应保存同输入下CPU/NPU子图输出、mask、位置与状态，做逐步差异定位。

### 9.4 回滚也是实验结论的一部分

| 路线 | RTF | 输出 | 判定 |
| --- | --- | --- | --- |
| 上游CPU＋NPU混合 | 约1.40 | 可识别中文，需进一步覆盖测试 | 保留基线 |
| 全NPU CP KV | 热均值0.723 | 内容错误、未自然EOS | 不采用 |
| 全NPU完整CP | 0.732 | 内容错误 | 不采用 |

原工程恢复上游pipeline，保留失败补丁和基准供继续定位。不要把失败版本留作默认启动项，再在文档末尾写“质量待优化”。工程验收应该能阻止这个版本进入默认服务。

## 十、Qwen3-TTS0.6B：动态IR的CPU成功与NPU失败

原测试使用`aurora2035/Qwen3-TTS-12Hz-0.6B-CustomVoice-OpenVINO-INT8`，来源模型`Qwen/Qwen3-TTS-12Hz-0.6B-CustomVoice`，下载约1.55GiB。独立环境为OpenVINO2026.2.1、torch/torchaudio2.8.0+cpu、transformers4.57.3、qwen-tts0.1.1。

CPU使用vivian音色、中文文本、max_new_tokens128，结果：

| 项目 | 原实测 |
| --- | --- |
| Pipeline load | 2.704s |
| 核心生成 | 8.735s |
| 音频时长/采样率 | 8.000s / 24kHz |
| RTF | 1.092 |
| 峰值RSS / swap | 3777252KiB / 0 |

ASR回译句子主体可识别，专有名词存在误差。NPU路径则先后在Encoder、Decoder、Talker的动态shape编译处失败，没有生成可用于性能计时的音频。原日期的官方Notebook也排除了NPU；这份动态IR成品不能仅靠更改device升级为NPU-ready制品。

如要继续，先固定text、codec和KV长度，分别导出所需bucket，再保持有效长度和状态语义。对于这个项目，CPU成功可以保留为对照，NPU适配仍是独立工程任务。

## 十一、Kokoro82M：把调研结论走到48例复测

### 11.1 准备过程

看到官方NPU路径后，原工程实际创建独立环境进行测试：Python3.12.3、OpenVINO2026.2.1、torch2.8.0+cpu、kokoro0.9.4、misaki0.9.4（含中文依赖）、transformers4.53.3、espeak-ng1.51。

模型来自`hexgrad/Kokoro-82M`。按官方Notebook生成动态IR，再保存NPU静态副本：input_ids`[1,512]` int64、ref_s`[1,256]` float32、speed`[1]` float32。源模型加载54.25秒、IR转换13.44秒、静态reshape/save0.17秒；两份IR各约184MiB。

### 11.2 NPUW的实际结果

配置使用`NPU_USE_NPUW=YES`、`NPUW_DEVICES=NPU,CPU`、`NPUW_KOKORO=YES`与专用cache目录。NPUW允许子图异构分工，不能表述为全NPU。

首次compile保持约100%单核CPU、RSS2.1—2.2GiB，写出9个cache blob、合计178MiB，但超过20分钟仍未返回，WAV为0。中断连接后发现编译子进程仍运行，原工程明确停止本次测试进程；连接退出不保证远端子进程自动结束。

已有缓存的新进程复测限时120秒，仍未完成加载，最终超时终止。记录状态137只能说明进程终止状态，不能直接反推OOM；该记录是受控超时实验。没有首条音频，就没有NPU RTF。

### 11.3 清理后台后再测CPU

先清理残留编译进程，再在音色已缓存、离线运行条件下测8个中文音色×6类文本，共48例。此前与后台编译共存的CPU结果不并入最终基准。

| 指标 | 干净环境CPU结果 | 原测试目标 | 判定 |
| --- | --- | --- | --- |
| compile / init | 0.670s / 0.277s | 记录 | 完成 |
| RTF mean | 0.183 | ≤0.8 | 通过 |
| RTF median | 0.180 | ≤0.8 | 通过 |
| RTF P95 | 0.189 | <1 | 通过 |
| RTF min / max | 0.175 / 0.288 | max<1 | 通过 |
| RTF≤0.8 | 48/48 | 48/48 | 通过 |
| 峰值RSS | 3144108KiB，约3.00GiB | <2GiB | 未通过 |
| Swap | 0 | 0 | 通过 |
| 48例总墙钟 | 79.97s | 记录 | 完成 |

按平均RTF计算约5.46倍实时，性能已有明显余量；内存目标却没有通过，报告应保留这一项。先前后台编译共存时P95为0.290，清理后的P95为0.189，这说明测试环境控制本身就是重要步骤。

### 11.4 质量和部署判断

48个WAV由同一个已加载Whisper NPU Pipeline批量回译，ASR加载0.446秒，处理墙钟8.51秒。8个音色的短句均能回译；中长文本、长数字与中英混合表现不同。`zf_xiaoni`中长文本错误较多，其他若干中文音色主体更完整；ASR回译只能辅助筛查，最终还要试听和对照文本。

可优先试听`zf_xiaoxiao、zf_xiaoyi、zf_xiaobei、zm_yunxia、zm_yunyang、zm_yunxi`。数字、单位和英文名先做规范化，再测试是否减少播报错误，避免用短欢迎语的成绩代表所有文本。

本次可保留的是CPU TTS路线，NPUW加载路径没有通过；16GB设备是否满足3GiB级TTS内存取决于整个应用预算。NPU可以继续用于已通过的ASR，再对三模型协同做实际负载测试。

## 十二、怎样复用这些语音工程经验

先把任务拆成输入预处理、子图、状态、后处理与输出验收。每个子图写明设备、shape和精度；计时分为准备、编译/加载、首输出、持续生成和进程总时间。TTS保留WAV、采样率、帧数、自然结束与文本覆盖，ASR保留参考文本、转写与错误统计。

迁移设备时从单子图数值比较开始，经过完整单句、长句、多轮，再做持续负载。最终保留正确而可恢复的组合；某个加速器没有通过，也可以通过CPU/GPU/NPU合理分工完成目标。
