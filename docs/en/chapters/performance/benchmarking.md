# Performance Testing: Turning a run into a comparable result

[简体中文](../../../01-deployment-foundations/chapters/performance/benchmarking.md) | **English**

**The full engineering record:** [Full load testing tools and operations](../../engineering/benchmark-tools.md) · [oMLX fully measured](../../engineering/apple-mlx.md)

[Contents](../../SUMMARY.md) · [Subject: Performance optimization](../../02-capability-layers/04-memory-performance.md) · [Full CPU running](../../practice/first-service/README.md)

## Overview of this chapter

Performance testing first determines what: model execution speed, individual user waiting, or service capacity under multiple requests. The same token/s token may come from the engine, single request decode or entire HTTP load testing window. The time boundaries are different and the numbers cannot be directly compared.

This chapter provides an overview of the load testing tools in FlowUs, GB10 random testing, oMLX concurrency testing, and the system's CPU running organization. First define the workload, then select the tools, save the details, check the quality, and finally explain the alternatives of throughput and latency.

## 1. Pre-write the test plan and submit the request

The test plan includes at least model and artifact, input and output length, concurrency or rate of arrival, request number, sampling and reasoning, setting, cache state, warm-up, measurement range, error handling and passed standards. The input length is calculated using a matching tokenizer; The number of characters cannot directly replace the number of tokens.

For example, the system's CPU real-time program fixes Qwen3-0.6B-Q8_0, 4 threads, pure CPU, two slots, c1/c2 for each of the 4 requests, output limit 32. The goal is to check the script links and observe the concurrency effect, with insufficient sample size to support stable P99 or production capacity conclusions. For the purposes of illustration, a teaching result should not be exaggerated as a server selection report.

Performance tasks can be fixed output lengths for comparison calculations, but must check for actual usage and end causes.`ignore_eos` This option is only used for service support and should indicate that it deviates from the natural end of business behavior. For quality tasks, the model should have the opportunity to give a complete answer, preserving the two types of results respectively.

## 2. Three measurement boundaries

|The border|Examples of tools|Questions Answered|
| --- | --- | --- |
|Engine execution|Llama-bench, vLLM offline bench|Basic performance of fixed computing workloads|
|Local Pipeline|OpenVINO GenAI and the like|Tokenization, generating and other pipeline expenses|
|HTTP client|Vllm bench service, EvalScope, self-writing client|Interface, queue, flow and complete request|

High TG, low HTTP throughput, not necessarily engine failure. HTTP adds templates, request scheduling, cache, queues and client charges; Workloads can also be quite different. First, write the boundaries on the front page and then explain the differences.

## 3. How are core indicators calculated?

If requested, the time to send is `t0 ` The first official letter arrived in `t1 ` The flow ends in `t2 ` The output tokens are: `N `. The TTFT client is about ` t1-t0 `E2E is the ` t2-t0 `It's in ` N>1 `The TPOT estimated at this boundary is: `(t2-t1)/(N-1)`. The end of the event and the transmission also contain a small amount of expense, which should indicate the method of measurement.

A stream event may carry multiple tokens at a time, and the event interval cannot be unconditionally considered a token-by-token ITL. This system allows small clients to record the first true and total time consumed, without falsifying the time for each token. Formal tools should check their ITL sampling and aggregation definitions.

The output throughput of the entire test window is the successful request of the total number of actual output tokens divided by the total time of the window. Request throughput is the successful completion of the countdown to window time. They differ from the average number of requests for each token/s. Failure, overtime and re-testing must be in the same order, otherwise rapid failure can also make the report look good.

The percentage must indicate the sample quantity, sample objects and algorithms. P99 for request-level TFT is not the same as P99 for all token spaces; The P99 calculated from 4 requests does not have a stable capacity meaning. Goodput further limits only requests that meet both quality and latency goals to include effective output for service acceptance testing.

## 4. Baseline of single instance engine prediction

Confirm that the same device does not run after another model competes:

```bash
llama-bench -m artifacts/gguf/Qwen3-0.6B-Q4_K_M.gguf \
  -ngl 0 -t 4 -p 64 -n 32 -r 3 -o json > engine.json
```

