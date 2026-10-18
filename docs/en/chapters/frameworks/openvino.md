# OpenVINO: Intel GPU inference with fixed IR

[简体中文](../../../01-deployment-foundations/chapters/frameworks/openvino.md) | **English**

**The full engineering record:** [Intel GPU/NPU Complete Section 17 report and subsequent TTS](../../engineering/intel-arc-npu.md)

[Contents](../../SUMMARY.md) · [The Intel platform](../hardware/intel.md) · [Quantization and verification](../models/quantization.md)

## Overview of this chapter

OpenVINO routes are usually accessed from IR artifact instead of GGUF being delivered directly to GenAI. First, check IR and Pipeline, and then confirm that GPUs or NPUs can compile, generate, and give a complete answer. These three things need to be checked gradually.

This chapter comes from the Qwen 3.5-9B platform test by the authors of FlowUs, and is organized into a sequence of tutorials according to the original record. It is available for the Core Ultra 7 256V, Arc Lunar Lake, 16GB of unified memory, Ubuntu 24.04.4; OpenVINO 2026.2.1; GenAI and Tokenizers 2026.2.1.0. The wheel is not running again on the device.

## 1. Create an independent Python environment

Install GPU drivers and runtime with Intel and distribution instructions to confirm that current users can access the device. Python packages cannot replace system drivers. The original recording uses Mesa 26.1.4, one API 2026.1.0 for another SYCL route; Running GenAI alone does not mean having to install a complete set of oneAPI compilation tools.

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

This is a list of installations organized by historical version. Whether the package supplies the current Python, system and architecture wheel needs to be verified first. Installed and running:

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

The device can be downloaded and can only indicate that the plug-in has detected the device. Model diagrams, shapes, accuracy and state management are still to be checked when creating and generating Pipeline.

## 2. Download two fixed IRs

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

There are 24 files in the history list, INT4 with a total of 6129582094 bytes and INT8 with a total of 9457724353 bytes. Check whether the configuration, tokenizer, IR chart and weights are complete; Download the cache with `.cache` Metadata should not be counted as model artifact size. The model license and the source see the corresponding model card, downloading does not mean you can ignore the conditions for redistribution.

16GB shared memory devices do not load two models at the same time. Each candidate processes independently, recording memory available prior to load, peak RSS and swap, leaving room for systems and drivers.

## 3. Preserving and running the complete inference procedure

Save as follows: `run_ir.py`. It records cold loads, warm-ups and formal generations, and saves text and performance separately:

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

Models with visual abilities, original engineering use `VLMPipeline` Complete the text test. This option does not indicate that the image functionality has been verified; Image input also requires public sampling, processor and independent acceptance testing.

```bash
python run_ir.py --model artifacts/ir/qwen35-int4 \
  --device GPU --output results/int4-gpu
python run_ir.py --model artifacts/ir/qwen35-int8 \
  --device GPU --output results/int8-gpu
```

At the end of each process, the model is released and the next one is run. This program is based on the full instructional input of the original snippet, which is not implemented on the hardware; The actual output is for the readers running files. It uses Pipeline metrics, which cannot be treated directly as HTTP service TTFT.

## 4. How can we read the historical output?

|Projects| INT4 GPU | INT8 GPU |
| --- | --- | --- |
|Input and output tokens| 19 / 128 | 19 / 128 |
|Loading time|8.251s, another cold loaded 13.528s| 12.140s |
| TTFT | 184.02ms | 169.73ms |
| TPOT | 47.26ms/token | 98.96ms/token |
|Pipeline report throughput| 21.1599token/s | 10.1047token/s |
|The complete answer|The reasoning phase reaches a ceiling|The reasoning phase reaches a ceiling|

This set of records shows that the current combination has been generated and gives short task performance observations. It does not prove the completeness of the final Chinese answer, nor does it prove the concurrency capacity of the service. Check first.`answer.txt` When necessary, adjust the reasoning configuration to generate budgets and model support, and then run a fixed quality set.

When comparing Vulkan, SYCL and GenAI, the input, artifact, offloading, output and timing boundaries are unified. The original recorded Llama-bench tg and GenAI Pipeline throughput should be separated and cannot be separated by the declaration of framework gains.

## 5. How can NPU failures be recorded?

In the original engineering, an INT4 repeat name calibration error occurred during the NPU compilation stage; INT8 compilation 420 seconds unfinished, terminated overtime, and withdrawn 124. Neither of which entered the token generation. Overtime and explicit compilation errors must be written separately, nor can NPU throughput be filled to zero compared to GPU drawing speeds.

