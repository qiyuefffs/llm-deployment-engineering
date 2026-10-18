# Speculative decoding: MTP, EAGLE, DFlash, and DSpark

[简体中文](../../../01-deployment-foundations/chapters/performance/speculative-decoding.md) | **English**

**The full engineering record:** [GB10 Off/Off MTP, DFlash Full build and test the original](../../engineering/nvidia-gb10.md)

[Contents](../../SUMMARY.md) · [General chapter of performance](../../02-capability-layers/04-memory-performance.md) · [Template of experimental records](../../templates/experiment-record.md)

## Overview of this chapter

Predictive decoding attempts to come up with multiple candidates at a lower cost and then verify by the target model, reducing the gradually generated serial costs. Whether or not it will benefit depends on the candidate's quality, acceptance rate, verification costs, device resources and workload. It's not going to accelerate by switching on all models.

This chapter combines MTP on/off and DFlash records in FlowUs. Historical throughput can be used to learn how to analyze, but the original request and quality evidence is incomplete and cannot be added to the optimization results of this round of reproduction.

## Current engineering workflow

Sources checked on 2026-10-18. The sections below describe current configurations; the original measurements later in this chapter retain their historical environments and evidence limits. See [DSpark](dspark.md) for its full llama.cpp procedure and adaptive verification.

### MTP training is not automatically MTP inference

MTP teaches prediction of several future positions. Inference acceleration requires published prediction layers or an assistant, engine support, and target verification. A paper using MTP does not establish that released weights contain the module.

Check config, weight indexes, and the engine's exact model_type. Quantized repositories may omit MTP weights. A missing module cannot be repaired by adding `method=mtp`.

| Route | Needs | Costs and constraints |
| --- | --- | --- |
| Native MTP | Prediction layers and engine implementation | Extra forward/state; quantization support varies |
| Gemma assistant | Matching assistant checkpoint | Uses a dedicated MTP path despite the model field |
| Standalone draft | A smaller compatible model | Weights, KV, drafting, vocabulary alignment |
| EAGLE/DFlash/DSpark | Target-specific trained drafter | Features, conversion, and version requirements |
| N-gram/suffix | Repeated input/history patterns | No large additional drafter; workload-dependent gains |

### Minimal vLLM MTP reference

The official example uses `XiaomiMiMo/MiMo-7B-Base`. In a compatible environment with complete local weights:

```bash
vllm serve /srv/models/MiMo-7B-Base \
  --served-model-name mimo-mtp-lab \
  --host 127.0.0.1 --port 8000 \
  --tensor-parallel-size 1 \
  --max-model-len 4096 --max-num-seqs 4 \
  --max-num-batched-tokens 4096 --gpu-memory-utilization 0.80 \
  --speculative-config '{"method":"mtp","num_speculative_tokens":1}'
```

This is a base model. Use an appropriate completion interface rather than assume a chat template:

```bash
curl --fail-with-body http://127.0.0.1:8000/v1/completions \
  -H 'Content-Type: application/json' \
  -d '{"model":"mimo-mtp-lab","prompt":"The capital of France is","temperature":0,"max_tokens":32}'
```

Start at K=1. For the baseline, preserve model, port, budgets, and sampling, and remove the whole speculative config. Start each group sequentially. Increase only K afterward and compare progress, verification cost, and total time.

### Gemma assistants need an explicit method

The current documented form is:

```bash
vllm serve /srv/models/gemma-4-E2B-it \
  --tensor-parallel-size 1 --max-model-len 8192 \
  --host 127.0.0.1 --port 8000 \
  --speculative-config '{"method":"mtp","model":"/srv/models/gemma-4-E2B-it-assistant","num_speculative_tokens":1}'
```

Use paired artifacts and observe their license/access requirements. If logs identify the assistant as `draft_model`, the installed engine may lack the dedicated MTP path. Do not reuse the older historical image command that omits method; verify support and use a matching version.

### Quantizing the draft output head

