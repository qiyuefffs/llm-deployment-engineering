# DSpark: block drafting and adaptive verification

[简体中文](../../../01-deployment-foundations/chapters/performance/dspark.md) | **English**

[Contents](../../SUMMARY.md) · [MTP](speculative-decoding.md) · [Benchmarking](benchmarking.md) · [Source review](../../evidence/2026-10-refresh.md)

**Sources checked: 2026-10-18.** These procedures follow official implementations and have not been executed on a GPU for this repository. Commands, teaching calculations, and upstream experiments are identified separately.

## 1. What DSpark changes

Ordinary decode runs the target to advance, usually by one token per step. Speculative decoding proposes candidates with a cheaper module, then verifies them in a batch. The goal is fewer expensive sequential steps for the same answer.

Drafting also takes time. An autoregressive drafter predicts candidates sequentially; DFlash proposes a block in one forward pass. DSpark adds a semi-autoregressive Markov head so positions can use information from the preceding token. A confidence head can estimate acceptance and help select candidates worth verifying.

There are two decisions: **how to produce useful drafts, and how much compute to spend verifying them.** vLLM adaptive verification addresses the latter. Current detailed developer documentation also covers other supported model-based drafters; adaptive speculation and DSpark are not interchangeable names.

| Method | Engineering role | Required artifacts |
| --- | --- | --- |
| MTP | Propose with a supported multi-token prediction structure | Native MTP weights or a prescribed assistant |
| EAGLE-3 | Use target hidden states to assist drafting | A target-specific drafter |
| DFlash | Propose a block using diffusion | Matching checkpoint and feature interface |
| DSpark | Add semi-autoregressive dependence, optionally with confidence prediction | Matching DSpark checkpoint |
| Dynamic SD | Choose K by batch-size interval | Engine support and measured intervals |
| Adaptive verification | Allocate verification slots using confidence and execution cost | Compatible runner, attention, graphs, and estimator |

**DSpark is an algorithm; DGX Spark is hardware.** See [DGX Spark](../hardware/dgx-spark.md) for ARM64, unified memory, and CUDA.

## 2. Why fixed K can slow high-concurrency serving

Low-concurrency decode is often bandwidth limited with compute headroom. More verification positions may advance more tokens at relatively little extra cost.

At higher concurrency, extra candidates compete with an already busy target batch for compute, attention, KV, and graph resources. Low-acceptance positions consume work before being discarded and can make speculation slower than ordinary decode.

```text
Effective progress = target-confirmed tokens advanced
                   / (draft + verification + scheduling/sampling/transfer time)
```

This explains a tradeoff, not a predicted speedup. If accepted length rises 20% but step time rises 40%, generation slows. Acceptance rate alone misses this.

### 2.1 Allocating verification slots

Illustrative conditional acceptance values 0.9, 0.8, 0.5 give prefix survival probabilities 0.9, 0.72, 0.36. Later positions generally offer less value at the same cost.

vLLM ranks candidates across requests: a confident request's fifth position can outrank another request's first. The global budget also uses measured startup step costs. A probability threshold alone does not reproduce this scheduler.

These are teaching values, not trained confidence values or measurements.

## 3. Check support first

Documentation snapshots:

- llama.cpp: `5aeac37a35b44fde4bdffaec9159f2fcb253b622`.
- vLLM: `2365177ddda7714502e4df7a1669cc79c0a4dfd0`.
- DeepSpec: `005e03b81cec38b7da6399833d609ee89a2587f2`.

They do not guarantee support in every released binary. Record your actual commit, model revisions, and executable.

| Check | Required match | Failure response |
| --- | --- | --- |
| Target/draft | Family, hidden-state interface, tokenizer, training target | Use the matching drafter |
| Mode | Thinking/non-thinking and task distribution | Measure each mode separately |
| Precision | Target, draft, KV, and kernels | Restore a working baseline |
| Memory | Weights/shared tensors, both states, workspace | Reduce one budget or model size |
| Execution | Attention, graphs, sampling, parallelism | Use a supported combination |

DeepSpec publishes Qwen3-4B/8B/14B and other paired checkpoints. Released experiments use non-thinking data from each corresponding target; acceptance does not automatically transfer to long reasoning. Training also needs target-feature caches: the default Qwen3-4B setup is approximately 38 TB. A small drafter does not imply a lightweight training pipeline.

## 4. Complete llama.cpp Qwen3-4B procedure

This example uses Linux Bash and NVIDIA CUDA. Other backends require independent build and compatibility checks. Approximately 8 GB of BF16 target weights excludes the draft, KV, and workspace.

### 4.1 Create directories and pin the source

