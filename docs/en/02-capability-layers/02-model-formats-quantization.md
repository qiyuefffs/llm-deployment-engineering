# Layer 2: model formats and quantization

[简体中文](../../01-deployment-foundations/02-capability-layers/02-model-formats-quantization.md) | **English**

[Contents](../SUMMARY.md) · [GGUF full process](../chapters/models/gguf-conversion.md) · [Quantization and AWQ groups](../chapters/models/quantization.md)

## 2.1 What this layer addresses

Model deployments require weights, network structures, tokenizers and input-output agreements to work together. downloaded to a weights file, completing only part of the preparation of the artifact; The engine also needs to be able to identify its structure and numerical representations.

### Five dimensions to distinguish

|Concepts|Meaning|Examples|
| --- | --- | --- |
|model architecture|How to connect to a network, which operators to use|Dense/MoE, Attention, Sliding Window or Circular State|
|File format|How weights and metadata are stored| safetensors,GGUF,ONNX,OpenVINO IR |
|Types of data|What is a numerical value?| FP32,FP16,BF16,FP8,INT8 |
|Quantization methods/ layout|How to display values with low bit width and how to group and pack them|AWQ, GPTQ, engine-supported GGUF quantization type|
|Implementing Implementation|Which backend and kernel are used when calculating|The corresponding matrix and dequantization kernel on CUDA/HIP/Metal|

The same model can produce artifacts of different formats and precision. The format conversion changes the storage or execution representation; Quantization reduces bit width, which may affect quality. GGUF is a format, AWQ/GPTQ is a quantization method and cannot be substituted in the same classification.

The order of selection is: **Tasks and quality requirements → Engine/Hardware support → Capacity budget → Format and precision → Actual quality and speed control.** Verify the existing supported artifact first and decide whether it needs to be converted or quantized on its own.

### Common deployment issues

|Issue|Objects examined|Output|
| --- | --- | --- |
|Don't let it go.|Weights size, KV/state, workspace, offloading location|Precision/Quantization/Parallelism with memory budget|
|Can't load|architecture, tensor name and type, shard, converter|The full artifact supporting the engine|
|Slow after quantization|It's the actual kernel, the group/layout, the dequantization, the batch|backend performance and quality contrast|
|The Answer Changes|Weights, errors, templates, tokenizers, samples, output budget|Differences between fixed sets of questions and conclusions|
|VLM lacks functionality|processor, visual encoder, projection and input protocol|Individual functionality Scope and completeness of materials|

Model identity is at least `仓库＋revision＋文件清单＋量化配置＋模板＋工具版本`. The name of the disk directory and the 4-bit aluminum label are insufficient to identify the artifact.

## 2.2 Model formats

```text
model artifact
├── Hugging Face directory: safetensors/bin + config + tokenizer + template
GGUF: tensor with model data container, containing F16/BF16 or quantization tensor
ONNX: Calculating charts and internal/external weights
OpenVINO IR: XML/BIN and GenAI, tokenizer/processor configuration
TensorRT/TensorRT-LLM: checkpoints for the corresponding version/executing the artifact
Plug-ins - platform-specific charts, running packages and compilation cache
```

|Documents|Responsibilities in Engineering|Failure|
| --- | --- | --- |
| config.json |Architecture, layer count, dimensions, RoPE/MoE, etc.|Unknown model, shape error|
|*safetensors+ index|Tensor content and tensor to shard file mapping|Missing tensor/shard, not in size|
| tokenizer* |Text encoding, special tokens, decoding|Token number error, miscoding or stop incorrect|
| chat_template.jinja |Characters, history, tools, reasoning and starting points|Character marking, reasoning only, tool analysis failure|
| generation_config.json |Default sampling and stop strategies|Overlapping with apparent parameters leads to inconsistencies in experiments|
| processor/preprocessor |Image/audio preprocessing|Successful text but multi-form failure|
| quantization_config |Methods, bit width, grouping, exclusion of modules|kernel/layout not supported or misloaded|

The shard index does not determine the GPU segmentation; Multi-shard can also be loaded into a single GPU. Conversion and quantization generate new artifacts that need to be stored as source identities, tool commits, commands, logs and output summaries.

```python
import json
from pathlib import Path
p = Path('/srv/models/example-model')
cfg = json.loads((p/'config.json').read_text(encoding='utf-8'))
print(cfg.get('model_type'), cfg.get('architectures'))
idx = p/'model.safetensors.index.json'
if idx.exists():
    shards = set(json.loads(idx.read_text(encoding='utf-8'))['weight_map'].values())
    assert all((p/s).is_file() for s in shards)
```