To review the NPU, set separate process time limits, maintain the complete compilation log, IR revision and plug-in versions, and check the architecture, precision and dynamic shape support. Don't wait indefinitely in the main service startup process, and don't extend failure to all Intel NPUs that can't run language models.

## 6. Delivery and follow-up work under this Chapter

Dependencies, snapshots, models, lists, devices, lists, commands, loading logs, raw text, performance JSON and quality checks should be stored. After the GPU text is passed, each of them adds a complete answer, long input, multi-round, image and HTTP service, each time adding a validation capability.

On-device deployments are particularly focused on shared memory competition: desktop programs, other models, and compilation caches change available budgets. Record cold start and hot run to judge the user's first time opening an app and their respective wait for continuous use.

## Seven, complete engineering record: cold start of the Whisper ASR and heat inference

This section continues to use Core Ultra7 256V, 16GB unified memory and OpenVINO2026.2.1. The test date is 2026-07-15, stopping the LLM service before running, reducing the unified memory competition with the background computing. The Whisper Base INT8 model is about 83 MiB, and the target device is the Intel AI Boost NPU.

### 7.1 Input, preprocessing and output

The original input was 4.400 seconds of 24kHz mono PCM16 audio. Pipeline resampled the audio at 16kHz, identifying the configuration for Chinese transcribe. Three rounds of consistent output, identifying a Chinese short sentence. Because the input comes from voice synthesis and the content itself is intercepted, this group of samples only proves that the link has been transcribed and cannot calculate the general ASR accuracy rate.

Public Returns can be exchanged for authorized autobiographical sentences: references, sample rates, duration and document summaries are provided. The new time of the new input should be kept alternately, without following the historical results in the table below.

### 7.2 An ASR input for storing measurement files

Save the following as `run_asr.py `. Environment using the OpenVINO version prior to this chapter, otherwise installed and fixed ` librosa `, ` soundfile `It's the actual parsing version of NumPy. Recorded ` pip freeze`. The model directory must be a Whisper GenAI loadable IR and its accompanying documents.

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

This instructional introduction complements the result of preservation, not the wording of the original private script public. Out of the process `time -v` It includes Python input, file read and output, and internal infer generates only; Do not replace the cold start experience with internal timing.

### 7.3 Three rounds measured full table

|Indicators| Run1 | Run2 | Run3 |
| --- | --- | --- | --- |
|Audio length| 4.400s | 4.400s | 4.400s |
|Core Inferno| 0.173s | 0.169s | 0.172s |
|RTF, source report four to five inputs| 0.039 | 0.038 | 0.039 |
|End to end of process| 8.97s | 1.65s | 1.66s |
|The peak of RSS| 1277992KiB | 764444KiB | 764588KiB |
| Swap | 0 | 0 | 0 |

The average core RTF is about 0.0387, and core processing is about 25.9 times real-time. The first round of the new process is 8.97 seconds, while the new process after the cache is about 1.66 seconds, which correspond to different users' expectations. If the service is permanently installed, the second request in the installation process should also be tested. The current process hot cache results cannot be filled in its place.

## BabelVox TTS: Mixed device split with three rounds of results

The original model was BabelVox OpenVINO INT8, about 2.5GiB, and the compilation cache was about 1.8GiB. Chinese input, `max_tokens=256` The Code Predictor KV cache is enabled, and Talker uses the 64/128/256 length bucket.

Although the command specifies `device=NPU` Speaker encoder, speaker and tokenizer decoder in NPU, Code Predictor prefill/decode and CP KV in CPU. The device parameter only specifies the Pipeline selection and cannot cover the specified CPU compilation path in the source code.

|Indicators| Run1 | Run2 | Run3 |
| --- | --- | --- | --- |
|model compile| 3.3s | 1.5s | 1.5s |
|Weights loaded with tokenizer| 1.5s | 0.6s | 0.6s |
| Codec frames | 42 | 42 | 55 |
|Core generated| 5.1s | 4.7s | 6.6s |
|Audio output| 3.36s | 3.36s | 4.40s |
|Framework reporting RTF| 1.5 | 1.3 | 1.4 |
|Clock of the process wall| 15.18s | 11.30s | 12.61s |
|The peak of RSS| 4415732KiB | 4584960KiB | 4585956KiB |
| Swap | 0 | 0 | 0 |

This table should retain the original RTF value of the framework. The source does not fully explain timing boundaries or rounding for “core generation time” and “framework RTF.” Dividing the recorded values does not reproduce every RTF exactly, so neither column is silently adjusted. The subsequent benchmark should specify the RTF molecule in the same layer and also note the process wall clock.

