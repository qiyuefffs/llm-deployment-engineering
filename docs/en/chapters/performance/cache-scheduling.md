# KV, cache and scheduling: what to solve separately

[简体中文](../../../01-deployment-foundations/chapters/performance/cache-scheduling.md) | **English**

**The full engineering record:** [Full configuration of MLX-VLM APC with original calls](../../engineering/apple-mlx.md)

[Contents](../../SUMMARY.md) · [VRAM and Performance](../../02-capability-layers/04-memory-performance.md) · [load testing](benchmarking.md)

## Overview of this chapter

KV Cache keeps the history state; PagedAttention organizing status; Continuous Batching arrange request; Chunked Prefill divides the input length calculation; Prefix Cache uses the same prefix. If you look at these five things, you can see why a switch might be useful and why it might not be profitable.

This chapter refers to the KV, Prefill and Prefix notes of FlowUs and the GB10 service configuration. The original note confused the vLLM prefix cache with RadixAttention, which distinguishes the implementation by project: RadixAttention is the name of the SGLang-related mechanism and cannot be directly used as an implementation description for the vLLM Prefix Cache.

## 1. What is preserved in the KV?

Auto-return generates an additional token each time, which requires historical information. Key and Value of the cache history token to avoid repeatedly computing the corresponding projection; Subsequent attention is still required to read the relevant status. As a result, KV reduces repetitive computing while consuming memory and bandwidth, and does not make long-term context completely free.

