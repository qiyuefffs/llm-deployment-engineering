# Part III: core concepts

[简体中文](../01-deployment-foundations/03-core-concepts.md) | **English**

[Contents](SUMMARY.md) · [Part One: Five levels of ability](02-capability-layers/README.md) · [Next part: Project retrospective](04-project-review.md)

## Overview

The first five layers provide answers on how the deployment process works, and this section explains the ten most commonly encountered concepts. Ten themes in the original framework, each with a single sentence of explanation, engineering explanation, engineering analysis. The complete commands and results are still in the topic chapter, not repeating the lesson here.

## 3.1 Why is vLLM fast?

**In one sentence:** It combines request scheduling, KV management and device execution to increase the efficiency of multiple requests using devices together.

**Engineering explains:** A single request generates a sequential dependency per token, not necessarily with a full device. Continuous batching allows different requests to be executed in batches together; KV management to reduce capacity waste; Optimizing the kernel, graphic execution and distributed routes further impacts computational efficiency. These mechanisms work together rather than a single name representing the entire performance.

**Engineering analysis:** It's important to compare objects and workloads. Using the same model, precision, input, output and quality, compare target concurrency, report throughput and latency. CPU, low concurrency, partial offloading, or unsupported architecture may be better suited to other frameworks, and cannot be excluded from the general speed list by frame name. [Full deployment](chapters/frameworks/vllm-service.md) In the GB10 test, multiple mechanisms are enabled at the same time, resulting in a complete configuration.

### Understand efficiency through request patterns

One person asks a question, the device may be mostly waiting to be decoded step by step; Many people simultaneously request, the framework can arrange multiple sequences into a round of execution, sharing some weights and reading costs. When the input is long, it is necessary to confuse the prefill with the request that is being generated. So, high concurrency throughput, high speed, and one-to-one first token are not the same thing.

GB10's sudden 200 request received 86.06 tokens/s, but had an average TTFT of about 148 seconds, indicating that scheduling efficiency could not be detached from the arrival mode. The framework has no obligation to keep unlimited queues low in latency, and service inputs and workloads are also involved in the results.

## 3.2 What is PagedAttention?

**In one sentence:** Block grouping of KVs makes it more flexible to allocate and share caches to growing, varying length requests.

**Engineering explains:** The history of logical continuity does not necessarily correspond to the memory of physical continuity. The block table maps the sequence location to the actual cache, increasing, completing, and sharing resources management as requested. Block granularity, metadata, and scheduling still have overhead; KV storage is still required.

**Engineering analysis:** See the sequence that can be run at the same capacity with the length, block use, seizure and recalculation, and see the performance of the service. Flash Attention optimizes attention-performing data access, which can exist simultaneously, as opposed to the KV block management role. See detailed experimental methods [Cache and scheduling](chapters/performance/cache-scheduling.md).

### From contiguous reservations to block-based growth

Suppose a single bar has a maximum of 4096 tokens, but a request only uses 100 tokens. If a complete continuous zone is retained for each fixed, many capacities are temporarily unused; Block by block allows it to have enough blocks first, and then generate growth. The last block may still be empty, there are also block tables and management expenses, and the split page is not wasted.

MLX-VLM APC records 8192 blocks, each with 16 tokens, corresponding to 131072 blocks of slot tokens, but also includes cross-request sharing, eviction and model windows. You can't put this multiplication in a single request context. See if statistics, memory, and target requests are actually used.

## 3.3 What is KV Cache?

**In one sentence:** Save the processed keys and values of the tokens for subsequent generations using historical information.

**Engineering explains:** Reusable status reduces repetitive computing, but increases storage and access as the length of the history and sequence of activity increases. The budget for conventional full attention, GQA, MLA, sliding windows and mixed structures is different. Weights are INT4, which does not mean that KV is also INT4.

**Engineering analysis:** The engine's actual allocation and target length are then verified according to structural estimates. Long requests are successful in loading OOMs, usually focusing on KVs and prefill workspaces. Formulas and examples of curriculum [Level 4 - Section 4.3](02-capability-layers/04-memory-performance.md#43-rough-memory-estimates).

### An intuitive view of Q, K, and V

Current tokens generate query, historical tokens provide key and value, and attention uses historical information based on matching relationships. The KV cache maintains the K/V state that will be used repeatedly afterwards; Currently, Query still needs to be calculated, and reading the historical status is still costly.

