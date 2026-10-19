# In addition to this, it is important to ensure that the quality of the product is consistent with the quality of the product.

[简体中文](../../01-deployment-foundations/appendices/benchmark-tools.md) | **English**

[Index of engineering examples](README.md) · [General directory of knowledge systems](../SUMMARY.md)

Technical labels: `engine / HTTP / fixed load / raw results`

## Engineering boundaries

|Tools|Objects of measurement|Must be fixed|
| --- | --- | --- |
| llama-bench |Engine pp/tg|build, model, backend, layer number, thread, pp/tg and repeat number|
| vLLM bench serve |HTTP requests from the server|Tokenizer, endpoint, input output, concurrency/arrival rate, cache and actual token|
| EvalScope |Interface workload and group reporting|API types, data sets, numbers, parallels, samples and raw details|
| Locust/wrk/hey |HTTP pressures and application processes|Setting the SSE/Ending semantics; Normal req/s does not replace tokens/s|

The following full author's tool description, installation, command and output fields are preserved; The commands for the current device and framework still need to be fixed to the actual version. Unified statistical definition and error sample see [Topics of performance testing](../chapters/performance/benchmarking.md).

## Agreement on the use of complete technical records

The following technical correctness, commands, tables, logs, failures and subsequent experiments of the relevant FlowUs articles are retained directly, without abbreviating the original process. private paths, nodes, authentication and sanitization of attached addresses; `<NODE_IP>` For example, the placeholder needs to be filled in the current environment. The original suggestion or prediction is still a suggestion or prediction. The above execution sequence and technical revisions are used to explain conflicts in historical records, and historical GPU/NPU experiments have not been repeated in this round.

## R48 · llama.cpp with vLLM inference performance assessment tool 2026 edition

