# vLLM: From model directories to measurable inference services

[简体中文](../../../01-deployment-foundations/chapters/frameworks/vllm-service.md) | **English**

**The full engineering record:** [GB10 build with quantization acceleration](../../engineering/nvidia-gb10.md) · [Double 4080/A6000](../../engineering/nvidia-dual-gpu.md) · [W7900](../../engineering/amd-w7900.md) · [Ascend 310P3](../../engineering/ascend-310p.md)

[Contents](../../SUMMARY.md) · [General Chapter: Inference framework](../../02-capability-layers/03-inference-frameworks.md) · [Load testing methods](../performance/benchmarking.md)

## Overview of this chapter

The goal of service deployment is to get the application passed, stable interfaces to be fully answered, and to know what workloads the current service can handle. Installation success is just the beginning. You'll also need to check the artifact, backend, template, memory, normal and error request, and finally load testing.

This chapter is based on the GB10/Qwen FP8 project of the author of FlowUs. The historical environment was submitted for DGX Spark GB10, ARM64, 128GB, Ubuntu 24.04, CUDA13, and vLLM.`17d87168d`. It provides a real build problem, start parameter and 200 request summary. The model revision and full dependency locks are not stored with the original records, so the following are the operations of the historical project, without committing to the word-for-word reproduction of the old numbers in any new environment. The wheel did not re-enact the GPU project.

## 1. Fixed environment and model identity

First, look at the CPU architecture, driver and toolchain, and then decide whether to use the supporting image or source code. The ARM64 device cannot be directly attached to the wheel of the x86_64; CUDA driver compatibility does not mean that all dependency libraries, kernels or model structures are supported.

```bash
uname -m
nvidia-smi
nvcc --version
python --version
python -m pip show torch vllm
```

The source code path must first prepare the Python Torch, compiler and CUDA dependency according to the build requirements submitted. The original notebook does not have a complete installation lock, so it is not possible to install the entire environment by running a single pip command with an empty plug-in. At least kept in working environment `pip freeze`PyTorch version, compilation configuration and CMake log

The historical source code is prepared in the following order:

```bash
git clone https://github.com/vllm-project/vllm.git
cd vllm
git checkout 17d87168d
git submodule update --init --recursive
export CUDA_HOME=/usr/local/cuda-13.0
export PATH="$CUDA_HOME/bin:$PATH"
export LD_LIBRARY_PATH="$CUDA_HOME/lib64:${LD_LIBRARY_PATH:-}"
export VLLM_TARGET_DEVICE=cuda
export MAX_JOBS=8
```

Originally recorded for bypassing compilation errors in a specific FP4 kernel, `TORCH_CUDA_ARCH_LIST="12.0"` After execution `python -m pip install --no-build-isolation -e .`. The device's own computing capability is still 12.1. This bypass belongs to specific submit and kernel paths and should not be copied into all GB10 default build rules. Detailed errors [NVIDIA theme](../hardware/nvidia.md).

The model is placed `/srv/models/Qwen3.6-35B-A3B-FP8`. This is a unified public directory that needs to include weights, configuration and matching tokenizer. It's not a download address. The new reproduction should first confirm the accuracy of the repository, revisions and licenses from the model's public page, and continue after preserving the list of artifacts.

## 2. The first start-up with a small budget

The goal of the first launch is to load, short request and log check, without maximizing the context, activity sequence and memory ratio. Keeping the same model under different names, using a smaller starting budget:

```bash
vllm serve /srv/models/Qwen3.6-35B-A3B-FP8 \
  --served-model-name Qwen3.6-35B-A3B-FP8 \
  --host 127.0.0.1 --port 8001 \
  --tensor-parallel-size 1 \
  --max-model-len 4096 \
  --max-num-seqs 1 \
  --gpu-memory-utilization 0.80
```

This is the initial configuration of the teaching, not the configuration of the later historical performance tables. It is possible to see the error directly when the front stage is started. In the second terminal, a request is sent. When loading errors occur, save the first error and the environment to avoid adding multiple optimization parameters immediately, making the problem harder to locate.

