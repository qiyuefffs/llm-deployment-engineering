# Intel Arc and NPU: Vulkan, SYCL, IR and voice commands

[简体中文](../../01-deployment-foundations/cases/C09-intel-arc-npu/README.md) | **English**

[Index of engineering examples](README.md) · [General directory of knowledge systems](../SUMMARY.md)

Technical labels: `Core Ultra 7 256V / 16GB / OpenVINO / ASR / TTS`

## Environment and three execution paths

|Projects|Conditions recorded|
| --- | --- |
|Device|Core Ultra7 256V,Arc Lunar Lake GPU,NPU,16GB shared memory|
|Systems and tools| Ubuntu24.04.4,Mesa26.1.4,oneAPI2026.1.0,OpenVINO2026.2.1 |
| GGUF |llama.cpp Vulkan and SYCL; GPU 23 layer/CPU 10 layer, pp512/tg128 three wheels|
| IR |Qwen 3.5-9B INT4/INT8 Fixed revision and list of files|
|Speech|Whisper ASR, BabelVox mixed TTS, full NPU experiment, Qwen3-TTS and Kokoro 48|

## Deploying adaptive execution order

```text
Driver and device inclusion → Independent Vulkan/SYCL build → GGUF sublayer with pp/tg
 ← IR file validation → GenAI GPU pipeline → functionality integrity
 → NPU compilation and shape checking → Voice segmentation modules → Full audio quality → RTF and RSS
```

GPUs and NPUs are different execution targets and can't be successfully concluded using GPUs by simply changing the device strings. NPU compilation failures, overtime, fallback, incorrect audio and CPU success are recorded respectively. Windows IPEX-LLM/Ollama belongs to another version combination, which retains the original operation without interfering with the Linux baseline.

## Practical optimization and results

|Experiments|Observation|Engineering judgement|
| --- | --- | --- |
| IR INT4/INT8 GPU |Fixed input generating rate observation ratio of about 2.09|The output is in the reasoning cut-off stage and the quality is not complete.|
| Vulkan/SYCL |Compared to pp/tg and 23/10 layer|Engine time doesn't rank directly with HTTP|
| Whisper NPU |4.4s audio, three rounds core time of about 0.17s|The process cold start is also noted, the core RTF is about 0.039.|
|BabelVox full NPU|Performance Standards, audio content errors|Quality failure, rollback, mixed path|
| Kokoro CPU |48 cases, P95 RTF 0.189, about 3GiB of RSS|Real-time targets passed, original memory targets failed|
| Kokoro NPUW |First run exceeded 20 minutes; the cached rerun timed out after 120 s|Without WAV, you can't report NPU throughput|

Acceptance testing is divided into four categories: functionality, completeness, accuracy, real-time, memory budget. All NPUs and minimum RTFs are not final targets; The failure program keeps the input shape, compilation configuration and exit state, so that it can return to the next version. The original Section 17 report, three rounds of data, all subsequent TTS experiments and the complete Windows route are as follows.

## Agreement on the use of complete technical records

The following technical correctness, commands, tables, logs, failures and subsequent experiments of the relevant FlowUs articles are retained directly, without abbreviating the original process. private paths, nodes, authentication and sanitization of attached addresses; `<NODE_IP>` For example, the placeholder needs to be filled in the current environment. The original suggestion or prediction is still a suggestion or prediction. The above execution sequence and technical revisions are used to explain conflicts in historical records, and historical GPU/NPU experiments have not been repeated in this round.

## R35 · Qwen 3.5-9B Intel openvino platform inference comparison report

> Test date: 2026-07-15
> device :Intel Core Ultra 7 256V,Intel Arc Graphics (Lunar Lake),Intel NPU,16 GB unified memory
> The system is based on Ubuntu 24.04.4 LTS, Linux 6.17.0-14-generic.

#### 1. Conclusions

1. **OpenVINO GenAI GPU + official INT4 IR** The following are the best and measured current performance successes: `21.16 tokens/s `,TTFT `184.02 ms ` More than `12 tokens/s` The target.

2. OpenVINO INT8 GPU inference was successful, but only `10.10 tokens/s `, INT4 is approximately this fraction of INT8: `2.09x` It is the first of its kind in the world to be produced using INT4.

3. llama.cpp Vulkan + Mesa 26.1.4 for the current stable service scheme, benchmark for the current stable service scheme `11.54 tokens/s ` The actual API is `11.38 tokens/s`.

4. llama.cpp SYCL is available but generates speed `10.22 tokens/s` This is the lowest level of Mesa 26.1.4 Vulkan.

5. OpenVINO INT4 NPU has a hard failure at the VPUX compiler stage; INT8 NPU compilation 420 seconds has not yet been completed and has been terminated too late. The current NPU program is not available for production.

6. The llama.cpp OpenVINO WIP backend can compile and list the device, but cannot run the current Qwen 3.5-9B GGUF; The correct OpenVINO path is the official pre-conversion IR + OpenVINO GenAI.

#### 2. Hardware and software environments

|Projects|Configuration|
| --- | --- |
| CPU | Intel Core Ultra 7 256V |
| GPU | Intel Arc Graphics (LNL), device ID 0x64a0 |
| NPU |Intel NPU, OpenVINO can be downloaded|
|memory|16 GB CPU/GPU/NPU unified memory|
| Mesa | 26.1.4~kisak1~n |
| Vulkan API | 1.4.354 |
| Vulkan driver | Intel open-source Mesa driver 26.1.4 |
| oneAPI compiler | 2026.1.0 |
| OpenVINO | 2026.2.1 |
| OpenVINO GenAI | 2026.2.1.0 |
| OpenVINO Tokenizers | 2026.2.1.0 |
| Optimum Intel | 2.0.0 |
| Transformers | 5.0.0 |
| llama.cpp ggml version |0.16.0, source code without .git, commit unknown|

OpenVINO is available on the following devices:

```text
CPU,GPU,NPU
```

#### 3. model

##### 3.1 llama.cpp GGUF

```text
/srv/llm/models/gguf/qwen3.5-9b/Qwen3.5-9B-Q4_K_M.gguf
```

- Parameters: 8.95B

- File size: about 5.23 GiB

- quantization :Q4_K_M

- GPU/CPU hybrid: of 33 offloadable layers, 23 ran on the GPU and 10 on the CPU; CPU layers accounted for approximately 30.3%.

##### 3.2 OpenVINO INT4 IR

```text
/srv/llm/models/openvino/Qwen3.5-9B-int4-ov
```

- The repository: `OpenVINO/Qwen3.5-9B-int4-ov`

- revision：`3f31fc1609edb0cbc8b131bc4c291f1b15cb0676`

- quantization :INT4_ASYM,group size 128

- There are 24 documents.`6,129,582,094` bytes

- Completeness: Total bytes are consistent with official metrics, no `.incomplete`

##### 3.3 OpenVINO INT8 IR

```text
/srv/llm/models/openvino/Qwen3.5-9B-int8-ov
```

- The repository: `OpenVINO/Qwen3.5-9B-int8-ov`

- revision：`3054198f70b6d50b97fa17ae80314e590c57def0`

- quantization :INT8

- There are 24 documents.`9,457,724,353` bytes

- Completeness: Total bytes are consistent with official metrics, no `.incomplete`

- Language IR resolution: 4 inputs, 1 output, 9,112 ops

#### 4. Overall performance contrast

> `llama-bench `, llama.cpp HTTP API, and OpenVINO GenAI ` PerfMetrics`The timeline is not exactly the same. Keep the test type in the table, without pretending that the results of different boundaries are the same benchmark.

