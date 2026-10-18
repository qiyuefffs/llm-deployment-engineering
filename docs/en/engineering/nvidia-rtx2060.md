# NVIDIA RTX 2060 12GB: CUDA mixed offloading with Qwen3 quantization inference

[简体中文](../../01-deployment-foundations/engineering/nvidia-rtx2060.md) | **English**

[Index of engineering examples](README.md) · [General directory of knowledge systems](../SUMMARY.md)

Technical labels: `CUDA / GGUF / CPU-GPU offload`

## Engineering configuration

|Projects|Configuration|
| --- | --- |
| GPU / RAM |RTX 2060 12GB / 32GB host memory|
|Model|Qwen3-30B-A3B Q6; 32B Q5 as a capacity control|
|Implementing the Path|GGUF → llama.cpp CUDA → Partial layer offloading → OpenAI API|
|Major restrictions|Weights can't fit all of 12GB; CPU end weights, KV and operating system competition 32GB RAM|
|Primary measurements|Q6 single input of 9 tokens, output of 182 tokens; Prefill about 9.04 tokens/s, decode about 5.26 tokens/s|

## Deployment of adaptation processes

1. `nvidia-smi ` Verify the driver with empty VRAM; `free -h `, ` vmstat 1`Record RAM and swap. The card is Turing and cannot be used under the new card assumption of native FP8 matrix computation.
2. According to [CUDA building instructions](../chapters/frameworks/llama-cpp.md) Fixed source code, built `llama-server/llama-bench/llama-cli `. RTX 2060 is available `-DCMAKE_CUDA_ARCHITECTURES=75`; check the actual logs.
3. Prepare the complete GGUF with SHA256.. Start with `-ngl 0 -c 2048 -np 1 ` Verify the CPU load, then increase the offloading at levels 16 and 24 until sufficient device workspace is retained; Don't take it `-ngl 99` As a 12GB card, the configuration must be available.
4. Each file runs under the same prompt, output budget, sampling and thread, and is saved.`load time/prompt eval/eval/total` and CPU/GPU buffers. The model separates loading time from heat generation.
5. Determine the configuration that does not cause swap vibration, start the HTTP service, check model lists, short questions, long questions, SSE, and cancel. The original configuration contains parallel 8, which can only describe the configuration value; Activity concurrency capabilities require additional load testing.

```bash
./build-cuda/bin/llama-server \
  -m /srv/models/Qwen3-30B-A3B-Q6_K.gguf \
  --host 127.0.0.1 --port 8080 -c 2048 -np 1 -ngl 16
```

This is a small budget entry for re-validation, not the original order for the following historical results. The final offloading number is determined by the original record and the device measured.

## Accelerated optimization and acceptance testing

|Experiments|Fixed conditions|Check results|
| --- | --- | --- |
|Add the GPU offloading layer|Same artifact, ctx, prompt, output, and thread count|Decode, PCIe transmission, CPU workload, VRAM surplus|
| Q6→Q5/Q4 |the same model and mission; Artifact changes recorded separately|Memory decreases, speed, response quality; Can't directly equate to lossless|
|Adjusting the number of threads|Offloading and Input|CPU end time, context switching; The more the threads, the faster they don't have to be|
|slot 1→2|The same length as the total sample|Total throughput, single request TPOT, p95, failure rate and RAM peak|

It retains an observation of about 5.26 tokens/s and is not packaged as a stable HTTP throughput. Qualified configuration: The target task must be completed, and the RAM/swap, VRAM and tail latency must meet the predefined budget. The full original parameters, timing and resources are recorded below.

## Agreement on the use of complete technical records

The following technical correctness, commands, tables, logs, failures and subsequent experiments of the relevant FlowUs articles are retained directly, without abbreviating the original process. private paths, nodes, authentication and sanitization of attached addresses; `<NODE_IP>` For example, the placeholder needs to be filled in the current environment. The original suggestion or prediction is still a suggestion or prediction. The above execution sequence and technical revisions are used to explain conflicts in historical records, and historical GPU/NPU experiments have not been repeated in this round.

## R01 · nvidai-llamacpp-qwen3:30-a3b-q6 test records

Hardware configuration

CPU： 12th Gen Intel(R) Core(TM) i5-12400F

Memory: 32GB

GPU:  **RTX 2060 12GB**

Software environment
Cuda Accelerated Framework

Inference engine: llama.cpp (CUDA build)

How to infer: CPU+GPU mixed inference

model :qwen3:30b-a3b

Format and precision: Qwen3-30B-A3B-Q6_K.gguf