Check the actual model structure with dtype, quantization kernel, attention backend, weights memory, KV capacity, graph compilation and warm-up, service ready.`gpu-memory-utilization` For example, it is not a device compute throughput utilization rate, nor is it a separation mechanism that strictly limits other process memory.

## 3. API checks are divided into four steps.

The first step is to check your health and model identity:

```bash
curl --fail-with-body http://127.0.0.1:8001/health
curl --fail-with-body http://127.0.0.1:8001/v1/models
```

The second step is to save the complete response to a non-flowing request:

```bash
curl --fail-with-body http://127.0.0.1:8001/v1/chat/completions \
  -H 'Content-Type: application/json' \
  -d '{"model":"Qwen3.6-35B-A3B-FP8","messages":[{"role":"user","content":"用三句话说明KV缓存的作用。"}],"max_tokens":256,"temperature":0,"stream":false}' \
  -o response.json
```

Verified `choices ` It's the real thing.`finish_reason` and usage. If the length limit is reached without a final answer, adding a reasonable budget or model-supported method of managing reasoning, can't generate a text string as a complete task passed.

The third step is to transform `stream:true ` and use `curl -N` Check the SSE event, increase the validity, end the event and cancel the client. The first character event is usually undocumented, and the client TTFT should adopt a clear calibre.

Step four is to test the wrong model name, empty messages, malformed JSON and long inputs, record HTTP status, the wrong type and subsequent health. the wrong return cannot reveal the path; The service should not be withdrawn due to a bad request. Error behaviour is measured in a fixed version without the interface compatibility declaration.

## 4. Restore the historical workload configuration

The following are the key performance parameters of the original recording, which the host monitors to the local loop; They are a running historical configuration and cannot replace the capacity budget of each device:

```bash
vllm serve /srv/models/Qwen3.6-35B-A3B-FP8 \
  --served-model-name Qwen3.6-35B-A3B-FP8 \
  --host 127.0.0.1 --port 8001 \
  --max-model-len 16184 \
  --max-num-batched-tokens 8192 \
  --max-num-seqs 4 \
  --gpu-memory-utilization 0.80 \
  --generation-config auto \
  --override-generation-config '{"temperature":0.6,"top_p":0.95,"top_k":20}' \
  --kv-cache-dtype fp8 \
  --load-format auto \
  --attention-backend flashinfer \
  --enable-prefix-caching \
  --enable-chunked-prefill
```

Other source commands `trust-remote-code`. It is only enabled when a fixed model is needed and the code has already been reviewed, not as a general default. Removing or adding such options should be recorded in the new run, not to mention that the commands after being rewritten have been retested.

This is where FP8 KV, Prefix Cache and Chunked Prefill are enabled. Historical reports indicate that the entire configuration is able to complete the workload without providing individual shutdown controls, so it is not possible to increase the percentage of allocation to each switch separately.

## 5. Run load testing with storage location

The historical workload is 200 requests, random input target 2048, output 128, rate of arrival inf, seed 42. The results of the new run were added to the directory and kept in detail:

```bash
mkdir -p results/gb10-fp8-burst
vllm bench serve \
  --backend openai-chat \
  --base-url http://127.0.0.1:8001 \
  --endpoint /v1/chat/completions \
  --model Qwen3.6-35B-A3B-FP8 \
  --tokenizer /srv/models/Qwen3.6-35B-A3B-FP8 \
  --dataset-name random \
  --random-input-len 2048 --random-output-len 128 \
  --num-prompts 200 --request-rate inf --seed 42 \
  --save-result --save-detailed \
  --result-dir results/gb10-fp8-burst
```

According to the fixed version `vllm bench serve --help` Check the parameters. Random input targets are not equal to the actual total input after the template is processed, and the output may be affected by EOS, reasoning or length limits, and should be specified in detail and usage.

The original record was 200 successes, 0 failures, total output of 25,600 tokens, total time of 297.46 seconds, output throughput of 86.06 tokens/s. The average TTFT is 148430.70ms, while the P99 TTFT is 293115.24ms. Activity sequence upper limit 4 is two levels with the client's sudden 200 request, and the additional request will be waiting; High TTFT suggests poor interaction experience in this emergency mode.