[Original note: image.png; [Unpublished transcript]

#### 1. Overall selection

|The scene|Recommended tools|Notes|
| --- | --- | --- |
|Llama.cpp Local nudity performance| llama-bench |Measure prompt processing/token generation, suitable for viewing GGUF at the base speed of the CPU/GPU/Metal/CUDA/ROCm backend|
|llama.cpp perplexity / preliminary quality checks| llama-perplexity |PPL with text aggregate, suitable for quantization model quality contrast|
|llama.cpp HTTP API load test|EvalScope / vLLM bench serve / self-written wrk script|llama-server supports OpenAI-compatible API, which can be used as load testing for services|
|VLLM online service load testing| vllm bench serve |Focus on TTFT, TPOT, ITL, E2E latency, throughput, and concurrency|
|VLLM offline throughput testing| vllm bench throughput |Not going to HTTP, measuring engine offline bulk inference capabilities|
|VLLM single batch latency testing| vllm bench latency |Base latency under fixed batch / input output length|
|Production load testing report| EvalScope / GuideLLM / Prometheus + Grafana |It's better suited for reporting, concurrency, curve, and SLA analysis.|

The official vLLM is currently putting the benchmark unified into the CLI: `vllm bench latency ` It's a bit of a bit of latency.`vllm bench serve ` for online service throughput; `vllm bench throughput ` It's used for offline throughput. Use bench commands to install `vllm [bench]`.([vLLM](https://docs.vllm.ai/en/latest/cli/))

---

#### How to evaluate llama.cpp 2.

##### 2.1 llama.cpp self-contained tools

Now write the llama.cpp review, and you can't say that the llama.cpp doesn't come with the benchmark tool itself. It's more accurate to say:

**llama.cpp is a basic performance testing tool, but for API load testing, concurrency load testing, and report analysis, it can be combined with EvalScope.**

The official llama.cpp README lists `llama-bench ` It is used to benchmark inference performance. It's also listed `llama-perplexity` It is used to measure perplexity and other quality indicators. ([GitHub](https://github.com/ggml-org/llama.cpp))

##### 2.2 Local performance testing: `llama-bench`

```text
# 基础测试
llama-bench -m /path/to/model.gguf
```

There are two types of core indicators that are commonly seen in output:

|Indicators|Meaning|
| --- | --- |
| pp512 |prompt processing, prompt word pre-filled phase speed|
| tg128 |token generation, decoding phase speed|
| t/s |Tokens/s, throughput speed|
| backend |The backend is currently used, such as CUDA, Metal, BLAS, ROCm, etc.|

Example:

```text
llama-bench \
  -m /models/Qwen3-32B-Q5_K_M.gguf \
  -ngl 99 \
  -t 16
```

Notes:

|Parameters|The role|
| --- | --- |
| -m |GGUF model path|
| -ngl |The number of layers of GPU offload, often used as 99, indicates the maximum offload.|
| -t |Number of CPU threads|
| -p |Prompt token number, partial version supported|
| -n |generation token number, partial version supported|

---

##### 2.3 llama.cpp service load testing: `llama-server + EvalScope`

It's called llama.cpp `llama-server ` It is an OpenAI API-compatible HTTP server that supports `/v1/chat/completions` It also supports parallelism, decoding, multi-user, continuous batching, OpenAI-compatible responses/embeddings, function calling, speculative decoding, and Prometheus metrics. ([GitHub](https://github.com/ggml-org/llama.cpp))

Start the service:

```text
llama-server \
  -m /models/Qwen3-32B-Q5_K_M.gguf \
  --host 0.0.0.0 \
  --port 8080 \
  -c 32768 \
  -np 4 \
  -ngl 99 \
  --metrics
```

Parameters are explained:

|Parameters|Meaning|
| --- | --- |
| -c 32768 |Length of context|
| -np 4 |Parallelism slot number, affecting the number of simultaneous processing requests|
| -ngl 99 |Try to offload the model layer to the GPU as much as possible.|
| --metrics |Open the Prometheus / Metrics indicator|

Open up `--metrics` Later, the llama.cpp server supports Prometheus compatibility metrics such as prompt tokens, generation tokens, average prompt throughput, average generation throughput, number of requests in processing, sequence request numbers. ([GitHub](https://github.com/ggml-org/llama.cpp/blob/master/tools/server/README.md))

---

#### 3. EvalScope: General API load testing and quality assessment

EvalScope is now better positioned as:

**General large language model assessment framework, which can both model capability assessment and OpenAI API compatibility service load testing.**

EvalScope officially states that it supports model capability assessment, inference performance load testing and result visualization, and supports model types such as LLM, VLM, Embedding, Reranker, AIGC. Its performance test indicators include TTFT, TPOT, etc. ([GitHub](https://github.com/modelscope/evalscope))

Installed:

```text
pip install evalscope[perf] -U
```

The official stress test documentation states that EvalScope supports OpenAI API formatting services and multiple data set formats; `parallel ` This is the number of concurrency requests.`number ` This is the total number of requests under each concurrency rating.`tokenizer-path` It is important for calculating token numbers, especially when using random dataset. ([EvalScope](https://evalscope.readthedocs.io/en/latest/user_guides/stress_test/quick_start.html))

##### 3.1 load testing llama.cpp OpenAI API

```text
evalscope perf \
  --parallel 1 2 4 \
  --number 3 6 12 \
  --url http://127.0.0.1:8080/v1/chat/completions \
  --model qwen3-32b-q5 \
  --api openai \
  --dataset random \
  --min-prompt-length 1024 \
  --max-prompt-length 1024 \
  --min-tokens 512 \
  --max-tokens 512 \
  --tokenizer-path /models/Qwen3-32B-tokenizer \
  --extra-args '{"ignore_eos": true}' \
  --stream
```

You used to be.`speed_benchmark ` Recommended to change `random `. The new version of EvalScope is used in the official quick start.`--dataset random ` and passed `min/max prompt length ` and `min/max tokens` Fixed input and output length. ([EvalScope](https://evalscope.readthedocs.io/en/latest/user_guides/stress_test/quick_start.html))

##### 3.2 load testing vLLM OpenAI API

```text
evalscope perf \
  --parallel 1 10 50 100 \
  --number 10 100 500 1000 \
  --url http://127.0.0.1:8000/v1/chat/completions \
  --model qwen3-32b \
  --api openai \
  --dataset random \
  --min-prompt-length 1024 \
  --max-prompt-length 1024 \
  --min-tokens 512 \
  --max-tokens 512 \
  --tokenizer-path /models/Qwen3-32B \
  --extra-args '{"ignore_eos": true}' \
  --stream
```

EvalScope output encounters include total/success/failed, request throughput, avg latency, TTFT, TPOT, ITL, output throughput, total throughput, and other indicators, which also output different percentage results. ([EvalScope](https://evalscope.readthedocs.io/en/latest/user_guides/stress_test/quick_start.html))

---

#### 4. vLLM official benchmark: New version writing

What did you write last year?`benchmark_serving.py ` and `benchmark_throughput.py` It is now suggested to change to:

```text
vllm bench serve
vllm bench throughput
vllm bench latency
```

VLLM's `benchmarks/README.md ` It has been pointed out that the original benchmark script directory now mainly refers to the Benchmark CLI documentation; `benchmark_throughput.py ` The document itself is also directly printed deprecated and prompted to be used `vllm bench throughput`.([GitHub](https://github.com/vllm-project/vllm/blob/main/benchmarks/README.md))

---

##### 4.1 Load testing of online services: `vllm bench serve`

VLLM OpenAI API services that are already in place for testing.

Start with the model:

```text
vllm serve /models/Qwen3-32B \
  --host 0.0.0.0 \
  --port 8000 \
  --served-model-name qwen3-32b \
  --tensor-parallel-size 1 \
  --gpu-memory-utilization 0.9 \
  --max-model-len 32768
```

Another load testing:

```text
vllm bench serve \
  --backend openai-chat \
  --host 127.0.0.1 \
  --port 8000 \
  --endpoint /v1/chat/completions \
  --model qwen3-32b \
  --dataset-name random \
  --num-prompts 100 \
  --max-concurrency 8 \
  --request-rate inf \
  --random-input-len 1024 \
  --random-output-len 512 \
  --ignore-eos \
  --percentile-metrics ttft,tpot,itl,e2el \
  --metric-percentiles 50,90,95,99 \
  --save-result \
  --save-detailed
```

Key parameters:

|Parameters|Meaning|
| --- | --- |
| --backend openai-chat |Use the OpenAI Chat Completions protocol|
| --endpoint /v1/chat/completions |For the vLLM OpenAI API|
| --model |It must be aligned with --served-model-name|
| --num-prompts |Total request number|
| --max-concurrency |Maximum number of concurrency|
| --request-rate |If the request reaches the speed, the inf indicates that you're going to start by hitting everything.|
| --random-input-len |Random data set input length|
| --random-output-len |Random data set output length|
| --ignore-eos |Ignore EOS, generate as much as possible to the specified length|
| --percentile-metrics |Compute percentiles for TTFT, TPOT, ITL, E2E, and related metrics|
| --metric-percentiles |Statistics P50/P90/P95/P99|
| --save-detailed |Save the detailed results of each request|

`vllm bench serve ` The document clearly states: `--max-concurrency ` It's the largest concurrency control.`--request-rate ` Control the speed at which the request is sent; When the service is not processed, the actual request rate may be lower than the set value. It also supports `ttft `, ` tpot `, ` itl `, ` e2el`It is also used to measure the percentage of the load, and ramp-up load testing. ([vLLM](https://docs.vllm.ai/en/stable/cli/bench/serve/))

---

##### 4.2 Offline throughput testing: `vllm bench throughput`

It is suitable for non-HTTP, directly measuring the maximum throughput of the vLLM engine.

```text
vllm bench throughput \
  --model /models/Qwen3-32B \
  --dataset-name random \
  --num-prompts 100 \
  --input-len 1024 \
  --output-len 512 \
  --tensor-parallel-size 1 \
  --gpu-memory-utilization 0.9 \
  --max-model-len 32768
```

The following is an overview of some of the scenarios:

|The scene|Is it appropriate?|
| --- | --- |
|See GPU theoretical inference throughput|It is appropriate.|
|Compared to different quantization precision|It is appropriate.|
|Compared to the TP/PP parameter|It is appropriate.|
|Simulating real HTTP user concurrency|Unsuitable|
|TTFT/network latency measurement|Unsuitable|

---

##### 4.3 Single batch latency testing: `vllm bench latency`

```text
vllm bench latency \
  --model /models/Qwen3-32B \
  --input-len 1024 \
  --output-len 128 \
  --tensor-parallel-size 1 \
  --gpu-memory-utilization 0.9
```

Useful for answering questions such as:

|Issue|What is it for?|
| --- | --- |
|How low is the single-request latency?| vllm bench latency |
|What is the service concurrency capability?| vllm bench serve |
|How many tokens/s do you have offline?| vllm bench throughput |
|Are the real production APIs unstable?| EvalScope + Prometheus + Grafana |

---

#### 5. Explanation of the core indicators

|Indicators|Chinese Explanation|What do you think?|
| --- | --- | --- |
| TTFT |Time to First Token, the first token latency|The lower the user response rate, the better.|
| TPOT |Time Per Output Token, the average time spent on each output token, excluding the first token|The lower the decoding speed, the better the core indicator.|
| ITL |Inter-token latency, token intervals|If the flow output is smooth|
| E2EL |End-to-End Latency, end to end total latency|One request, full time|
| Req Throughput |Requests/s, complete the number of requests per second|Service request throughput|
| Output Throughput |output tok/s, generating a number of tokens per second|decoding throughput|
| Total Throughput | input + output tok/s |Total processing throughput, including prefill|
| Concurrency |concurrency request number|How many requests are processed at the same time|
| Request Rate |Request to reach speed|Simulating user traffic to speed|
| Goodput |Meeting effective throughput of SLA|Production environment is more meaningful|

The EvalScope documentation has clear indicator explanations for TTFT, TPOT, ITL, Output Throughput, Total Throughput; Where TTFT is the average time from sending the request to receiving the first response token, TTPOT is the average generation time of each output token after excluding the first token, and ITL is the average interval between the tokens. ([EvalScope](https://evalscope.readthedocs.io/en/latest/user_guides/stress_test/quick_start.html))

---

#### 6. Recommended standard testing process

##### Group one: single request basic speed

Objective: See how fast the model generates base on the current hardware.

```text
vllm bench serve \
  --backend openai-chat \
  --host 127.0.0.1 \
  --port 8000 \
  --endpoint /v1/chat/completions \
  --model qwen3-32b \
  --dataset-name random \
  --num-prompts 5 \
  --max-concurrency 1 \
  --random-input-len 1024 \
  --random-output-len 512 \
  --ignore-eos
```

Focus on:

```Markdown
Mean TTFT
Mean TPOT
Output token throughput
Total token throughput
```

---

##### Second group: concurrency curve testing

Objectives: See if concurrency increases from small to large, throughput increases, latency explodes.

```text
for c in 1 2 4 8 16 32; do
  vllm bench serve \
    --backend openai-chat \
    --host 127.0.0.1 \
    --port 8000 \
    --endpoint /v1/chat/completions \
    --model qwen3-32b \
    --dataset-name random \
    --num-prompts 100 \
    --max-concurrency $c \
    --random-input-len 1024 \
    --random-output-len 512 \
    --ignore-eos \
    --save-result \
    --result-dir ./bench-results \
    --metadata concurrency=$c
done
```

How to judge:

|The phenomenon|Notes|
| --- | --- |
|The concurrency is up, the output tok/s are clearly up.|Batching is effective|
|Concurrency increases, TTFT increases slightly|It's normal.|
|Concurrency increases, TTFT/E2E riots|reaching the bottle of service|
|Failed requests increase|Context, VRAM, service errors or overtime|
|Output tok/s not upgraded|GPUs or scheduling are full.|

---

##### Group 3: Long Context Testing

Objective: Verify the stability in the context of 32K / 64K / 128K.

```text
vllm bench serve \
  --backend openai-chat \
  --host 127.0.0.1 \
  --port 8000 \
  --endpoint /v1/chat/completions \
  --model qwen3-32b \
  --dataset-name random \
  --num-prompts 20 \
  --max-concurrency 2 \
  --random-input-len 32768 \
  --random-output-len 512 \
  --ignore-eos \
  --percentile-metrics ttft,tpot,itl,e2el \
  --metric-percentiles 50,90,95,99
```

In the long context, emphasize:

|Indicators|Focus|
| --- | --- |
| TTFT |Prefill pressure will increase significantly.|
|GPU VRAM|KV Cache has exploded.|
| failed requests |Is it more than max_model_len|
| total throughput |Long prompt below the prefill performance|
| output throughput |decode is affected|

---

#### 7. llama.cpp vs vLLM load testing

|Comparisons| llama.cpp | vLLM |
| --- | --- | --- |
|The main model format| GGUF |HF Transformers / safetensors / quantization format|
|Typical deployment scenarios|On-device, local, small server, CPU/GPU mix|High concurrency, multi-GPU inference|
|Bring your own benchmark| llama-bench,llama-perplexity | vllm bench latency/serve/throughput |
|API services| llama-server | vllm serve |
|Compatibility with OpenAI API|Support|Support|
|Competence|Support for -np, parallel decoding, continuous batching|Strong, continuous batching / PagedAttention|
|Monitoring|-- metrics exposure / metrics| /metrics + Prometheus/Grafana |
|What's best to measure?|GGUF quantization speed, on-device inference speed|TFT, TPOT, concurrency curves|
|Recommended load testing tools| llama-bench + EvalScope | vllm bench serve + EvalScope |

---

#### 8. The final recommendation

Now this part can be said as follows:

**If it was llama.cpp, I'd use it first.`llama-bench ` Measuring the basic inference speed of the local GGUF model, focusing on prompt processing and token generation tokens/s; If the model is `llama-server` exposes an OpenAI API, I then use EvalScope for concurrent load tests, tracking TTFT, TPOT, ITL, request success rate, and throughput curves.**

**If it's vLLM, I prefer the official new version.`vllm bench ` The order.`vllm bench serve ` to measure online serving concurrency; `vllm bench throughput ` It's used to measure the offline limit throughput.`vllm bench latency` It's used to measure the latency of a single batch. In the production environment, I work with Prometheus/Grafana to look at KV Cache, request queues, GPU utilization rates, and service end indicators, avoiding seeing only one token/s.**

## R49 · large language model performance Assessment framework set

The following are the two categories of performance fuels: **Inference services performance load testing**, measuring throughput, latency, concurrency, and TTFT/ITL/TPOT; and ** Ability assessment of models**, assessing MMLU, C-Eval, GSM8K, RAG, agent, multimodal, and related task quality.

#### 1. vLLM related load testing tools

|Tools|Suitable for the Scenes|Key indicators/abilities|Notes|
| --- | --- | --- | --- |
| vllm bench serve |Online service load testing, press vLLM OpenAI-compatible API|In addition, the request throughput, output token throughput, total token throughput, TTFT, TPOT, ITL, P99, and so on.|The old benchmark_serving.py has been discontinued and the official suggestion is to replace it with vllm bench serve. (GitHub)|
| vllm bench throughput |Offline batch inference throughput testing| requests/s,total tokens/s,output tokens/s |It is suitable for comparing model, batch, parallelism, strategy, quantization, and spec decoding effects on offline throughput. (vLLM)|
| vllm bench latency |Single model/local inference latency testing|Latency class indicators|The current CLI clearly provides latency/serve/throughput for three types of bench inputs. (GitHub)|
| vLLM specialized benchmarks |Features of load testing|Structured output, prefix caching, long-document QA, multimodal tasks, embeddings, rerankers, etc.|It is used to verify the switch or return of a particular vLLM functionality, rather than a complete production flow simulation. (vLLM)|
| GuideLLM |Production-level vLLM service load testing|Workload patterns, real-time progress, reporting, latency distribution, throughput behaviour|The official vLLM documentation clearly states: vLLM is a benchmark-specific bias/return test; Producing vLLM server load testing GuideLLM is recommended because of the greater flexibility of data set loads, request formats, workload patterns. (vLLM)|

`vllm bench serve` The most commonly used form is:

```text
vllm serve Qwen/Qwen2.5-7B-Instruct --host 0.0.0.0 --port 8000

vllm bench serve \
  --backend vllm \
  --model Qwen/Qwen2.5-7B-Instruct \
  --endpoint /v1/chat/completions \
  --dataset-name sharegpt \
  --dataset-path /path/to/sharegpt.json \
  --num-prompts 1000 \
  --request-rate inf \
  --max-concurrency 64 \
  --save-result
```

Focus on load testing `--request-rate `, `--burstiness `, `--max-concurrency ` The official explanation: `request-rate=inf ` For maximum throughput, limited RPS is more like real flow; `burstiness ` It is possible to simulate sudden or uniform flow; `max-concurrency` It is used to simulate the concurrency ceiling of a balanced transit/workload. ([vLLM](https://docs.vllm.ai/en/latest/benchmarking/cli/))

#### 2. General open source inference performance load testing framework

|The Framework|Types|Suitable for use|
| --- | --- | --- |
| GuideLLM |LLM services performance load testing|Recommended for the production of vLLM service capacity assessment, concurrency scanning, reporting output; It supports rate-based load, HTML/JSON/CSV reporting. (GitHub)|
| NVIDIA GenAI-Perf |Inference services benchmark|It supports LLM, Multimodal, Embedding, Reranking, LoRA, and so on. In addition, it is also used to measure TTFT, ITL, TPS, and RPS. It supports OpenAI API specification services, so vLLM endpoints can be compressed. (NVIDIA Docs)|
| Ray LLMPerf |LLM API load testing|Passed concurrency request measures inter-token latency and generation throughput, as well as a simple correctness test. It is suitable for comparing different API/service endpoints horizontally. (GitHub)|
| Kubernetes SIGs Inference Perf |Production/K8s inference load testing|GenAI inference deployment, model-server agnostic, is suitable for apples-to-apples comparison in different backend K8s environments. (GitHub)|
| EvalScope |Rating + load testing integrated|The framework for the ModelScope community, which supports both general capacity assessment, multi-model comparison, and stress testing; It covers LLM, VLM, Embedding, Reranker, AIGC and so on. (GitHub)|

#### 3. Open source model Ability assessment framework

|The Framework|What is more appropriate?|Features|
| --- | --- | --- |
| lm-evaluation-harness |Academic/general NLP benchmark|EleutherAI maintains and uniquely evaluates a large number of generated language model tasks, supports 60+ standard academic benchmarks, vLLM, Transformers, API models, and is also used by Hugging Face Open LLM Leaderboard. (GitHub)|
| OpenCompass |Chinese + General large language model|It is used nationally to emphasize fair and comprehensive assessments. It supports rich data sets, models, lists, and is suitable for C-Eval, CMMLU, MMLU, mathematics, code, long context, and Chinese tasks. (GitHub)|
| EvalScope |One-stop model evaluation|It supports general capabilities, multi-model comparison, and load testing. Built-in MMLU, C-Eval, GSM8K, and integrated with the backend of OpenCompass, VLMEvalKit, and RAGEval. (GitHub)|
| HELM |Reproducibility, transparency and overall evaluation|The Stanford CRFM open source framework focuses on holistic evaluation, covers dimensions such as efficiency, bias, toxicity, and has a leaderboard and Web UI; However, the project states that it will enter maintenance mode from 2026-06-01. (GitHub)|
| LightEval |Hugging Face ecological assessment|The HF Leaderboard/Evals team maintains, with an emphasis on fast, flexible, multi-backend assessment, and has continued to adapt to vLLM in the near future. (GitHub)|
| VLMEvalKit |Multimodal/VLM ratings|The OpenCompass series is a multi-modal large language model, one-key assessment tool, suitable for tables, multi-modal benchmarks. (GitHub)|
| DeepEval |Application of the LLM single-test/return evaluation|An LLM app testing framework similar to pytest is suitable for RAG, Agent, chatbot, application level indicators and CI regression. (GitHub)|
| Ragas |RAG appraisal|Focused on RAG/LLM application assessment, providing metrics, synthetic test sets and development/production quality monitoring workflows. (ragas.io)|

#### Suggestions for selection

Doing it **VLLM service pre-connection capacity assessment** Priority: `GuideLLM ` or `vllm bench serve`. The former is more suitable for production flow patterns and reports, while the latter is lighter, closer to vLLM itself.

Doing it **Model / Deployment Parameters** Used: `vllm bench throughput ` To compare offline throughput, use `vllm bench serve` Or GenAI-Perf compares the online TTFT, ITL, P99, tokens/s, and concurrency limits.

Doing it **Chinese/Common Capacity Assessment** It is the first of its kind in the world. English/academic benchmarks aligned with lm-evaluation-harness; It is a multi-mode application of VLMEvalKit. RAG/Agent app quality with Ragas or DeepEval.

large language model quality Assessment framework set ((private page links are not public))
