# Layer 4: memory and performance optimization

[简体中文](../../01-deployment-foundations/02-capability-layers/04-memory-performance.md) | **English**

[Contents](../SUMMARY.md) · [load testing](../chapters/performance/benchmarking.md) · [cache / scheduling](../chapters/performance/cache-scheduling.md) · [multi-GPU and multi-node](../chapters/performance/parallelism.md) · [MTP/DFlash](../chapters/performance/speculative-decoding.md)

## 4.1 Core questions

Optimize the goal first: Single users want the first token to be generated quickly and continuously; Multi-user services also look at total throughput, tail latency and success rates. On-device also meets memory, power consumption and continuous operation requirements. The goal is different and the appropriate parameters are different.

### Understand prefill and decode first

|Stages|What to do?|Common influences|
| --- | --- | --- |
| Prefill |Processing input tokens, calculating model status and KV|Input length, matrix computation, capacity, batch, attention implementation, workspace|
| Decode |dependency is already in the state of generating the next token|Weights /KV reading, batch, kernel, CPU offloading and communication|

Long inputs and larger batches may have higher dependency matrix computation throughput; Low-batch decoding is often affected by memory bandwidth and execution costs. This is the positioning direction, the actual bottle is still to be passed, time decomposition and resources sample confirmation.

Optimization should form a hybrid phenomenon → Assumptions → Evidence → Individual or combined changes → quality/performance/resources Quantization may reduce capacity and improve reading, or may introduce dequantization costs; Increased concurrency may increase total throughput, as well as increased waiting and KV demand.

### Diagnose by symptom

|Issue|Dissociation|The first is to collect|
| --- | --- | --- |
|VRAM is not enough.|Weights, KV/circular state, diagrams, communication, prefill workspace|Failure stage, segmentation buffer, peak|
|TTFT high|Queueing, tokenization, prefill, compilation/cold caches, and transfer|Customer time, queue, input length, cooling|
|TPOT high|Weights /KV access, kernel, batch, communication, host offloading|Engine time, GPU/CPU, bandwidth and topology|
|Not on concurrency.|Activity sequence/token budget, KV capacity, scheduling, request length|waiting/running, block occupancy, tail latency and errors|

## 4.2 Memory components

```text
Peak device memory = weights +KV/circle state + chart/runtime
             + prefill/decode workspace + communication buffer + other processes
```

|Subsections|What changes?|Inspection Stage|
| --- | --- | --- |
|weights|Parameters, dtype, scale/zero, layout, and partitioning|Loading completed|
|KV/ state|architecture, tokens, sequence of activities, dtype, share/window|Pre-allocation and request growth|
|Chart/Runtime|CUDA graph, compilation, fixed shape, allocator|Warm-up / Capture|
|workspace|batched tokens,ubatch,attention/ quantization kernel|Long prefill, decode peak|
|communication| TP/PP/EP,rank,collective |Multi-GPU initialization and operation|

UMA also monitors host RSS, system availability, device, budget, memory pressure and swap. These counts can overlap and cannot be simply combined. [395 GTT/TTM examples](../engineering/amd-395-rpc.md) Explanation: Physical capacity, driver, budget and actual allowability are three layers.

## 4.3 Rough memory estimates

```text
Ideal weights Byte ≈ Total parameter quantity × bit width / 8
7B×2 ≈ 14GB；32B×2 ≈ 64GB；70B×2 ≈ 140GB
```

The above is a decimal of the original weights for the numerical order, without scale, non-quantisation layer, alignment, KV and workspace. Total MoE weights capacity by total parameter, calculation by activation path; Activation 3B cannot be understood as having only 3B weights.

For example, 32B INT4, with an ideal weights of 16GB around 14.90GiB, the actual artifact may be larger, and 16GB GPUs require KV and workspace, so it cannot be determined that a single-GPU can be deployed. Loading, warm-up, long input and continuous workload peak records respectively.

## 4.4 Why KV Cache matters

It's an ideal cache budget for pure attention, a layer of the same shape:

```text
KV bytes ≈ 2 × number of attention layers × KV heads × head_dim
          × number of cache tokens × number of activity sequences × number of bytes per element
```

2 from K and V; GQA uses KV heads instead of query heads. Sharing prefixes, sliding windows, block alignment, compression, MLA, GDN/SSM cycling status and cross-card allocation are required to perform an alternative calculation.