You can't write it to 200 concurrency at the same time in a GPU, and you can't use this result to represent low workload first token latency. The next step should be to complement limited concurrency with controlled arrival rates to find workpoints that meet the target TTFT and tail latency. Specific processes [Section of load testing](../performance/benchmarking.md).

## 6. Standards for stopping, restoring and completing

The front-end service stops using Ctrl+C, confirming that the port and process have been withdrawn; Do not terminate other models with a vague process name batch. When the service is managed by systemd or container, use the corresponding instance stop commands.

The available results of this chapter shall include: Fixed environment and model identity, final commands, boot logs, normal and error request, request-by-request performance data, resources, sampling and conclusions. Historical works provide a part of it, which must be completed when new deployments are made. Successful deployments should describe the model, functionality, length, and workload that has passed, so that the next engineer knows where to go next.

## Seven, complete links from image files to streaming answers

This section uses GB10 to deploy Qwen3-VL-8B in FlowUs to organize the original native image base64 with SSE snippets into a program that can be used independently. Example images are converted to public test cards generated by the repository to avoid requiring the reader to search for private inputs.

### 7.1 Clearly draw the execution link

```text
Local PNG → Bytes/Abstract → base64 data URL → chat request
 → Service parsing → processor and image tokens → visual encoder
 → Language model generated → SSE increase → answer.txt and event recording → content acceptance testing
```

Every single episode is a failure. HTTP 400 first checks the fields and input restrictions; Weights load successfully but the image 500 needs to check the processor/encoder; The flow has begun but not ended, given the production ceilings, the client and the engine. Don't deal with all the mistakes of addiction and max_model_len.

### 7.2 Public images ready for answers

In the repository root directory, use Pillow to generate 960×640 test cards:

```bash
python -m pip install Pillow==12.1.1
python docs/01-deployment-foundations/examples/make_vision_input.py \
  --output docs/01-deployment-foundations/assets/vision-input
```

! [Reusable visual input test card](../../../01-deployment-foundations/assets/vision-input/vision-card.png)

Notes: Program-generated public input containing four lines of text and red squares, blue circles, green triangles; This is a test input, not a model run screenshot. Response [Expected fields and summaries](../../../01-deployment-foundations/assets/vision-input/expected.json).

The check items are titled, numbered DEMO-042, number 3, amount 128.50, and the order and color of the three graphs. Text recognition and graphic recognition separate records. Requiring the model not to read is uncertain, and to avoid successfully completing the full text.

### 7.3 Single model entrance using the original design

Prepare a complete catalog of images and Qwen3-VL-8B supported by ARM64/GB10 and confirm that the processor, template and weights match. Start inside the support container, retain the original memory 0.8, port 8007, and use ctx8192, seqs1 as an additional smoking budget:

```bash
vllm serve /srv/models/Qwen3-VL-8B \
  --served-model-name qwen3-vl-8b \
  --host 127.0.0.1 --port 8007 \
  --tensor-parallel-size 1 \
  --max-model-len 8192 --max-num-seqs 1 \
  --gpu-memory-utilization 0.80
```

The smoking budget is not the same as the historical performance configuration. This section provides run-of-the-mill materials and acceptance testing methods, without historical model output for new test cards. Check whether the model requires additional templates or code options, according to the fixed artifact and version.

After the service is ready, you can send pictures with a short article in plain text. This will confirm whether the additional failure is caused by visual pathways. The original Qwen3-VL30B record was set to 100000/131072 context; This does not mean that the input in this section is so large, nor does it have the corresponding image quality results.

### 7.4 Request and save the entire process

repository provided [vision_client.py](../../../01-deployment-foundations/examples/vision_client.py) It's only a Python standard library. The client reads the image, generates the data URL, saves the request.json, receives the SSE and records the arrival time of the event, and finally saves the answer.txt and summary.json.

```bash
python docs/01-deployment-foundations/examples/vision_client.py \
  --url http://127.0.0.1:8007/v1/chat/completions \
  --model qwen3-vl-8b \
  --image docs/01-deployment-foundations/assets/vision-input/vision-card.png \
  --max-tokens 512 --output results/qwen-vl-card
```

