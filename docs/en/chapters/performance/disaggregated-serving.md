# Disaggregated inference: prefill/decode, KV transfer, and MoE

[简体中文](../../../01-deployment-foundations/chapters/performance/disaggregated-serving.md) | **English**

[Contents](../../SUMMARY.md) · [Caching](cache-scheduling.md) · [Parallelism](parallelism.md) · [Engines](../frameworks/serving-engines.md)

**Sources checked: 2026-10-18.** These official-documentation-based procedures have not been executed on multiple GPUs for this repository.

## 1. Start with the two inference phases

Prefill processes input and builds generation state; decode uses that state to continue generating. Long prefills can interrupt active decoding and increase streaming gaps. Chunked prefill reduces interference but retains shared devices.

PD disaggregation assigns the phases to different instances and transfers KV plus necessary metadata. Each side can use different devices, batches, parallelism, and capacity. Transfer, routing, queues, and recovery add costs.

```text
Client → Router → Prefill → KV transfer/state mapping → Decode → SSE
                 input       blocks/positions/identity    sampling/cancellation
```

Phase isolation does not guarantee throughput improvement. On one local GPU, first evaluate chunked prefill, prefix reuse, token budgets, and quantization.

## 2. Distinguish three KV mechanisms

| Mechanism | State involved | Goal | Cost |
| --- | --- | --- | --- |
| Prefix cache | Matching computed input state | Avoid repeated prefill | Residency, indexing, eviction |
| KV offload | Device state moved to/from another memory tier | Expand state capacity or retained prefixes | Host memory, links, transfers |
| PD transfer | State moved between inference instances | Separate phases | Network, layout conversion, lifecycle |

NIXL is a transfer library; Mooncake provides KV-related storage/transfer capabilities. Engines integrate them through connectors. Installing a package does not create a complete PD deployment.

## 3. Estimate transfer cost

```text
KV bytes = 2 × layers × KV heads × head_dim × input tokens × bytes/element
Transfer lower bound ≈ actual bytes / effective link bandwidth
```

Teaching example: 32 GQA layers, 8 KV heads, head dimension 128, BF16, and 8192 input tokens produce approximately 1 GiB. At 10 GbE's theoretical 1.25 GB/s, that takes about 0.86 s before overhead; at effective 1 GB/s it takes about 1.07 s. These are calculations, not hardware measurements.

Paging, MLA, windows, quantization, overlap, and reuse change actual traffic. Compare measured transfer costs against the original phase interference.

## 4. Minimal two-GPU SGLang procedure

Each GPU must hold a full Llama-3.1-8B-Instruct instance and cache. Obtain access and a complete local artifact. Prepare matching SGLang, router, and NIXL versions using official installation instructions and preserve the resolved environment.

### 4.1 Inspect the environment

```bash
mkdir -p records/pd
python -m pip show sglang sglang-router nixl > records/pd/packages.txt
python -m pip freeze > records/pd/requirements-resolved.txt
python -m sglang.launch_server --help > records/pd/server-help.txt
python -m sglang_router.launch_router --help > records/pd/router-help.txt
nvidia-smi topo -m > records/pd/topology.txt
```

Confirm disaggregation flags exist. First validate an ordinary instance with the same model, template, precision, lengths, and quality set.

### 4.2 Prefill terminal P

```bash
CUDA_VISIBLE_DEVICES=0 python -m sglang.launch_server \
  --model-path /srv/models/Llama-3.1-8B-Instruct \
  --disaggregation-mode prefill \
  --disaggregation-transfer-backend nixl \
  --host 127.0.0.1 --port 30000 \
  > records/pd/prefill.log 2>&1
```

### 4.3 Decode terminal D

```bash
CUDA_VISIBLE_DEVICES=1 python -m sglang.launch_server \
  --model-path /srv/models/Llama-3.1-8B-Instruct \
  --disaggregation-mode decode \
  --disaggregation-transfer-backend nixl \
  --host 127.0.0.1 --port 30001 \
  > records/pd/decode.log 2>&1
```

Each process sees one locally numbered GPU0. Do not additionally select local GPU1 for decode. Confirm loading and transfer initialization on both sides.

### 4.4 Router terminal R

```bash
python -m sglang_router.launch_router \
  --pd-disaggregation \
  --prefill http://127.0.0.1:30000 \
  --decode http://127.0.0.1:30001 \
  --host 127.0.0.1 --port 8000 \
  > records/pd/router.log 2>&1
```

Send requests to the router:

```bash
curl --fail-with-body http://127.0.0.1:8000/v1/models
curl --fail-with-body http://127.0.0.1:8000/v1/chat/completions \
  -H 'Content-Type: application/json' \
  -d '{"model":"/srv/models/Llama-3.1-8B-Instruct","messages":[{"role":"user","content":"Explain prefill and decode in two sentences."}],"max_tokens":128,"temperature":0}'
```

Use the ID returned by `/v1/models`. Confirm prefill activity on P and generation on D. Then test public long inputs, retaining both logs and transfer bytes. A correct answer without KV transfer does not establish PD success.

### 4.5 vLLM connector route

The current NIXL example uses `--kv-transfer-config`:

```json
{"kv_connector":"NixlConnector","kv_role":"kv_both"}
```

Use one version's complete example for both instances, routing, and request association. Merely adding this JSON to two servers does not complete the protocol. The vLLM feature remains experimental.

## 5. EP and PD are independent

EP distributes experts and dispatches/combines their token results. PD separates generation phases. They can be combined but solve different problems.

| Component | Main work | Metrics |
| --- | --- | --- |
| Attention TP/DP | State and request assignment | Per-rank KV, replication, synchronization |
| MoE EP | Dispatch, experts, combine | All-to-all time and routing skew |
| Prefill pool | Larger token batches | Input tokens/s, queue, TTFT |
| Decode pool | Repeated generation steps | TPOT, ITL, resident state, output tokens/s |

vLLM MoE sharding depends on the TP×DP combination. Dense-model assumptions about complete DP replication do not automatically describe experts. Enabling EP does not establish topology, communication, or kernel compatibility.

Popular experts can overload one rank while others wait. Record per-expert token counts and communication before evaluating EPLB or adding devices. DeepEP throughput and latency paths have different workload requirements.

## 6. Acceptance and rollback

Compare equal device counts: independent ordinary replicas, one model-parallel replica, and PD. Twice the hardware prevents a pure architecture speedup claim.

Record model/template identity, KV format/layout, block size, TP/DP/EP, effective link throughput, transfer bytes, both queues, latency tails, throughput, errors, and peak memory. Different TP layouts may require supported gather/scatter or staging.

On your own test deployment, stop one decode worker. Check router errors, cancellation, KV release, recovery, and a repeated fixed input. State leaks after timeouts can escape short benchmarks.

Return to ordinary serving when transfer erases gains, recovery/state correctness fails, or ordinary replicas meet the SLO.

## 7. Official sources

- [SGLang PD](https://docs.sglang.ai/advanced_features/pd_disaggregation.html).
- [Pinned vLLM PD](https://github.com/vllm-project/vllm/blob/2365177ddda7714502e4df7a1669cc79c0a4dfd0/docs/features/disagg_prefill.md).
- [vLLM EP](https://docs.vllm.ai/en/stable/serving/expert_parallel_deployment/).
- [NIXL](https://github.com/ai-dynamo/nixl) · [Mooncake](https://github.com/kvcache-ai/Mooncake).