Therefore, the growth of KV affects two things: increased capacity, and the need to access more history for subsequent generation. Reducing weights bit width does not automatically compress KV, improving model windows or automatically adding cache space to the device. The long-context test should be performed simultaneously to see if the pump remembers the contents of the pump and whether the pump can run within the budget.

## 3.4 What is continuous batching?

**In one sentence:** In the process of generating new requests to be added, completed requests to be withdrawn, dynamic use of batch execution.

**Engineering explains:** The request varies in length, the static whole batch waits and is easily left empty. Continuous scheduling can be added to new requests. Activity sequence caps, each round of token budget, input length, arrival mode and KV co-impact execution. Client concurrency is also not equal to the number of sequences actually executed per round.

**Engineering analysis:** In the real-time running of the system, total throughput is increased by c2 relative to c1, while TFT and E2E are increased. Explain that capacity and experience must go hand in hand with acceptance testing. The historical oMLX record shows a similar direction, but contains no isolated ablation, so the full difference cannot be attributed to this mechanism. See you. [Examples of load testing](chapters/performance/benchmarking.md).

### A simple scheduling timeline

```text
Round 1: A, B starts to generate
Round two: A, B continues.
Round 3: A completed, B continued, C joined
Round four: B, C continue.
```

It's just a sign of a mechanism, not a real trace of a framework. Whether to join C immediately depends on KV, each round's budget and prefill strategy. After completion of the request, the resources are recycled in a timely manner, allowing batching to continue; Cancellation or incorrect paths can also affect subsequent capacity if not properly recycled.

## 3.5 What is chunked prefill?

**In one sentence:** Long-input prefill by scheduling budget blocks, increasing the chance of cross-exercise with other requests.

**Engineering explains:** Long inputs can take up computing and workspace and interfere with decoding requests that have already started. The block does not reduce all inputs, block size and budget will change the length of the request, its own efficiency and other requests waiting.