|Initial number|The Path|Model|device / layered|Type of test| Prompt | Generation |Results|
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | llama.cpp Vulkan | Q4_K_M | GPU 23 / CPU 10, Mesa 25.2.8 | llama-bench |Not maintained|About 7.76 t/s|Success, old driver baseline|
| 2 | llama.cpp SYCL | Q4_K_M | GPU 23 / CPU 10 | llama-bench, pp512/tg128, 3 rounds | 353.70 ± 15.31 t/s | 10.22 ± 0.19 t/s |Successful|
| 3 | llama.cpp SYCL | Q4_K_M | GPU 23 / CPU 10 | HTTP API, 16/128 tokens | 11.67 t/s | 9.21 t/s |Successful, short request|
| 4 | llama.cpp Vulkan | Q4_K_M | GPU 23 / CPU 10, Mesa 26.1.4 | llama-bench, pp512/tg128, 3 rounds | 244.91 ± 0.79 t/s | 11.54 ± 0.13 t/s |Successful|
| 5 | llama.cpp Vulkan | Q4_K_M | GPU 23 / CPU 10, Mesa 26.1.4 | HTTP API, 22/128 tokens | 10.53 t/s | 11.38 t/s |Success, current service|
| 6 | OpenVINO GenAI | INT4 IR | GPU | VLMPipeline, 19/128 tokens |Not measured separately| 21.16 ± 0.71 t/s |Successful, at best|
| 7 | OpenVINO GenAI | INT8 IR | GPU | VLMPipeline, 19/128 tokens |Not measured separately| 10.10 ± 0.18 t/s |Successful|
| 8 | OpenVINO GenAI | INT4 IR | NPU | VLMPipeline compile | — | — |VPUX compiler failure|
| 9 | OpenVINO GenAI | INT8 IR | NPU | VLMPipeline compile | — | — |420 s overtime, not generated|
| 10 | llama.cpp OpenVINO | Q4_K_M | GPU | llama-bench | — | — |Cache_r_l0 / CPY not supported|

#### 5. Detailed indicators of the OpenVINO GPU

The two official tests used the same pronoun:

```text
请用中文简要说明人工智能推理加速的作用。
```

Both are used:

```text
max_new_tokens=128
do_sample=False
输入 tokens=19
生成 tokens=128
```

|Indicators| INT4 GPU | INT8 GPU |INT4 compared to INT8|
| --- | --- | --- | --- |
| Pipeline load |8.251 s (another cold start: 13.528 s)| 12.140 s |INT4 is faster.|
| Warmup 8 tokens |1.265 s (first recording)| 1.073 s |Not as the main performance indicator|
| TTFT | 184.02 ms | 169.73 ms |INT8 low 14.29 ms|
| TPOT | 47.26 ms/token | 98.96 ms/token |INT4 decreased by about 52.2%|
| Throughput | 21.1599 ± 0.7100 t/s | 10.1047 ± 0.1766 t/s | 2.09x |
| Generate duration | 6,193.33 ms | 12,745.07 ms |INT4 is about 2.06x.|
| Inference duration |Not maintained| 12,610.92 ms | — |
| Tokenization | 0.518 ms | 2.058 ms |The impact is small.|
| Detokenization | 7.221 ms | 6.776 ms |The impact is small.|

##### 5.1 Explanation

- The INT8 TTFT is about 14 ms lower than the INT4, but this advantage is small and should not be considered a stable conclusion.

- The TPOT of continuous generation stage INT4 is about half that of INT8, generating throughput up to 2.09 times that of INT8.

- The device has only 16 GB of unified memory, the INT4 model is about 6.13 GB, and the INT8 is about 9.46 GB. The INT4 has a lower memory pressure and higher throughput.

- Current performance results support the introduction of the INT4 GPU as an OpenVINO production candidate, and the INT8 as a precision control or compatibility alternative, not recommended as a default performance option.

#### 6. NPU test records

##### 6.1 INT4 NPU

OpenVINO is able to list NPUs, but `VLMPipeline(model, "NPU")` In the VPUX compiler phase failure:

```text
StopLocationVerifierPass Pass failed:
Found 32 duplicated names after full verification

Compilation failed.
vclAllocatedExecutableCreate3 result: 0x78000004
[NPU_VCL] Compiler returned msg: Compilation failed
```

Conclusion: Hard failure, not in token generation.

##### 6.2 INT8 NPU

- The NPU device was successful.

- `VLMPipeline(model, "NPU")` Compilation lasted 420 seconds without completing output.

- by `timeout 420 ` End and exit code `124`.

- It has not entered warm-up or token generation, so it cannot report NPU inference throughput.

Conclusion: remembered as a compilation of NPUs, super-timers, not as inference successes; It is not the same as a clear compiler error.

#### 7. llama.cpp OpenVINO failure record

llama.cpp `GGML_OPENVINO=ON` The compilation was successful and included the OpenVINO backend, but inference was created using Qwen 3.5-9B Q4_K_M GGUF:

```text
pre-allocated tensor
(cache_r_l0 (view) (copy of ))
in a buffer (OPENVINO0)
that cannot run the operation (CPY)
```

Open and close separately `GGML_OPENVINO_STATEFUL_EXECUTION` It's time for reproduction. This is a llama.cpp OpenVINO WIP backend compatibility issue with the current Qwen 3.5 GGUF graph, which does not mean that OpenVINO's official IR cannot run on GPUs.

#### 8. Upgrading of Mesa

|driver| Vulkan generation |Changes|
| --- | --- | --- |
| Mesa 25.2.8 |About 7.76 t/s|baseline|
| Mesa 26.1.4 | 11.54 ± 0.13 t/s |About 48.7%|

Mesa 26.1.4 makes Vulkan upgrade from a significantly slower than SYCL to slightly faster than SYCL:

```text
Vulkan 26.1.4: 11.54 t/s
SYCL:           10.22 t/s
相对提升:       约 12.9%
```

#### 9. Test commands

##### 9.1 Vulkan benchmark

```text
/srv/llm/src/llama.cpp/build/bin/llama-bench \
  -m /srv/llm/models/gguf/qwen3.5-9b/Qwen3.5-9B-Q4_K_M.gguf \
  -ngl 23 \
  -t 8 \
  -fa on \
  -p 512 \
  -n 128 \
  -r 3
```

##### 9.2 SYCL benchmark

```text
source /opt/intel/oneapi/setvars.sh --force
export ONEAPI_DEVICE_SELECTOR=level_zero:0
export ZES_ENABLE_SYSMAN=1

/srv/llm/src/llama.cpp/build-sycl/bin/llama-bench \
  -m /srv/llm/models/gguf/qwen3.5-9b/Qwen3.5-9B-Q4_K_M.gguf \
  -ngl 23 \
  -t 8 \
  -fa on \
  -p 512 \
  -n 128 \
  -r 3
```

##### 9.3 OpenVINO GenAI GPU

```text
import openvino_genai as ov_genai

model = "/srv/llm/models/openvino/Qwen3.5-9B-int4-ov"
pipe = ov_genai.VLMPipeline(model, "GPU")

# 预热
pipe.generate("Hello", max_new_tokens=8, do_sample=False)

result = pipe.generate(
    "请用中文简要说明人工智能推理加速的作用。",
    max_new_tokens=128,
    do_sample=False,
)

metrics = result.perf_metrics
print(metrics.get_num_input_tokens())
print(metrics.get_num_generated_tokens())
print(metrics.get_ttft().mean)
print(metrics.get_tpot().mean)
print(metrics.get_throughput().mean)
```

INT8 will only be `model` It was replaced by:

```text
/srv/llm/models/openvino/Qwen3.5-9B-int8-ov
```

#### 10. Export behaviour and restrictions

- INT4/INT8 OpenVINO tests normally generate content, but Qwen 3.5 is defaulted as reasoning/thinking text.

