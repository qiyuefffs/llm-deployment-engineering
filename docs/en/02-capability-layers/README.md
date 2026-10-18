# Part II: five capability layers

[简体中文](../../01-deployment-foundations/02-capability-layers/README.md) | **English**

[Contents](../SUMMARY.md) · [Device engineering examples](../engineering/README.md)

How the five-layer button hardware is called → model how to display → engine how to execute → performance how to optimize → service how to deliver the pump. General concepts and selection methods in the main framework, platform themes supplementing the software stack differences, actual device records for verification and reuse.

|Levels|Number of sections|The scope of technology|Understanding Goals and Project Locations|
| --- | --- | --- | --- |
| [1. Hardware and runtime](01-hardware-backends.md) | 1.1—1.4 |CPU/GPU/NPU, memory and bandwidth, driver/runtime, compute library, building and communication|Understand platform software stacks, select and verify execution routes|
| [2. Model formats and quantization](02-model-formats-quantization.md) | 2.1—2.6 |HF/GGUF/IR, W/A/KV, AWQ/GPTQ, artifact integrity|Fixed model and quality baseline|
| [3. inference framework](03-inference-frameworks.md) | 3.1—3.6 |Loading, executor, KV, scheduling, APIs, and backend builds|Calling services with valid parameters|
| [4. VRAM and performance](04-memory-performance.md) | 4.1—4.6 |Memory models, metrics, workloads, caching, speculative decoding, and parallelism|Baseline, testing and acceptance testing|
| [5. Engineering delivery](05-engineering-delivery.md) | 5.1—5.3 |Environment, shutdown, SSE, monitoring, recovery, delivery list|Complete deployment packages and operational records|

## How the material is organized

- The main frameworks: technical definition, component structure, execution mechanism, selection type, parameters and judgement conditions.
- Platform topics: introduction of hardware and runtime, configuration, deployment and explanation of failures.
- [Complete engineering records](../engineering/README.md) The process of optimization and 50 FlowUs: the execution sequence of specific GPUs.
- [Results and sources](../evidence/README.md) Historical environment, structured numbers, billing and shortcomings.

## Adaptation sequence

```text
device with minimal computation → model integrity → single request correct → API/SSE/ error
 → baseline and peak → control optimization → quality / performance / resources acceptance testing → delivery / rollback
```

When the model cannot be executed correctly, support and functionality are dealt with first; Enter fixed model, input and timing boundaries after optimization. The environment of each device combines with digital non-intersectional recording into a combination of operations.