Teaching example: 32 layers, 8 KV heads, head_dim128, FP16, about 128 KiB per token; 8192 tokens are about 1GiB/sequence, 4 completely independent sequences are about 4GiB, and no other expense has been counted. Do not directly replace the KV head structure with hidden size.

|Optimization|What Changes|Verified|
| --- | --- | --- |
|Limit the sequence of ctx/activities|State capacity and scope of tasks|Long inputs, each slot context and peak|
|KV quantization|Number of state bytes and read/convert|Backend support, long context quality and ITL|
| Prefix Cache |Repeat prefill, possibly shared status|Identical token prefixes, cold/warm runs, eviction, and tenants|
| PagedAttention |Block allocation and reference|Block occupation, recycling, fragmentation and scheduling|
| Chunked Prefill |Scheduling Grid and instant prefill work|TTFT, ITL, total throughput, common changes|

## 4.5 Performance metrics

|Indicators|Definition / statistical qualities|We must be careful.|
| --- | --- | --- |
| TTFT |request  issuer→ first valid token or first authentic, clearly calibrated|The empty role cannot be automatically correctly calculated; Links and transmissions|
| TPOT |Usually the time of the last token - the time of the first token) / the time of the output token -1)|Single token and less than two token samples treated separately|
| ITL |Neighbouring token/event interval, implemented by tool|An SSE event can contain multiple tokens, not equal to a TPOT distribution|
|Output throughput|Total output of tokens/test wall clock time|You can't directly add the request token/s.|
|Total token throughput|(Input + Output Token) / time|It must be marked and cannot pretend to output throughput|
| req/s |Successful request Number/time of the window wall clock|request Longitude Difference Impact Comparison|
| p95/p99 |The corresponding sample score and calculation method|A small sample cannot represent a stable tail|
|Effective throughput|At the same time satisfying quality, error and SLO completion/time|Workplaces should be selected based on|

```text
The controls must be fixed: model / revision, template, input/output, sample, request number
             concurrency/reach rate, cache, warm-up, tool version, timing range
```

[Complete original load testing articles and commands](../engineering/benchmark-tools.md). Engine pp/tg, GenAI pipeline and HTTP are not directly ranked; Workload c4 and the inf200 request are also different experiments.

## 4.6 Common bottlenecks and optimization options

|Evidence / Bottle|Optimization of variables|Cost and acceptance testing|Responsive engineering|
| --- | --- | --- | --- |
|Weights greater than device|weights quantization ,offload,TP/PP|Quality, RAM, PCIe/communication and loading| [2060](../engineering/nvidia-rtx2060.md), [W7900](../engineering/amd-w7900.md) |
|Weights Access/CPU fallback|It's actually offloading, kernel, precision.|Not replacing data flow evidence with GPU utilization| [8060S](../engineering/amd-8060s.md) |
|KV/ workspace OOM| ctx,seqs,batched,ubatch,KV dtype |Task scope, long text quality and peak| Intel16GB,395 |
|Repeat the long prefix| Prefix Cache/APC |Heating group, tenants, hits, exits| [MLX APC](../engineering/apple-mlx.md) |
|Long prefill interference|Chunked, token budget, short request group|TTFT and ITL balances|GB10 and Double 4080|
|Decode computation/verification|MTP, DFlash, draft length|Acceptance rate, cost of verification, quality, VRAM| [GB10 speculative decoding](../engineering/nvidia-gb10.md) |
|concurrency throughput is insufficient|Activity sequence, batching, arrival rate|Single-stream TPOT and tail latency are rising| [oMLX c1/c2/c4](../engineering/apple-mlx.md) |
|multi-GPU communication|TP/PP, network cards, collective, cutting|Each rank memory, topology, bubble and recovery| W7900,HIP RPC |
|NPU fast but wrong content|shape/operator/precision Repair or rollback|Double acceptance testing between performance and quality| [Intel full NPU TTS](../engineering/intel-arc-npu.md) |

Experimental processes: baseline → bottleneck evidence→ assumptions→ changes→ the same workload Replication→ quality / resources → adoption or fallback. A single variable can be attributed and a multi-variable is retained as a combined observation. Unimproved results must also be saved, such as 8060S BF16 10.8→10.1 tokens/s after batch enlargement.