- `max_new_tokens=128` When the output reaches a length limit during the reasoning stage, it does not enter the final Chinese answer; This is not inference failure.

- The performance comparison focuses on the same INT4/INT8 GPU differences under 19 input tokens and 128 generated tokens.

- A single API/GenAI record in this report is not equivalent to a long-term stability test; Multi-round, long-context, concurrency and memory stress tests should also be added before the OpenVINO service is available.

#### 11. Suggestions for production

##### Strongly recommended

```text
OpenVINO GenAI + Qwen3.5-9B INT4 IR + Intel GPU
```

The reason:

- Real token generation has been completed.

- `21.16 tokens/s ` Significantly more `12 tokens/s` The target.

- It's 2.09 times faster than the INT8 GPU.

- This is about 83.4% faster than the current Vulkan benchmark.

- The model is smaller and better suited for 16 GB of unified memory.

##### The fallback order

1. Vulkan + Mesa 26.1.4: Current stable service, 11.54 t/s benchmark

2. SYCL: Stability is available, 10.22 t/s.

3. OpenVINO INT8 GPU: Functionality Successful, but current performance is lower than the Vulkan benchmark, not as a default performance option.

##### Not in use

- OpenVINO INT4 NPU: VPUX compiler clear failure.

- OpenVINO INT8 NPU:420 seconds compilation Overtime

- llama.cpp OpenVINO + Qwen3.5 GGUF: `CPY` It's not compatible.

#### 12. Current operating status

Before the dedicated ASR/TTS NPU tests on 2026-07-15, the llama.cpp Vulkan LLM service was stopped at the user's request to free unified memory. After the test, stop and do not automatically restore:

```text
qwen35-9b-gpu.service: inactive
enabled: enabled
```

The service still retains an open-source configuration, but is not currently running, so the following ports do not provide LLM API for the time being:

```text
http://<NODE_IP>:8009/v1
```

The order to restart the LLM service is as follows:

```text
sudo systemctl start qwen35-9b-gpu.service
```

#### 13. OpenVINO NPU ASR/TTS measurements

##### 13.1 Testing conditions

|Projects|Configuration|
| --- | --- |
| OpenVINO | 2026.2.1 |
| OpenVINO GenAI | 2026.2.1.0 |
| NPU | Intel(R) AI Boost |
|LLM services|Stop and avoid unified memory competition|
| TTS | BabelVox OpenVINO INT8，Chinese，NPU |
| ASR | Whisper Base OpenVINO INT8，Chinese transcribe，NPU |
|The number of repetitions|TTS 3 wheels, ASR 3 wheels|
|Process measurement| /usr/bin/time -v |

ASR model :

```text
/srv/llm/models/asr/whisper-base-int8-ov
磁盘占用：83 MiB
```

TTS model :

```text
/srv/llm/models/tts/babelvox-openvino-int8
磁盘占用：2.5 GiB
```

TTS OpenVINO compiled model cache：

```text
/srv/llm/cache/openvino/tts
磁盘占用：1.8 GiB
```

##### 13.2 TTS NPU test

Input the text:

```text
你好，这是英特尔NPU语音合成性能测试。OpenVINO正在进行本地语音推理。
```

parameter :

```text
device=NPU
precision=int8
cp-kv-cache=on
talker buckets=64,128,256
language=Chinese
max_tokens=256
```

BabelVox clearly lists and uses:

```text
NPU device: Intel(R) AI Boost
Generating with BabelVox (NPU)
```

|Indicators| Run 1 | Run 2 | Run 3 |Average of three rounds|Heat caches average of run 2/3.|
| --- | --- | --- | --- | --- | --- |
| OpenVINO models compile | 3.3 s | 1.5 s | 1.5 s | 2.10 s | 1.50 s |
| Weights + tokenizer load | 1.5 s | 0.6 s | 0.6 s | 0.90 s | 0.60 s |
| Codec frames | 42 | 42 | 55 | 46.33 | 48.5 |
|Core generation is time consuming| 5.1 s | 4.7 s | 6.6 s | 5.47 s | 5.65 s |
|Audio output time| 3.36 s | 3.36 s | 4.40 s | 3.71 s | 3.88 s |
|BabelVox reports RTF| 1.5 | 1.3 | 1.4 | 1.40 | 1.35 |
|The end of the process to the end of the clock| 15.18 s | 11.30 s | 12.61 s | 13.03 s | 11.96 s |
|RSS peak| 4,415,732 KiB | 4,584,960 KiB | 4,585,956 KiB | 4,528,883 KiB | 4,585,458 KiB |
| Swap | 0 | 0 | 0 | 0 | 0 |

Interpretation:

- All three rounds of TTS were successful, confirming the performance of the speaker encoder and tokenizer decoder on the NPU.

- `CP prefill+decode` The log clearly shows the use of the CPU KV cache, so this is the NPU + CPU sync path, not all operators are 100% on the NPU.

- After life cache model compilation decreased from 3.3 s to 1.5 s, weights / tokenizer load decreased from 1.5 s to 0.6 s.

- The RTF reported by BabelVox is the first of its kind in the world.`1.3～1.5` It is also important to note that the core generation time is still higher than the audio generation time and has not yet reached real-time TTS.

- Run 3 generates 55 codec frames, while the first two rounds are 42, indicating that the current generation is random. The difference in output time should not be ignored only when comparing the time of the wall clock.

- RSS peak is about 4.21 to 4.37 GiB, with no swap.

Examples of effective output:

```text
/srv/llm/outputs/tts-npu.wav
PCM signed 16-bit, mono, 24000 Hz
```

The original log:

```text
/srv/llm/outputs/benchmarks/tts/tts-run-1.log
/srv/llm/outputs/benchmarks/tts/tts-run-2.log
/srv/llm/outputs/benchmarks/tts/tts-run-3.log
```

TTS currently has two non-fatal warnings:

1. `qwen3_tts` Model type with compatibility warning for instance type.

2. Tokenizer regex warning, recommended for upstream use `fix_mistral_regex=True`.

These two warnings do not prevent this generation, but should not be ignored prior to voice quality/text coverage acceptance testing.

##### 13.3 ASR NPU testing

Input files:

```text
/srv/llm/outputs/tts-npu.wav
PCM signed 16-bit, mono, 24000 Hz
音频时长：4.400 s
```

WhisperPipeline will pass librosa and input a 16 kHz mono resampling and use:

```text
ov_genai.WhisperPipeline(
    "/srv/llm/models/asr/whisper-base-int8-ov",
    "NPU",
)
```

Identify the configuration:

```text
language=<|zh|>
task=transcribe
```

The three rounds of output are consistent:

```text
你好,这是英特尔NPU語音合成服务
```

|Indicators| Run 1 | Run 2 | Run 3 |Average of three rounds|Heat caches average of run 2/3.|
| --- | --- | --- | --- | --- | --- |
|Audio length| 4.400 s | 4.400 s | 4.400 s | 4.400 s | 4.400 s |
|Core infer| 0.173 s | 0.169 s | 0.172 s | 0.171 s | 0.171 s |
| RTF | 0.039 | 0.038 | 0.039 | 0.0387 | 0.0385 |
|Equivalent real-time multiples of 1/RTF| 25.64x | 26.32x | 25.64x | 25.86x | 25.97x |
|The end of the process to the end of the clock| 8.97 s | 1.65 s | 1.66 s | 4.09 s | 1.66 s |
|RSS peak| 1,277,992 KiB | 764,444 KiB | 764,588 KiB | 935,675 KiB | 764,516 KiB |
| Swap | 0 | 0 | 0 | 0 | 0 |

Interpretation:

- Whisper Base INT8 completed three rounds of actual transcripts on OpenVINO NPU, no longer just models and scripts.