Current developer documentation provides `draft_lm_head_quantization` with fp8 or nvfp4. It creates a quantized copy for an MTP drafter sharing an unquantized target lm_head; target verification retains its own head. This does not quantize the whole target.

It requires Model Runner V2 and compatible kernels. The copy consumes memory and may change acceptance length. Evaluate it separately after ordinary MTP, especially for bandwidth-limited large-vocabulary workloads; measure draft time, acceptance, and remaining KV budget.

### Dynamic SD versus adaptive verification

Dynamic SD uses `num_speculative_tokens_per_batch_size` entries `[start_batch,end_batch,K]`. Derive intervals from your own workload. The reviewed documentation lists EAGLE, EAGLE-3, and DFlash testing; DP>1 disables the dynamic intervals and falls back to static K.

Adaptive verification instead assigns budgets from request confidence and measured costs. Its FULL-graph requirements are separate; see [DSpark](dspark.md).

### Run an interpretable experiment

1. Save target/draft revisions, quantization, tokenizer, template, engine, and device.
2. Without speculation, complete a quality set and record answers, termination, actual lengths, and resources.
3. Add the shortest supported draft; verify mechanism activation through logs and acceptance counters.
4. Fix inputs/sampling; sweep K and c1/c2/c4/c8 with at least three repetitions.
5. Evaluate dynamic policies, quantization, and caching separately before combining changes.

Distribution-preserving speculative sampling targets the distribution of the **given target model**. It does not restore pre-quantization information or guarantee identical strings across kernels, random streams, or batches. Verify rejection sampling, settings, and task quality; one matching answer is not statistical equivalence.