**Engineering analysis:** Fixed long input with short request, mixed workload, longer request TTFT, short request ITL, throughput and resources. A single short request cannot explain the value of a block for a mixed service. Parameters and experiments [Subject: Section 4](chapters/performance/cache-scheduling.md#4-chunked-prefill-gives-long-input-segments).

### Two users can experience opposite effects

User A submits a long material, user B is generating a short response. Once A is processed, the input may prevent B from receiving the new document for a long time; After the block A requires more wheels to complete the prefill, and B may be smoother. TFT of A and ITL of B are measured at the same time, rather than just one of them.

Block budgets are also influenced by model and kernel efficiency. Setting the blocks up to a minimum will increase the cost of scheduling and calling, and can't just pursue a fairer, more fragmented approach. The ratio of fixed mixed inputs to the arrival order explains the parameter changes.

## 3.6 What is prefix caching?

**In one sentence:** Repeat the same token prefix to the already calculated state, reducing repetitive prefill.

**Engineering explains:** The same long system prompts or documents may form repeatable prefixes. Whether the target is affected by the template, token sequence, block, model identity and cache strategy. The implementation should not be known as RadixAttention; The structure and semantics of each framework cache need to be checked separately.

**Engineering analysis:** First round cold request, repeat prefix and different prefix separation, save hit with TTFT. The numbering of each change in a long document may disrupt subsequent matching; Caches can also be extracted due to capacity. Hot cache scores cannot represent the first entry of a new document. See you. [Complete experimental sequence](chapters/performance/cache-scheduling.md#5-prefix-cache-repeating-the-same-token-prefix).

### Why changing one character can affect later reuse

Prefix Repeated dependency is the consistent state from the beginning of the sequence. Time slots are inserted at the front and may change the entire subsequent prefix even if the documentation is the same at the back. Even if the characters look the same, different templates, special tokens or processors can change the sequence of tokens.

Verify the hit with a stable long prefix, then add new questions, change prefixes and change tenants to make a contrast. The cache should only be duplicated to achieve an identity-conforming state; After the model version changes, it is not possible to continue using the old KV to save the load.

## 3.7 TP：Tensor Parallelism

**In one sentence:** The tensor is calculated by dividing the same layer into multiple devices, and then the combined results of the passed communication.

**Engineering explains:** TP shares weights and calculations, and also introduces communication within layers. The number head and shard, quantization kernel, interconnection and backend support all affect availability. Two 16GB devices do not automatically turn into a 32GB device, and each rank still has a separate budget.

**Engineering analysis:** First look at physical topology and communication, then run shard loads, small requests and target workloads. RTX4080 does not have NVLink and cannot be deployed under the assumption of bridge interconnection. DP as a multi-model copy is better suited for extending the request capacity when the model can hold independently. MoE's EP is a distributed expert, with other routing and workload disproportionate issues. See you. [Multi-device topics](chapters/performance/parallelism.md).

### Why tensor partitioning requires communication

A matrix computation can be understood as multiple devices, each as a part, and the result can be combined or exchanged at the desired location. Different operators use different cutting methods, some outputs keep shard, and some need to be rounded/clustered. Communication frequency, message size and interconnectedness will affect the benefits of sharing computing.

The model shard also has to meet the head count, quantization layout and model limitations. TP2 does not necessarily support seeing two cards. First check the framework for the shard rules of the structure, then look at each rank memory and the actual communication log.

## 3.8 PP：Pipeline Parallelism

**In one sentence:** Put different layers or phases into different devices and pass the middle result in order.

**Engineering explains:** A single request will wait for multiple phases, when the phases are calculated unevenly; There is an opportunity to fill the pipes, but there are bubbles and transportation costs. PP and TP can be combined according to the supported situation, and the number of nodes does not directly determine the single mapping.

**Engineering analysis:** Record memory, calculation, and waiting at each stage, and compare throughput to meet latency requirements. Layer offloading in llama.cpp cannot be directly explained by the vLLM strategy of the same name as RPC. AMD's five-machine record demonstrates that short-context capacity routes can run without a single-machine baseline, and therefore do not calculate multi-node acceleration ratios.

### What are pipeline bubbles?

Each request goes through stage A and then through stage B. B, when A, A waits for the next dependency, there is a blank window; Multiple requests can be filled in mistakenly, but short requests and uneven layers of distribution still leave a bubble. Additional single-request latency may be added to the storage capacity of the PP.

The original W7900 dual node 671B route configuration is TP8×PP2. It describes a set of 16 rank combinations, the actual stages and device placement still need to be checked, and can't equate PP2 directly to every single half-barrel in all cases. Embedding, output heads and uneven layers may lead a rank to reach its capacity limit earlier.

## 3.9 What is GGUF?

**In one sentence:** Save model tensor and metadata file format, commonly used in llama.cpp routes.

**Engineering explains:** GGUF can store different accuracy and quantization types, containing information such as architecture and tokenizer; It is neither a quantization algorithm nor an execution framework. Q4_K_M belongs to the K-quant series, K is not interpreted as k-means, and M is not a model parameter scale.

**Engineering analysis:** The source directory is complete, the converter is supported, the GGUF is complete, the executor is supported and correctly generated. FP8 switches F16 will not recover lost information, and special tensor types may also fail at the backend. Operations see [Converted tutorials](chapters/models/gguf-conversion.md) Quality and speed [How to quantize](chapters/models/quantization.md).

### Why a parsable file can still fail to generate

The executor may know the GGUF container but does not know its model architecture; The concept of an architecture lacks a specific kind of tensor kernel. Weights can be allocated, and warm-up only enters the unrealized operator. The Mac type 42 fault description file, model and backend support must be created separately.

The same model name may also be derived from different converters or fork agreements. Keeping source revisions, converting commits, and output summaries with the target executor can make the GGUF that can't be used with the GGUF a specific localizable problem.

## 3.10 Choosing between vLLM and llama.cpp

**In one sentence:** First, select a combination of tasks to accomplish the goal, then compare resources, performance, and maintenance costs.

**Engineering explains:** vLLM focuses on service scheduling and device execution, while llama.cpp focuses on GGUF and multi-backend local execution, but the scope of the two intersects. Intel can also verify OpenVINO routes, and Apple can verify MLX. The format, model, structure, functionality, device kernel and delivery conditions must be met together.

**Engineering analysis:** Button task functionality → artifact → device → capacity → quality → target workload → maintenance of the functionality to make decisions. Complete the same minimal task, then compare input, concurrency, error and recovery. High throughput and no complete answer still failed. Write down the reason for the selection [Project retrospective](04-project-review.md) It's easy to upgrade and re-check.

Speculative decoding, MTP, DFlash, and other optimizations are covered in Layer 4; see [Speculative decoding](chapters/performance/speculative-decoding.md). They follow the same principles: fixed conditions, retaining quality and raw data, and talking about benefits.
