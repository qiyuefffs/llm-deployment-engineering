# Hardware deployment adapts to accelerated optimization instances index

[简体中文](../../01-deployment-foundations/engineering/README.md) | **English**

[Knowledge base home](../README.md) · [List of five levels of competence](../SUMMARY.md) · [The source text retains the list](../../01-deployment-foundations/evidence/source-coverage.json)

## Example matrix

Each hardware input contains environments, deployment of adaptation sequences, baseline, optimization parameters, original results, failure and acceptance testing, and the corresponding FlowUs. The author's historical notes contained this content; This is not the same as the re-testing of this round or the complete reproduction of the material that has met the requirements of the Independent Case.

|Hardware|Examples and models|Deployment of adaptation|Accelerated optimization and results|Status|
| --- | --- | --- | --- | --- |
| RTX2060 12GB | [Qwen3 Q6/Q5](nvidia-rtx2060.md) |CUDA, GGUF, CPU/GPU mixed offloading|Layer number / quantization / host memory; A decode of about 5.26 tokens/s|A single historical record|
| RTX4080×2 | [DeepSeek32B GPTQ INT4](nvidia-dual-gpu.md) | Docker,Toolkit,TP2,PCIe | ctx/seqs/memory/chunked;35→55→52token/s |Multi-variable, workload incomplete|
| A6000×2 | [DeepSeek 70B FP8 directory](nvidia-dual-gpu.md) |Double 48GB, TP2, and kernel checks|17.1→17.5token/s; Ampere has no native FP8 matrix capability|Historical observation, verification of the actual kernel|
| GB10 | [Qwen FP8,Gemma AWQ/MTP/DFlash](nvidia-gb10.md) |ARM64, CUDA13, source code and extensions|Four groups of quantization, three groups of MTP, DFlash combined controls|Complete summary, original details missing|
|More than 10 GB models| [VL,Omni,Docling](nvidia-gb10-multimodal.md) |processor, encoder, image/audio protocol|Resolution, token budget, cache, scheduling experiments|Acceptance testing for each skill|
| Radeon780M | [8845HS Windows HIP/Ollama](amd-780m.md) |Gfx1103 community library, DLL isolation, model load|CPU/GPU fallback, context and UMA budget|Deployment steps, not complete performance tables|
| Radeon8060S | [395 Vulkan Q4/BF16](amd-8060s.md) |Full offloading, GDN, shared memory| Q4 22.9→47.2→58.4;BF16 10.8→10.1token/s |There is a list of parameters, quality needs to be improved|
|8060 S × 5 aircraft| [Kimi HIP RPC](amd-395-rpc.md) |GTT/TTM, DKMS, build and distribute the same version|Split with small workspace; Multi-node acceleration ratio|Capacity and loading process|
| W7900 | [Double/Four/Eight cards and double nodes](amd-w7900.md) | ROCm/RCCL,Ray,TP/PP |single-machine → multi-node , communication ,rank memory , resources scheduling|Complete operational iteration, performance is not perfect|
| Intel Arc | [Qwen 3.5-9B GPU 3 backend](intel-arc-npu.md) |Vulkan/SYCL/IR, device and precision comparison|INT4/INT8, Mesa, and 23 GPU / 10 CPU layers|Original three-wheeled and pipeline indicators|
| Intel NPU | [ASR/TTS and Kokoro](intel-arc-npu.md) |Form, NPUW, Device|In the meantime, we're going to have to make a decision. Keep all NPU failures and rollbacks|48 CPU and NPU failures|
| Apple M3 Ultra | [Metal/GGUF](apple-metal.md) |Xcode, shader, tensor/type compatible|Actual offloading ctx/ubatch/FA verification|Failure to load specific artifact if retained|
| Apple M3 Ultra | [MLX/APC/oMLX](apple-mlx.md) |Native extensions, templates, VLMs, and model discovery| c1/2/4:29.38/41.11/55.15token/s |Separate text/visual scope|
|Ascend 310P3| [Qwen3-32B](ascend-310p.md) |Cann, device, nodes, plugins, FP16/TP2|Approximately 4.5936token/s for one long-generation sample|Do not treat 1 request as concurrency 10|
| MUSA | [Complete verification process](musa.md) |Toolkit, GGML backend, GGUF, and API|CPU→GPU, number of layers, FA, batch, slot|Not found measured source, waiting for device verification|
| CPU | [Fixed full Windows exercises](../practice/first-service/README.md) |Fixed model/binary, SHA256, API|8 requests, 3 engine runs, and complete actual outputs|Functionality 2/3, error returned 500, total acceptance testing failure|

## Execution and evidence of each case

```text
Environmental list → artifact identity → create log → single request with interface
 → No optimization baseline → Single or combined experiments → performance + quality + resources acceptance testing
 → Final command, start stop, rollback, limit
```

The full technical article retains 50 copies, and technical paragraphs, code blocks, parameters, logs and test tables are not removed as abstracts. Privacy fields, certificates and private annexes exceptions; Wrong technical conclusions in the instance input statement or modification of the original location. Storage range and number of code fences [List of source languages covered](../../01-deployment-foundations/evidence/source-coverage.json).

## Shared engineering materials

- [Model conversion, quantization and Ollama full text](gguf-ollama.md)
- [Load testing tools and execution commands](benchmark-tools.md)
- [Environment, on and off rollback](../chapters/delivery/environment-operations.md)
- [API monitoring and acceptance testing](../chapters/delivery/api-monitoring.md)
