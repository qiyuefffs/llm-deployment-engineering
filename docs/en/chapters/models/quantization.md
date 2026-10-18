# Quantization Options: From Putting It Down to Using It Well

[简体中文](../../../01-deployment-foundations/chapters/models/quantization.md) | **English**

[Contents](../../SUMMARY.md) · [Headquarters](../../02-capability-layers/02-model-formats-quantization.md) · [Previous: GGUF conversion](gguf-conversion.md)

## Overview of this chapter

On-device memory is limited, and quantization is usually the first capacity solution. It changes the representation of weights or intermediate states, reducing storage and data transfer, and introducing additional error and computational processing. A suitable solution should meet both capacity, quality and service performance, and not just see how many GB of files are reduced to how many GB.

This chapter combines the GGUF quantization in FlowUs, Intel IR INT4/INT8 and GB10 AWQ comparison records, and explains the selection and verification process. A continuous chapter of the conversion operation; Preserving historical data centers [Measurement documents](../../../01-deployment-foundations/evidence/measurements.json).

## 1. Separate format, method and bit width

GGUF, safetensors and OpenVINO IR are represented by artifact; AWQ,GPTQ is a quantization method or associated deployment route; INT4,INT8,FP8 describes a numeric value of bit width or type; The actual execution also depends on the layout and kernel. Document all these dimensions, rather than only stating “4bit.”

Q4_K_M belongs to the K-quant series of programs of llama.cpp. K in the name is not interpreted by k-means, nor does M represent the scale of the model parameter. Mixed quantization takes up the same amount of space for different tensors with different processing, metadata, and scaling parameters, so the final file size will not be strictly equal to the parameter quantity multiplied by 4 bits.

FP16 and BF16 themselves are also limited precision floating point representations, usually used in projects as baseline precision. The two indices differ from the tail distribution and cannot be interchanged by default on all models, devices and kernels. FP8, MXFP4, NVFP4 and others also need to confirm that specific formats and hardware are supported, not just by the number of digits in the name.

## 2. Determine where the capacity problem occurs.

If weights fail when loading, consider smaller models, lower bit width weights, shard or offloading. If the short request is normal, long context or concurrency is OOM, focus on checking the KV, workspace and activity sequence. The latter problem may require adjusting the context, concurrency, or KV indicates that continuing to compress weights is not necessarily the most effective.

In the case of pure instructional calculations using the 27B parameter, the ideal data volume for 4bit weights is about 13.5GB, or about 12.57GiB. This does not include scaled parameters, some high-precision tensors, KVs, workspaces and running surpluses. MoE models still need to store total weights even if only a few experts activate each token. Activation parameter is not equal to the amount of parameter to download or load.

## 3. Create a comparable group of candidates

Using the F16 source file from the previous chapter, generate Q4, Q5 and Q8 under the same llama.cpp submission:

```bash
for scheme in Q4_K_M Q5_K_M Q8_0; do
  llama.cpp/build-cpu/bin/llama-quantize \
    artifacts/gguf/Qwen3-0.6B-F16.gguf \
    artifacts/gguf/Qwen3-0.6B-${scheme}.gguf "$scheme" \
    > "records/quantize-${scheme}.log" 2>&1 || exit 1
done
sha256sum artifacts/gguf/*.gguf > records/gguf-sha256.txt
```

These are pending testing candidates. Do not immediately select the minimal file as the delivery version after the quantization script is successfully withdrawn. If an importance matrix or calibration data is required, authorized representative samples should be used to record sample sources, preprocessing, quantity and tool versions. Test sets should be separated from calibration sets to avoid using quantization as an independent quality verification.

## 4. Quality verification to cover actual tasks

Using a dozen simple questions, you can quickly spot templates, cuts, output formats, and severe degradation. It then prepares a set of fixed representative tasks, such as questions and answers in Chinese, extraction of long-text information, digital computation, JSON constraints and tool calls. Each record of input, expected or artificial rating rules, original output, end cause and actual token.

The task of having clear answers is to be judged by fixed rules; Open missions use pre-determined human dimensions, such as accuracy of facts, completeness of critical information, and availability of expression. Don't just let another model give you a total score without a scorecard and an original answer. Confusion can help compare language modeling changes, but it cannot replace structured interfaces, tool calls and business task acceptance testing.

In the CPU run, the Q8 model returned “2” for “2+2”; only two of the three smoke-test questions passed. It's a reminder: high bit width files, models, successful loading and interface 200 cannot replace quality checks. The result belongs to a particular model, template and parameter combination, and cannot be derived from this quality of all Q8 models.

## 5. Performance measurements first set boundaries

The same thread, the same offloading and the same length of engine pp/tg are measured for each candidate; The same request set, concurrency, flow rate and sampling are used to restart the service. Save weights memory, KV budget, peak memory and errors, and don't just cut the last line of tok/s.

Low bit width can reduce bandwidth stress, but may also require unpackaging and dequantization; The support and optimization for different kernels varies. Small batch decoding, long input prefill and high concurrency services, bottlenecks are not exactly the same. If the speed of one of the scenarios is promoted as quantization, it will be faster and easier to choose the wrong way.