```bash
mkdir -p dspark-lab/models dspark-lab/artifacts dspark-lab/records
cd dspark-lab
git clone https://github.com/ggml-org/llama.cpp.git
git -C llama.cpp checkout 5aeac37a35b44fde4bdffaec9159f2fcb253b622
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r llama.cpp/requirements.txt huggingface_hub
git -C llama.cpp rev-parse HEAD > records/llama-commit.txt
python -m pip freeze > records/conversion-packages.txt
```

Save resolved dependencies. Build prerequisites are covered in the [CUDA chapter](../hardware/nvidia.md).

### 4.2 Download matching revisions

Resolve each public model revision once, then download it:

```bash
python - <<'PY'
import json
from pathlib import Path
from huggingface_hub import HfApi, snapshot_download

items = {
    "target": ("Qwen/Qwen3-4B", "models/Qwen3-4B"),
    "draft": ("deepseek-ai/dspark_qwen3_4b_block7", "models/DSpark-Qwen3-4B"),
}
revisions = {}
api = HfApi()
for role, (repo, directory) in items.items():
    revision = api.model_info(repo).sha
    snapshot_download(repo_id=repo, revision=revision, local_dir=directory)
    revisions[role] = {"repo": repo, "revision": revision, "directory": directory}
Path("records/model-revisions.json").write_text(
    json.dumps(revisions, indent=2), encoding="utf-8")
PY
```

Later reproductions must reuse those revisions rather than resolve main again. Check model licenses/access requirements; keep credentials out of scripts and records.

### 4.3 Convert both artifacts

```bash
python llama.cpp/convert_hf_to_gguf.py models/Qwen3-4B \
  --outtype bf16 --outfile artifacts/Qwen3-4B-BF16.gguf
python llama.cpp/convert_hf_to_gguf.py models/DSpark-Qwen3-4B \
  --target-model-dir models/Qwen3-4B \
  --outtype bf16 --outfile artifacts/Qwen3-4B-DSpark-BF16.gguf
sha256sum artifacts/*.gguf > records/gguf-sha256.txt
```

`--target-model-dir` supplies the tokenizer and relevant shared tensors. A drafter is not an interchangeable chat model. Start with BF16 and introduce target quantization separately; ordinary quantizers may not support the draft's Markov/confidence modules.

### 4.4 Build and inspect available flags

```bash
cmake -S llama.cpp -B llama.cpp/build-cuda \
  -DGGML_CUDA=ON -DCMAKE_BUILD_TYPE=Release
cmake --build llama.cpp/build-cuda \
  --target llama-server llama-bench -j 4
llama.cpp/build-cuda/bin/llama-server --version > records/server-version.txt
llama.cpp/build-cuda/bin/llama-server --help > records/server-help.txt
rg 'draft-dspark|spec-draft-conf-min|gpu-layers-draft' records/server-help.txt
```

Use `grep -E` without `rg`. Missing DSpark options indicate a version or executable-path problem.

### 4.5 Baseline A

```bash
llama.cpp/build-cuda/bin/llama-server \
  -m artifacts/Qwen3-4B-BF16.gguf \
  -ngl 99 -c 8192 -np 1 -b 512 -ub 128 -fa on --jinja \
  --alias qwen3-dspark-lab --host 127.0.0.1 --port 8080 \
  > records/baseline.log 2>&1
```

Check `/health` and `/v1/models` from another terminal, then short prompts and a fixed quality set. The foreground command continues running while serving.

### 4.6 Stop A and run B

Press Ctrl+C in A's terminal; confirm device allocations and port 8080 are released:

```bash
llama.cpp/build-cuda/bin/llama-server \
  -m artifacts/Qwen3-4B-BF16.gguf \
  -md artifacts/Qwen3-4B-DSpark-BF16.gguf -ngld 99 \
  --spec-type draft-dspark --spec-draft-n-max 7 \
  --spec-draft-p-min 0 \
  -ngl 99 -c 8192 -np 1 -b 512 -ub 128 -fa on --jinja \
  --alias qwen3-dspark-lab --host 127.0.0.1 --port 8080 \
  > records/dspark-k7.log 2>&1
```

`-ngld` controls draft offloading. Confirm both placements in logs. K=7 matches this checkpoint's block; longer requested drafts remain constrained by the trained block.

B disables confidence trimming. Change only `--spec-draft-p-min`, for example to 0.3 or 0.5, for further groups. Per-request trimming is **not** vLLM's cost-based allocation across requests.



At this snapshot, the prose guide still names `--spec-draft-conf-min`, while `common/arg.cpp` and `common/speculative.cpp` implement `--spec-draft-p-min`. The commands here follow the implementation; verify your binary help.

### 4.7 Fix functional input and timing

Use the same non-thinking setting in both groups:

```bash
curl --fail-with-body http://127.0.0.1:8080/v1/chat/completions \
  -H 'Content-Type: application/json' \
  -d '{"model":"qwen3-dspark-lab","messages":[{"role":"user","content":"计算12乘13，只输出结果。"}],"chat_template_kwargs":{"enable_thinking":false},"temperature":0,"max_tokens":64}'
```

The expected number is 156. Also test Chinese, code, numbers, JSON, long text, and multiple turns, retaining every answer. Use the shared [matrix script](../../../01-deployment-foundations/examples/run_optimization_matrix.py) for A/B/C with identical `--extra-body` template settings. HTTP performance does not establish quality.

## 5. vLLM fixed-K and adaptive routes

The official example uses `DeepSeek-V4-Flash-DSpark`: 284B total and 13B activated parameters. Budget total mixed-precision weights, not 13B. Its 4×GB300 example is a server setup, not a single-GB10 promise.

Complete capacity, model, and parallel setup using the matching recipe first. Add this fragment to its working `vllm serve` command; it is not a standalone command:

```json
{
  "method": "dspark",
  "model": "/srv/models/DeepSeek-V4-Flash-DSpark",
  "num_speculative_tokens": 7,
  "draft_sample_method": "probabilistic",
  "enable_adaptive_verification": true
}
```

A removes speculation; B sets adaptive verification false; C sets it true. Keep revision, sampling, parallelism, KV, graphs, and input fixed. Changing greedy drafting in B to probabilistic in C introduces another variable.

### 5.1 Requirements at this snapshot

- Attention must tolerate device-decided query lengths; incompatible combinations are rejected.
- FULL CUDA graphs are required; `--enforce-eager` is incompatible.
- LoRA and pipeline parallelism are unsupported.
- Without a confidence head, the online estimator needs full draft logits, so `use_local_argmax_reduction` is rejected.

Detailed documentation covers EAGLE, MTP, DFlash, and other model-based drafts, while some overview text still says “DSpark only.” Resolve differences using fixed-version implementation, detailed documentation, configuration checks, and startup validation.

### 5.2 Long-context profiling

```bash
export VLLM_ADAPTIVE_VERIFICATION_PROFILE_CONTEXT_LEN=131072
```

This changes synthetic startup-profile KV length; the snapshot default is 8192. It changes neither the serving limit nor 128K quality status. Evaluate it separately when long context represents the actual workload.

## 6. Experiment matrix

| Group | Change | Workload | Question |
| --- | --- | --- | --- |
| A | No speculation | c1/c2/c4/c8; short/long input-output pairs | Ordinary decode baseline |
| B | Fixed-K DSpark | Same requests and sampling | Net value of drafting |
| C | Same K ceiling plus adaptive verification or trimming | Same as B | Incremental budget value |
| D | Fixed config, increasing arrival rate | Steady and bursty traffic | Queuing and crossover below baseline |

Repeat at least three times and alternate A/B order. Retain actual tokens, successes/failures, TTFT P50/P95/P99, TPOT, SSE gaps, wall-clock throughput, accepted/proposed tokens, accepted length, draft/verification time, and peak memory.

Adopt only a configuration improving the chosen latency/goodput target on the same quality tasks and load, with resource headroom. Provide ordinary decode or a validated dynamic policy if gains disappear at higher concurrency.

## 7. Failure reference

| Symptom | Check | Action |
| --- | --- | --- |
| Unknown `draft-dspark` | Version, PATH, commit | Use the explicit new binary |
| Shape/token mapping error | Pairing and conversion | Reconvert with the fixed target |
| Low acceptance | Mode, tasks, template, precision | Align training conditions; shorten K |
| Unexpected memory | Placement, both states, graphs, workspace | Record buffers; reduce one budget |
| Fast c1, slow c8 | Saturated verification batch | Shorter K or supported adaptive policy |
| Adaptive eager/attention rejection | FULL graphs and query-length support | Use a supported combination |
| TTFT unchanged | Optimization acts mainly on decode | Report phases separately |

## 8. Official sources

- [DeepSpec](https://github.com/deepseek-ai/DeepSpec/tree/005e03b81cec38b7da6399833d609ee89a2587f2).
- [DSpark paper](https://arxiv.org/abs/2607.05147).
- [Pinned llama.cpp documentation](https://github.com/ggml-org/llama.cpp/blob/5aeac37a35b44fde4bdffaec9159f2fcb253b622/docs/speculative.md).
- [Pinned vLLM adaptive verification](https://github.com/vllm-project/vllm/blob/2365177ddda7714502e4df7a1669cc79c0a4dfd0/docs/features/speculative_decoding/adaptive_verification.md).
- [Model card](https://huggingface.co/deepseek-ai/DeepSeek-V4-Flash-DSpark): read hardware, precision, encoding, and execution requirements together.