Save the program submission, model, summary, backend, thread, pp/tg length and repeat times. The actual result of the Q8 CPU of this system is that ppp64 is 319.08±17.26 tokens/s and tg32 is 69.88±0.22 tokens/s. They belong to different stages; It is not possible to convert the ppp and tg to the mean of the hydrogen model.

The first load, compilation, image capture and warm-up separated records from stable generation. On-device users are concerned about waiting for the first time to open, and service engineers are concerned about running for a long time, both of which are worth checking out.

## 5. Rethink the HTTP concurrency curve

First, complete the normal, flow and error API checks and then start load testing. Following example of vLLM service [Deployment chapters](../frameworks/vllm-service.md), keeping the same alias, port, and tokenizer:

```bash
for c in 1 2 4; do
  vllm bench serve \
    --backend openai-chat --base-url http://127.0.0.1:8001 \
    --endpoint /v1/chat/completions \
    --model Qwen3.6-35B-A3B-FP8 \
    --tokenizer /srv/models/Qwen3.6-35B-A3B-FP8 \
    --dataset-name random --random-input-len 2048 \
    --random-output-len 128 --num-prompts 100 \
    --max-concurrency "$c" --request-rate inf --seed 42 \
    --save-result --save-detailed --result-dir "results/c${c}"
done
```

This is a new test program, with no replacement running results. Starting with a small concurrency run, error or resources, stop expanding when pressure occurs, check logs and capacity. Each class uses the same sample quantity and task, and formal comparisons should be performed in multiple rounds, controlling the thermal state and observing the difference.

The model for vLLM bench is called a request, while a tokenizer path is used for constructing and counting, both of which are used differently. Save before using some version parameter `vllm bench serve --help `; The Old ` benchmark_serving.py`The script cannot be confused with the new CLI.

### Similar tests with EvalScope

Author oMLX Engineering uses EvalScope 1.7.0. The same tool can also measure the compatibility of HTTP services. Independent environment installed `evalscope [perf]==1.7.0` Afterwards, check out Perf help first; The following examples are still available:

```bash
evalscope perf \
  --parallel 1 2 4 --number 100 100 100 \
  --url http://127.0.0.1:8001/v1/chat/completions \
  --model Qwen3.6-35B-A3B-FP8 --api openai \
  --dataset random --min-prompt-length 2048 --max-prompt-length 2048 \
  --min-tokens 128 --max-tokens 128 \
  --tokenizer-path /srv/models/Qwen3.6-35B-A3B-FP8 --stream
```

The tool defaults the sample, output directory and parameter to the installed version and saves the complete configuration before running. Don't compare the default data sets and timing of the two tools with the better frameworks.

## 6. concurrency is a different experiment than the arrival rate

Fixed concurrency typically uses a closed loop: one request ends and another is added. Open arrival rates are expected to continue to increase when requests are sent at scheduled times. The access rate inf expression is initiated as soon as possible, and the client concurrency upper limit determines how it is actually sent; Without a limit, the requests form a burst.

The author's historical GB10 burst test of 200 requests had a mean TTFT of approximately 148 seconds, indicating substantial queueing under that workload. It does not represent the model's calculation of the first token for 148 seconds, nor can it estimate light load latency accordingly. A limited concurrency and a gradual rate of arrival should be added to see if the queue is stable.

## 7. How are the results of two sets of real concurrency analysed?

The system's CPU results are as follows: Each group of 4 requests, 128 output tokens, original file see [HTTP summary](../../../01-deployment-foundations/practice/first-service/results/2026-10-18-windows-cpu/http-summary.json):

|Client concurrency|HTTP is successful|Output throughput|Average TTFT|Average E2E|
| --- | --- | --- | --- | --- |
| 1 | 4/4 | 53.18token/s | 131.16ms | 601.56ms |
| 2 | 4/4 | 82.12token/s | 217.49ms | 778.99ms |

concurrency 2 increases total output, while average requests wait to change. That's why we need to draw the two curves of throughput and latency. The small sample illustrates only this observation, and cannot illustrate long-term stability or all concurrency trends.