### Historical observations of the Intel IR INT4/INT8

In the same Core Ultra7 256V, 16GB, OpenVINO 2026.2.1 records, the INT4 artifact is about 6.13GB, while the INT8 is about 9.46GB. The same 19 inputs and 128 outputs were measured at 21.1599 and 10.1047 tokens/s respectively, with Int4 approximately 2.09 times; TTFT is 184.02 and 169.73ms respectively.

INT4 generates a higher rate, and the first token of INT8 is earlier, and the two are not contradictory. TTFT and continuous generation measure different stages. Both outputs reached the upper limit at the reasoning stage, and the complete task quality also failed, so these numbers support the performance candidate selection, and cannot support the final line alone.

### Historical observation of AWQ 4bit/8bit

In the same series of 26B-A4B models as the author GB10, the 4bit/8bit output throughput below the c2 and 200 request is 60.08 and 47.81 tokens/s respectively, with an average TTFT of 272.97 and 338.92ms. The original record lacks model revision, calibration identity and quality results, and is therefore reserved for the overall deployment combination observation.

This group of results cannot answer that all 4bit models are faster, nor can the difference be attributed to bit width alone. The kernel, layout, model artifact and the environment need to be verified as well.

## 6. weights quantization and KV quantization separate experiments

Weights quantization solves the problem of part of the model's permanent storage; KV quantization reduces the occupancy of historical states, making it easier to influence long context and activity sequence capacities. Downloading FP8 or INT4 weights does not mean that KV automatically adopts the same representation.

In the experiment, the weights are kept stationary, and the separate adjustment K/V indicates that the check frame requires a combination of the quantization type, Flash Attention, and the backend. The quality set should add long context retrieval, cross-sectional references and multi-cycle tasks; The short question and answer passed is not enough to show that there are no obvious errors in the long context state.

## 7. What is the ultimate choice?

With the same result table, the candidate is recorded without a disconnected need for optimal quantization:

|Candidates|Peak memory|Quality passed rate|Target workload throughput|TTFT/ tail latency|Conclusions|
| --- | --- | --- | --- | --- | --- |
|Original precision|measured|Fixed topics|Measured with caliber|Measured with caliber|quality baseline|
|Q8/INT8 and so on|measured|Compared to baseline|Same as above|Same as above|Reasons for retaining or eliminating|
|Q4/INT4 and so on|measured|Compared to baseline|Same as above|Same as above|Reasons for retaining or eliminating|

First, eliminate candidates who do not meet the quality or capacity criteria, and then compare the speed and cost within the service objectives. If several schemes are substituted, specify the default schemes, low memory schemes and fallback conditions, and save recoverable artifact summaries and configurations.

## Eight: Complete engineering: Gemma 4 AWQ of GB10 comparison of four groups

FlowUs originally recorded not only a pair of 26B numbers, but also included AWQ4/8 bits of 26B-A4B and 31B respectively. All four groups were tested in GB10, 128GB, Ubuntu 24.04, vLLM0.19.0+cu130 environments. This is where you put the deployment configuration, workload and results together to verify.

### 8.1 First identify artifact and computational structure

26B-A4B and 31B belong to the same series, but one is the structure of the parameters of each step of activation, the other is a different computational structure and cannot be approximated by the total parameter quantity if the calculation quantity is approximate. 4bit/8bit needs to be checked.`quantization_config` Group size, symmetry, zero point, layer exclusion strategy and actual kernel

A directory name containing AWQ is not sufficient to confirm that each tensor uses the same representation. The original record lacks model revision and calibration status, so public tables are classified as the historical performance of four sets of artifact/service combinations, not taking bit width as the only influencing factor.

### 8.2 Preserving the Unified Service Configuration

The original four groups shared ctx16384, seqs2, batched4096, memory 0.65, prefix caching, eager, text testing disabled images/video. Each candidate is activated and released separately, and is not on the same device at the same time.

```bash
vllm serve /srv/models/gemma-4-26B-A4B-it-AWQ-4bit \
  --served-model-name gemma26-awq4 \
  --host 127.0.0.1 --port 8003 \
  --dtype auto --gpu-memory-utilization 0.65 \
  --max-model-len 16384 --max-num-seqs 2 \
  --max-num-batched-tokens 4096 \
  --enable-prefix-caching --enforce-eager \
  --limit-mm-per-prompt '{"image":0,"video":0}'
```

The remaining three groups were replaced by corresponding model directories with other names, with the other parameters identical. The backend of the quantization is selected by this version to read the artifact configuration, and the start log should save the actual kernel; It is not possible to force the same quantization backend name on all models without support.

In the original version, four sets of VRAMs were used for 81GB and the GPU limit was 0.65GB. It's closer to the engine's common budget/memory pool observation. **You can't put together four sets of weights the same size**. Model weights, KV pool and overall device occupancy should be stored in different fields; Without the original resources samples, the four groups of peak weights cannot be added to the table.

### 8.3 Measuring the same workload

The common workload is 200 requests, concurrency 2, random input target 1024, output maximum 128, random length ratio 0.1, 10 warmup, temperature 0. The order is as follows:

```bash
vllm bench serve \
  --backend openai-chat \
  --base-url http://127.0.0.1:8003 \
  --endpoint /v1/chat/completions \
  --model gemma26-awq4 \
  --tokenizer /srv/models/gemma-4-26B-A4B-it-AWQ-4bit \
  --dataset-name random --num-prompts 200 --max-concurrency 2 \
  --random-input-len 1024 --random-output-len 128 \
  --random-range-ratio 0.1 --request-rate inf --num-warmups 10 \
  --percentile-metrics ttft,tpot,itl,e2el --metric-percentiles 50,95,99 \
  --extra-body '{"max_tokens":128,"temperature":0.0}' \
  --save-result --save-detailed --result-dir results/gemma26-awq4
```

The model names and tokenizer are different parameters, different names for HTTP routing and tokenizer for constructing/counting. The new run should complement the fixed seed, input list and source code version; If strictly co-input is required, not only should the target length be fixed, but also the request data generated should be saved.

### 8.4 Four groups of practical results

All four groups have 200 successes and 0 failures, with actual input of 206,139 tokens and output of 25,696 tokens. For a surface budget of more than 200×128 output, the quality of the tool/service reporting should also be reviewed on a request usage basis; The system calculates throughput based on the original actual total, instead of replacing the original record with 25,600.

|Indicators| 26B-A4B AWQ4 | 26B-A4B AWQ8 | 31B AWQ4 | 31B AWQ8 |
| --- | --- | --- | --- | --- |
|Total time s| 427.70 | 537.49 | 1550.23 | 2587.60 |
|Output throughput token/s| 60.08 | 47.81 | 16.58 | 9.93 |
|request throughput req/s| 0.47 | 0.37 | 0.13 | 0.08 |
| TTFT mean ms | 272.97 | 338.92 | 1554.39 | 2879.26 |
| TTFT P50 ms | 264.55 | 335.99 | 1537.91 | 2846.44 |
| TTFT P95 ms | 283.52 | 359.94 | 1660.53 | 3027.51 |
| TTFT P99 ms | 418.72 | 504.80 | 2448.72 | 4703.69 |
| TPOT mean ms | 31.32 | 39.39 | 109.12 | 179.92 |
| TPOT P95 ms | 31.85 | 40.11 | 111.02 | 183.70 |
| ITL mean ms | 31.07 | 39.08 | 108.24 | 178.48 |
| ITL P99 ms | 94.44 | 118.89 | 405.37 | 737.11 |
| E2E mean ms | 4264.87 | 5360.53 | 15461.46 | 25809.91 |
| E2E P95 ms | 4626.35 | 5838.26 | 16744.49 | 27932.55 |
| E2E P99 ms | 4759.75 | 5889.24 | 17295.65 | 29163.73 |

The source tool also reports peak concurrent requests 4x, which conflict with the configuration's maximum concurrency 2; The field definition has no explanation, so it is not used to claim that four paths are executed simultaneously. The remaining values are retained for historical reporting, followed by the original request for time to reconstruct statistics.

### 8.5 How to draw useful engineering conclusions

With the 26B series, AWQ4 output throughput is about 1.257 times that of AWQ8; Approximately 1.670 times the result for the same 31B series. Both are observations of the environment and the artifact. Between 26B and 31B, the difference cannot be interpreted as a mere 5B parameter.

If the instructional requirement is set at TFT P95 below 500ms, the average TPOT below 50ms, then two sets of 26B configurations meet these two performance conditions, and two sets of 31B do not. Here's an example of how to use the acceptance testing threshold, which does not represent the original project's official SLO, nor does it replace the four groups with a complete quality passed conclusion.

The next step is to set a fixed quality set in the two performance candidates of 26B: numerical, long-form, structured output, tool calling and multipurpose. Only quality differences are acceptable and resources are stable, so AWQ4 can be selected. If the degradation of a class of tasks is evident, the AWQ8 or original precision route is retained and the applicable task is clearly stated.

## Nine: Quantization problems, first ranked by stage

Unknown quantization type, first check the frame/converter layout and artifact layout; The kernel cannot find, verify the target architecture, compilation product and support matrix; generate but decode, first compare tokenizer with template, and then compare quantization errors; Short subjects are normal, long contexts are degraded, check the KV representation, location/window and long text quality.

Gradual controlling can be done under three conditions: original precision, candidate quantization, and the same input. Initially, avoid introducing speculative decoding, prefix caching, or new sampling settings together, so output differences can be attributed to the correct change. If you encounter NaN or an error stop, keep the first log and minimal input instead of just the last HTTP error.

## How to register and fallback products

Each artifact saves the source model revision, conversion/quantization, tool commit, command, quantization configuration, calibration data description, file summary, permission and acceptance testing results. The name describes the series, size, quantization type and version, with no ambiguous final, new, best as the only identifier.

Service configuration References to a specific version directory, and updates to pass acceptance testing are deleted by default. When decay occurs, restore the corresponding model, tokenizer, template and engine configuration, not only change the weights files, but retain the new template and incompatible cache.