The code only checks the existence of the shard and does not verify the correct content. Downloading summaries is still subject to independent verification.

## 2.3 Quantization

```text
The numbers are: FP16/BF16, FP8, INT8/INT4, MXFP4/NVFP4, and so on.
Quantization objects: weights W, activation A, KV/recorded state of the loop
Quantization methods: AWQ, GPTQ, dynamic/static/online program supported by tools
Storage layout: grouping, scale/zero-point, pack, mixed precision, excluding modules
Implementation: Device native low precision kernel or dequantization/conversion path
```

|The term|Specific meanings|I can't draw any conclusions from this.|
| --- | --- | --- |
| W4A16 |The main weights are 4 bits, activation is 16 bits.|KV is also 4bit, all layers are 4bit.|
| AWQ/GPTQ |Weights quantization method and corresponding artifact|All devices use the same kernel|
| Q4_K_M |GGUF K-quant mixed solution|K stands for k-means, which is 4BPW.|
| FP8 |Distinguishing between specific formats and scales|Any GPU has native FP8 matrix instructions.|
|KV quantization|Historical state of low precision storage|Weights, small, long context, no quality loss|
|Online quantization|Routes converted during loading/running|Unclassified costs equal to offline files|

The data area of 128 4bit weights is 64 bytes. If there are two additional bytes on the scale, it is at least 66 bytes, not including zero, alignment and sensitive layers. The capacity estimate cannot be multiplied by just 0.5 bytes. Low-precision source transfers to the F16 will not recover lost information.

## 2.4 Common formats explained

|Candidates|Applicable checks|Performance and quality risks|
| --- | --- | --- |
| FP16/BF16 |Support, weights, capacity, baseline|Weights bandwidth higher than memory|
| FP8 |Hardware generation, format/scale, model kernel|Software conversion, fallback, calibration and long-text quality|
| INT8/INT4 |Method, group, layout and calibration set|Small files don't have to be faster, tasks can get worse|
| AWQ/GPTQ |Engine, model and device kernel combinations|A different artifact cannot be attributed to bit width alone.|
| GGUF |Transformer/backend recognition architecture and tensor type|Unknown type, lack of tensor, auxiliary model not supported|
| IR |Device can be compiled, tokenizer/GenAI is complete|GPU success does not mean NPU compilation|
|KV low precision|Resources and quality comparison under length/ concurrency|Long-range retrieval, stability and backend restrictions|

## 2.5 Format selection for vLLM and llama.cpp

|Execute the route|Select the artifact|Requirements|
| --- | --- | --- |
| vLLM |Supported by HF architecture with FP16/BF16/FP8/AWQ/GPTQ etc.|Quantization kernels, templates, activity sequences, KVs and APIs|
| llama.cpp |Supported GGUF and required mmproj/assisted weights|tensor type, backend offloading, ctx, full output|
| OpenVINO GenAI |Full IR and pipeline configuration|Compilation device, shape, actual generation and output quality|
| MLX-LM/VLM |Supported MLX artifact|Tokenizer, template, processor, and unified memory|

GGUF is supported by some versions of vLLM based on actual functionality testing, not assuming the same as llama.cpp. The order of selection is engine support→ capacity→ quality → workload performance, you can't pre-select minimal files to solve all compatibility issues.

## 2.6 Choosing a format

```text
Objective tasks and device → Engine support matrix → Original precision baseline / candidate quantization
 ← Full Download with Summary → Uploads/Templates → Fixed quality
 → The same workload performance / peak → artifact adoption or fallback
```

|Examples|Specific choices and results|
| --- | --- |
| [RTX2060](../engineering/nvidia-rtx2060.md) |GGUF+CPU/GPU mix, focusing on total memory and offloading|
| [8060S](../engineering/amd-8060s.md) |Q4 about 58 tokens/s and BF16 about 10 tokens/s, quality and timing absence|
| [GB10 AWQ](../engineering/nvidia-gb10.md) |26B-A4B/31B 4/8bit groups, maintaining full latency; Not just bit width attribution|
| [Intel IR](../engineering/intel-arc-npu.md) |The fixed revision of INT4/INT8; GPU and NPU acceptance testing|
| [Mac](../engineering/apple-mlx.md) |GGUF/Metal and MLX artifact segmentation routes, visuals not based on text|

The original full text: [HF→GGUF→ quantization →Ollama](../engineering/gguf-ollama.md). Artifact delivery includes identity lists, complete files, conversion/quantisation records, summaries, functionality and quality results.