OMLX history testing also appeared in the same direction: c1/c2/c4 output throughput 29.38/41.11/55.15token/s, average request latency of 7.582/10.257/13.459 seconds. However, the request numbers are 20/10/10, the cache and the original files are incomplete and can only be stored for historical reference and cannot be confused with the CPU data in the hardware rankings.

## 8. Observe resources and quality at the same time

NVIDIA can sample VRAM, computational utilization, temperature and power consumption, CPU and unified memory platforms to record RSS, available memory, swap, frequency and thermal status per second on an independent terminal. At the end of the process, the sampler stops its own start, marking the sampling frequency; A second sample could miss a very short peak.

Service indicators supplement activity request, queue request, KV occupancy, hit, robbery/recalculation, error and engine running status. When the client TFT is high and the computing utilization rate is low, the client, tokenizer, network and queue must also be excluded and the GPU budget cannot be increased immediately.

Quality check at least to confirm the complete answer, JSON legality and typical task. Increased speed, but output of miscodes, errors or only remaining reasoning, should be judged as quality not met. The performance report's passed criteria are determined by the project's objectives, not by the fastest results.

## 9. A reviewable directory of results

```text
results/run-id/
├── environment.json
├── model-manifest.json
├── server-command.txt
├── workload.json
├── requests.jsonl
├── responses.jsonl
├── resource.csv
├── server.log
├── summary.json
└── acceptance.md
```

The tool keeps the original files, summarized from the original data. Finally, write down the boundaries of workload, quality, latency, capacity, and failure, and recommend a workplace that meets the needs; Don't just write down how much zinc has increased.

## 10 oMLX full concurrency results and workpoint selection

OMLX was measured using DeepSeek-V4-Flash-4bit, EvalScope 1.7.0, input target 128, output upper limit 256. The device supports M3 Ultra, 512GB of unified memory; The performance page does not retain the full dependency lock and cache state, so when reading, look at the terms of service and the numbers simultaneously, without using the first token in the hot life to represent the first request.

### 10.1 Initial three grade results

|Client concurrency|Number of requests|Output throughput token/s|Average E2E seconds|P99 E2Es|Average TFT ms|Average TPOT ms|
| --- | --- | --- | --- | --- | --- | --- |
| 1 | 20 | 29.38 | 7.582 | 8.58 | 25.0 | 34.2 |
| 2 | 10 | 41.11 | 10.257 | 12.8 | 3.2 | 47.5 |
| 4 | 10 | 55.15 | 13.459 | 19.34 | 3.7 | 69.8 |

Aggregate output throughput at c4 was approximately 1.877 times c1, while mean request duration was approximately 1.775 times c1. It shows that throughput in this workload is a substitute for a single request. The TTFT for c2/c4 is significantly smaller than c1, and may be related to warm-up, cache, short input and run order, with insufficient data to prove why separately.

The original P99 is reserved for verification, but the 10/20 request is not stable enough to describe the tail. In order to judge the delivery capacity, the duration and number of requests should be increased, repeated repeats should be made, and the sample structure, cache and power consumption should be confirmed to be consistent.

### 10.2 A plan that is easier to test

Complete the model list, shortcuts with SSE checks, fixed EvalScope 1.7.0, model tokenizer and prompt. Then each file uses the same 100 entries to save different result directories; The following are the completed measurement schemes, the historical figures in the table are not the results of this new scheme:

```bash
evalscope perf \
  --parallel 1 2 4 --number 100 100 100 \
  --url http://127.0.0.1:8000/v1/chat/completions \
  --model DeepSeek-V4-Flash-4bit --api openai \
  --dataset random --min-prompt-length 128 --max-prompt-length 128 \
  --min-tokens 256 --max-tokens 256 \
  --tokenizer-path /srv/models/DeepSeek-V4-Flash-4bit --stream
```

Model ID should be `/v1/models ` It's ready. The tool's output saving options and the random data generation behaviour according to `evalscope perf --help` Verify and preserve the actual version and configuration of the analysis. Random length constraints are not natural business text; Quality issues are assessed separately.