The key structure of the request is as follows: The script automatically fills in the data URL without the need to manually spell base64:

```json
{
  "model": "qwen3-vl-8b",
  "messages": [{"role": "user", "content": [
    {"type": "text", "text": "逐行读取全部文字，再描述图形。"},
    {"type": "image_url", "image_url": {"url": "data:image/png;base64,..."}}
  ]}],
  "temperature": 0,
  "max_tokens": 512,
  "stream": true
}
```

`...` For structural interpretation only, real requests must use full bytes. The client's local file path is not visible to the server when remote calling, and the data URL addresses the input and transmission; A file name string will not automatically upload images.

### 7.5 How to read saved results

|Documents|Check the content|
| --- | --- |
| request.json |Model name, prompt, image field and output limits|
| events.jsonl |Each data event, relative to the time of arrival and end mark|
| answer.txt |Real words, figures, graphics and illusions|
| summary.json |HTTP status, start time, reason for termination, usage (when service is provided)|
|server.log, save as an alternative|processor, image token, encoder and engine errors|

The first_content_s of the script is the first non-empty text snippet, not the image encoder, nor is the empty role event the first token. A single SSE segment may contain multiple tokens, so no tokens/s are counterfeited from the number of segments. The service does not send the usage time field as null, and cannot add to the token counting with a character count.

`finish_reason=length` indicate that the budget has been reached and that the final sentence and all acceptance testing items must be checked; Just HTTP200 is not enough. Identifying the past does not prove that complex forms, handwriting, multi-page PDFs have been passed, and should gradually increase the difficulty with the corresponding true value.

### 7.6 Where to change when reusing Mac services

Another way of using this system is through the history of MLX-VLM `type=input_image、image_url为字符串` The script is provided `--image-style mlx` It's the right deal. Port and model ID are available for this service:

```bash
python docs/01-deployment-foundations/examples/vision_client.py \
  --url http://127.0.0.1:8081/v1/chat/completions \
  --model /srv/models/Qwen3.6-35B-A3B-bf16 --image-style mlx \
  --image docs/01-deployment-foundations/assets/vision-input/vision-card.png \
  --output results/mlx-vl-card
```

If the upgraded MLX-VLM is changed to another protocol, it should be adjusted according to its schema, and the old field cannot be considered a long-term standard. Images are similarly favorable for acceptance testing, but the visual preprocessing, model and cache of different frameworks may still be different, and cross-device rankings need to unify these conditions.

## Eight, OCR, the boundary between the deployment of VLM and Omni

GB10's granite-docling-258M records are TP1/PP1, max-num-seqs 512, batched 8192, chunked prefill, memory 0.9. The model parameter does not represent that 512 document requests can be committed to meeting latency; Image resolution, multi-page, output structure and actual scheduling are still to be measured.

The document task first determines the delivery object, such as the text, form elements or DocTags structure in order to be read. Typical VLM describes a table and a transcript of the document, with each format being a different task. Acceptance testing should cover leaks, misspellings, sequences, column relationships with images, not output length as quality.

Qwen3-Omni 30B is recorded as TP1/PP1, memory 0.9, port 8008; Qwen 2.5-Omni7B records memory of 0.8. When deployed, establish a functionality matrix: text input, image input, audio input, text output, audio output and flow patterns. Model architecture has a capability that is not equal to the full protocol supported by current vLLM inputs.

First verify input, load and output, and then receive real-time audio. The audio tasks also include sampling rates, audio channels, blocks, lead audio latency, continuous RTF and cancellation behavior. Don't try to write chat text successfully and make Omni run its full capabilities.

## How to configure a service configuration into a stable version

The final command retains only the necessary and verified switches. First, create short text→ full text→ single chart→ multi-chart/goal resolution→goal length→goal workload  Acceptance testing staircase, where each layer saves request, response, log and resources. Functionality not updated model/template/encoder, functionality passed and adjusted scheduling and quantization.

When updating a model, processor, framework, or template, run the same set of public inputs again; The results of the old version were retained as a return counter. Delivery is a clear device, artifact, interface and capability range, not just a command to start.
