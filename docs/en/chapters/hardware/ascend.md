# 1.2.5 Ascend: chips, CANN and framework plugins

[简体中文](../../../01-deployment-foundations/chapters/hardware/ascend.md) | **English**

[Contents](../../SUMMARY.md) · [Hardware and runtime overview](../../02-capability-layers/01-hardware-backends.md)

## Hardware basics

Ascend is an accelerator platform for AI computing, often used as the name of an NPU device in tools. Differences in chip-oriented scenarios, device memory, support for precision, operator and parallelism capabilities do not extend a single 310P instance to all Ascend devices.

The hardware selection model looks at the precise models and resources, and then confirms whether model architecture, target precision, input length and concurrency are supported. The device peak compute throughput only describes capabilities under specific conditions, and the actual LLM speed also depends on kernel, KV, graph compilation, memory, and communication.

## Relationship between CANN and the upper frame

|Components|Responsibilities|What to confirm when deployed|
| --- | --- | --- |
|driver and firmware|Device management, underlying execution and hardware support|Chips and system support, device nodes, version relationships|
| CANN |AI compute software stack containing runtime, operators, compilation and development tools|Supported with chips, frameworks, plugins and models|
|AscendCL and supporting APIs|memory, execution and model/operator call interfaces|Interface and run library versions of the program links|
|Operator library and graph compilation|Implementation or compilation Matrix, attention, quantization etc.|Model diagrams, shapes, dtype and actual kernel coverage|
| HCCL |Collective communication between devices|Multi-GPU rank, topology, network and parallelism strategies|
| torch_npu |PyTorch faces the adaptive layer of Ascend|PyTorch, plugins, CANN and device combinations|
| vLLM Ascend / MindIE |inference scheduling, model execution and service capabilities|Current support for chips, models, precision and versions|

```text
Applications → inference engine / framework plugins → CANN runtime with operator → driver / firmware → Ascend device
```

After installing CANN, the execution framework that supports the target model is selected. The plugins in the container, the operator and the user mode library must also be compatible with the host device and driver, and the image name does not contain the ascend string that constitutes a complete compatibility conclusion.

## How to Determine Routes for Deployment

First check the device, the CANN and the support matrix for the upper frame, and then verify the small computation and single request. When the required operator or precision is not achieved, preference is given to the supported model, artifact or version; Simply adding memory won't match the operator.

A single request can be used to correctly add context, sequence of activities and card count. Compilation/warm-up diagrams, communication and service queues must be measured separately to determine the reasons for the first token slowdown, token-by-token slowdown or insufficient throughput.

Basic information: [CANN](https://www.hiascend.com/en/software/cann) · [vLLM Ascend](https://github.com/vllm-project/vllm-ascend).

## Deployment procedures and examples

Subsequent use of 310P3 records describes specific container, model, interface and load testing checks. See full text [310P3 Deployment and Error Record](../../engineering/ascend-310p.md).

## A fixed known combination

Original notes used `quay.io/ascend/vllm-ascend:v0.10.0rc1-310p` The model is Qwen3-32B, dual device, float 16. The image tag belongs to the historical portfolio, and the current environment should be reworked to verify the accompanying description of the chip and version, and record the image digest.

```bash
npu-smi info
```

Continue to record the drivers, firmware, CANN, Python, Python, Python Torch/torch_npu and vLLM Ascend versions. The device name can't directly replicate the supporting conclusions of another generation.

## Container pre-verified device accessible

The device nodes and driver libraries must be provided according to the current image documentation and the model must be installed. The model directory is read-only, port and shared memory are clear configuration. The original notebook used high permissions, host networks were more widely installed, and delivery should be scaled down according to actual needs.

First perform device checks and small calculations in the container and then run the target model. This allows the model to distinguish between container access, plug-in initialization and weights when loading failures.

## Three, launch the target model

The following is a selection of public routes for the original service, provided that the supporting container environment has been passed; Length and memory budget need to be updated according to current device acceptance testing.

```bash
python -m vllm.entrypoints.openai.api_server   --model /srv/models/Qwen3-32B   --served-model-name Qwen3-32B   --host 127.0.0.1 --port 8000   --tensor-parallel-size 2 --dtype float16   --max-model-len 32768 --gpu-memory-utilization 0.95   --distributed-executor-backend mp --enforce-eager   --block-size 64 --swap-space 16
```

Don't use the historically high budget as the starting point for your first smoke. The original resources can be verified for a long time and then gradually restored to the target configuration. When remote code is required, the model reviews and fixes separately, without adding all commands by default.

## Four: Interface and load testing

After the service is ready, first check the model list and then submit the request using the corresponding chat or completion endpoint. The prompt field must be consistent with the endpoint: `messages ` It's for chat.`prompt` It's for completion.

The original load testing was set `parallel=10 ` and `number=1` In the end, there was only one request. This is a record of about 14336 output tokens, 3120.88 seconds, and 4.5936 tokens/s. It is a long output observation that cannot prove ten-way simultaneous service, nor can it provide reliable tail latency.

When re-testing, each concurrency group should have enough samples to keep the actual request consistent with the output, length, sampling and cache. Specific methods [How to test load](../performance/benchmarking.md).

## 5 Import location and environmental variables

The original note mentioned differences between running in the source code directory and running in the work directory. When faced with this kind of problem, check `python` Paths, source modules and environmental variables to prevent the current directory from covering the installed packages. Switches such as V1/V0 are set to support the fixed version and record the final effective value.

## Six, complete the inspection.

the device, plug-in and target model have evidence, respectively; A single request, functionality and workload acceptance testing; Dependence and image traceability The current material does not preserve the complete clean reconstruction chain, so this section preserves historical orders and known results for engineering reference.

Source: Ascend 310P3 inference Qwen3-32B Ascend 310P3 deployment Qwen3-32B benchmark recording [List of corresponding articles](../../evidence/chapter-sources.md).