Preview each cold input and then determine the fixed prefix heat input. If you want to compare concurrency, don't just replace model quantization, max_tokens, cache budget and template. After each round, save memory, swap, temperature and background tasks, explaining the error sample.

### 10.3 Selection of workplaces based on constraints

The average E2E of c1 has a higher reference value if the application is only one-to-one interaction; If more people are allowed to line up and give more importance to total output, the assessment of c2/c4 can be continued. The real decision is to first set the latency threshold and then calculate the completion of the threshold, rather than picking the biggest number of 55.15.

Assuming that the average E2E is not more than 11 seconds across the curriculum, table c1/c2 falls within the range and c4 is absent; Selecting c2 requires additional tail latency and quality checks. The average value passed does not mean that every user can do it in 11 seconds, which is why request-level data and P95/P99 are needed.

## 11 GB10's 200 request: how to unlock the waiting

Qwen FP8 historical service max-num-seqs4, and customers send 200 requests as soon as possible. The total time was 297.46 seconds; output was 25,600 tokens; output throughput was 86.06 tokens/s; average TFT was 148.43 seconds; P99 TTFT was 293.12 seconds. All of the service platforms have been successfully launched at the same time as the user platforms.

Time is divided into client preparation/connection, service receipt, queue, prefill, first formal transmission and subsequent decoding. The client can't directly name 148 seconds as the prefill time when it only knows the total TTFT.

### 11.1 Three-step differential computation slow and linear slow

The first request is to test the TTFT with the input once and keep the cold/hot twice. Then set the concurrency 1/2/4, observing the mean and tail; Finally, with limited access rates, there is a gradual increase in demand. At the same time, it records running, waiting, KV occupancy, preemption and device activity.

If a single request is fast, a sudden TTFT will follow a waiting-line growth, prioritizing the arrival rate and capacity; Check the input length, processor, tokenizer, compilation and prefill if there is no queue but the TTFT is still high. If the service indicator is normal and the client is slow, see network, connect repurposing and client scheduling.

### 11.2 Why can't you keep increasing the sequence of activities?

Seqs adds to the assembly an increase in active KV and computing burden, and may also increase batching utilization. After reaching the bandwidth or memory bottleneck, adding concurrency only slows down a single request or triggers a seizure. The curves of throughput, TTFT, E2E and resources should be drawn under fixed input and output to find areas that meet the threshold.

Activity sequence 4 does not only allow HTTP to receive 4 requests, 200 connections or 200 model sequences are not computed simultaneously. The model needs to be differentiated from the queue, denial and overtime strategies of the service and the gateway.

## 12. Resources Sampling should be aligned with the request window

There's only one `nvidia-smi` The picture cannot show the peak of the whole cycle, average power consumption and continuous frequency. The NVIDIA environment allows for fixed-cycle sampling on another terminal:

```bash
nvidia-smi \
  --query-gpu=timestamp,index,memory.used,utilization.gpu,temperature.gpu,power.draw,clocks.sm \
  --format=csv -l 1 > results/gpu-resource.csv
```

Certain fields are not supported on specific devices and should be kept N/A and modified with the corresponding platform tool, without filling in 0. Running ends and the sampler that starts itself stops collecting, saving the start and end times of load testing. Unified memory also records host MemAvailable, process RSS, swap and disk activity.

When the CPU, Intel NPU, and Mac use different platform tools, it is clear that the process, device, or entire machine is powered. The number of watts at different boundaries cannot be directly ranked. the energy consumption required to at least score at the same measurement boundary, divided by the effective output or completion of the task; In fact, instant peak times total time cannot replace real energy consumption.

One second of the sampling cycle may miss a short peak; Performance timing requires single-mode clocks, not dependency. The transversal log uses wall clocks in alignment, single request, single-tone clocks, both of which are used.

## How to put service delays and voice RTFs in the same report

TTF/TPOT for text tasks and RTF for voice answers different questions. The RTF of TTS is the time limit of a particular generation divided by the length of the audio, less than 1 which represents the average generation reaching playback; The first audio wait is decided by the compilation, the block and the buffer, and cannot be launched directly from the RTF.