- Core transcription of RTFs `0.0387` It's about 25.9 times faster in real time, and performance is good.

- The first round process wall clock 8.97 s includes Python startup, audio load/re-sampling, OpenVINO NPU compilation and pipeline initialization; It is not possible to replace cold start end-to-end latency with 0.173s.

- After the cache life, the new process end-to-end time is about 1.65 to 1.66 s, peak RSS is about 746.6 MiB, no swap.

- The three-wheeled output is perfectly consistent and stable.

- Input audio is longer, and the ASR only recognizes the "hello" button, which is an Intel NPU voice synthesis service button; This mainly reflects the fact that TTS's actual content/audio termination is not entirely consistent with input text, and the general ASR accuracy rate cannot be calculated using this synthetic sample.

The original log:

```text
/srv/llm/outputs/benchmarks/asr/asr-run-1.log
/srv/llm/outputs/benchmarks/asr/asr-run-2.log
/srv/llm/outputs/benchmarks/asr/asr-run-3.log
```

##### 13.4 ASR/TTS Conclusions

|Task|OpenVINO NPU functionality|Core performance|Cold start / end to end|Peak memory|Production judgement|
| --- | --- | --- | --- | --- | --- |
| ASR Whisper Base INT8 |Passed|RTF 0.0387, about 25.9x in real time|First round 8.97s, new process 1.66s after cache|First round 1.22 GiB and cache 0.73 GiB|Performance Available and Required for Real Voicemail Accuracy Testing|
| TTS BabelVox INT8 |Passed|RTF of about 1.40|15.18 s ahead, 11.96 s after the cache|It's about 4.21 to 4.37 GiB|Functionality Available, not yet in real time, needs optimization and quality acceptance testing|

ASR's core rewriting performance is sufficient to support real-time scenarios. TTS has successfully used NPUs, but the current core RTF is greater than 1, and it is not yet able to play full audio in real-time.

#### 14. TTS Full NPU Optimization Experiment

##### 14.1 Objectives of the experiment and current status of source code

The goal is to place the entire OpenVINO subchart of BabelVox TTS in the NPU and remove the RTF from the baseline approx.`1.40 ` It's down.`1.0` Here it is.

BabelVox is currently streaming in `device=NPU` The actual allocation of time is:

|Subtitles|baseline device|
| --- | --- |
| Speaker encoder | NPU |
| Talker 64/128/256 buckets | NPU |
| Tokenizer decoder | NPU |
| Code Predictor prefill/decode | CPU |
| Code Predictor KV cache | CPU memory |

The source code contains explicit hardcoding:

```text
self.cp_prefill = core.compile_model(..., "CPU")
self.cp_decode = core.compile_model(..., "CPU")
```

So it's just going in.`--device NPU` It's not all NPU.

##### 14.2 Experimental patches

The experimental patch fixed the shape of the CP graph and disabled the CPU fallback:

```text
cp_prefill inputs_embeds: [1,2,1024]
cp_decode inputs_embeds: [1,1,1024]
cp_decode attention_mask: [1,1,1,20]
past_keys/past_values: [5,1,8,20,128]
fallback_cpu: false
```

log Confirmed that the CP KV cache path was successful in the NPU compilation:

```text
NPU device: Intel(R) AI Boost
CP prefill+decode: 1.7s (NPU/NPU - KV cache)
Tok decoder: 96.9s (NPU)
```

At the same time, the full Code Predictor NPU path, which does not use the CP KV cache, was also tested to rule out a single KV cache implementation problem.

##### 14.3 CP KV-cache Full NPU performance

Using fixed random seeds `20260715 `, ` max_tokens=128`Three rounds of the same Chinese text. The SHA-256 of the three WAVs is exactly the same, indicating that the results can be reproduced.

|Indicators| Run 1 | Run 2 | Run 3 |Heat caches average of run 2/3.|
| --- | --- | --- | --- | --- |
| Pipeline load | 127.03 s | 3.89 s | 2.17 s | 3.03 s |
|Core generated| 7.572 s | 7.421 s | 7.381 s | 7.401 s |
|Audio output| 10.24 s | 10.24 s | 10.24 s | 10.24 s |
| RTF | 0.739 | 0.725 | 0.721 | 0.723 |
|The end of the process to the end of the clock| 138.41 s | 14.94 s | 12.52 s | 13.73 s |
|RSS peak| 5,589,676 KiB | 4,553,232 KiB | 4,550,872 KiB | 4,552,052 KiB |
| Swap | 0 | 0 | 0 | 0 |

From pure speeds, RTF from baseline is about `1.40 ` It's down.`0.723` Core generation is faster than real-time playback.

However, all three rounds reach the 128 codec-frame ceiling, which does not naturally generate EOS. For the output of Run 3, the Whisper Base INT8 NPU is translated as follows:

```text
我
```

The original input is two complete Chinese phrases, and the translations are not in line with the input. Therefore, the path, although speedy, is ineffective and cannot be deployed.

The original log:

```text
/srv/llm/outputs/benchmarks/tts-all-npu/run-1.log
/srv/llm/outputs/benchmarks/tts-all-npu/run-2.log
/srv/llm/outputs/benchmarks/tts-all-npu/run-3.log
/srv/llm/outputs/benchmarks/tts-all-npu/run-3-asr-qc.log
```

##### 14.4 Full Code Predictor Full NPU Reviewed

Turn off the CP KV cache and switch to fixed `[1,17,1024]` The full Code Predictor NPU chart:

|Indicators|Results|
| --- | --- |
| Pipeline cold load | 125.03 s |
|Core generated| 7.497 s |
|Audio output| 10.24 s |
| RTF | 0.732 |
|Clock of the process wall| 135.72 s |
|RSS peak| 5,713,012 KiB |
|ASR translated|I did.|

Both full CP and full CP KV cache paths generate ineffective audio, explaining the problem not only of KV cache state management but also of the current INT8 Code Predictor IR numerical precision, fixed shape semantics or compatibility of NPU operators on the NPU.

##### 14.5 Final judgement and rollback

|The Path|device allocation| RTF |Accuracy of pronunciation|Deployed|
| --- | --- | --- | --- | --- |
|Upstream baseline| Talker/Speaker/Decoder=NPU,CP=CPU |About 1.40|Chinese is recognizable|Yes, but not in real time.|
|Full NPU CP KV cache|It's all openVINO subchart = NPU| 0.723 |Failure, translating just makes me sick|Unavailable|
|Full NPU full CP|It's all openVINO subchart = NPU| 0.732 |Failure, translating just makes me sick|Unavailable|

In conclusion:

> The current BabelVox INT8 model can move the entire OpenVINO subchart compilation to the Intel NPU at real-time speeds. However, the Code Predictor NPU output is incorrect and the final audio is not available. Therefore, it is currently not possible to meet the three requirements for the correct output of all NPU aluminum, real-time aluminum and aluminum at the same time.

To avoid using the wrong audio path to produce, the remote Python environment has restored the original upload.`pipeline.py`:

```text
SHA-256: 5e5151bc3852b9cf0ea22585d34ad8fe8ae52932ee747b5764b3eb4f0af4ca84
hybrid_pipeline_restored=true
```

All NPU experiment patches and benchmark scripts are retained in the project for submission of upstream reproducibility issues to BabelVox/OpenVINO/NPU, not for current production run.

#### 15. Qwen3-TTS 0.6B Official OpenVINO Pipeline measured

##### 15.1 Model and Environment

To distinguish between BabelVox customization routes, we downloaded and tested community products that have been structured according to OpenVINO's official Notebook model:

```text
Repository: aurora2035/Qwen3-TTS-12Hz-0.6B-CustomVoice-OpenVINO-INT8
Remote path: /srv/llm/models/tts/Qwen3-TTS-12Hz-0.6B-CustomVoice-OpenVINO-INT8
Download size: about 1.55 GiB
Source model: Qwen/Qwen3-TTS-12Hz-0.6B-CustomVoice
```

The model includes the Talker Language Model, Code Predictor, Text/Codec Embedding, Text Projection and the OpenVINO IR of the Speech Tokenizer Encoder/Decoder.

Independent environment:

```text
/srv/llm/venvs/qwen3-tts-ov
OpenVINO 2026.2.1
torch 2.8.0+cpu
torchaudio 2.8.0+cpu
transformers 4.57.3
qwen-tts 0.1.1
```

OpenVINO Official Qwen3-TTS Notebook The current device controller is displayed `exclude=["NPU"]` Therefore, the official example does not state that the conversion structure can be run directly on the NPU.

##### 15.2 OpenVINO CPU loading and inference

Used `vivian ` Preset voices, Chinese test text, and `max_new_tokens=128`:

|Indicators|measured value|
| --- | --- |
| Pipeline load | 2.704 s |
|Core generated| 8.735 s |
|Audio output| 8.000 s |
| RTF | 1.092 |
|Sampling rate| 24,000 Hz |
|RSS peak|3,777,252 KiB (approximately 3.60 GiB)|
| Swap | 0 |

WAV output:

```text
/srv/llm/outputs/benchmarks/qwen3-tts-official/cpu.wav
SHA-256: e7fc70a7f8161c688b7f4084c6941e505a92f26ab430cdf0eb58cd6cd76ee161
```

The Whisper Base INT8 NPU is used to translate:

```text
你好,這是Q準TTS在Intel設備上的OpenVi-NO與音合成性能測試
audio_s=8.000 infer_s=0.222 rtf=0.028
```

There are simple, nouns and syntactic differences, but the subject of the sentence is consistent with the original, confirming the validity of the voice content generated by the CPU path.

##### 15.3 NPU direct loading failure

Use the same model to enter directories.`device=NPU` When the original Pipeline first failed in the Speech Tokenizer Encoder compilation phase:

```text
Upper bounds are not specified
Channels count of input tensor shape and filter shape must be the same
LLVM ERROR: Failed to infer result type(s)
```

CustomVoice does not require a Speech Tokenizer Encoder. After converting the Encoder to a latency compilation, the Decoder is still unable to compile due to the dynamic token length:

```text
Got negative shape dim bound: '-1'
ZE_RESULT_ERROR_INVALID_ARGUMENT
```

After leaving the Speech Tokenizer in the CPU, only the Talker generator is placed in the NPU, the Talker Language Model still fails:

```text
Upper bounds are not specified for ShapeOf input
to_shape was called on a dynamic shape
```

Level 3 verification indicates that the Speech Tokenizer Encoder, Decoder and Talker of the finished product IR retain an NPU unacceptable infinite dynamic shape. It's not an NPU driver that hasn't been installed and can't be passed.`device` The string is solved.

##### 15.4 Conclusion

|The Path|Results| RTF |Accuracy of pronunciation|Currently deployable|
| --- | --- | --- | --- | --- |
|The official Helper + OpenVINO CPU|Successful| 1.092 |Passed ASR translated|Yes, but slightly slower than in real time.|
|The official Helper + OpenVINO NPU|compilation failure|It's not.|Unproduced audio|Unavailable|
| Talker=NPU, Tokenizer=CPU |Talker compilation failure|It's not.|Unproduced audio|Unavailable|

> The Qwen3-TTS 0.6B INT8 product has been successfully downloaded and uses OpenVINO CPU load inference to output sound effectively; But it's not an NPU-ready static shape model. To run on the Lunar Lake NPU, multiple buckets need to be redirected at the fixed text/token/KV-cache/codec length instead of using the dynamic IR product directly.

The original log:

```text
/srv/llm/outputs/benchmarks/qwen3-tts-official/cpu.log
/srv/llm/outputs/benchmarks/qwen3-tts-official/cpu-asr-qc.log
/srv/llm/outputs/benchmarks/qwen3-tts-official/npu.log
/srv/llm/outputs/benchmarks/qwen3-tts-official/npu-lazy-encoder.log
/srv/llm/outputs/benchmarks/qwen3-tts-official/npu-talker-cpu-tokenizer.log
```

#### 16. Intel NPU real-time TTS networking software research

Research date: 2026-07-15. The criteria for determining `RTF < 1.0` OpenVINO can be used to run the pump, pump subchart with NPU pump and pump subchart with NPU pump.

##### 16.1 Ranking of candidates

|Priorities|Models and schemes|How to execute NPU|Chinese|Real-time evidence|256V is determined|
| --- | --- | --- | --- | --- | --- |
| 1 | Kokoro-82M |OpenVINO NPUW, mainframe NPU, precision sensitive parts of the CPU fallback|Support|Officially available NPU dedicated static shape paths, but not disclosed 256V RTF|The most immediate measurement|
| 2 | MeloTTS INT8 |BERT = NPU, TTS/VITS Subject = CPU|Support|Light non-auto-return, high real-time probability at system level, and no public 256V RTF|Second choice for real-time stability|
| 3 | BabelVox/Qwen3-TTS 0.6B INT8 |Talker/Decoder=NPU,CP/part prefill=CPU|It is strong.|258V public best RTF 1.0; The original output is about 1.40|Short sentence segments and streaming playback are not guaranteed for RTF<1|
| 4 | SpeechT5 + OpenVINO GenAI |API to receive NPU device|Weak, mainly English|Unbelievable Lunar Lake NPU RTF|Compatibility only in English|

##### 16.2 Highly recommended: Kokoro-82M

The latest official Kokoro Notebook for OpenVINO explicitly requires OpenVINO 2026.1 or an updated version and enables the NPU-specific path:

```text
input_ids: [1,512]
ref_s: [1,256]
speed: [1]
NPU_USE_NPUW=YES
NPUW_DEVICES=NPU,CPU
NPUW_KOKORO=YES
NPUW_CACHE_DIR=.cache/npuw
```

The key features:

- 82M parameter, which is much smaller than Qwen3-TTS 0.6B.

- Non-large self-return Audio LLM, more easily left with RTF<1 performance surplus.

- The NPU input is fixed to a static shape and will not repeat the Qwen3-TTS dynamic shape compilation failure.

- The official use of NPUW is to fallback the precision-sensitive operator to the CPU, so NPU+CPU is an asynchronous operation rather than strictly a full NPU.

- Standard Kokoro-82M supporting Mandarin `lang_code='z'` We need to `misaki [zh]`, providing 4 female and 4 male voices.

- Standard Chinese audio model card ratings are low, and the speed is up to date, but Chinese audio quality must be true acceptance testing.

- `Kokoro-82M-v1.1-zh` Additionally, about 100 Chinese speakers are available, but the official NPU Notebook is standard Kokoro-82M, which requires additional confirmation of export compatibility.

##### 16.3 Available but not all NPU: MeloTTS

The official blog of Intel/OpenVINO is:

```text
Chinese multilingual BERT: NPU, static shape, INT8
MeloTTS/VITS acoustic model: CPU
post-processing/speech enhancement: CPU
```

It supports a mix of Chinese and Chinese-English, has a lighter architecture, and does not require a large number of Codec tokens to be self-generated like Qwen3-TTS. MeloTTS is a viable candidate if the business requirement is a full-fledged real-time pump rather than a full-fledged NPU pump.

##### 16.4 Not recommended as first-round NPU real-time testing

The limitations of the device in OpenVINO's latest official Notebook:

|Model|The current status of the official Notebook|
| --- | --- |
| Qwen3-TTS |exclude=["NPU"], and the host has confirmed a dynamic IR compilation failure|
| FireRedTTS2 | exclude=["NPU"] |
| Parler-TTS | exclude=["NPU"] |
| OpenVoice/OpenVoice2 | exclude=["NPU"] |
| CosyVoice3 |LLM can select NPU, Flow and HiFT to explicitly exclude NPU|
| SpeechT5 |The OpenVINO GenAI API is capable of transmitting NPUs but lacks a 256V real-time benchmark.|

Therefore, it is not possible to determine whether a specific TTS Pipeline can run on NPUs based on the CPU/GPU/NPU pipeline that supports OpenVINO Runtime.

##### 16.5 Proposed test sequence

1. **Kokoro-82M standard edition + OpenVINO 2026.2 + NPUW** First verify the official NPU path, Chinese tone, RTF and CPU fallback examples.

2. **Kokoro-82M-v1.1-zh** If the standard version speeds up to the standard but the Chinese language is not soundproof, test the Chinese special version.

3. **MeloTTS INT8,BERT=NPU + TTS=CPU** As a fixed tone and stable real-time baseline in Chinese.

4. BabelVox retains only high-speed/sound clone routes, passed short-sentence buckets and streaming playback that reduce perceptual latency, and no longer pursues the current INT8 CP full NPU.

Sources:

- OpenVINO Kokoro Notebook: [https://github.com/openvinotoolkit/openvino_notebooks/blob/latest/notebooks/kokoro/kokoro.ipynb](https://github.com/openvinotoolkit/openvino_notebooks/blob/latest/notebooks/kokoro/kokoro.ipynb)

- OpenVINO Qwen3-TTS Notebook: [https://github.com/openvinotoolkit/openvino_notebooks/blob/latest/notebooks/qwen3-tts/qwen3-tts.ipynb](https://github.com/openvinotoolkit/openvino_notebooks/blob/latest/notebooks/qwen3-tts/qwen3-tts.ipynb)

- OpenVINO MeloTTS NPU blog: [https://blog.openvino.ai/blog-posts/optimizing-melotts-for-aipc-deployment-with-openvino-a-lightweight-tts-solution](https://blog.openvino.ai/blog-posts/optimizing-melotts-for-aipc-deployment-with-openvino-a-lightweight-tts-solution)

- BabelVox model card with 258V benchmark: [https://huggingface.co/djwarf/babelvox-openvino-int8](https://huggingface.co/djwarf/babelvox-openvino-int8)

- Kokoro in Chinese: [https://huggingface.co/hexgrad/Kokoro-82M/blob/main/VOICES.md](https://huggingface.co/hexgrad/Kokoro-82M/blob/main/VOICES.md)

- Kokoro in Chinese: [https://huggingface.co/hexgrad/Kokoro-82M-v1.1-zh](https://huggingface.co/hexgrad/Kokoro-82M-v1.1-zh)

#### 17. Kokoro-82M OpenVINO NPUW and CPU measurements

Test date: 2026-07-15.

##### 17.1 Environment and model preparedness

To avoid affecting existing LLM, ASR and BabelVox environments, create an independent environment:

```text
/srv/llm/venvs/kokoro-ov
Python 3.12.3
OpenVINO 2026.2.1
torch 2.8.0+cpu
kokoro 0.9.4
misaki 0.9.4 + misaki[zh]
transformers 4.53.3
espeak-ng 1.51
```

The official Notebook method can be used to `hexgrad/Kokoro-82M` Generate dynamic OpenVINO IR and reproduce it as a static copy of NPU:

```text
Dynamic IR: /srv/llm/models/tts/kokoro/Kokoro-82M-openvino
NPU static IR: /srv/llm/models/tts/kokoro/Kokoro-82M-openvino-npu-static
input_ids: [1,512] int64
ref_s: [1,256] float32
speed: [1] float32
```

|Preparation Stage|It takes time.|
| --- | --- |
|PyTorch source model loaded| 54.25 s |
|OpenVINO IR conversion| 13.44 s |
|NPU static reshape/save| 0.17 s |
|Preparing for the process peak RSS| 2,194,460 KiB |

Model size:

```text
Dynamic IR: 184 MiB
NPU static IR: 184 MiB
NPUW partial cache: 178 MiB
Python environment: 1.7 GiB
```

##### 17.2 NPUW Loading Results: failed

Compilation configuration is consistent with OpenVINO's official Notebook:

```text
device=NPU
NPU_USE_NPUW=YES
NPUW_DEVICES=NPU,CPU
NPUW_KOKORO=YES
NPUW_CACHE_DIR=/srv/llm/.cache/openvino/kokoro-npuw
```

For the first time `compile_model` For a long time maintaining about 100% single-core CPU, the RSS is about 2.1 to 2.2 GiB, generating 9 NPUW cache blobs, for a total of 178 MiB; However, over 20 minutes have passed and the first WAV has not been produced.

After disrupting the local SSH pipeline, it was discovered that the remote compilation subprocess did not leave with SSH and was still running. Subsequently, the PID was explicitly terminated and verified that there were no residual testing processes.

The new process repeats using a 178 MiB cache, which is still unloaded for 120 seconds, and is eventually terminated by timeout:

```text
cache retry limit: 120 s
result: timeout
pipeline status: 137
generated WAV: 0
```

It is therefore not possible to report the NPU RTF, nor can it be confirmed that the program can be deployed on the current Linux/OpenVINO/NPU driver combination. The official Notebook provides the NPU path of the notebook, which is not the same as the current notebook.

##### 17.3 OpenVINO CPU clean environment performance

To eliminate the impact of backend NPUW compilation on CPU performance, after clearing all remaining processes, the audio has been cached, `HF_HUB_OFFLINE=1` Under the conditions, re-tested eight Chinese-toned × 6 class texts for a total of 48 cases.

|Indicators|Clean environment CPU results|Objectives|Decided|
| --- | --- | --- | --- |
| Pipeline compile | 0.670 s | — |Passed|
| Pipeline init | 0.277 s | — |Passed|
| RTF mean | 0.183 | ≤0.8 |Passed|
| RTF median/P50 | 0.180 | ≤0.8 |Passed|
| RTF P95 | 0.189 | <1.0 |Passed|
| RTF min | 0.175 | — | — |
| RTF max | 0.288 | <1.0 |Passed|
| RTF≤0.8 | 48/48 | 48/48 |Passed|
| RTF<1.0 | 48/48 | 48/48 |Passed|
|RSS peak|It's about 3,144,108 KiB (about 3.00 GiB)| <2 GiB |failed|
| Swap | 0 | 0 |Passed|
|48 total wall clocks| 79.97 s | — | — |

Equivalent generation speeds of about `1/0.183 = 5.46x` In real time. Even without using NPU, the model has significantly exceeded the real-time target on the current CPU.

Note: The two rounds of CPU testing prior to the final clean replay were concurrent with the remaining NPUW compilation process, with the thermal cache P95 being 0.290. The data was used as a conservative reference under concurrency workload, and was ultimately concluded to be P95 0.189 after clearance.

##### 17.4 Audio and text quality

The Whisper Base INT8 NPU Pipeline uses a verified Whisper Base INT8 NPU Pipeline to perform single loading of 48 hot caches of WAVs.

```text
ASR load: 0.446 s
files: 48/48
ASR process wall time: 8.51 s
ASR peak RSS: 707,284 KiB
```

Quality is determined by:

- The short sentence “你好,欢迎回家” was correctly transcribed back for all 8 voices.

- `zf_xiaobei `, ` zf_xiaoxiao `, ` zf_xiaoyi `, ` zm_yunxi `, ` zm_yunxia `, ` zm_yunyang`The Chinese subtitle is more complete.

- `zf_xiaoni` Chinese transliteration errors are more pronounced and are not recommended as the default Chinese tone.

- The subject of the multi-syllable text is generally recognizable, but there are still near-voicing errors such as co-voicing/simultaneous voicing, long-distance voicing/long-distance voicing.

- Long digit sequences often contain incorrect digits or digit counts; The common numerical meanings of temperature, hour, minute are essentially identifiable.

- Mixed English text `OpenVINO `, ` Intel Core Ultra `, ` Kokoro TTS`Pronunciation/translation errors are obvious and are not suitable for direct broadcasting of English-language nouns without preprocessing.

It is recommended to give a prioritized manual test:

```text
female: zf_xiaoxiao, zf_xiaoyi, zf_xiaobei
male: zm_yunxia, zm_yunyang, zm_yunxi
avoid as default: zf_xiaoni
```

##### 17.5 Final deployment decided

|The Path|performance|quality|memory|Deployed|
| --- | --- | --- | --- | --- |
| Kokoro OpenVINO NPUW |Unfinished Loading, No RTF|No audio verifiable|Compilation about 2.2 GiB|No|
| Kokoro OpenVINO CPU |P50 0.180, P95 0.189, about 5.46x in real time|The Chinese subject is recognizable, and the tone varies greatly|About 3.00 GiB|Yes, it is.|

The final conclusion:

> The Kokoro-82M can be easily reached in real time on the current device, but the passed OpenVINO CPU reaches, not the NPUW. Current NPUW path loading/compilation time is unacceptable and should not be considered as a production schedule. The product path recommends using the OpenVINO CPU and keeping the NPU to Whisper ASR.

Raw materials:

```text
/srv/llm/outputs/benchmarks/kokoro-npu/prepare.log
/srv/llm/outputs/benchmarks/kokoro-npu/run-cold.log
/srv/llm/outputs/benchmarks/kokoro-npu/run-npu-cache-retry.log
/srv/llm/outputs/benchmarks/kokoro-npu/run-cpu/metrics.csv
/srv/llm/outputs/benchmarks/kokoro-npu/run-cpu/asr-quality.csv
/srv/llm/outputs/benchmarks/kokoro-npu/run-cpu-clean/metrics.csv
/srv/llm/outputs/benchmarks/kokoro-npu/run-cpu-clean/summary.json
```

Qwen3.5-9B INT4 IR Multimodal Visual Inference Testing Report ((private page links are not public))

Qwen 3.5-9B + TTS + ASR test report ((private page link not public))

Qwen 3.5-4B INT4 VLM test report ((private page link not public))

## R36 · Qwen 3.5-9B INT4 IR Multimodal visual inference test report

[Original note image: 微信图片_20260721112741_277_2.jpg; [Unpublished transcript]

[Original note image: 微信图片_20260721112740_276_2.jpg; [Unpublished transcript]

### ======================================================================
Qwen 3.5-9B INT4 IR Multimodal visual inference test report
device :Windows 11 25H2 / Intel Arc 130V GPU (8GB)
Date: 2026-07-21

#### One: Environmental information

OS              Windows 11 25H2

CPU             Intel Core Ultra (Lunar Lake)

GPU             Intel(R) Arc(TM) 130V GPU (8GB) (iGPU)

GPU Driver      32.0.101.8509 (DCH)

Python          3.10.11

OpenVINO        2026.2.1

OpenVINO GenAI  2026.2.1.0

OpenVINO Tokenizers  2026.2.1.0

Optimum Intel   2.0.0

Transformers    5.0.0

Torch           2.13.0

It can be used with CPUs, GPUs, NPUs.

model OpenVINO/Qwen3.5-9B-int4-ov (INT4 ASYM, group size 128)

Model path        C:/llm\models\openvino\Qwen3.5-9B-int4-ov

### ======================================================================
Two, multi-brand contrast testing

Test images:

- 1.jpg (1920x1080) - POKKA green tea bottle

- 2.jpg (1920x1080) - POKKA bottle of grass

---

#### Test 1: Brand recognition and contrast

Prompt:

What brand of bottle is shown in Figure 1 and Figure 2 respectively? Please provide details on the differences between the two bottles in terms of brand, appearance, color, body design, label text, etc.

Model Output:

Users asked me to identify the brands of bottles in Figure 1 and Figure 2 and compare them in detail.

Step 1: Identify the bottle in Figure 1.

- Observation: This is a green bottle placed on a wooden table.

- Brand: The bottle has the distinctive red letter "POKKA", which is the brand name in the image; The private input is not used as a public acceptance testing sample.

- Product: The bottle body label has the words "green tea" in Chinese and "green tea" in English.

- Color: The bottle body is mostly green, with a yellow decoration, representing green tea.

- The bottle cap: white bottle cap.

- Details of the label: "No Caffeine" and the words "LIGHT REFRESHING".

Step 2: Identify the bottle in Figure 2.

- Note: This is a pink orange bottle placed on a wooden table.

- Brand: The bottle also has the word "POKKA" on it, although the location of the bottle is the same as the one above, it belongs to the same brand.

- Product: Looks like a strawberry-flavored or mixed fruit-flavored drink with the words "ICE" and "STRAWBERRY" written on the bottle.

Performance:

Input tokens:      4,125

Generated tokens:  256

TTFT:              13,931 ms

TPOT:              59.9 ms/token

Throughput:        16.70 tokens/s

Inference time:    29.2 s

---

#### Test 2: Detailed analysis of differences

Prompt:

Please look closely at the two bottles in Figure 1 and Figure 2 and point out all their differences, including but not limited to: brand name, shape of bottle, color of bottle cap, design of label, capacity label.

Model Output:

The user asked me to look closely at the two bottles in Figure 1 and Figure 2 and point out all the differences between them.

Figure one:

- Brand name: The bottle has the red word "POKKA" on it.

- Bottle shape: This is a typical plastic beverage bottle with a round top and thinner body.

- The color of the bottle cap: the bottle cap is white.

- Label design: The label is predominantly yellow-green, with the words "green tea" in Chinese and "GREEN TEA" in English. There is also a "caffeine-free" sign on the label, which looks fresh green overall.

- Capacity marking: Capacity marking appears below the bottle body, although it is somewhat vague, but is roughly recognizable as being around 500ml.

Figure two:

- Brand name: There is also a word "POKKA" on the bottle, although you can see the "POK" part.

- The shape of the bottle: The shape of the bottle is very similar to the picture 1 and is a cylindrical plastic bottle.

- The color of the bottle cap: the picture is not very clear, and may be white or light.

- Label design: The label is predominantly pink/orange with "ICE" and "STRAWBERRY" written on it.

- Capacity labelling: similar to 500ml specifications.

This is not the case.

Both are POKKA branded tea/drinking products, but picture 1 is green tea flavored (green bottle) and picture 2 is grass flavored (pink bottle).

The shape of the bottle is the same, with different colors and label designs depending on the taste.

Performance:

Input tokens:      4,127

Generated tokens:  256

TTFT:              11,844 ms

TPOT:              61.8 ms/token

Throughput:        16.18 tokens/s

Inference time:    27.7 s

### ======================================================================
3 - Performance Optimization of contrast testing

Test image: test_image.png (512x384, colored shapes)

Prompt: "Please describe what's in this picture, including color, shape and quantity". "

---

#### configuration Loading s) throughput (t/s) TTFT

1. Baseline (default) 24.70 17.15 1.801.70 58.30

2. CACHE (first written) 34.96 16.61 2,363.93 60.22

3. CACHE + THROUGHPUT          35.30    17.08     1,761.16  58.55

4. CACHE + THROUGHPUT + FP16 31.42 17.39 1,339.28 57.51 ★ Best of the TTFT

5. CACHE + LATENCY 30.77 17.44 1,374.33 57.33 ★ Best throughput

6. CACHE Hot load (2nd load) 28.22 17.21 1,358.52 58.10

---

Optimal configuration:

PERFORMANCE_HINT = "LATENCY"

INFERENCE_PRECISION_HINT = "f16"

TTFT improvement: 1,802ms → 1,339ms ((-25.7%)

### ======================================================================
Four, pure text inference baseline

Model Output (text-only, no image):

Users requested a brief description in Chinese of the role of AI inference in accelerating.

1. Analysis request:

  - Subject: Artificial intelligence speeds up inference

  - Mission: Summarizing its role

  - Language: Chinese

2. Definition of "AI inference acceleration":

  - What is it? It is a process that makes the inference phase of an AI model faster and more efficient.

  - What is inference? It was...

Performance:

Input tokens:      19

Generated tokens:  128

Throughput:        17.34 t/s

TTFT:              488 ms

TPOT:              57.7 ms/token

### ======================================================================
Five, the conclusion.

1. Multimodal visual inference: ✅ Success

  - VQA is normal.

  - Inference versus multi-graphing correctly distinguishes between different products of the same brand

2. Inference throughput: 17.34 t/s (text only) / 16.70 t/s (two images)

  - Production target of more than 12 t/s

  - Approximately 82% of the reference performance for Linux/Mesa 26.1.4

3. Optimized effects:

  - TTFT decreased by 25.7% (f16 precision hint)

  - Throughput increased by 1.7% (LATENCY performance hint)

  - Model cache can reduce loading time by about 5%.

4. NPU is not available (refer to Ubuntu deployment report has confirmed compilation failure)

  - Currently only using GPU inference

5. Recommended production configuration:

  pipe = VLMPipeline(model, "GPU",

  PERFORMANCE_HINT="LATENCY",

  INFERENCE_PRECISION_HINT="f16",

  )

======================================================================

## R37 · Useipex-llm to quantize and produce ollama models, deployed on Intel integrated GPUs.

ipex-llm link: [https://ipex-llm-latest.readthedocs.io/en/latest/doc/LLM/Quickstart/ollama_quickstart.html](https://ipex-llm-latest.readthedocs.io/en/latest/doc/LLM/Quickstart/ollama_quickstart.html)

1. Create a conda environment and downloadipex-llm, and make sure to download Intel driver in advance, which can be viewed in the link.

```text
conda create -n llm-cpp python=3.11
conda activate llm-cpp
pip install --pre --upgrade ipex-llm[cpp]
```

1. Create an llama-cpp directory and enter it.

```text
mkdir llama-cpp
cd llama-cpp
```

1. Quantization model based on the teaching of quantization

2. Open cmd with administrator permissions

- Please. **Use administrator permissions in the Miniforge Prompt** Run the following command.

  ```text
  conda activate llm-cpp
  init-ollama.bat

  ```

1. Starting the Ollama service

- Please run the following commands in the Miniforge Prompt:

  ```text
  set OLLAMA_NUM_GPU=999
  set no_proxy=localhost,127.0.0.1
  set ZES_ENABLE_SYSMAN=1
  set SYCL_CACHE_PERSISTENT=1
  rem under most circumstances, the following environment variable may improve performance, but sometimes this may also cause performance degradation
  set SYCL_PI_LEVEL_ZERO_USE_IMMEDIATE_COMMANDLISTS=1

  ollama serve
  ```

Note: Please set the environment variable `OLLAMA_NUM_GPU ` For the `999` Ensure that all layers of the model run on the Intel GPU, otherwise certain layers may run on the CPU.

1. Creating a Modelfile file

Ollama supports importing GGUF models into the Modelfile, for example, assuming you've already moved from [Mistral-7B-Instruct-v0.1-GGUF](https://huggingface.co/TheBloke/Mistral-7B-Instruct-v0.1-GGUF/tree/main) I downloaded it.`mistral-7b-instruct-v0.1.Q4_K_M.gguf ` So you can create a name.`Modelfile` The document:

```text
FROM ./mistral-7b-instruct-v0.1.Q4_K_M.gguf
TEMPLATE [INST] {{ .Prompt }} [/INST]
PARAMETER num_predict 64
```

Then you can pass in Ollama.`ollama create example -f Modelfile ` Creating and using models `ollama run` The model is running directly on the controller.

1. Operating model

Please run the following commands in the Miniforge Prompt.

```text
set no_proxy=localhost,127.0.0.1
ollama create example -f Modelfile
ollama run example
```

## R38 · Intel NPU makes model inference: deepseek-r1:1.5b, 7b, 8b

The link is as follows: [https://www.51openlab.com/article/728/](https://www.51openlab.com/article/728/)

This technical document describes in detail how to deploy the DeepSeek-R1 series large language model (1.5B/7B/8B) using its powerful neural processing unit (NPU) on a device equipped with Intel Core Ultra processors. We will present the complete deployment of OpenVINOTM GenAI from environment to model quantization and NPU inference.

1. Build an environment

  1.1 Creating a conda environment

  ```text
  #创建环境
  conda create -n 环境名称 python=3.10
  #激活环境
  conda activate 环境名称
  ```

  1.2 Build an OpenVINOTM GenAI development environment

  ```text
  # 安装OpenVINO GenAI

  pip install openvino-genai

  # 安装optimum-intel，用于转换并量化生成式AI模型

  pip install optimum-intel[openvino]
  ```

2. Download model and perform quantization model (converted to openvineo format)

  2.1 Download the model

  ```text
  # 安装ModelScope

  pip install modelscope

  # 下载DeepSeek-R1-Distill-Qwen-1.5B模型到指定

  modelscope download --model deepseek‑ai/DeepSeek‑R1‑Distill‑Qwen‑1.5B --local_dir "C:/llm\Desktop\llm-NPU"

  #下载8b-0528
  modelscope download --model deepseek-ai/DeepSeek-R1-0528-Qwen3-8B --local_dir "C:/llm\Desktop\llm-NPU\ds-8b-0528"

  # 下载ds-8b
  modelscope download --model deepseek-ai/DeepSeek-R1-Distill-Llama-8B --local_dir "C:/llm\Desktop\llm-NPU\ds-8b"
  ```

  2.2 Model quantization and format conversion using optimum-cli

  ```text
  optimum-cli export openvino
    --model C:/llm\Desktop\llm-NPU\deepseek-r1-1_5
    --task text-generation-with-past
    --weight-format int4
    --sym
    --ratio 1.0
    --group-size 128
    C:/llm\Desktop\llm-NPU\deepseek-r1-1_5-openvino


    #转换并量化ds-8b
    optimum-cli export openvino --model "C:/llm\Desktop\llm-NPU\ds-8b" --task text-generation-with-past --weight-format int4 --sym --ratio 1.0 --group-size -1 "C:/llm\Desktop\llm-NPU\ds-8b-openvino"
  ```

1. inference and test script

  ```text
  import openvino_genai as ov_genai

  # 创建 LLMPipeline 对象，指定模型路径和设备类型
  pipe = ov_genai.LLMPipeline(r"C:/llm\Desktop\llm-NPU\deepseek-r1-1_5-openvino", "NPU")

  # 定义流式输出的回调函数
  def streamer(subword):
      print(subword, end='', flush=True)
      # 返回状态，指示生成是否继续
      return ov_genai.StreamingStatus.RUNNING

  # 启动对话
  pipe.start_chat()

  # 提示用户输入问题
  while True:
      try:
          prompt = input('问题：\n')
      except EOFError:
          break
      # 调用 generate 方法进行生成，并传入回调函数
      pipe.generate(prompt, streamer=streamer, max_new_tokens=4096)
      print('\n----------\n')

  # 结束对话
  pipe.finish_chat()

  ```
