# How can a local LLM respond sooner when two users ask at once?

[简体中文](CASE.md) | **English**

## Deploy Qwen3.8-27B Q4 with llama.cpp and measure Flash Attention

A machine with one 24GB GPU can hold a quantized 27B model. But can it answer two users at once? How long will they wait for the first text? Does enabling Flash Attention actually help?

This tutorial follows a completed ModelScope Notebook experiment, from GPU checks and model downloads through service startup, requests, and comparison of results. The measured device was an NVIDIA A10. For the same longer-question workload, with 20 requests per configuration at concurrency 2, P95 time to first output fell from **1.7893 seconds** to **1.5740 seconds**, a reduction of approximately **12.0%**. These observations apply to this machine and workload; they are not a guaranteed improvement on other devices.

> Measured on 2026-10-17. Commands and images refer to an experiment that was already completed. Screenshots were taken afterward to verify saved inputs, logs, and results. They do not prove that downloading, compilation, and every benchmark were rerun when the screenshots were captured. See the [technical appendix](CASE_TECHNICAL.en.md) for metric definitions and limitations.

- **Audience:** readers deploying a local model in a GPU Notebook for the first time who want to determine whether a parameter change improved performance.
- **Difficulty and time:** commands are explained step by step; you need to be able to copy commands into a Linux terminal. Initial preparation takes approximately 1–3 hours.
- **Environment:** a ModelScope GPU Notebook Linux terminal, one A10 24GB, and llama.cpp `b10430`.
- **Deliverables:** a local model service, valid and malformed request records, four rounds of comparison data, a CSV, and a recommendation report.

## The problem

Consider two colleagues sharing an internal question-answering service. It answers questions, but when both submit a request, the page takes a long time to show text. The administrator needs to establish whether the service failed or simply slowed down, and whether changing one inference parameter reduces that wait.

The comparison keeps the **model, machine, input questions, and other service parameters fixed, and changes only Flash Attention from off to on**. First verify functionality, then measure waiting time, aggregate processing speed, success rate, and VRAM usage. Finally, generate a report that can be traced back to individual requests.

```text
Public Chinese questions
    ↓
llama.cpp loads the GGUF model on an A10
    ↓
The script simulates one or two users and records every request
    ↓
Compare Flash Attention off / on
    ↓
Summary tables, recommended configuration, and raw evidence
```

### Terms used in the commands

- **GGUF** is a model weight file format. The file used here is approximately 16.8GB and ends in `.gguf`.
- **Q4_K_M** is a quantization scheme. Roughly, it stores weights at lower precision so a 27B model can fit more easily on a 24GB GPU. Quantization can affect answer quality; this experiment does not evaluate that effect.
- **llama.cpp** runs the model. Its `llama-server` exposes the local HTTP API used by the scripts.
- **Flash Attention** is an attention computation implementation used during inference. Here, `-fa off` and `-fa on` control it. Whether it is faster must be measured under the same workload.
- **Time to first output**, abbreviated **TTFT** here, runs from sending a client request to receiving the first nonempty streaming text. The model may emit reasoning text first, so this is not necessarily the first character of the final answer.
- A **token** is a unit of model text processing, not necessarily one Chinese character. The experiment records actual input and output token counts. `max_tokens=64` allows at most 64 generated tokens.
- **JSONL** stores one JSON record per line. Each input line is a question; each result line describes a request.
- **SHA256** acts as a file fingerprint. Matching the recorded hash establishes that the same file is used in the comparison. It says nothing about model quality.
- **Concurrency 2** means that the script maintains at most two simultaneous requests, representing two users. It does not test hundreds or thousands of users.

**P95** describes the slower end of the waiting-time distribution. Sort the durations from shortest to longest; with 20 requests, the nearest-rank method used here selects the 19th value. The fastest request alone does not represent everyday experience.

## Prerequisites