Intel's Whisper Core RTF0.0387, with a first-round process of 8.97 seconds, is a prime example. The first time users start, they still have to wait for the initialization; The model's post-residency performance will also be measured differently. Kokoro CPU average RTF0.183 also cannot cover the RSS of about 3GiB over the original 2GiB target.

The report draws four parallel conclusions: whether functionality is complete, whether quality is correct, whether performance is met, whether resources are within budget. All NPU TTS speeds passed but quality failure, should be clearly stated as a whole failed; Keep these four checks distinct instead of reporting a vague “success.”

## 14. Write the next executable step from the form.

A useful report should be able to answer: which configuration is recommended now, how long input/output and workload is appropriate, how the boundaries are exceeded, what is the next best thing to try. For example, oMLX supplements the sample quantity concurrency curve, GB10 supplements the limited reach rate, AWQ supplements the quality return, and DFlash separates the configuration variables.

In this way, each subsequent experiment solves a clear problem. Do not constantly change tools, change data and run back enough results to increase the number of tests; The remaining risks are advanced around the preservation of recoverable raw materials.

## 2026 update: a repeatable optimization matrix

The shared [matrix script](../../../01-deployment-foundations/examples/run_optimization_matrix.py) fixes HTTP benchmark settings, alternates concurrency order, and saves each round. It does not start models or change GPU settings. By default it writes a plan only; execution requires a ready server and matching `vllm bench serve` client.

From the repository root, generate a plan:

```bash
python docs/01-deployment-foundations/examples/run_optimization_matrix.py \
  --model serving-lab --tokenizer /srv/models/example-model \
  --base-url http://127.0.0.1:8000 \
  --input-len 512 --output-len 256 --num-prompts 64 \
  --concurrency 1 2 4 8 --repeats 3 \
  --output results/baseline-plan
```

Inspect the 12 commands, IDs, tokenizer, counts, and sampling in manifest.json. `status=plan_only` means no requests were sent. Choose a new directory and add execute:

```bash
python docs/01-deployment-foundations/examples/run_optimization_matrix.py \
  --model serving-lab --tokenizer /srv/models/example-model \
  --base-url http://127.0.0.1:8000 \
  --input-len 512 --output-len 256 --num-prompts 64 \
  --concurrency 1 2 4 8 --repeats 3 \
  --output results/baseline-run --execute
```

The script verifies required CLI flags and saves help/version information. Each round writes benchmark.log and result.json. Failed commands, missing or incomplete result files, and failed requests stop execution and mark the manifest failed. An exit code of zero still requires complete, valid results.

Sampling is temperature 0, fixed seed, and ignore_eos for a controlled output load. This is a performance workload; quality needs natural termination and task evaluation. Confirm actual lengths from results. A seed compares inputs only with the same generator, tokenizer, and version; the configuration hash is not a prompt-file hash. Use a fixed public custom dataset for strict byte-identical requests.

The script does not reset caches. Repeated seeds with APC can produce warm-prefix runs. Explicitly disable prefix reuse for isolated engine comparisons; define separate cold/warm groups and counters for cache experiments.

| Workload | Illustrative lengths | Observe |
| --- | --- | --- |
| Decode-heavy | 512 input, 1024 output | TPOT, accepted length, bandwidth, draft cost |
| Prefill-heavy | 8192 input, 128 output | TTFT, compute, workspace, graphs |
| Mixed service | Fixed short/long request set, increasing arrival rate | Queues, ITL tails, preemption, goodput |

Check that input plus output fits the service limit. A finite request-rate introduces controlled arrivals while retaining the client concurrency cap. Concurrency and actual arrival rate are different measurements.

Measure baseline, then candidates with the same settings. The script alternates within each concurrency sweep; alternate A/B or B/A across separately started configurations too. Preserve actual tokens, duration, tails, and failures; verify total_output_tokens/duration.

Collect resources and quality separately. Typical latency goodput is qualifying requests/s. To require quality as well, associate per-request quality results and state whether the resulting unit is requests/s or tokens/s.

Topics: [MTP](speculative-decoding.md) · [DSpark](dspark.md) · [Quantization](../models/quantization.md) · [PD](disaggregated-serving.md).