Regular full attention estimates are available `2 × 层数 × KV头数 × 头维度 × token数 × 每元素字节`. GQA reduces the number of KVs; Sliding windows, MLA and mixed architecture need to be calculated separately. General Chapter [Section 4.3](../../02-capability-layers/04-memory-performance.md#43-rough-memory-estimates) For example, the actual budget would have to verify the engine log.

## 2. PagedAttention improves memory organization

The length of the request varies, and the generation will also grow dynamically. For each request, a large block of KV is reserved for the maximum length, making it easy to waste capacity. Block management maps logical sequences to physical blocks for allocation and recycling at the time of request growth and completion, and supports some form of sharing.

It improves cache management rather than reducing the bit width of each element. Block granularity, metadata, reference counting, and sharing still have overhead. When you look at the actual KV capacity, the sequence of activities, the empty blocks, the seizure and the weighting, you can't just look at how much VRAM the service starts using.

Flash Attention mainly improves attention computing data access with intermediate storage, which is different. A service can use a split-page KV and the appropriate attention kernel simultaneously.

## 3. How does continuous batching affect concurrency?

Suppose the output lengths of the three requests are 20, 200, 50 respectively. If the whole batch waits for all requests to be completed, some resources may be empty after a short request. Continuous batching between iterations allows new requests to be added, completed requests to be withdrawn, and usually improves the use of multiple requests.

However, the more the sequence of activities, the more resources and KV pressure will change each round, and the slower the single request may be.`max-num-seqs ` It's a sequence of activity budgets.`max-num-batched-tokens` It is the input workload for each round of the token budget, client concurrency, and arrival rate. Together, the three decided to line up with batching, and could not call any of the numbers "true GPU concurrency".

In the CPU run, c2 increased aggregate HTTP throughput relative to c1, while TTFT and E2E latency increased. This result should be judged by the target latency, rather than just selecting the highest throughput file.

## 4. Chunked Prefill gives long input segments

Long-input prefiles may take up more computation and workspace and interfere with requests that have already begun decoding. Chunked Prefill processes the input blocks according to the scheduling budget, giving more opportunities for prefill and decode switching.

It doesn't reduce all the inputs that need to be read, nor does it guarantee a drop in TTFT for every request. Small block budgets may improve the flow spacing of other requests while increasing the number of scheduling rounds of long inputs of their own; The budget may be more favourable to prefill efficiency. The experiment should look at both long request TTFT and short request ITL/E2E simultaneously.

Two types of public tasks are prepared for design testing: fixed long input, short output, and short input, longer output. First, test separately and mix at a fixed rate; Only one change when switching off/off or adjusting the budget, keeping request-level records.

## 5. Prefix Cache Repeating the same token prefix

When multiple requests repeatedly contain the same long system prompts or documents, the prefix cache can be used to duplicate the already calculated state. The matching object is the sequence of tokens and the cache identity of the request, not the similarly-looking sentences. Templates, blank spaces, time slots, or changes in sampling pre-processing can all affect reusable parts.

Do not add the number of each change before the public prefix; This would disrupt the prefix matching of subsequent long paragraphs. When you need to distinguish the request, place the change to the stable length prefix and check the sequence of the tokenizer obtained.

### The sequence of execution of a cache experiment

1. Save current templates, tokenizers, cache switches and resources budgets, restart controlled test instances to a known initial state.
2. Send the public long prefix plus question A, save first round time and hit indicators.
3. Send exactly the same public prefix plus question B, C, observe reusable tokens, TTFT and resources.
4. Instead of a different prefix, but with a length close to D, E is used as an unintended contrast.
5. Adjust the cache capacity or add interference request to see if it needs to be recalculated after eviction.

The first round was reported separately from the heat stroke. If the same sentence is repeated a hundred times, it can verify the mechanism, but it cannot represent the performance of the first entry of a new document. Overall throughput is constant, and may be due to bottlenecks at decode or other stages.

## 6. KV quantization and offloading are capacity solutions

KV quantization reduces the storage of each element, with the opportunity to hold a longer history or more sequences; It is also possible to increase errors and conversion costs. There is a combination limitation between K and V types, backend, attention implementations. First, check the fixed version support and then test the context quality separately.

KV offloading puts some states into other storage layers, reducing the permanent pressure on the device, but bringing with it transport and access latency. The cost of CPU memory, unified memory and disk memory are different and should not be referred to as VRAM-added memory. When frequent swaps occur, verify the system's actual available memory and concurrency budget.

## 7. Optimization of order and review

First fix the model and the quality baseline, and then choose one according to the actual problem: undercapacity to see the KV budget, long input interference to see the block scheduling, repeat the document to see the prefix, repeat, multiple request using low batching. Each time you save switches, requests, caches, status, resources and quality.

The author GB10 service enables multiple mechanisms simultaneously and completes 200 requests, indicating that the configuration can run as a whole; There is no single-variable control, and no mechanism can be claimed to have resulted in a definite gain. Mechanism interpretation and experimental attribution need to be established separately.

## 8 MLX-VLM APC: from configuration to cold-heat cache experiments

FlowUs also have a complete set of APC configurations. It operates in the context of related implementations `mlx_vlm.server ` It's not.`omlx serve` The model is Gemma4 26B-A4B/31B MXFP8. The original note does not preserve the source code patch, so the reader should first confirm that the current installation does support these environment variables and cache endpoints; They cannot be automatically attached to any upstream version.

### 8.1 Understanding configuration by practical action

|Parameters|Primary value|Roles and checks|
| --- | --- | --- |
| APC_ENABLED | 1 |Whether it's actually enabled to start log verification|
| APC_NUM_BLOCKS | 8192 |Budget of cache blocks|
| APC_BLOCK_SIZE | 16 |The grain of each token|
| APC_DISK_MAX_GB |26B is 80, 31B is 100.|Upper limit of disk cache and check for remaining space|
| APC_DISK_SHARD_MAX_BLOCKS | 256 |Single disc shard block budget|
| APC_LAYER_MAJOR_MEMORY_MIN_TOKENS | 50000 |The implementation of the deployment strategy|
| APC_HASH | fast |To implement the provided hash mode, version verification and isolation requirements are required|
| max-kv-size | 65536 |Service KV related limits, meaning checked by version|
| prefill-step-size | 2048 |Budgeting for Input|
| vision-cache-size | 32 |Visual cache budget, separated from text APC|

8192×16=131072 is just a block-based token slot budget, so it cannot be claimed that each request supports 131072 context. Model windows, single request KV settings, activity request number, block sharing and actual memory will also limit capacity respectively.

The following is an example of maintaining route 26B, which is unified as a public route. Create a dedicated cache directory before running, not to be confused with other services:

```bash
mkdir -p ./cache/gemma26-apc
APC_ENABLED=1 \
APC_NUM_BLOCKS=8192 \
APC_BLOCK_SIZE=16 \
APC_DISK_PATH="$PWD/cache/gemma26-apc" \
APC_DISK_MAX_GB=80 \
APC_DISK_SHARD_MAX_BLOCKS=256 \
APC_LAYER_MAJOR_MEMORY_MIN_TOKENS=50000 \
APC_HASH=fast \
python -m mlx_vlm.server \
  --model /srv/models/gemma-4-26b-a4b-it-mxfp8 \
  --host 127.0.0.1 --port 18082 \
  --max-tokens 2048 --max-kv-size 65536 \
  --prefill-step-size 2048 --vision-cache-size 32 --log-level INFO
```

Route 31B uses another cache directory, port 18083 and 100GB disk budget. The cache must be consistent with model and configuration; Sharing an empty directory does not guarantee model identity isolation.

### 8.2 Prepare a really repeatable long prefix

The original notebook uses a stability system prompt and two problem verification interfaces. In order to observe the more obvious prefill differences, a public prefix can be generated, keeping the system in line with the prefix, and changing the question only at the tail. The following is a new verifiable experimental input that is not labeled as historical:

```python
import json
from pathlib import Path

out = Path('requests/apc')
out.mkdir(parents=True, exist_ok=True)
prefix = '\n'.join(
    f'条目{i:03d}：设备部署需要核对模型、版本、内存、接口与验收结果。'
    for i in range(128)
)
questions = {'a': '概括这份材料的主题。', 'b': '提取五项部署检查。'}
for name, question in questions.items():
    body = {
        'model': '/srv/models/gemma-4-26b-a4b-it-mxfp8',
        'messages': [
            {'role': 'system', 'content': '依据所给材料回答，使用简洁中文。'},
            {'role': 'user', 'content': prefix + '\n问题：' + question},
        ],
        'temperature': 0, 'max_tokens': 256, 'stream': True,
    }
    (out / f'{name}.json').write_text(
        json.dumps(body, ensure_ascii=False), encoding='utf-8')
```

The model field is still marked with the server's actual accepted ID. Article 128 is an input generating rule, not equal to 128 tokens; The official report uses model tokenizer or service statistics to store the actual number of inputs. Inserting the timestamp and run-id at the front of the long text will cause the stable prefix to be lost, and the running number should store metadata instead of contaminated input.

### 8.3 Verification of cold, heat and isolation in order

Health and initial statistics are first checked in their own dedicated test instances; This example is only reset when empty cache is needed, without affecting the services of others:

```bash
curl --fail-with-body http://127.0.0.1:18082/health
curl --fail-with-body http://127.0.0.1:18082/v1/cache/stats -o cache-before.json
curl --fail-with-body -X POST http://127.0.0.1:18082/v1/cache/reset

curl -N --fail-with-body http://127.0.0.1:18082/v1/chat/completions \
  -H 'Content-Type: application/json' -H 'X-APC-Tenant: book-demo' \
  --data-binary @requests/apc/a.json -o cold-a.sse
curl --fail-with-body http://127.0.0.1:18082/v1/cache/stats -o cache-after-a.json

curl -N --fail-with-body http://127.0.0.1:18082/v1/chat/completions \
  -H 'Content-Type: application/json' -H 'X-APC-Tenant: book-demo' \
  --data-binary @requests/apc/b.json -o warm-b.sse
curl --fail-with-body http://127.0.0.1:18082/v1/cache/stats -o cache-after-b.json
```

`X-APC-Tenant ` Cache isolation is involved in this implementation. It is a stability test identifier, not an identity card. The test values remain the same and are then converted separately to `book-demo-2` Observing isolation cannot allow real-world users to share arbitrary states in order to increase hit rates.

Keeping a curl wall clock is not enough to get TTFT. Full performance measurements should be performed using tools that support SSE timing and record the first true, total time, actual tokens and hit statistics. The above commands mainly show the order of operation and the location of the original evidence.

### 8.4 A table of experiments covering critical states

|Grouping|Prefix / tenant / process status|Check the content|
| --- | --- | --- |
|Cold A|Cache, prefix P, tenant T|First prefill, write, TTFT|
|Heat B|Prefix P, tenant T, just change the tail question|It's easy to replicate tokens, hits and TTFT.|
|Not hit C.|It's a different prefix Q, tenant T|Avoid using process warm-up alone to explain the benefits|
|Separated D|Prefix P, tenant U|Whether the tenant is isolated|
|Extruded E.|Add other prefixes over budget|Recycling, recounting, errors and memory|
|Disc F|Restart after achieving cache|Disc recovery costs and first request behavior|

Each group checks the answers and then calculates the speed. It is not possible to keep the whole problem the same between a/b without care in order to get a heat stroke, and finally to use the full response repeat as the prefix repeat. Frameworks may cache different stages. Logs and metrics should state exactly what was reused.

### 8.5 Why not temporarily combine APC with KV quantization

The original MLX-VLM implementation is enabled `--kv-bits` APC is skipped in this case. This limitation comes from this realization, not the universal law of all frameworks. First set up two separate configurations - APC-only and KV-quant-only, check the boot log, and do not write the two switches and declare them to be in effect at the same time.

If the main pain point is repeated long-text TTFT, APC can be measured as a priority; KV quantization may be more relevant if it is a long context capacity. In the end, two sets of different configurations for the workload can be retained, but the quality, cache behaviour and resources boundaries must be recorded.

## 9. Multimodal cache: A single graph is not the same as the entire computation.

Visual cache may be duplicate with image encoder output, text prefix cache may be duplicate with subsequent KVs, both of which have different identities and capacities. The image bytes are the same but the scaled, cut, processor version changes and the visual characteristics may differ. The image is the same but the location of the message varies, and the language model status may not always be repeatable.

The vision-cache-size 32/64 of the original MLX-VLM is a numerical budget of items in different service configurations, and cannot be used as a fixed memory for 32/64 images of any size. The test should record the resolution, snippets, visual tokens, processor and cache statistics; Run separate comparisons with the same image and different questions, different images and the same question, and different sizes of the same image.

Don't pass a high-impact short test to cover the cost of the first new map. On-device photo and document applications may process the same material repeatedly, or they may upload new images each time, both of which are worth preserving their respective results.

## 10 - How to schedule parameters step by step

Start with the historical configuration of GB10:ctx16184, seqs4, batched8192,FP8 KV, prefix and chunked prefill. It is a combination of over 200 requests. To know the bottleneck, you should first do the single request, the long input and the long output, respectively, and then do the mixed workload.

The first round fixed all the conditions, only changing the activity sequence 1/2/4, observing KV, output throughput and TTFT. The second round fixed the appropriate seqs, changed only the batched budget, observed the long input TTFT, short request ITL and workspace. The third round fixed workload, separately compared to the cold/hot cache. All operations retain the input and end causes, and quality failure operations are not involved in effective throughput.

If the short request is slower after the batched budget is reduced, the long input of the first token is slower, it can be explained as scheduling substitution. If it all slows down, keep looking at the extra rounds, utilization rates and software costs. The goal of modeling is to find the work point to meet the task, not to maximize the value of each parameter.