The experiment used a Linux GPU instance in the [ModelScope Notebook workspace](https://www.modelscope.cn/code/workspace). The recorded GPU was an NVIDIA A10 with 24564 MiB VRAM and driver 550.54.15. Reserve at least **35GB** under `/mnt/workspace` for the model, caches, CUDA toolchain, and build files. Initial setup usually takes **1–3 hours**, mostly downloading approximately 16.8GB of weights and compiling the program. Extend or restart the Notebook instance first if too little runtime remains.

The tutorial directory contains:

```text
cases/llama-cpp-flash-attention/
├── CASE.en.md               English tutorial
├── CASE_TECHNICAL.en.md     Metrics and experimental limitations
├── scripts/
│   ├── setup.sh             Download model, prepare CUDA, build llama.cpp
│   ├── smoke.py             Valid and malformed requests
│   ├── bench.py             Performance measurements
│   └── report.py            Summarize results
├── data/
│   └── workload.jsonl       8 public Chinese questions
└── figures/                 Actual verification screenshots
```

The tutorial, scripts, sample input, screenshots, and summary tables are in the [public repository](https://github.com/qiyuefffs/llm-deployment-engineering). Complete raw results also remain in the temporary ModelScope workspace, which is not a public download URL. Public raw evidence and reproduction in a fresh environment are still incomplete; the current repository alone does not establish that all submission requirements have been met.

Run the following commands in the **ModelScope Notebook Linux terminal**. Do not copy prompts such as `root@...#` or `case$`. The reproduction directory is `/mnt/workspace/llm-serving-diagnosis/cases/llama-cpp-flash-attention`. The original experiment ran at the repository root, and its screenshots retain the old paths. Reorganizing files did not rerun the GPU experiment.

## Step 1: open the terminal and check the machine

Open the [ModelScope Notebook workspace](https://www.modelscope.cn/code/workspace), sign in, and create or start a GPU instance. This record used an A10 24GB. Wait until the instance is running, then enter Code Editor. Open the terminal panel at the bottom; use the Terminal menu to create a terminal or `Ctrl+J` to show the bottom panel if needed. Once a prompt such as `root@...:/mnt/workspace#` appears, paste the Linux commands there. Button positions can change between page versions; confirm that **commands execute inside the GPU instance**, rather than in your computer's PowerShell.

Run:

```bash
nvidia-smi
df -h /mnt/workspace
python3 --version
```

`nvidia-smi` shows the GPU, VRAM, and driver. The recorded values were `NVIDIA A10`, `24564 MiB`, and `550.54.15`. `df -h` checks available workspace disk space; `python3 --version` checks Python 3. If the first command cannot find a GPU, check that the Notebook is a GPU instance before downloading the model.

Install the download and build tools:

```bash
apt-get update
apt-get install -y aria2 cmake g++ make python3-pip curl git
```

`aria2` downloads large files over multiple connections. `cmake`, `g++`, and `make` build llama.cpp; `curl` checks the service. Continue only after installation finishes without errors. Notebook images may differ in packages and permissions; retain the complete terminal output when an error occurs.

## Step 2: get the project and inspect the questions

In the **cloud terminal**, retrieve the tutorial, scripts, and inputs from the public repository:

```bash
cd /mnt/workspace
git clone https://github.com/qiyuefffs/llm-serving-diagnosis.git
cd /mnt/workspace/llm-serving-diagnosis/cases/llama-cpp-flash-attention
ls scripts data
```

`ls` should show four scripts and `workload.jsonl`. If the repository already exists, open its `cases/llama-cpp-flash-attention` directory and check the files. Back up any original results before reorganizing an older workspace. Uploading through the web IDE previously failed, so the public repository is the preferred way to obtain the files.

Each line of `workload.jsonl` is a question. The script separates short and longer questions and measures them separately:

```bash
wc -l data/workload.jsonl
python3 -c 'import json,collections; x=[json.loads(s) for s in open("data/workload.jsonl",encoding="utf-8")]; print(collections.Counter(r["bucket"] for r in x)); print([r["id"] for r in x])'
sha256sum data/workload.jsonl
```

Expect **8 rows**, with **4** each in `short` and `long`, IDs `s01`–`s04` and `l01`–`l04`, and SHA256 `18de6bb66f8cfe3e5dcad5df776cc200728c564aa781516dd5670007d73571f3`. These author-written public deployment questions represent acceptance-test needs. They contain no customer data and are not presented as production traffic.

![Input verification: 8 questions, 4 in each category, and SHA256.](figures/00-workload-check.png)

*Figure 1. Verify the input with `wc`, Python, and `sha256sum`. This screenshot checks the saved experimental input after the experiment.*

## Step 3: download the model and build the service

Fix both the model and llama.cpp version so the comparison is not affected by changing either. The model is [Abiray/Qwen3.8-27B-Q4_K_M-GGUF](https://www.modelscope.cn/models/Abiray/Qwen3.8-27B-Q4_K_M-GGUF), file `Qwen3.8-27B-Q4_K_M.gguf`. The engine is pinned to [llama.cpp b10430](https://github.com/ggml-org/llama.cpp/tree/b10430).

Run in the project directory:

```bash
cd /mnt/workspace/llm-serving-diagnosis/cases/llama-cpp-flash-attention
bash scripts/setup.sh
```

The script downloads the model using `aria2c -x 8 -s 8`, retrieves the pinned llama.cpp source, prepares a local CUDA 12.4 toolchain in this Case directory, and builds `build-cuda12/bin/llama-server`. CUDA 12.4 ran successfully on this A10; the instance's bundled CUDA 13.0 caused compatibility issues. The compatibility reported by `nvidia-smi` is not the installed toolchain version. Keep the pinned versions for reproduction. By default, the script derives its working directory from its own location.

The downloaded model is exactly **16,810,714,400 bytes**. If interrupted, `aria2` supports resuming with `-c`. Check the original error before rerunning. The script verifies SHA256 for both the model and source archive; do not benchmark mismatched files.

After setup, run the checks below. The `export` command puts the local CUDA library first in the current terminal's runtime library search path. **Repeat this export whenever you open a new terminal.**

```bash
cd /mnt/workspace/llm-serving-diagnosis/cases/llama-cpp-flash-attention
export LD_LIBRARY_PATH="$PWD/cuda12/cuda_nvcc-linux-x86_64-12.4.131-archive/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
./build-cuda12/bin/llama-server --help >/dev/null && echo "llama-server: OK"
sha256sum models/Qwen3.8-27B-Q4_K_M.gguf
```

`llama-server: OK` confirms that the executable starts. The model SHA256 must be `6a96cc760fc65cc6b9ea7f1922e3ff8b2a48c09f209456f23bbae9ef7032c867`. Hashing 16.8GB may take a while; no immediate output does not necessarily mean a hang. Matching source, hash, and version is necessary for a meaningful comparison.

![A10 GPU, executable startup, and model SHA256 checks.](figures/01-environment-model-hash.png)

*Figure 2. A10, driver version, `llama-server: OK`, and weight hash. The image shows the terminal after the commands above completed.*

**Build evidence limitation:** `logs/build-cuda12.log` retains an earlier failed compilation and cannot prove a successful build. After correction, the binary passed `--help`, loaded the model, and served requests, but the complete successful build log was not retained. `setup.sh` consolidates those successful operations and has not been run from scratch in a second fresh instance. Complete that validation before formal submission.

## Step 4: start the baseline service

The baseline here has **Flash Attention disabled**, labeled `fa_off`. Check for an old service first:

```bash
ps -o pid,args -C llama-server
```

Continue if no process is listed. Otherwise, verify that the process belongs to this project and stop it using the shutdown command at the end. Do not start a second service on the same port 8000.

Start the service:

```bash
mkdir -p logs results
./build-cuda12/bin/llama-server \
  -m models/Qwen3.8-27B-Q4_K_M.gguf \
  --host 127.0.0.1 --port 8000 -ngl 99 -c 4096 -np 2 -fa off \
  > logs/server-fa-off.log 2>&1 &
SERVER_PID=$!
echo "$SERVER_PID" > logs/server.pid
```

The main options are:

- `-m` points to the downloaded, verified model.
- `--host 127.0.0.1 --port 8000` allows access from the instance itself. This tutorial does not configure authentication for external access; **do not expose the port directly to the public internet**.
- `-ngl 99` attempts to offload model layers to the GPU; `-c 4096` sets the total context; `-np 2` creates two parallel slots. The recorded log showed 2048 tokens per slot.
- `-fa off` selects the baseline. Later, change only this value to `on`.
- `> logs/... 2>&1 &` writes logs to a file and runs the service in the background. `logs/server.pid` stores its process ID for shutdown.

The health endpoint may initially return `503 Loading model`. This indicates loading, **not a failed benchmark request**. Reading the weights from the workspace took approximately 3 minutes. Check periodically:

```bash
curl -sS http://127.0.0.1:8000/health
tail -n 12 logs/server-fa-off.log
```

Continue only after health returns `{"status":"ok"}` and the log shows `model loaded` and `listening on http://127.0.0.1:8000`. If 503 persists, check `ps -p "$(cat logs/server.pid)" -o pid,args` and `tail -n 60 logs/server-fa-off.log` to confirm the process is still running.

## Step 5: send a valid request and a malformed request

Performance measurements are useful only when the service works. `smoke.py` sends a valid Chinese question followed by a malformed request and saves both responses in `results/smoke.json`:

```bash
python3 scripts/smoke.py --output results/smoke.json
```

The valid request returned HTTP **200**. The malformed request supplied `messages` as a string and returned HTTP **400**. This verifies valid input handling and rejection of malformed input. If the valid request is not 200, inspect health and logs. If the malformed request returns 200, record that error handling did not meet expectations.

The script prints a summary. In this run, the fields included `"valid_status": 200`, `"valid_elapsed_s": 4.1286`, and `"malformed_status": 400`. `valid_elapsed_s` measures this one functional request; it is not P95 for the later 20-request group.

Read the saved status codes without resending requests:

```bash
python3 -c 'import json; x=json.load(open("results/smoke.json")); print("normal",x["valid_response"]["status"],"malformed",x["malformed_response"]["status"])'
```

![Saved valid request status 200 and malformed request status 400.](figures/03-smoke-status.png)

*Figure 3. Status codes read from the existing `smoke.json`, which also contains the complete requests and responses.*

This step also warms up the service. Subsequent measurements use the **loaded, warmed service** and exclude initial weight loading.

## Step 6: measure waiting time with Flash Attention off

Keep `-fa off` and explicitly set the input, output directory, configuration label, concurrency, requests per group, and output limit:

```bash
python3 scripts/bench.py --workload data/workload.jsonl --output results \
  --config-id fa_off --concurrency 1 2 --requests 8 --max-tokens 64
```

`--concurrency 1 2` tests one user and two users. Each is measured for both question categories: **4 groups of 8 requests**, not 8 requests in total. `--max-tokens 64` uses the same generation cap for both service configurations. Some answers are truncated, so this experiment measures **serving performance**, not answer completeness.

The script prints group summaries and writes:

```text
results/fa_off/
  metadata.json             Model, configuration, concurrency, request counts
  long_c2.jsonl             Longer questions, concurrency 2, one request per line
  long_c2_gpu.json          GPU samples once per second
  long_c2_summary.json      Group success and latency summary
  ...                       Other groups and configurations
```

For example, `cat results/fa_off/long_c2_summary.json` showed 8/8 successes and TTFT P95 **1.7796 seconds** in the initial run. If your numbers differ, first compare `successes` with `requests`, then check the model hash, hardware, and service parameters. Do not judge optimization from the fastest observation alone.

Inspect one request:

```bash
sed -n '1p' results/fa_off/long_c2.jsonl
```

The output is one JSON record. `request_id` identifies the request; `prompt_id` links it to `data/workload.jsonl`; `status` is the HTTP status; `ttft_s` and `total_s` are first-output and total duration in seconds; `prompt_tokens` and `completion_tokens` are actual token counts; `error` stores failure details. Check for 8 rows with `wc -l results/fa_off/long_c2.jsonl`. Summary values must be traceable to these records.

## Step 7: enable Flash Attention and repeat

Stop the previous service and wait for it to exit:

```bash
kill "$(cat logs/server.pid)"
while kill -0 "$(cat logs/server.pid)" 2>/dev/null; do sleep 1; done
```

Restart with the same model and parameters, changing **only `-fa on`**:

```bash
./build-cuda12/bin/llama-server \
  -m models/Qwen3.8-27B-Q4_K_M.gguf \
  --host 127.0.0.1 --port 8000 -ngl 99 -c 4096 -np 2 -fa on \
  > logs/server-fa-on.log 2>&1 &
SERVER_PID=$!
echo "$SERVER_PID" > logs/server.pid
```

Wait for health to return `ok`:

```bash
curl -sS http://127.0.0.1:8000/health
ps -p "$(cat logs/server.pid)" -o pid,args
```

The `ps` command line must include `-fa on`. The screenshot also shows `-c 4096 -np 2` and the listener at `127.0.0.1:8000`:

![Flash Attention enabled: parameters, health, and loading log.](figures/02-server-fa-on-health.png)

*Figure 4. Post-experiment verification of the optimized configuration. Health returns `ok`; the log shows the model loaded and 2048 tokens per slot.*

The instance also retained the launch-command history:

![Shell history showing fa off and fa on launch parameters.](figures/05-start-command-history.png)

*Figure 5. Compare `-fa off` and `-fa on`. History supports parameter verification but does not replace service logs or request results.*

Repeat the same four initial groups:

```bash
python3 scripts/bench.py --workload data/workload.jsonl --output results \
  --config-id fa_on --concurrency 1 2 --requests 8 --max-tokens 64
```

All 8 longer-question requests at concurrency 2 succeeded, with TTFT P95 **1.5469 seconds**, compared with 1.7796 seconds for `fa_off`. With only 8 requests, nearest-rank P95 is the slowest sample. A larger follow-up test is needed.

## Step 8: repeat with 20 requests per group

The service still has `-fa on`. Run:

```bash
python3 scripts/bench.py --workload data/workload.jsonl --output results \
  --config-id fa_on_repeat --concurrency 2 --requests 20 --max-tokens 64
cat results/fa_on_repeat/long_c2_summary.json
```

This tests only concurrency 2, with **20 requests** in each category. The longer-question group had 20/20 successes, TTFT P95 **1.5740 seconds**, total-duration P95 **4.5937 seconds**, and aggregate output throughput **28.1866 token/s**.

![Summary JSON for 20 longer-question requests with Flash Attention on.](figures/06-fa-on-repeat-summary.png)

*Figure 6. Actual values in `fa_on_repeat/long_c2_summary.json`; `requests` and `successes` are both 20.*

Next, switch Flash Attention off again to check whether the direction survives a change in run order. Stop the service using Step 7, restart with Step 4's `-fa off` command, wait for healthy status, and run:

```bash
python3 scripts/bench.py --workload data/workload.jsonl --output results \
  --config-id fa_off_repeat --concurrency 2 --requests 20 --max-tokens 64
cat results/fa_off_repeat/long_c2_summary.json
```

This longer-question group had 20/20 successes, TTFT P95 **1.7893 seconds**, total-duration P95 **4.8071 seconds**, and aggregate output throughput **26.8582 token/s**.

![Summary JSON for 20 longer-question requests with Flash Attention off.](figures/04-fa-off-repeat-summary.png)

*Figure 7. Actual values in `fa_off_repeat/long_c2_summary.json`, using the same category, concurrency, and output limit as Figure 6.*

The actual order was **off initial → on initial → on repeat → off repeat**. Follow this order to compare your four configurations with the record. Both rounds showed the same direction, but this does not establish the same benefit on all hardware or longer inputs.

## Step 9: generate the report and select a configuration

Run:

```bash
python3 scripts/report.py results --bucket long --concurrency 2 \
  --max-ttft-p95-s 2 --max-total-p95-s 5 --min-success-rate 1
```

The command defines three acceptance thresholds for the longer-question, concurrency-2 workload: **all requests succeed**, TTFT P95 **≤2 seconds**, and total-duration P95 **≤5 seconds**. The script reads saved `_summary.json` files and does not predict untested configurations. It creates:

- `results/summary.csv`: all 12 measured groups.
- `results/recommendation.json`: passing configurations, the recommendation, and its source summary.
- `results/report.md`: a readable report.

Check:

```bash
wc -l results/summary.csv
cat results/recommendation.json
sed -n '1,24p' results/report.md
```

The CSV had **13 rows**: 1 header and 12 measured groups. All four target configurations passed. Ranking by TTFT P95 selected the initial `fa_on` group. The report points to `fa_on/long_c2_summary.json`; use `long_c2.jsonl` in that directory for request-level verification.

![Report thresholds, 12 groups, recommended configuration, and CSV row count.](figures/07-report-selection.png)

*Figure 8. Acceptance results read from `recommendation.json`. This screenshot verifies an already generated report.*

## Final results

For the predefined longer-question workload at concurrency 2, the four groups were:

| Round | Flash Attention | Successful requests | TTFT P95 | Total-duration P95 | Aggregate output throughput |
| --- | --- | ---: | ---: | ---: | ---: |
| Initial, 8 requests | Off | 8/8 | 1.7796 s | 4.8450 s | 27.1245 token/s |
| Initial, 8 requests | On | 8/8 | 1.5469 s | 4.6099 s | 28.4047 token/s |
| Repeat, 20 requests | Off | 20/20 | 1.7893 s | 4.8071 s | 26.8582 token/s |
| Repeat, 20 requests | On | 20/20 | 1.5740 s | 4.5937 s | 28.1866 token/s |

Throughput is **the entire group's output tokens per second**, not one user's generation speed. In the 20-request repeat, TTFT P95 decreased by **0.2153 seconds, approximately 12.0%**, and aggregate output throughput increased by approximately **4.9%**. Once-per-second `nvidia-smi` sampling recorded peaks of **16111 MiB** and **16063 MiB**, a 48 MiB difference. Sampling can miss shorter peaks, so 48 MiB is not an exact memory saving.

The experiment establishes observations for this A10, these short-output questions, and concurrency 2. It does **not** establish better answer accuracy, performance on phones or personal computers, true 1600-token inputs, or larger user counts. Although the longer questions mention an “approximately 1600-token” scenario, actual inputs were only approximately **199–229 tokens**. Some responses ended with `finish_reason=length` because of `max_tokens=64`. Do not treat truncated answers as complete operational advice.

## Reproduction checks

1. The GPU is visible, the model SHA256 matches, and `llama-server --help` succeeds.
2. Health returns `{"status":"ok"}` and `ps` shows the expected `-fa off/on` for the current round.
3. The smoke test returns 200 for the valid request and 400 for the malformed request.
4. All four configuration directories contain `metadata.json`, request JSONL, GPU samples, and group summaries, with successful counts matching request counts.
5. `summary.csv` has 12 data rows, and the recommendation points to its source summary.

Latency need not match to four decimal places. GPU clocks, temperature, neighboring tasks, and caches can change results. Verify inputs and functionality first, then compare relative trends. If the direction differs, preserve the raw JSONL and logs and report that observation.

## Troubleshooting

**GPU enumeration works, but CUDA compilation is incompatible.** Check the driver, `nvcc`, and runtime libraries actually loaded. Local CUDA 12.4 worked here; the preinstalled CUDA 13.0 failed to initialize the GPU. The `nvidia-smi` compatibility field is not the installed toolchain version. Use the local toolchain from `setup.sh` and repeat the `LD_LIBRARY_PATH` export in new terminals. A failed build log is not success evidence.

**The model hash differs.** Do not start the service. Check completeness and resume with the script's `aria2` support. Retrieve the correct file if the mismatch persists. Results for a different model cannot be compared directly.

**Health initially returns 503.** Allow the large file to load and inspect the relevant server log. Investigate if the process has exited or logs show an error. Exclude cold loading from TTFT.

**Port 8000 is occupied.** Inspect `ps -o pid,args -C llama-server`. After confirming it is this project's previous service, stop it with `kill "$(cat logs/server.pid)"` before restarting. Running two configurations simultaneously can make labels disagree with actual parameters.

**VRAM is insufficient.** Reducing `-c` or `-np` creates a new configuration that requires a complete new measurement. Do not reuse the A10 results. This service binds only to `127.0.0.1` and has no API key or access controls configured for public exposure.

**The report recommends no configuration.** Keep its `none passed` result. Adjust the target according to real requirements or continue experimenting. Do not substitute the fastest individual request.

## Files, sources, and submission status

Complete code is in `scripts/`; public input is `data/workload.jsonl`; 8 real verification screenshots are in `figures/`; the 12 transcribed groups are in `results/observed-summary.csv`. The [technical appendix](CASE_TECHNICAL.en.md) defines request fields, P95, sampling, and limitations. Sources: [ModelScope model page](https://www.modelscope.cn/models/Abiray/Qwen3.8-27B-Q4_K_M-GGUF), [llama.cpp b10430](https://github.com/ggml-org/llama.cpp/tree/b10430), [NVIDIA CUDA redistribution](https://developer.download.nvidia.com/compute/cuda/redist/), and PyPI `nvidia-*` packages. Verify the model repository's license before public redistribution.

Raw request JSONL, GPU samples, and logs remain under temporary `/mnt/workspace/llm-serving-diagnosis`, packaged as `case-evidence.tar.gz`. The public repository currently contains summary transcriptions and screenshots, without raw request evidence. The web IDE download did not produce an accessible artifact. The **complete successful build log was not retained, and setup.sh has not been rerun from scratch in a second fresh instance**. This is a tutorial draft based on real measurements that can be further checked; it **does not yet satisfy every community submission requirement**. Before submission, validate in a fresh environment and publish sanitized raw evidence.

After the experiment, confirm that `logs/server.pid` belongs to this service, then stop it:

```bash
kill "$(cat logs/server.pid)"
```