The three-round output is different, indicating that random generation changes the audio length. Run2 vs. Run3 can be used directly to evaluate performance in just 1.9 seconds, mixing up with changes in workload. Formal comparison of fixed text, tone, seed and upper limit, preserving natural EOS, frequency, audio length and quality.

The average RTF is about 1.40, and core generation is slower than real-time audio playback. Streamed playback can shorten the user's perception of the first part of the wait, but does not automatically convert the continuously generated RTF to less than 1.

## Nine, one should rollback optimization: Full NPU Code Predictor

### 9.1 Optimization of objectives and graphics

The goal is to move the Code Predictor to the NPU, so that the RTF is below 1. The experiment created a fixed shape for the CP prefill/decode, disabled CPU fallback, and recorded the main inputs:

|Input/state|Fixed shape|
| --- | --- |
| CP prefill inputs_embeds | `[1,2,1024]` |
| CP decode inputs_embeds | `[1,1,1024]` |
| CP decode attention_mask | `[1,1,1,20]` |
| past_keys / past_values | `[5,1,8,20,128]` |

Log confirms that the CP compilation has reached the NPU, and cannot confirm that the adaptation has been completed. The next step is to compare the output with the CPU baseline, then check the multi-step status and final audio. The original experiment used seed20260715 max_tokens128, a three-round generated file summary consistent, showing that errors can occur steadily.

### 9.2 The speed is indeed the mark

|Indicators| Run1 | Run2 | Run3 |
| --- | --- | --- | --- |
| Pipeline load | 127.03s | 3.89s | 2.17s |
|Core generated| 7.572s | 7.421s | 7.381s |
|Audio length| 10.24s | 10.24s | 10.24s |
| RTF | 0.739 | 0.725 | 0.721 |
|Clock of the process wall| 138.41s | 14.94s | 12.52s |
|The peak of RSS| 5589676KiB | 4553232KiB | 4550872KiB |

Run2/3 averages RTF0.723, which is faster than real time. But all three wheels hit the 128 ton ceiling, and there was no natural EOS. As a result of the ASR translation of the audio of the original full Chinese complaint, I was only able to get my hands on it. This performance change cannot be delivered as a viable optimization outcome.

### 9.3 The exclusion of the hypothesis is only a single hypothesis for KV to achieve a false hypothesis

The experiment then switched off the CP KV and used the full Code Predictor to input `[1,17,1024]`. Results: cold load 125.03 seconds, generation 7.497 seconds, audio 10.24 seconds, RTF 0.732, peak RSS 5713012KiB; It's just a matter of translating it.

It allows the scanning range to be extended from a single KV to the numerical value of the INT8 CP, fixed shape semantics and NPU execution compatibility. There is no layered tensor error with upstream positioning, and no further assertion can be made that any cause has been determined. The next step is to save the output, masks, location and state of the CPU/NPU subchart from the input to the step-by-step differential positioning.

### 9.4 rollback is also part of the experimental conclusion

|Routes| RTF |Output|Decided|
| --- | --- | --- | --- |
|Upstream CPU+NPU mix|It's about 1.40.|Chinese is recognizable and needs to be covered further|Keeping the baseline|
|Full NPU CP KV|Heat average of 0.723|Content is wrong, unnatural EOS|Not adopted|
|Full CPU of the NPU| 0.732 |Mistakes in content|Not adopted|

The original project restored the upstream pipeline, retaining the failure patches and benchmarks for continued positioning. Do not leave the failure version as the default startup item, and write "quality" at the end of the document. Engineering acceptance testing should prevent this version from accessing the default service.

## Qwen3-TTS0.6B: CPU success and failure in dynamic IR

Original testing use `aurora2035/Qwen3-TTS-12Hz-0.6B-CustomVoice-OpenVINO-INT8 ` Source model `Qwen/Qwen3-TTS-12Hz-0.6B-CustomVoice` It's about 1.55 GiB. The independent environment is OpenVINO 2026.2.1. torch/torchaudio 2.8.0+cpu 4.57.3 qwen-tts 0.1.1

The CPU uses Vivian tones, Chinese text, max_new_tokens128, and the result is:

|Projects|Originally measured|
| --- | --- |
| Pipeline load | 2.704s |
|Core generated| 8.735s |
|Audio length/sampling rate| 8.000s / 24kHz |
| RTF | 1.092 |
|Peak RSS / swap| 3777252KiB / 0 |

ASR translations are subject-identifiable, and nouns are erroneous. The NPU path fails in the dynamic shape compilation of the Encoder, Decoder, Talker and does not generate audio for performance timing. The official notebook of the original date also excludes the NPU; This dynamic IR product cannot be upgraded to an NPU-ready artifact by changing the device.