Sources: [Pinned MTP documentation](https://github.com/vllm-project/vllm/blob/2365177ddda7714502e4df7a1669cc79c0a4dfd0/docs/features/speculative_decoding/mtp.md) · [Pinned Dynamic SD](https://github.com/vllm-project/vllm/blob/2365177ddda7714502e4df7a1669cc79c0a4dfd0/docs/features/speculative_decoding/dynamic_speculative_decoding.md).

## 1. Understand what happens in a round

Normal decodes typically add a target model token each step. The guessing route first presents a number of candidates, then verifies them by the target model, accepts a candidate, and, if necessary, corrects and continues. The draft may come from another model, the model's own forecast head or other mechanisms.

The more tokens that are accepted effectively, the lower the number of rounds in the target model sequence. But draft generation and verification are also calculated, stored and scheduled. If the acceptance rate is low, the batch is larger or the additional model takes up significant resources, the overall gains may be small or even negative.

Different algorithms have specific conditions for distribution, sampling and model structure. The framework claims to support a mechanism that is not equivalent to the current quantization, TP and attention combinations; Check the fixed version and run quality and statistical checks.

## 2. Historical results of the MTP

The authors document the use of the same set of models, input 512 and output upper limit 256, compared to the shutdown and start of MTP, candidate number 3. The following is a summary:

|concurrency/request number|Turn off the throughput|Turn on the throughput|Observing the Change|
| --- | --- | --- | --- |
| 1 / 20 | 20.82token/s | 30.14token/s | +44.76% |
| 2 / 40 | 36.87token/s | 48.92token/s | +32.68% |
| 4 / 80 | 49.33token/s | 75.57token/s | +53.19% |

There are pairs between the concurrency switches, but you can't just look at this table. The average ITL of c1 is from 46.12ms to 78.27ms, and the TTFT of c2 is from 352.24ms to 608.22ms. An increase in gross output does not guarantee an improvement in initial token and flow intervals.

It should be combined with the original ITL definition, batch acceptance of the output form generated, actual token and request-by-request time analysis. The original record lacks the original request-by-request files, model revision and quality equivalence evidence, so these phenomena cannot be packaged and all users are addicted faster.

## 3. How to write 2.03 times DFlash?

The historical aggregate throughput of 21.52 was 43.74 tokens/s, observing a ratio of about 2.03. But the configuration changes simultaneously: context 32768→8192, activity sequence 1→8, memory budget 0.70→0.85, baseline is obviously eager and the other side is not explicitly set.

These changes can affect resources, scheduling and execution, so it is not possible to write a single Dflash file as a 2.03-fold hash, which is suitable for writing a combination of two deployments. Recognising that attribution conditions are insufficient can help the next round of experiments to be designed more clearly.

## 4. How can an explanatory set of experiments be reconstructed?

First, set the target model and artifact, environment, context, sequence budget, chart pattern, cache, request set and sampling. Group A that does not enable speculation is recorded and group B that enables speculation is kept consistent except for additional parameters required by the mechanism. If the framework has to link configuration adjustments, the experiment is clearly a combined solution.

Each group starts with a warm-up, runs multiple rounds, and alternates in order to reduce temperature, cache, and time drift. Record the number of candidates, acceptance rate or length of acceptance, draft expenditure, target model, execution, actual output and resources. Additional VRAM and verification costs should also be observed when increasing candidate lengths separately.

Quality Check using fixed task sets and original answers. A combination of frameworks, sampling and quantization still needs to be verified for the realisation of the distribution that should theoretically be maintained; For schemes that do not guarantee the same output, the correctness of the task and the scoring rules should be compared. It is not possible to reduce the completion time as an acceleration only because the output is shorter.

## 5. How do you decide to keep it?

If the goal is local interaction, focus on TTFT, output flow density, complete response and power consumption; If the goal is service capacity, focus on the total output that meets latency and quality constraints. Acceptance rates, throughput and tail latency can be used together to determine whether the gains are worth the additional model and maintenance costs.

Preserving the boot configuration and artifact identity before and after switching. Quality degradation, increased error rate or resource instability can return to normal decode baseline. In the absence of complete controls, the candidate must be registered in advance to avoid using historically beautiful numbers as a delivery standard.

## Gemma MTP: Restore the service conditions first

The original two recordings used GB10 and image.`vllm/vllm-openai:gemma4-0505-cu130 `. The target model is ` gemma-4-26B-A4B-it `MTP routes are loaded.` gemma-4-26B-A4B-it-assistant`. This is an implementation of an assisted artifact, which cannot be confused with an in-built predictive headline and the costs of an assistant model.

Shared conditions include TP1, BF16, ctx8192, seqs4, batched8192, memory 0.90, async scheduling, disabling image/audio input. The following shows the service parameters in the fixed image, the main model and the assistant need to prepare the complete artifact first:

```bash
vllm serve /srv/models/gemma-4-26B-A4B-it \
  --served-model-name gemma4-mtp --host 127.0.0.1 --port 8015 \
  --tensor-parallel-size 1 --dtype bfloat16 \
  --max-model-len 8192 --max-num-seqs 4 \
  --max-num-batched-tokens 8192 --gpu-memory-utilization 0.90 \
  --limit-mm-per-prompt '{"image":0,"audio":0}' \
  --async-scheduling \
  --speculative-config '{"model":"/srv/models/gemma-4-26B-A4B-it-assistant","num_speculative_tokens":3,"draft_tensor_parallel_size":1}'
```

The control service uses the same main parameter, removes the speculative-config, and changes the port to 8016 with the `gemma4-base` Another name. Testing two services in sequence to reduce resource competition; If the artifact does require remote code, review the source and enable the corresponding option.

### 6.1 Original workload and running order

Input goal 512, output 256, c1/c2/c4 and 20/40/80 request respectively. The number of requests for each concurrency grade is the same, and the number of requests between the three grades is different. The new replication suggests the same quantity, multiple rounds and alternate switching sequences, while the original table is still preserved under the conditions of the time.

```bash
vllm bench serve \
  --backend openai-chat --base-url http://127.0.0.1:8015 \
  --endpoint /v1/chat/completions --model gemma4-mtp \
  --tokenizer /srv/models/gemma-4-26B-A4B-it \
  --dataset-name random --random-input-len 512 --random-output-len 256 \
  --num-prompts 20 --max-concurrency 1 \
  --save-result --save-detailed --result-dir results/mtp/c1
```

c2 changes 40 request / concurrency 2, c4 changes 80 request / concurrency 4; Baseline uses 8016 as the model name. Random seed, sampling, reasoning, warmup, and cache states should also be preserved to avoid actual inconsistencies in the input of the two groups with the same target length.

## Seven: Full results of MTP: throughput, wait and see with the flow

|Indicators|C1 Closed|C1 opened|c2 closed|C2 opened|C4 Closed|C4 opened|
| --- | --- | --- | --- | --- | --- | --- |
|Number of requests| 20 | 20 | 40 | 40 | 80 | 80 |
|Always output the token| 5120 | 5120 | 10240 | 10240 | 20480 | 20480 |
|Time s| 245.92 | 169.88 | 277.70 | 209.31 | 415.19 | 271.00 |
|Output of the token/s| 20.82 | 30.14 | 36.87 | 48.92 | 49.33 | 75.57 |
|Average TFT ms| 488.14 | 462.90 | 352.24 | 608.22 | 562.37 | 596.33 |
|Average TPOT ms| 46.30 | 31.49 | 53.06 | 38.38 | 79.19 | 50.41 |
|Average ITL ms| 46.12 | 78.27 | 52.85 | 99.52 | 78.88 | 131.48 |
|Acceptance rate| — | 38.07 | — | 40.77 | — | 41.16 |

Throughput improved in all three grades, but TTFT did not improve uniformly, and ITL reporting values increased. The guessing route may validate and output a token at a time, and the way events are packaged will affect the client interval. Therefore, the total time required for each output token on average for the pending pending pending pending pending pending and pending continuous flow events may have different trends.

To determine if users are more comfortable, you need the original SSE time, each event token and page display strategy. It is not possible to confirm the uniformity of the output from the polymer table alone, nor is it possible to explain the ITL enlargement as the target model.

### 7.1 The acceptance rate should be checked against the subtractor

c1 records 2032 draft tokens, 8128 draft tokens, 3094 accepted tokens, with an acceptance rate of about 38.07%; Reported acceptance length 2.52. The configuration candidate number is 3, while the tool split position statistic shows four positions of 0 to 3, indicating that the tool's internal counting may contain additional position/verification behaviour, and cannot automatically rewrite the report with the tool's configuration 3.

The acceptance rate and the average length of acceptance are not the same proportion. Drafts, draft tokens, accepted tokens, acceptance rates and tool definitions must be stored at the same time. With an acceptance rate of 40%, it is not possible to calculate how much the throughput will increase, as it is also time consuming to submit candidates, target verification, fallback and output transfer.

Peak output throughput and configuration concurrency are inconsistent fields that are not recommended in the system. Reserving a comparison of the total output/total time that can be calculated, and reserving a problem for unexplained fields to avoid choosing a column that looks best.

## Eight:DFlash:GB10 source code and execution path

This recording environment is different from the previous Qwen FP8 service: vLLM commit `2cc008e7b`, CUDA 13.0.88, PyTorch 2.11.0+cu130, Python 3.12.13, a 20-core ARM CPU, and approximately 119GiB unified memory. The target is Qwen 3.6-35B-A3B BF16 with support for the DFlash drafter.

### 8.1 What conditions to preserve before construction

The first steps are to record CPU architecture, device capabilities, PyTorch builds, CUDA_HOME,nvcc/ptxas, source code commits and changes. Environmental use `TORCH_CUDA_ARCH_LIST=12.1a` and specify ptxas; This value is bypassed by 12.0 in 17d87168d and does not belong to the same construct and cannot be merged into a fixed set of suggestions.

Original process used repository `use_existing_torch.py ` Keep the torch already built, then `--no-build-isolation` compilation . This requires the proactive preparation and recording of the entire buildup of dependency; It doesn't automatically guarantee that the ABI is correct. When modifying the requirements to fit ARM64/FlashInfer, save the diff and verify the final actual installation.

```bash
git rev-parse HEAD
python -m pip freeze > build-packages.txt
python - <<'PY'
import torch
print(torch.__version__, torch.version.cuda)
print(torch.cuda.get_device_name(0), torch.cuda.get_device_capability(0))
import vllm
from vllm.v1.spec_decode.dflash import DFlashProposer
print(vllm.__version__, DFlashProposer.__name__)
PY
```

Imported modules are first checked, and the first service generated may trigger the JIT,attention or CUDA Graph path. Previously encountered `linear_attention not supported by flash_attn` The direction of processing is to confirm the backend selection of the mixed layer, and not to force an unsupported implementation on all layers.

### 8.2 Enabling and confirming mechanisms in place

High throughput configuration: The following routes, listeners and logs are organized into public format:

```bash
vllm serve /srv/models/Qwen3.6-35B-A3B \
  --host 127.0.0.1 --port 18000 \
  --served-model-name qwen36-dflash --dtype bfloat16 \
  --max-model-len 8192 --max-num-seqs 8 \
  --gpu-memory-utilization 0.85 \
  --speculative-config '{"method":"dflash","model":"/srv/models/Qwen3.6-35B-A3B-DFlash","num_speculative_tokens":5}'
```

Drafter If the pass auto_map loads code, the corresponding remote code option should be enabled after a fixed repository review. Start by completing the short queries, verifying the actual appearance of DFlash, draft and acceptance in the log/indicator, and then load testing. The command writes that the speculative-config is not the same as the expectation mechanism for a certain hit in operation.

## Nine: Full DFLASH controls the next round of experiments.

The original workload for spec_bench, 50 request, concurrency 1, seed 42, output 256, actual input 13655, output 12800.. The results of the combination of the two deployments are as follows:

|Indicators|Common decode combinations|DFlash combined|
| --- | --- | --- |
| ctx / seqs | 32768 / 1 | 8192 / 8 |
|memory budget| 0.70 | 0.85 |
| eager |Clearly opened|Not explicitly set|
|Time s| 594.69 | 292.62 |
|Output of the token/s| 21.52 | 43.74 |
| TTFT mean / median ms | 893.20 / 213.45 | 294.13 / 261.00 |
| TTFT P99 ms | 16024.24 | 571.91 |
| TPOT mean / P99 ms | 43.14 / 43.34 | 21.80 / 29.03 |
| ITL mean / P99 ms | 42.97 / 53.15 | 72.82 / 87.71 |
|Acceptance rate / Acceptance length| — | 48.15% / 3.41 |

Baseline mean TTFT was much higher than the median, and P99 reached 16 seconds, indicating slow outlier requests. The absence of the original timeline cannot be judged whether it is compilation, cache, queue or otherwise. It is not possible to attribute all TTFT changes directly to DFlash.

The next round can be divided into four groups: A normal decode + fixed budget; B only adds DFlash; Budget after adjustment of C ordinary decode +; D DFlash+ adjusted budget. A/B looks at mechanism changes, A/C looks at service configuration changes, C/D looks at the benefits of the new budget mechanism. If a combination is not supported by this version, it is clearly stated that complete single-variable control cannot be formed.

The number of candidates should also be scrutinized separately, from small to large. Increasing the length of the drafts will result in more ineffective calculations when the acceptance rate of the back position decreases; Observe the acceptance length, memory, target verification time and final Goodput, and then decide whether to increase it. The expected multiples in the original text are not included in the measured results table.

## X. How to write a verifiable speculative decoding conclusion

Conclusions first describe the device, target/drafter identity, version, task and workload; Add the actual output numbers, total time, TTFT, TPOT, flow intervals, accept statistics and resources; Finally, the quality, set, error and fallback are explained.

For these two historical records, the combined schematic differences between the three sets of MTP paired observations and DFlash can be preserved. To be further called Delivability Optimization, the original request needs to be complemented with quality return. They are already enough to be used to learn complete experimental methods without the need to pass over configuration differences to enhance conclusions.