The inference command:

```text
llama-server.exe -m D:\xiangmu\llamacpp\model\dir\Qwen3-30B-A3B-Q6_K.gguf --top-k 1 -c 2048 -n 1000 -ngld 99 -ngl 99 --mlock --parallel 8

```

Memory occupancy: 82 to 100%

Model Conventional Loading Memory occupancy: 76%

Disc exchange: 100%

[Original note image: image.png; [Unpublished transcript]

Ask about the test data:

```text
1. 简单提问：“你好”

性能占比：
CPU: 21%
memory: 85%~89%
GPU: 98%~100%


```

[Original note image: image.png; [Unpublished transcript]

The token data:

|Indicators|Values|Notes|
| --- | --- | --- |
| Prompt Eval Time | 995.30 ms |Time for the first response prompt|
| Tokens (Prompt) | 9 tokens |Number of words entered|
| Time per Token (Prompt) | 110.59 ms/token |Average time spent processing each word|
| Tokens per Second (Prompt) | 9.04 tokens/sec |Model number of words processed per second|
| Eval Time | 34,618.63 ms |Overall estimate of the time of inference|
| Tokens (Eval) | 182 tokens |The number of words processed during inference|
| Time per Token (Eval) | 190.21 ms/token |Average time spent processing each word|
| Tokens per Second (Eval) | 5.26 tokens/sec |Model number of words processed per second|
| Total Time | 35,613.93 ms |Total processing time, including prompt and evaluation time|
| Tokens (Total) | 191 tokens |Total number of words processed, including all the words in the prompt and evaluation phases|
| Slots Status | All slots are idle |Computational resources (slots) are empty and there are currently no tasks in the works.|

[Original note image: image.png; [Unpublished transcript]

## R02 · nvidai-llamacpp-qwen3:30-a3b-q6 benchmark performance Test records

Hardware configuration

CPU： 12th Gen Intel(R) Core(TM) i5-12400F

Memory: 32GB

GPU:  **RTX 2060 12GB**

Software environment
Cuda Accelerated Framework

Inference engine: llama.cpp (CUDA build)

How to infer: CPU+GPU mixed inference

model :qwen3:30b-a3b

Format and precision: Qwen3-30B-A3B-Q6_K.gguf

The inference command:

```text
llama-server.exe -m D:\xiangmu\model\Qwen3-30B-A3B-Q6_K\Qwen3-30B-A3B-Q6_K.gguf --top-k 1 -c 2048 -n 1000 --tensor-split 0.9,0.1 -ngl 99 --mlock --parallel 8

```

Memory occupancy: 82 to 100%

Model Conventional Loading Memory: 69%

Disc exchange: 100%

[Original note image: image.png; [Unpublished transcript]

benchmark test records

Evalscope testing tool - performance testing

The test command:

```text
evalscope perf --url http://127.0.0.1:8080/v1/chat/completions --model Qwen3-30B-A3B-Q6_K --api openai --parallel 8 --number 2 --stream
```

[Original note image: image.png; [Unpublished transcript]

[Original note image: image.png; [Unpublished transcript]

Testing logs

[benchmark.log]

## R03 · nvidai-llamacpp-qwen3:32B-q5 benchmark performance Test records

Hardware configuration

CPU： 12th Gen Intel(R) Core(TM) i5-12400F

Memory: 32GB

GPU:  **RTX 2060 12GB**

Software environment
Cuda Accelerated Framework

Inference engine: llama.cpp (CUDA build)

How to infer: CPU+GPU mixed inference

model : [qwen3:30b-a3b](qwen3:32B-q5)

Format and precision: Qwen3-32B-Q5_K_M.gguf

The inference command:

```text
llama-server.exe -m D:\xiangmu\model\Qwen3-32B-Q5_K_M\Qwen3-32B-Q5_K_M.gguf --top-k 1 -c 2048 -n 1000 --tensor-split 0.6,0.4 -ngl 99 --mlock --parallel 4
```

Memory occupancy: 82 to 100%

Model Conventional Loading Memory occupancy: 59%

Disc exchange: 69 to 79%

[Original note image: image.png; [Unpublished transcript]

benchmark test records

Evalscope testing tool - performance testing

The test command:

```text
evalscope perf --url http://127.0.0.1:8080/v1/chat/completions --model Qwen3-32B-Q5_K_M --api openai --parallel 1 --number 5 --max-tokens 200 --stream
```

[Original note image: image.png; [Unpublished transcript]

[Original note image: image.png; [Unpublished transcript]

Testing logs

[benchmark.log]