If you want to continue, first fix the text, codec and KV lengths, exporting the required bucket, respectively, and then maintain the valid length and state semantics. For this project, the success of the CPU can be reserved for control, and the NPU adaptation is still an independent engineering task.

## Kokoro82M: The results of the study were reduced to 48 repeats

### 11.1 Preparation process

After seeing the official NPU path, the original engineer actually created an independent environment to test: Python 3.12.3, OpenVINO 2026.2.1, torch 2.8.0+cpu, kokoro 0.9.4, misaki 0.9.4, with Chinese dependency, transformers 4.53.3, speak-ng1.51.

The model comes from `hexgrad/Kokoro-82M `. Generate the dynamic IR in the official Notebook and save the static copy of the NPU:input_ids `[1,512]` int64,ref_s `[1,256]` float32,speed `[1]` float32. The source model loads 54.25 seconds, the IR converts 13.44 seconds, the static reshape/save 0.17 seconds; The two IRs are about 184 MiB.

### 11.2 Actual results of the NPUW

Configuration used `NPU_USE_NPUW=YES `, ` NPUW_DEVICES=NPU,CPU `, ` NPUW_KOKORO=YES`and a dedicated cache directory. NPUW allows sub-graphite separation and cannot be expressed as a full NPU.

The first compile kept about 100% single-core CPU, RSS 2.1 and 2.2GiB, wrote 9 cache blobs, totaling 178MiB, but for more than 20 minutes, the WAV was 0. After disconnection, the compilation subprocess is still running, and the original engineer explicitly stops the current test process; Connection withdrawal does not guarantee that the remote end process ends automatically.

The new process, which already has a cache, has a time limit of 120 seconds and has not yet been loaded. Record State 137 only indicates the process termination state and cannot directly reverse OOM; The record is a controlled super-time experiment. Without the first audio, there is no NPU RTF.

### 11.3 Background cleaning and CPU testing

The remainder of the compilation process was cleaned up and 48 texts were tested in 8 Chinese tones x 6 in the case of offline operation under the condition that the audio has been cached. The CPU results that previously coexisted with the background compilation do not fit into the final benchmark.

|Indicators|Clean environment CPU results|Primary testing objectives|Decided|
| --- | --- | --- | --- |
| compile / init | 0.670s / 0.277s |Recorded|Completed|
| RTF mean | 0.183 | ≤0.8 |Passed|
| RTF median | 0.180 | ≤0.8 |Passed|
| RTF P95 | 0.189 | <1 |Passed|
| RTF min / max | 0.175 / 0.288 | max<1 |Passed|
| RTF≤0.8 | 48/48 | 48/48 |Passed|
|The peak of RSS|3144108KiB, about 3.00GiB| <2GiB |failed|
| Swap | 0 | 0 |Passed|
|48 total wall clocks| 79.97s |Recorded|Completed|

There is a significant overlap in real-time performance, which is about 5.46 times higher than the average RTF. The memory target has not been passed, and the report should keep this one. P95 was 0.290 while background compilation was running and 0.189 after cleanup, showing why control of the test environment matters.

### 11.4 Quality and deployment judgement

48 WAVs have been mass-translated by the same Whisper NPU Pipeline, with an ASR of 0.446 seconds and a wall clock of 8.51 seconds. The short sentences for all 8 voices could be transcribed back; Results differ for medium and long texts, long numbers, and mixed Chinese/English input.`zf_xiaoni` Chinese language text is more error-prone and some other Chinese phonetic subjects are more complete. ASR translations can only assist in screening and ultimately test and test text.

It's a priority to try.`zf_xiaoxiao、zf_xiaoyi、zf_xiaobei、zm_yunxia、zm_yunyang、zm_yunxi`. Numbers, units and English names are normalised first, then tested to see if they reduce broadcast errors, avoiding the results of short welcome words representing all texts.

This time, the CPU TTS path can be retained, and the NPUW load path has not been passed; Whether the 16GB device meets the 3GiB TTS memory level depends on the overall application budget. The NPU can continue to use the ASR that has been passed and then synchronize the three models for actual workload testing.

## How to replicate these voice engineering experiences

First, break down the task into input preprocessing, subcharting, status, postprocessing and output acceptance testing. Each sub-graph shows the device, shape and precision; Timing is divided into preparation, compilation/loading, first output, continuous generation and total process time. TTS retains WAV, sampling rate, frequency, natural end and text coverage, and ASR retains reference text, transcription and error statistics.

When moving the device, start by comparing the unit graph values, then complete the single, long, multi-cycle, and then continue the workload. the correct and recoverable combinations are ultimately preserved; An accelerator that has not passed can also pass CPU/GPU/NPU to a reasonably distributed target.
