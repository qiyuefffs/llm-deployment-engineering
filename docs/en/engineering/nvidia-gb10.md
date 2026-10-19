# NVIDIA GB10: ARM64 build, FP8, AWQ, MTP and DFlash

[简体中文](../../01-deployment-foundations/cases/C03-gb10/README.md) | **English**

[Index of engineering examples](README.md) · [General directory of knowledge systems](../SUMMARY.md)

Technical labels: `CUDA 13 / ARM64 / vLLM / speculative decoding`

## Engineering configuration and experimental branches

|Branch|Environment / model|Problems with Adaptation|Performance data inputs|
| --- | --- | --- | --- |
|Building the foundation| GB10,ARM64,128GB,CUDA13 |The x86 wheel cannot be used directly; SM12.1 built with a specific kernel|Source code, dependency and building logs|
| Qwen FP8 | vLLM commit17d87168d;Qwen3.6-35B-A3B FP8 | FP8 KV,FlashInfer,prefix/chunked |200 requests, 25,600 output tokens, 297.46s, 86.06 tokens/s|
| Gemma AWQ |26B-A4B and 31B each 4/8bit|Packaging, quantization kernel, model, and computational structure|The four groups TTFT/TPOT/ITL/E2E|
| Gemma MTP |Main model + assistant 3 candidates|Acceptance rate, verification cost, batch|C1/c2/c4 matching|
| DFlash |Custom branch, drafter, CUDA extension|Multiple sets of torch/CUDA/source code needed|The original two configurations were observed about 2.03 times, not attributable to a single variable.|

## Deploying adaptive execution order

```text
ARM64/ driver / CUDA Confirmation → Fixed source code and torch → Build extension
 → Small inputs complete generation → API and SSE → No optimized baseline
 → AWQ or MTP or DFlash independent branches → Same workload replication → quality and resources acceptance testing
```

1. Each branch is recorded separately `git rev-parse HEAD `, ` pip freeze `, ` torch.__version__`, ` nvcc --version`With the template. Many of the following articles have different environments and cannot be combined into a virtual environment to claim reproduction.
2. Qwen's construction of the `TORCH_CUDA_ARCH_LIST` Set 12.0 to bypass a specific FP4 kernel error; This does not change GB10's computing capability 12.1, nor does it change the default compilation parameter for all versions.
3. It's used [Qwen FP8 Full Service Steps](../chapters/frameworks/vllm-service.md) Complete the startup, request and output savings, and then restore the historical performance budget.
4. AWQ four groups unified input targets 2048, output 128, 200 requests, c2; Confirm the configuration of the artifact with the actual output before comparing. MTP uses its own 512/256 workload and does not cross rank with AWQ's absolute throughput.
5. DFlash first checks the drafter matches the draft statistics and then looks at TTFT/TPOT and target model quality; The original configuration simultaneously changes ctx, seqs, memory and eager, and the combined benefits cannot be attributed to a single module.

## Results and acceptance testing

Qwen's original 200 requests mean sudden TTFT of 148,430.70ms, P99 of 293,115.24ms, throughput of 86.06 tokens/s does not represent a good interaction experience. Acceptance testing should complement limited access rates and concurrency to achieve the goals of TTFT and tail latency.

MTP original throughput increased by c1/c2/c4 approximately 44.76%/32.68%/53.19%. Keeping the raw data, not using the acceptance rate or total throughput as proof of quality equity. The complete constructions, parameters, logs and all controls are listed below in the order of the original technical text.

## Agreement on the use of complete technical records

The following technical correctness, commands, tables, logs, failures and subsequent experiments of the relevant FlowUs articles are retained directly, without abbreviating the original process. private paths, nodes, authentication and sanitization of attached addresses; `<NODE_IP>` For example, the placeholder needs to be filled in the current environment. The original suggestion or prediction is still a suggestion or prediction. The above execution sequence and technical revisions are used to explain conflicts in historical records, and historical GPU/NPU experiments have not been repeated in this round.

## R05 · NVIDIA GB10 ARM compilation llamacpp

Device: NVIDIA GB10

architecture :ARM64

GPU architecture parameter:12.1 is set to 121 in compilation

OS: Ubuntu 24 (as recorded)

The compilation process is as follows:


```text
# 1. 拉取llamacpp源码
git clone https://github.com/ggml-org/llama.cpp.git

# 2. 进入llamacpp项目。创建build目录并进入
mkdir build
cd build

# 3. 编译命令
cmake ..   -DGGML_CUDA=ON   -DCMAKE_CUDA_ARCHITECTURES=121   -DCMAKE_BUILD_TYPE=Release

注：如果编译时出现以下错误：
-- Could NOT find CURL (missing: CURL_LIBRARY CURL_INCLUDE_DIR)
CMake Error at common/CMakeLists.txt:91 (message):
  Could NOT find CURL.  Hint: to disable this feature, set -DLLAMA_CURL=OFF

运行以下命令修复：
sudo apt-get update
sudo apt-get install libcurl4-openssl-dev

然后运行以下命令：
cmake .. \
  -DGGML_CUDA=ON \
  -DCMAKE_CUDA_ARCHITECTURES=121 \
  -DCMAKE_BUILD_TYPE=Release \
  -DLLAMA_CURL=ON

# 运行并行编译命令
cmake --build . --config Release -j$(nproc)


```

Model quantization command

```text
cd /srv/llm/xiangmu/llamacpp/llama.cpp

# 第一步：如果还没转换为 GGUF（假设你需要先从 FP8 模型转换）
python3 convert_hf_to_gguf.py \
  /srv/llm/models/Qwen3-Next-80B-A3B-Instruct-FP8 \
  --outfile /srv/llm/models/Qwen3-Next-80B-A3B-Instruct-FP8.gguf \
  --outtype f16

# 第二步：进入 build/bin 目录（假设你已编译好）
cd build/bin

# 第三步：使用 llama-quantize 将 GGUF 转为 Q5_K_M
./llama-quantize \
  /srv/llm/models/Qwen3-Next-80B-A3B-Instruct-FP8.gguf \
  /srv/llm/models/Qwen3-Next-80B-A3B-Instruct-Q5_K_M.gguf \
  Q5_K_M

```

Qwen 3-30B-A3B model FP16 precision

```text
# GGUF转换方法
python3 convert_hf_to_gguf.py ~/models/Qwen3-30B-A3B-Instruct-2507 \
    --outtype bf16 \
    --outfile ~/models/Qwen3-30B-A3B-2507-bf16.gguf

# 加载命令
./llama-server \
  -m /srv/llm/models/Qwen3-30B-A3B-2507-bf16.gguf \
  -c 4096 \
  -n 512 \
  -t 8 \
  -ngl 99 \
  --temp 0.7 \
  --top-k 50 \
  --top-p 0.95 \
  --host 0.0.0.0 \
  --port 8080

# 测试方法
curl [服务地址按本实例配置] \
  -H "Content-Type: application/json" \
  -d '{
        "model": "Qwen3-30B-A3B",
        "messages": [
          {"role": "system", "content": "你是一个玄幻小说大师"},
          {"role": "user", "content": "请使用极其夸张的写法描述一下玄武门之变。"}
        ],
        "temperature": 0.7,
        "top_k": 50,
        "top_p": 0.95,
        "max_tokens": 2000
      }'
```

## R06 · nvidia GB10 device (arm64 architecture ) compilation vllm

Environmental configuration:

Nvidia: cuda 12.8 and above

Conda virtual environment

This is a compilation link: [https://forums.developer.nvidia.com/t/run-vllm-in-spark/348862](https://forums.developer.nvidia.com/t/run-vllm-in-spark/348862)

Compilation process

```text
# 步骤1：安装基础工具
sudo apt install -y build-essential cmake ninja-build git python3-venv python3-dev wget curl

# 步骤 2: 设置 CUDA 环境变量
export CUDA_HOME=/usr/local/cuda-13.0      # 根据实际路径修改
export PATH=$CUDA_HOME/bin:$PATH
export LD_LIBRARY_PATH=$CUDA_HOME/lib64:$LD_LIBRARY_PATH

# 确认
nvcc --version
ptxas --version

# 步骤 3: 创建 Python 虚拟环境 (推荐)
python3 -m venv ~/vllm_env
source ~/vllm_env/bin/activate
pip install --upgrade pip setuptools wheel

# 步骤4：安装 PyTorch (确保 CUDA 支持 + arm64 支持)
# 注意：如果 PyTorch 官方 wheel 在 arm64 + CUDA13 不可用，可能要安装 nightly 或自编译
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu130

# 步骤 5: 克隆 vLLM 源码
git clone --recursive https://github.com/vllm-project/vllm.git
cd vllm

# 步骤 6: 使用已有 PyTorch 安装（强调 arm64 场景）
python3 use_existing_torch.py

# 检测当前ptorch是否支持当前设备架构
python -c "import torch; print(torch.__version__, torch.version.cuda, torch.cuda.is_available(), torch.cuda.get_device_name(0))"

输出：
/srv/llm/miniconda3/envs/qwen3-omni/lib/python3.12/site-packages/torch/cuda/__init__.py:283: UserWarning:
    Found GPU0 NVIDIA GB10 which is of cuda capability 12.1.
    Minimum and Maximum cuda capability supported by this version of PyTorch is
    (8.0) - (12.0)

  warnings.warn(
2.9.0+cu130 13.0 True NVIDIA GB10


# 测试ptorch是否兼容
python - <<'EOF'
import torch
x = torch.randn(2,2).cuda()
print(x)
print(x * 2)
EOF

# 输出
/srv/llm/miniconda3/envs/qwen3-omni/lib/python3.12/site-packages/torch/cuda/__init__.py:283: UserWarning:
    Found GPU0 NVIDIA GB10 which is of cuda capability 12.1.
    Minimum and Maximum cuda capability supported by this version of PyTorch is
    (8.0) - (12.0)

  warnings.warn(
tensor([[ 1.5451, -0.4001],
        [-1.6385,  0.2363]], device='cuda:0')
tensor([[ 3.0902, -0.8002],
        [-3.2770,  0.4727]], device='cuda:0')


# 步骤7：开始编译
# 获取当前GPU架构命令
(base) operator@node:~$ nvidia-smi --query-gpu=name,compute_cap --format=csv
输出：
name, compute_cap
NVIDIA GB10, 12.1

# 设置GPU架构
export TORCH_CUDA_ARCH_LIST="12.1"

export MAX_JOBS=8
pip install --no-build-isolation -e .

# 如果报错缺少该包aiohttp，执行以下安装命令
pip install aiohttp    （安装报错使用conda命令安装）
或者
conda install aiohttp  (使用的conda环境)


```

## R07 · DGX Spark adaptive compilation vllm deployment Qwen 3.6-35B-A3B model (bf16/fp8 precision)

Device: DGX Spark GB10

Memory：128 GB

The system is Ubuntu 24.04.

model :

Qwen3.6-35B-A3B

Qwen3.6-35B-A3B-FP8

vLLM version:

Version：0.19.1rc1.dev337+g17d87168d.cu130

Conda environment: vllm-qwen3.6

Vllm compilation process:

```Markdown
git clone https://github.com/vllm-project/vllm.git
cd vllm
git checkout 17d87168d
git submodule update --init --recursive

export CUDA_HOME=/usr/local/cuda-13.0
export PATH=$CUDA_HOME/bin:$PATH
export LD_LIBRARY_PATH=$CUDA_HOME/lib64:$LD_LIBRARY_PATH

export VLLM_TARGET_DEVICE=cuda
export TORCH_CUDA_ARCH_LIST="12.0"
export MAX_JOBS=8

python -m pip install --no-build-isolation -e .

#踩坑
为什么 sm121 会报错，而 sm120 路线更容易成功
GB10 确实是 compute capability 12.1 / sm121，这点没有错。NVIDIA 的 Blackwell 兼容文档也说明了 Blackwell 家族里不同分支并不是所有底层特性都完全相同。

失败的关键报错是：

Instruction 'cvt with .e2m1x2' not supported on .target 'sm_121'

这不是普通编译器小毛病，而是 SM121 上不支持某些 NVFP4 / FP4 microscaling 路径需要的底层指令。NVIDIA 社区针对 DGX Spark 的帖子明确指出：

SM121 缺少 cvt.e2m1x2
因此某些 NVFP4 kernels 在 SM121 上不会编过
但 SM121 可以运行很多 sm120 代码路径。

所以这里看起来反直觉，但实际成立：

GB10设备是 sm121
但在源码编译时，按 sm120 路线生成代码反而更容易成功
因为这样更可能绕开那批不适用于 GB10 的 FP4/NVFP4 内核路径。
```

inference :

```Markdown
推理命令：
vllm serve /srv/llm/models/Qwen3.6-35B-A3B-FP8 \
  --served-model-name Qwen3.6-35B-A3B-FP8 \
  --host 0.0.0.0 \
  --port 8001 \
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
  --enable-chunked-prefill \
  --trust-remote-code

显存占用：100GB GPU限制：0.80

性能压测命令：
vllm bench serve \
  --backend openai-chat \
  --base-url http://127.0.0.1:8001 \
  --endpoint /v1/chat/completions \
  --model Qwen3.6-35B-A3B-FP8 \
  --tokenizer /srv/llm/models/Qwen3.6-35B-A3B-FP8 \
  --dataset-name random \
  --random-input-len 2048 \
  --random-output-len 128 \
  --num-prompts 200 \
  --request-rate inf \
  --seed 42

  压测结果：
============ Serving Benchmark Result ============
Successful requests:                     200
Failed requests:                         0
Benchmark duration (s):                  297.46
Total input tokens:                      411678
Total generated tokens:                  25600
Request throughput (req/s):              0.67
Output token throughput (tok/s):         86.06
Peak output token throughput (tok/s):    139.00
Peak concurrent requests:                200.00
Total token throughput (tok/s):          1470.04
---------------Time to First Token----------------
Mean TTFT (ms):                          148430.70
Median TTFT (ms):                        148122.85
P99 TTFT (ms):                           293115.24
-----Time per Output Token (excl. 1st token)------
Mean TPOT (ms):                          35.79
Median TPOT (ms):                        35.27
P99 TPOT (ms):                           40.15
---------------Inter-token Latency----------------
Mean ITL (ms):                           35.51
Median ITL (ms):                         34.25
P99 ITL (ms):                            42.13
==================================================

```

```Markdown
推理命令：
vllm serve /srv/llm/models/Qwen3.6-35B-A3B \
  --served-model-name Qwen3.6-35B-A3B \
  --host 0.0.0.0 \
  --port 8001 \
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
  --enable-chunked-prefill \
  --trust-remote-code

显存占用：100GB GPU限制：0.80

性能压测：
vllm bench serve \
  --backend openai-chat \
  --base-url http://127.0.0.1:8001 \
  --endpoint /v1/chat/completions \
  --model Qwen3.6-35B-A3B \
  --tokenizer /srv/llm/models/Qwen3.6-35B-A3B \
  --dataset-name random \
  --random-input-len 2048 \
  --random-output-len 128 \
  --num-prompts 200 \
  --request-rate inf \
  --seed 42


```

## R08 · NVIDIA GB10 deploys Qwen3-30B-A3B-Instruct-2507

Docker to create commands

```text
docker run  -it \
  --name Qwen3-30B \
  --gpus all \
  --ipc=host \
  --shm-size=32g \
  -v /srv/llm/models/Qwen3-30B-A3B-Instruct-2507:/app/model:ro  \
  -v ~/.cache/huggingface:/root/.cache/huggingface:rw \
  -p 8000:8000 \
  nvcr.io/nvidia/vllm:25.10-py3 \
  /bin/bash


 # 创建Qwen3-32b模型容器
 docker run  -it \
  --name Qwen3-32B \
  --gpus all \
  --ipc=host \
  --shm-size=32g \
  -v /srv/llm/models/Qwen3-32B:/app/model:ro  \
  -v ~/.cache/huggingface:/root/.cache/huggingface:rw \
  -p 8000:8000 \
  nvcr.io/nvidia/vllm:25.11-py3 \
  /bin/bash

  # 创建Qwen2.5-omni-7B模型
  docker run  -it \
  --name Qwen2_5-omni-7b \
  --gpus all \
  --ipc=host \
  --shm-size=32g \
  -v /srv/llm/models/Qwen2.5-Omni-7B:/app/model:ro  \
  -v ~/.cache/huggingface:/root/.cache/huggingface:rw \
  -p 8000:8000 \
  nvcr.io/nvidia/vllm:25.11-py3 \
  /bin/bash


```

Vllm starts inference command

```text
vllm serve /app/model \
  --host 0.0.0.0 \
  --port 8000 \
  --tensor-parallel-size 1 \
  --pipeline-parallel-size 1 \
  --gpu-memory-utilization 0.8 \
  --enable-expert-parallel


# 启动tool_call功能
vllm serve /app/model   --host 0.0.0.0   --port 8000   --tensor-parallel-size 1   --pipeline-parallel-size 1   --gpu-memory-utilization 0.9 --served-model-name qwen3-30b   --enable-expert-parallel   --enable-auto-tool-choice   --tool-call-parser openai


vllm serve /srv/llm/models/Qwen3-Omni-30B-A3B-Instruct \
  --host 0.0.0.0 \
  --port 8000 \
  --tensor-parallel-size 1 \
  --pipeline-parallel-size 1 \
  --gpu-memory-utilization 0.8 \
  --enable-expert-parallel


vllm serve /app/model \
  --host 0.0.0.0 \
  --port 8002 \
  --served-model-name Qwen3-32B \
  --gpu-memory-utilization 0.85 \
  --tensor-parallel-size 1


```

The test command:

```text
curl -X POST [服务地址按本实例配置] \
  -H "Content-Type: application/json" \
  -d '{
      "model": "/app/model",
      "prompt": "讲一下金融投顾的策略方法",
      "max_tokens": 2000,
      "temperature": 0.3
    }'


    curl -X POST [服务地址按本实例配置] \
  -H "Content-Type: application/json" \
  -d '{
      "model": "/app/model",
      "prompt": "讲一下金融投顾的策略方法",
      "max_tokens": 2000,
      "temperature": 0.3
    }'
```

Locally deployed, exposing ports to other devices

```text
# vllm推理命令
vllm serve /app/model \
  --host 0.0.0.0 \
  --port 8000 \
  --tensor-parallel-size 1 \
  --pipeline-parallel-size 1 \
  --gpu-memory-utilization 0.8 \
  --enable-expert-parallel \
  --served-model-name Qwen3-30B

# 其他设备curl测试命令
curl -X POST http://<NODE_IP>:8000/v1/completions \
  -H "Content-Type: application/json" \
  -d '{
        "model": "Qwen3-30B",
        "prompt": "你好，给我讲一下金融投顾的策略方法。",
        "max_tokens": 100,
        "temperature": 0.3
      }'

```

Docker to create commands

```text
docker run -it \
  --name Qwen3-80B \
  --gpus all \
  --ipc=host \
  --shm-size=32g \
  -v ~/models/Qwen3-Next-80B-A3B-Instruct-FP8:/app/model:ro \
  -v ~/.cache/huggingface:/root/.cache/huggingface:rw \
  -p 8001:8000 \
  nvcr.io/nvidia/vllm:25.10-py3 \


 # vllm命令
 vllm serve /app/model \
  --host 0.0.0.0 \
  --port 8000 \
  --tensor-parallel-size 1 \
  --pipeline-parallel-size 1 \
  --gpu-memory-utilization 0.8 \
  --enable-expert-parallel


```

Performance testing

```text
evalscope perf \
  --url "http://127.0.0.1:8000/v1/chat/completions" \
  --model "/app/model" \
  --api openai \
  --dataset openqa \
  --parallel 5 \
  --number 10 \
  --min-tokens 64 \
  --max-tokens 128 \
  --min-prompt-length 8 \
  --max-prompt-length 32 \
  --connect-timeout 60 \
  --read-timeout 120 \
  --log-every-n-query 1 \
  --name "vLLM_Test"

```

## R09 · DGX GB10 deploys the Gemma-4 series AWQ quantization model

Device: DGX Spark GB10

Memory：128 GB

The system is Ubuntu 24.04.

model :
It represents the instructionally tuned, untrained pre-trained model;
How to quantize: AWQ
quantization precision :4bit,8bit


gemma-4-26B-A4B-it-AWQ-4bi

gemma-4-26B-A4B-it-AWQ-8bit

gemma-4-31B-it-AWQ-4bit

gemma-4-31B-it-AWQ-8bit

vLLM version:

python wheel: vllm-0.19.0+cu130

VRAM occupies: 81GB and the GPU limit is 0.65.

```Markdown
推理命令：
vllm serve /srv/llm/models/gemma-4-26B-A4B-it-AWQ-4bit   --served-model-name gemma-4-26B-A4B-it-AWQ-4bit   --host 0.0.0.0   --port 8003   --dtype auto   --gpu-memory-utilization 0.65   --max-model-len 16384   --max-num-seqs 2   --max-num-batched-tokens 4096   --enable-prefix-caching   --enforce-eager   --limit-mm-per-prompt '{"image":0,"video":0}


压测命令：
vllm bench serve   --backend openai-chat   --model /srv/llm/models/gemma-4-26B-A4B-it-AWQ-4bit   --tokenizer /srv/llm/models/gemma-4-26B-A4B-it-AWQ-4bit   --served-model-name gemma-4-26B-A4B-it-AWQ-4bit   --host 127.0.0.1   --port 8003   --endpoint /v1/chat/completions   --dataset-name random   --num-prompts 200   --max-concurrency 2   --random-input-len 1024   --random-output-len 128   --random-range-ratio 0.1   --request-rate inf   --num-warmups 10   --percentile-metrics ttft,tpot,itl,e2el   --metric-percentiles 50,95,99   --extra-body '{"max_tokens":128,"temperature":0.0}'

性能压测结果：
============ Serving Benchmark Result ============
Successful requests:                     200
Failed requests:                         0
Maximum request concurrency:             2
Benchmark duration (s):                  427.70
Total input tokens:                      206139
Total generated tokens:                  25696
Request throughput (req/s):              0.47
Output token throughput (tok/s):         60.08
Peak output token throughput (tok/s):    70.00
Peak concurrent requests:                4.00
Total token throughput (tok/s):          542.05
---------------Time to First Token----------------
Mean TTFT (ms):                          272.97
Median TTFT (ms):                        264.55
P50 TTFT (ms):                           264.55
P95 TTFT (ms):                           283.52
P99 TTFT (ms):                           418.72
-----Time per Output Token (excl. 1st token)------
Mean TPOT (ms):                          31.32
Median TPOT (ms):                        31.30
P50 TPOT (ms):                           31.30
P95 TPOT (ms):                           31.85
P99 TPOT (ms):                           32.40
---------------Inter-token Latency----------------
Mean ITL (ms):                           31.07
Median ITL (ms):                         29.82
P50 ITL (ms):                            29.82
P95 ITL (ms):                            32.35
P99 ITL (ms):                            94.44
----------------End-to-end Latency----------------
Mean E2EL (ms):                          4264.87
Median E2EL (ms):                        4281.37
P50 E2EL (ms):                           4281.37
P95 E2EL (ms):                           4626.35
P99 E2EL (ms):                           4759.75
==================================================

```

```Markdown
推理命令：
vllm serve /srv/llm/models/gemma-4-26B-A4B-it-AWQ-8bit \
  --served-model-name gemma-4-26B-A4B-it-AWQ-8bit \
  --host 0.0.0.0 \
  --port 8003 \
  --dtype auto \
  --gpu-memory-utilization 0.65 \
  --max-model-len 16384 \
  --max-num-seqs 2 \
  --max-num-batched-tokens 4096 \
  --enable-prefix-caching \
  --enforce-eager \
  --limit-mm-per-prompt '{"image":0,"video":0}'

性能压测命令：
vllm bench serve \
  --backend openai-chat \
  --model /srv/llm/models/gemma-4-26B-A4B-it-AWQ-8bit \
  --tokenizer /srv/llm/models/gemma-4-26B-A4B-it-AWQ-8bit \
  --served-model-name gemma-4-26B-A4B-it-AWQ-8bit \
  --host 127.0.0.1 \
  --port 8003 \
  --endpoint /v1/chat/completions \
  --dataset-name random \
  --num-prompts 200 \
  --max-concurrency 2 \
  --random-input-len 1024 \
  --random-output-len 128 \
  --random-range-ratio 0.1 \
  --request-rate inf \
  --num-warmups 10 \
  --percentile-metrics ttft,tpot,itl,e2el \
  --metric-percentiles 50,95,99 \
  --extra-body '{"max_tokens":128,"temperature":0.0}'

性能压测结果：
============ Serving Benchmark Result ============
Successful requests:                     200
Failed requests:                         0
Maximum request concurrency:             2
Benchmark duration (s):                  537.49
Total input tokens:                      206139
Total generated tokens:                  25696
Request throughput (req/s):              0.37
Output token throughput (tok/s):         47.81
Peak output token throughput (tok/s):    62.00
Peak concurrent requests:                4.00
Total token throughput (tok/s):          431.33
---------------Time to First Token----------------
Mean TTFT (ms):                          338.92
Median TTFT (ms):                        335.99
P50 TTFT (ms):                           335.99
P95 TTFT (ms):                           359.94
P99 TTFT (ms):                           504.80
-----Time per Output Token (excl. 1st token)------
Mean TPOT (ms):                          39.39
Median TPOT (ms):                        39.48
P50 TPOT (ms):                           39.48
P95 TPOT (ms):                           40.11
P99 TPOT (ms):                           40.54
---------------Inter-token Latency----------------
Mean ITL (ms):                           39.08
Median ITL (ms):                         37.66
P50 ITL (ms):                            37.66
P95 ITL (ms):                            40.63
P99 ITL (ms):                            118.89
----------------End-to-end Latency----------------
Mean E2EL (ms):                          5360.53
Median E2EL (ms):                        5383.14
P50 E2EL (ms):                           5383.14
P95 E2EL (ms):                           5838.26
P99 E2EL (ms):                           5889.24
==================================================

```

```Markdown
vllm serve /srv/llm/models/gemma-4-31B-it-AWQ-4bit \
  --served-model-name gemma-4-31B-it-AWQ-4bit \
  --host 0.0.0.0 \
  --port 8003 \
  --dtype auto \
  --gpu-memory-utilization 0.65 \
  --max-model-len 16384 \
  --max-num-seqs 2 \
  --max-num-batched-tokens 4096 \
  --enable-prefix-caching \
  --enforce-eager \
  --limit-mm-per-prompt '{"image":0,"video":0}'

  性能压测命令：
  vllm bench serve \
  --backend openai-chat \
  --model /srv/llm/models/gemma-4-31B-it-AWQ-4bit \
  --tokenizer /srv/llm/models/gemma-4-31B-it-AWQ-4bit \
  --served-model-name gemma-4-31B-it-AWQ-4bit \
  --host 127.0.0.1 \
  --port 8003 \
  --endpoint /v1/chat/completions \
  --dataset-name random \
  --num-prompts 200 \
  --max-concurrency 2 \
  --random-input-len 1024 \
  --random-output-len 128 \
  --random-range-ratio 0.1 \
  --request-rate inf \
  --num-warmups 10 \
  --percentile-metrics ttft,tpot,itl,e2el \
  --metric-percentiles 50,95,99 \
  --extra-body '{"max_tokens":128,"temperature":0.0}'

性能压测结果：
============ Serving Benchmark Result ============
Successful requests:                     200
Failed requests:                         0
Maximum request concurrency:             2
Benchmark duration (s):                  1550.23
Total input tokens:                      206139
Total generated tokens:                  25696
Request throughput (req/s):              0.13
Output token throughput (tok/s):         16.58
Peak output token throughput (tok/s):    23.00
Peak concurrent requests:                4.00
Total token throughput (tok/s):          149.55
---------------Time to First Token----------------
Mean TTFT (ms):                          1554.39
Median TTFT (ms):                        1537.91
P50 TTFT (ms):                           1537.91
P95 TTFT (ms):                           1660.53
P99 TTFT (ms):                           2448.72
-----Time per Output Token (excl. 1st token)------
Mean TPOT (ms):                          109.12
Median TPOT (ms):                        109.30
P50 TPOT (ms):                           109.30
P95 TPOT (ms):                           111.02
P99 TPOT (ms):                           111.84
---------------Inter-token Latency----------------
Mean ITL (ms):                           108.24
Median ITL (ms):                         98.98
P50 ITL (ms):                            98.98
P95 ITL (ms):                            105.08
P99 ITL (ms):                            405.37
----------------End-to-end Latency----------------
Mean E2EL (ms):                          15461.46
Median E2EL (ms):                        15549.51
P50 E2EL (ms):                           15549.51
P95 E2EL (ms):                           16744.49
P99 E2EL (ms):                           17295.65
==================================================

```

```Markdown
vllm serve /srv/llm/models/gemma-4-31B-it-AWQ-8bit \
  --served-model-name gemma-4-31B-it-AWQ-8bit \
  --host 0.0.0.0 \
  --port 8003 \
  --dtype auto \
  --gpu-memory-utilization 0.65 \
  --max-model-len 16384 \
  --max-num-seqs 2 \
  --max-num-batched-tokens 4096 \
  --enable-prefix-caching \
  --enforce-eager \
  --limit-mm-per-prompt '{"image":0,"video":0}'

  性能压测命令：
  vllm bench serve \
  --backend openai-chat \
  --model /srv/llm/models/gemma-4-31B-it-AWQ-8bit \
  --tokenizer /srv/llm/models/gemma-4-31B-it-AWQ-8bit \
  --served-model-name gemma-4-31B-it-AWQ-8bit \
  --host 127.0.0.1 \
  --port 8003 \
  --endpoint /v1/chat/completions \
  --dataset-name random \
  --num-prompts 200 \
  --max-concurrency 2 \
  --random-input-len 1024 \
  --random-output-len 128 \
  --random-range-ratio 0.1 \
  --request-rate inf \
  --num-warmups 10 \
  --percentile-metrics ttft,tpot,itl,e2el \
  --metric-percentiles 50,95,99 \
  --extra-body '{"max_tokens":128,"temperature":0.0}'

性能压测结果：
============ Serving Benchmark Result ============
Successful requests:                     200
Failed requests:                         0
Maximum request concurrency:             2
Benchmark duration (s):                  2587.60
Total input tokens:                      206139
Total generated tokens:                  25696
Request throughput (req/s):              0.08
Output token throughput (tok/s):         9.93
Peak output token throughput (tok/s):    15.00
Peak concurrent requests:                4.00
Total token throughput (tok/s):          89.59
---------------Time to First Token----------------
Mean TTFT (ms):                          2879.26
Median TTFT (ms):                        2846.44
P50 TTFT (ms):                           2846.44
P95 TTFT (ms):                           3027.51
P99 TTFT (ms):                           4703.69
-----Time per Output Token (excl. 1st token)------
Mean TPOT (ms):                          179.92
Median TPOT (ms):                        180.39
P50 TPOT (ms):                           180.39
P95 TPOT (ms):                           183.70
P99 TPOT (ms):                           184.53
---------------Inter-token Latency----------------
Mean ITL (ms):                           178.48
Median ITL (ms):                         161.40
P50 ITL (ms):                            161.40
P95 ITL (ms):                            167.32
P99 ITL (ms):                            737.11
----------------End-to-end Latency----------------
Mean E2EL (ms):                          25809.91
Median E2EL (ms):                        25989.45
P50 E2EL (ms):                           25989.45
P95 E2EL (ms):                           27932.55
P99 E2EL (ms):                           29163.73
==================================================
```

## R10 · DGX Spark GB10 deploys gemma-4 series models and shut down MTP inference acceleration

1. Inference command

```Markdown
docker run -it \
  --name gemma4-26b-a4b-base-8016 \
  --gpus all \
  --ipc=host \
  --network host \
  --shm-size 16G \
  -v /srv/llm/models:/models \
  -v ~/.cache/huggingface:/root/.cache/huggingface \
  -e HF_HOME=/root/.cache/huggingface \
  -e VLLM_USE_V1=1 \
  vllm/vllm-openai:gemma4-0505-cu130 \
  /models/gemma-4-26B-A4B-it \
  --served-model-name gemma4-26b-a4b-base \
  --host 0.0.0.0 \
  --port 8016 \
  --tensor-parallel-size 1 \
  --dtype bfloat16 \
  --max-model-len 8192 \
  --gpu-memory-utilization 0.90 \
  --max-num-seqs 4 \
  --max-num-batched-tokens 8192 \
  --limit-mm-per-prompt '{"image":0,"audio":0}' \
  --async-scheduling \
  --trust-remote-code
```

Enter the container: docker exec -it gemma4-26b-a4b-base-8016 bash

1. performance load testing

```Markdown
并发1
HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 vllm bench serve \
  --backend openai-chat \
  --host 127.0.0.1 \
  --port 8016 \
  --endpoint /v1/chat/completions \
  --model gemma4-26b-a4b-base \
  --tokenizer /models/gemma-4-26B-A4B-it \
  --dataset-name random \
  --num-prompts 20 \
  --random-input-len 512 \
  --random-output-len 256 \
  --max-concurrency 1

结果：
============ Serving Benchmark Result ============
Successful requests:                     20
Failed requests:                         0
Maximum request concurrency:             1
Benchmark duration (s):                  245.92
Total input tokens:                      10507
Total generated tokens:                  5120
Request throughput (req/s):              0.08
Output token throughput (tok/s):         20.82
Peak output token throughput (tok/s):    22.00
Peak concurrent requests:                2.00
Total token throughput (tok/s):          63.55
---------------Time to First Token----------------
Mean TTFT (ms):                          488.14
Median TTFT (ms):                        333.21
P99 TTFT (ms):                           2185.60
-----Time per Output Token (excl. 1st token)------
Mean TPOT (ms):                          46.30
Median TPOT (ms):                        46.38
P99 TPOT (ms):                           46.42
---------------Inter-token Latency----------------
Mean ITL (ms):                           46.12
Median ITL (ms):                         45.73
P99 ITL (ms):                            51.89
==================================================


并发2
HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 vllm bench serve \
  --backend openai-chat \
  --host 127.0.0.1 \
  --port 8016 \
  --endpoint /v1/chat/completions \
  --model gemma4-26b-a4b-base \
  --tokenizer /models/gemma-4-26B-A4B-it \
  --dataset-name random \
  --num-prompts 40 \
  --random-input-len 512 \
  --random-output-len 256 \
  --max-concurrency 2

结果：
============ Serving Benchmark Result ============
Successful requests:                     40
Failed requests:                         0
Maximum request concurrency:             2
Benchmark duration (s):                  277.70
Total input tokens:                      21017
Total generated tokens:                  10240
Request throughput (req/s):              0.14
Output token throughput (tok/s):         36.87
Peak output token throughput (tok/s):    40.00
Peak concurrent requests:                4.00
Total token throughput (tok/s):          112.56
---------------Time to First Token----------------
Mean TTFT (ms):                          352.24
Median TTFT (ms):                        339.31
P99 TTFT (ms):                           881.65
-----Time per Output Token (excl. 1st token)------
Mean TPOT (ms):                          53.06
Median TPOT (ms):                        52.95
P99 TPOT (ms):                           53.68
---------------Inter-token Latency----------------
Mean ITL (ms):                           52.85
Median ITL (ms):                         52.31
P99 ITL (ms):                            58.92
==================================================


并发4：
HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 vllm bench serve \
  --backend openai-chat \
  --host 127.0.0.1 \
  --port 8016 \
  --endpoint /v1/chat/completions \
  --model gemma4-26b-a4b-base \
  --tokenizer /models/gemma-4-26B-A4B-it \
  --dataset-name random \
  --num-prompts 80 \
  --random-input-len 512 \
  --random-output-len 256 \
  --max-concurrency 4

 结果：
 ============ Serving Benchmark Result ============
Successful requests:                     80
Failed requests:                         0
Maximum request concurrency:             4
Benchmark duration (s):                  415.19
Total input tokens:                      42035
Total generated tokens:                  20480
Request throughput (req/s):              0.19
Output token throughput (tok/s):         49.33
Peak output token throughput (tok/s):    52.00
Peak concurrent requests:                8.00
Total token throughput (tok/s):          150.57
---------------Time to First Token----------------
Mean TTFT (ms):                          562.37
Median TTFT (ms):                        426.89
P99 TTFT (ms):                           3407.81
-----Time per Output Token (excl. 1st token)------
Mean TPOT (ms):                          79.19
Median TPOT (ms):                        79.00
P99 TPOT (ms):                           80.04
---------------Inter-token Latency----------------
Mean ITL (ms):                           78.88
Median ITL (ms):                         78.35
P99 ITL (ms):                            89.58
==================================================

```

## R11 · DGX Spark GB10 deployment of gemma-4 series models and MTP inference acceleration

Inference command

```Markdown
docker run -it \
  --name gemma4-26b-a4b-mtp-v3 \
  --gpus all \
  --ipc=host \
  --network host \
  --shm-size 16G \
  -v /srv/llm/models:/models \
  -v ~/.cache/huggingface:/root/.cache/huggingface \
  -e HF_HOME=/root/.cache/huggingface \
  -e VLLM_USE_V1=1 \
  vllm/vllm-openai:gemma4-0505-cu130 \
  /models/gemma-4-26B-A4B-it \
  --served-model-name gemma4-26b-a4b-mtp \
  --host 0.0.0.0 \
  --port 8015 \
  --tensor-parallel-size 1 \
  --dtype bfloat16 \
  --max-model-len 8192 \
  --gpu-memory-utilization 0.90 \
  --max-num-seqs 4 \
  --max-num-batched-tokens 8192 \
  --limit-mm-per-prompt '{"image":0,"audio":0}' \
  --async-scheduling \
  --trust-remote-code \
  --speculative-config '{"model":"/models/gemma-4-26B-A4B-it-assistant","num_speculative_tokens":3,"draft_tensor_parallel_size":1}'

```

Enter the container: docker exec -it gemma4-26b-a4b-mtp-v3 bash

concurrency load testing records

```Markdown
vllm bench serve \
  --backend openai-chat \
  --host 127.0.0.1 \
  --port 8015 \
  --endpoint /v1/chat/completions \
  --model gemma4-26b-a4b-mtp \
  --tokenizer /models/gemma-4-26B-A4B-it \
  --dataset-name random \
  --num-prompts 20 \
  --random-input-len 512 \
  --random-output-len 256 \
  --max-concurrency 1

结果：
============ Serving Benchmark Result ============
Successful requests:                     20
Failed requests:                         0
Maximum request concurrency:             1
Benchmark duration (s):                  169.88
Total input tokens:                      10507
Total generated tokens:                  5120
Request throughput (req/s):              0.12
Output token throughput (tok/s):         30.14
Peak output token throughput (tok/s):    15.00
Peak concurrent requests:                2.00
Total token throughput (tok/s):          91.99
---------------Time to First Token----------------
Mean TTFT (ms):                          462.90
Median TTFT (ms):                        371.17
P99 TTFT (ms):                           1253.08
-----Time per Output Token (excl. 1st token)------
Mean TPOT (ms):                          31.49
Median TPOT (ms):                        28.98
P99 TPOT (ms):                           49.50
---------------Inter-token Latency----------------
Mean ITL (ms):                           78.27
Median ITL (ms):                         79.27
P99 ITL (ms):                            90.94
---------------Speculative Decoding---------------
Acceptance rate (%):                     38.07
Acceptance length:                       2.52
Drafts:                                  2032
Draft tokens:                            8128
Accepted tokens:                         3094
Per-position acceptance (%):
  Position 0:                            62.01
  Position 1:                            42.96
  Position 2:                            27.21
  Position 3:                            20.08
==================================================

```

```Markdown
vllm bench serve \
  --backend openai-chat \
  --host 127.0.0.1 \
  --port 8015 \
  --endpoint /v1/chat/completions \
  --model gemma4-26b-a4b-mtp \
  --tokenizer /models/gemma-4-26B-A4B-it \
  --dataset-name random \
  --num-prompts 40 \
  --random-input-len 512 \
  --random-output-len 256 \
  --max-concurrency 2

结果：
============ Serving Benchmark Result ============
Successful requests:                     40
Failed requests:                         0
Maximum request concurrency:             2
Benchmark duration (s):                  209.31
Total input tokens:                      21017
Total generated tokens:                  10240
Request throughput (req/s):              0.19
Output token throughput (tok/s):         48.92
Peak output token throughput (tok/s):    28.00
Peak concurrent requests:                4.00
Total token throughput (tok/s):          149.33
---------------Time to First Token----------------
Mean TTFT (ms):                          608.22
Median TTFT (ms):                        438.43
P99 TTFT (ms):                           4527.16
-----Time per Output Token (excl. 1st token)------
Mean TPOT (ms):                          38.38
Median TPOT (ms):                        36.51
P99 TPOT (ms):                           59.55
---------------Inter-token Latency----------------
Mean ITL (ms):                           99.52
Median ITL (ms):                         99.52
P99 ITL (ms):                            129.84
---------------Speculative Decoding---------------
Acceptance rate (%):                     40.77
Acceptance length:                       2.63
Drafts:                                  3894
Draft tokens:                            15576
Accepted tokens:                         6351
Per-position acceptance (%):
  Position 0:                            66.31
  Position 1:                            45.74
  Position 2:                            30.43
  Position 3:                            20.62
==================================================

```

```Markdown
============ Serving Benchmark Result ============
Successful requests:                     80
Failed requests:                         0
Maximum request concurrency:             4
Benchmark duration (s):                  271.00
Total input tokens:                      42035
Total generated tokens:                  20480
Request throughput (req/s):              0.30
Output token throughput (tok/s):         75.57
Peak output token throughput (tok/s):    37.00
Peak concurrent requests:                7.00
Total token throughput (tok/s):          230.69
---------------Time to First Token----------------
Mean TTFT (ms):                          596.33
Median TTFT (ms):                        545.51
P99 TTFT (ms):                           1639.68
-----Time per Output Token (excl. 1st token)------
Mean TPOT (ms):                          50.41
Median TPOT (ms):                        47.95
P99 TPOT (ms):                           83.53
---------------Inter-token Latency----------------
Mean ITL (ms):                           131.48
Median ITL (ms):                         128.37
P99 ITL (ms):                            290.90
---------------Speculative Decoding---------------
Acceptance rate (%):                     41.16
Acceptance length:                       2.65
Drafts:                                  7742
Draft tokens:                            30968
Accepted tokens:                         12746
Per-position acceptance (%):
  Position 0:                            66.39
  Position 1:                            46.18
  Position 2:                            30.69
  Position 3:                            21.38
==================================================

```

## R12 · DGX Spark GB10 compilation DFlash inference Acceleration modules integrated into vllm

```Markdown
# DGX Spark GB10 编译 vLLM 集成 DFlash 操作手册

> 目标：在 NVIDIA DGX Spark（GB10、`aarch64`、Blackwell-Tegra `sm_121a`）上从源码编译 vLLM，支持 **DFlash 推测解码** 与 **Qwen3.6 系列**。
>
> 实测环境：vLLM commit `2cc008e7b`、CUDA 13.0.88、PyTorch 2.11.0+cu130、Python 3.12.13、20 核 ARM CPU、119 GiB unified memory。

---

## 1. 源码拉取

```bash
### 国内必做：配 GitHub 加速镜像（cmake FetchContent 会拉 triton + LLVM ~500MB）
git config --global url."https://gh-proxy.com/https://github.com/".insteadOf "https://github.com/"

### 拉取带 DFlash 的 vLLM（main 分支已合入）
mkdir -p ~/xiangmu/vllm_dflash_gb10
cd ~/xiangmu/vllm_dflash_gb10
git clone https://github.com/vllm-project/vllm.git
cd vllm

### 验证 DFlash 文件存在
ls vllm/v1/spec_decode/dflash.py
```

---

## 2. Environmental configuration

### 2.1 System dependency

```bash
sudo apt update && sudo apt install -y \
    build-essential gcc-13 g++-13 \
    python3.12 python3.12-dev python3.12-venv \
    cmake ninja-build ccache git git-lfs \
    libibverbs-dev rdma-core librdmacm-dev pkg-config
```

> Don't wear it.`libnvidia-cudnn9-cu13-dev ` / ` libnccl-dev`The NCCL/cuDNN, which is a self-contained PyTorch wheel, clashes with the PyTorch wheel.

### 2.2 Conda Environment + PyTorch cu130

```bash
conda create -n vllm-dflash-gb10 python=3.12 -y
conda activate vllm-dflash-gb10
pip install --upgrade pip setuptools wheel packaging ninja

pip install --index-url https://download.pytorch.org/whl/cu130 \
    torch==2.11.0 torchvision==0.26.0 torchaudio==2.11.0
```

The GB10 capability must be validated for `(12, 1)`:

```bash
python -c "import torch; print(torch.cuda.get_device_capability(0), torch.cuda.get_device_name(0))"
### (12, 1) NVIDIA GB10
```

### 2.3 compilation Environmental variable scripts

in `vllm/` The source code is rooted `source-build-env.sh`:

```bash
cat > source-build-env.sh <<'EOF'
export CUDA_HOME=/usr/local/cuda
export PATH="$CUDA_HOME/bin:$PATH"
export LD_LIBRARY_PATH="$CUDA_HOME/lib64:$LD_LIBRARY_PATH"

export TORCH_CUDA_ARCH_LIST="12.1a"           # 必带 a 后缀
export TRITON_PTXAS_PATH=/usr/local/cuda/bin/ptxas

export MAX_JOBS=20
export CMAKE_BUILD_PARALLEL_LEVEL=20
export NVCC_THREADS=2

export CCACHE_DIR=$HOME/.cache/ccache
mkdir -p "$CCACHE_DIR"
export CMAKE_CXX_COMPILER_LAUNCHER=ccache
export CMAKE_CUDA_COMPILER_LAUNCHER=ccache
export CCACHE_MAXSIZE=50G
export CCACHE_COMPRESS=1
EOF

source ./source-build-env.sh   # 必须 source，不能 ./
echo "$TORCH_CUDA_ARCH_LIST"   # 12.1a
```

---

## 3. Compilation process

```bash
cd ~/xiangmu/vllm_dflash_gb10/vllm
conda activate vllm-dflash-gb10
source ./source-build-env.sh

### 剥离 vLLM 写死的 torch 版本锁定（防止 pip 重装把 cu130 wheel 冲掉）
python use_existing_torch.py

### aarch64+cu13 没有 flashinfer PyPI wheel，先删
sed -i "/^flashinfer/d" requirements/cuda.txt

### 装 build 期依赖
pip install --no-build-isolation -r requirements/build.txt

### 编译 vLLM（首次 25-35 分钟，二次 ccache 命中 5-8 分钟）
pip install --no-build-isolation -v -e . 2>&1 | tee /tmp/vllm-build.log

### 装 flashinfer + 运行时依赖（aarch64+cu13 走官方私有 index）
pip install --no-deps --index-url https://flashinfer.ai/whl/cu130/torch2.11/ \
    flashinfer-python flashinfer-cubin flashinfer-jit-cache
pip install requests einops cuda-tile nvidia-cudnn-cu13

### 验证编译结果
python -c "
import vllm
from vllm.v1.spec_decode.dflash import DFlashProposer
print('vllm:', vllm.__version__, '| DFlash:', DFlashProposer.__name__)
"
```

> **Three of them.`--no-` It's a must.**: `--no-build-isolation `(Pip recharging torch) Flashinfer when installed `--no-deps `(Torch-free version)` cuda-tile `Not with me.`[tileiras]` extra (requires CUDA 13.1+).

---

## 4. Inference commands

> The model path:
> - The main model `~/models/Qwen3.6-35B-A3B`(67 GB BF16)
> - DFlash drafter `~/models/DFlash/Qwen3.6-35B-A3B-DFlash`（905 MB）

### 4.1 Pre-start cleaning

```bash
sudo sync && echo 3 | sudo tee /proc/sys/vm/drop_caches
free -h        # available 必须 >= 100 GiB
nvidia-smi --query-compute-apps=pid,process_name,used_memory --format=csv
```

### 4.2 First start of conservative, single concurrency)

```bash
conda activate vllm-dflash-gb10
source ~/xiangmu/vllm_dflash_gb10/vllm/source-build-env.sh

vllm serve /srv/llm/models/Qwen3.6-35B-A3B \
    --host 0.0.0.0 --port 18000 \
    --served-model-name qwen36-35b-a3b-dflash \
    --trust-remote-code \
    --dtype bfloat16 \
    --speculative-config '{"method":"dflash","model":"/srv/llm/models/DFlash/Qwen3.6-35B-A3B-DFlash","num_speculative_tokens":5}' \
    --max-model-len 32768 \
    --max-num-seqs 1 \
    --gpu-memory-utilization 0.70 \
    --enforce-eager \
    2>&1 | tee /tmp/vllm-qwen36-35b-dflash.log
```

### 4.3 High throughput configuration (switched after runway baseline)

```bash
vllm serve /srv/llm/models/Qwen3.6-35B-A3B \
    --host 0.0.0.0 --port 18000 \
    --served-model-name qwen36-35b-a3b-dflash \
    --trust-remote-code --dtype bfloat16 \
    --speculative-config '{"method":"dflash","model":"/srv/llm/models/DFlash/Qwen3.6-35B-A3B-DFlash","num_speculative_tokens":5}' \
    --max-model-len 8192 \
    --max-num-seqs 8 \
    --gpu-memory-utilization 0.85
```

### 4.4 Interface smoking measurements

```bash
curl [服务地址按本实例配置]

curl [服务地址按本实例配置] \
    -H "Content-Type: application/json" \
    -d '{
        "model": "qwen36-35b-a3b-dflash",
        "messages": [{"role":"user","content":"用 Python 写一个快排"}],
        "max_tokens": 512,
        "temperature": 0
    }'
```

### 4.5 Confirm DFlash is working

```bash
grep -E "dflash|Mean acceptance length|accept" /tmp/vllm-qwen36-35b-dflash.log | tail -20
```

Expect to see `Mean acceptance length: 2.x ` with `Per-position acceptance rate` and related metrics.

---

## 5. Performance load testing command

### 5.1 ShareGPT data collection load testing (recommended)

```bash
### 下载 ShareGPT 样本
mkdir -p ~/datasets && cd ~/datasets
wget https://huggingface.co/datasets/anon8231489123/ShareGPT_Vicuna_unfiltered/resolve/main/ShareGPT_V3_unfiltered_cleaned_split.json

### 压测：300 个请求，并发 8
vllm bench serve \
    --backend openai-chat \
    --base-url [服务地址按本实例配置] \
    --endpoint /v1/chat/completions \
    --model qwen36-35b-a3b-dflash \
    --dataset-name sharegpt \
    --dataset-path ~/datasets/ShareGPT_V3_unfiltered_cleaned_split.json \
    --num-prompts 300 \
    --max-concurrency 8 \
    --save-result \
    --result-dir /tmp/vllm-bench
```

### 5.2 Random length load testing (controlling the number of token inputs/outputs)

```bash
vllm bench serve \
    --backend openai \
    --base-url [服务地址按本实例配置] \
    --endpoint /v1/completions \
    --model qwen36-35b-a3b-dflash \
    --dataset-name random \
    --random-input-len 1024 \
    --random-output-len 512 \
    --num-prompts 200 \
    --max-concurrency 4 \
    --save-result --result-dir /tmp/vllm-bench
```

### 5.3 Attention to indicators

|Indicators|Meaning|DFlash expected value|
| --- | --- | --- |
| `Mean acceptance length` |Average accepted length| 2.4 – 3.1(5 spec tokens) |
| `Avg Draft acceptance rate` |Overall acceptance rate of draft| 28% – 42% |
| `Per-position acceptance rate` |The acceptance rate for each spec position|The first digit is 0.7-0.9, the fifth digit is 0.05-0.13.|
| `Avg generation throughput` |End-to-end generating throughput|Concurrency 1: 22–29 tok/s (eager)|

### 5.4 Real-time indicators captured

```bash
### 服务侧日志（每 10 秒一行 SpecDecoding metrics）
tail -F /tmp/vllm-qwen36-35b-dflash.log | grep -E "SpecDecoding|generation throughput"

### Prometheus 端点
curl -s [服务地址按本实例配置] | grep -E "^vllm_(spec|generation|prompt)"
```

### 5.5 Modify the order of each change of press

1. Take it off.`--enforce-eager`→ Enable CUDA Graph, throughput 1.3 to 1.8x
2. `num_speculative_tokens`5 → 10 → 15, see acceptance rate
3. `--max-num-seqs` 1 → 2 → 4 → 8
4. `--gpu-memory-utilization` 0.70 → 0.80 → 0.85
5. `--max-model-len` Length by business context and release on demand

---

## 6. Crash records

| # |The phenomenon|The root cause|Resolved|
| --- | --- | --- | --- |
| 1 | `no kernel image is available for execution on the device` | `TORCH_CUDA_ARCH_LIST ` Lack of `a` The back row|We have to `12.1a ` Weighing `source` Re-written|
| 2 | `TORCH_CUDA_ARCH_LIST` Verification is empty|It's used.`./source-build-env.sh`(sub-shell)|Changed `source ./source-build-env.sh` |
| 3 |The compilation card is dead.`git clone triton-lang/triton.git` |GitHub connects directly to ~40 KB/s|with `gh-proxy.com ` image , `rm -rf vllm/.deps/triton_kernels-*` Restarted|
| 4 | `pip install` Put the torch into cu128 / nightly.|Not running.`use_existing_torch.py ` Or not added.`--no-build-isolation` |Remove the wrong torch and do Section 3 again|
| 5 |flashinfer aarch64+cu13 can't find the wheel|PyPI doesn't have to go to the official index| `--index-url https://flashinfer.ai/whl/cu130/torch2.11/` and `--no-deps` |
| 6 |Flashinfer imported newspaper `ModuleNotFoundError: requests` | `--no-deps` It's the only way to overcome Python dependency.|Additionally `requests einops cuda-tile` |
| 7 | `cuda-tile [tileiras]` CUDA 13.1 is missing|extra requires 13.1+; the local version is 13.0.88|Just dressed up.`cuda-tile` The main bag, no extra|
| 8 |Compilation CPU utilization rate is only 30%| `MAX_JOBS=6 ` Triggered `setup.py` Internal flow restrictions| `MAX_JOBS=20, NVCC_THREADS=2`→ 10 x 2 = 20 threads filled|
| 9 |OOM at the weights loading stage|Unified memory is not enough: 67GB main model + 5GB drafter + KV cache)| `drop_caches `; `--gpu-memory-utilization 0.60 `; It's down.`--max-model-len` |
| 10 | `linear_attention not supported by flash_attn` |Clearly specified `--attention-backend flash_attn` |Remove the parameter and let vLLM automatically select by layer|
| 11 | `DFlashDraftModel not found` |Drafter used `auto_map` Remote code not enabled|Starting to add `--trust-remote-code` |
| 12 |CUDA Graph Capture Stage Card dead/fried|sm_121a + spec decode compatibility paths are still closing|Required for the first run `--enforce-eager`, remove it after a successful run|
| 13 | `Triton compile error` Runtime error| `TORCH_CUDA_ARCH_LIST` Lost in the process of service|We have to do more before we start.`source source-build-env.sh` |
| 14 |Starting `OSError: Address already in use` |Port is occupied|Changing port or `sudo fuser -k 18000/tcp` |
| 15 | `--enable-prefix-caching` It crashes simultaneously with the spec decode.|A known bug|After a run, evaluate separately, do not run together|
| 16 |The second compilation didn't hit Ccache.| `CCACHE_DIR` Not exported / compilation Directory inconsistency|Let's go first.`ccache -s ` Check the hit rate, confirm `CMAKE_*_COMPILER_LAUNCHER=ccache` |

---

## Added: edition focus

|Title|Published|
| --- | --- |
| vLLM commit | `2cc008e7b`（main, 2026-04-28） |
| PyTorch | `2.11.0+cu130` |
| Triton | `3.6.0` |
| flashinfer | `0.6.9` |
| transformers | `5.6.2` |
|CUDA Toolkit / driver| `13.0.88 ` / `580.95.05` |
| Python / gcc | `3.12.13` / `13.3.0` |

---

## Supplement: Daily maintenance

```bash
### 重新激活环境（每次开终端）
conda activate vllm-dflash-gb10
source ~/xiangmu/vllm_dflash_gb10/vllm/source-build-env.sh

### 增量重编（命中 ccache）
cd ~/xiangmu/vllm_dflash_gb10/vllm
pip install --no-build-isolation -v -e . --force-reinstall --no-deps

### 完全清理重编
ccache -C
rm -rf ~/xiangmu/vllm_dflash_gb10/vllm/{build,.deps}

### 升级 vLLM
git pull && python use_existing_torch.py && sed -i "/^flashinfer/d" requirements/cuda.txt
pip install --no-build-isolation -v -e .
```

```

#### 一、推理对比

1. 添加dflash模块

```Markdown
推理命令：
vllm serve /srv/llm/models/Qwen3.6-35B-A3B     --host 0.0.0.0 --port 18000     --served-model-name qwen36-35b-a3b-dflash     --trust-remote-code --dtype bfloat16     --speculative-config '{"method":"dflash","model":"/srv/llm/models/DFlash/Qwen3.6-35B-A3B-DFlash","num_speculative_tokens":5}'     --max-model-len 8192     --max-num-seqs 8     --gpu-memory-utilization 0.85

性能压测：
vllm bench serve     --backend openai-chat     --base-url http://127.0.0.1:18000     --endpoint /v1/chat/completions     --model qwen36-35b-a3b-dflash     --tokenizer /srv/llm/models/Qwen3.6-35B-A3B     --dataset-name spec_bench     --dataset-path /srv/llm/datasets/spec_bench_question.jsonl     --spec-bench-output-len 256     --num-prompts 50     --max-concurrency 1     --seed 42

结果：
============ Serving Benchmark Result ============
Successful requests:                     50
Failed requests:                         0
Maximum request concurrency:             1
Benchmark duration (s):                  292.62
Total input tokens:                      13655
Total generated tokens:                  12800
Request throughput (req/s):              0.17
Output token throughput (tok/s):         43.74
Peak output token throughput (tok/s):    15.00
Peak concurrent requests:                2.00
Total token throughput (tok/s):          90.41
---------------Time to First Token----------------
Mean TTFT (ms):                          294.13
Median TTFT (ms):                        261.00
P99 TTFT (ms):                           571.91
-----Time per Output Token (excl. 1st token)------
Mean TPOT (ms):                          21.80
Median TPOT (ms):                        21.95
P99 TPOT (ms):                           29.03
---------------Inter-token Latency----------------
Mean ITL (ms):                           72.82
Median ITL (ms):                         73.61
P99 ITL (ms):                            87.71
---------------Speculative Decoding---------------
Acceptance rate (%):                     48.15
Acceptance length:                       3.41
Drafts:                                  3766
Draft tokens:                            18830
Accepted tokens:                         9066
Per-position acceptance (%):
  Position 0:                            76.26
  Position 1:                            57.12
  Position 2:                            44.56
  Position 3:                            35.05
  Position 4:                            27.75
```

1. There is no Dflash module

```Markdown
1.推理命令
vllm serve /srv/llm/models/Qwen3.6-35B-A3B \
    --host 0.0.0.0 \
    --port 18001 \
    --served-model-name qwen36-35b-a3b-baseline \
    --trust-remote-code \
    --dtype bfloat16 \
    --max-model-len 32768 \
    --max-num-seqs 1 \
    --gpu-memory-utilization 0.70 \
    --enforce-eager \
    2>&1 | tee /tmp/vllm-qwen36-35b-baseline.log

2. 性能压测命令
vllm bench serve \
    --backend openai-chat \
    --base-url http://127.0.0.1:18001 \
    --endpoint /v1/chat/completions \
    --model qwen36-35b-a3b-baseline \
    --tokenizer /srv/llm/models/Qwen3.6-35B-A3B \
    --dataset-name spec_bench \
    --dataset-path /srv/llm/datasets/spec_bench_question.jsonl \
    --spec-bench-output-len 256 \
    --num-prompts 50 \
    --max-concurrency 1 \
    --seed 42


结果：
============ Serving Benchmark Result ============
Successful requests:                     50
Failed requests:                         0
Maximum request concurrency:             1
Benchmark duration (s):                  594.69
Total input tokens:                      13655
Total generated tokens:                  12800
Request throughput (req/s):              0.08
Output token throughput (tok/s):         21.52
Peak output token throughput (tok/s):    25.00
Peak concurrent requests:                2.00
Total token throughput (tok/s):          44.49
---------------Time to First Token----------------
Mean TTFT (ms):                          893.20
Median TTFT (ms):                        213.45
P99 TTFT (ms):                           16024.24
-----Time per Output Token (excl. 1st token)------
Mean TPOT (ms):                          43.14
Median TPOT (ms):                        43.14
P99 TPOT (ms):                           43.34
---------------Inter-token Latency----------------
Mean ITL (ms):                           42.97
Median ITL (ms):                         42.83
P99 ITL (ms):                            53.15
==================================================
```

#### Second, the control panel is set to: single concurrency / spec_bench / 50 prompt)

|  |  |  |  |
| --- | --- | --- | --- |
|Indicators| Baseline | DFlash |Changes|
| Duration | 594.69 s | 292.62 s |It's 2.03 x.|
| Output tok/s | 21.52 | 43.74 | 2.03× ✅ |
| Total tok/s | 44.49 | 90.41 | 2.03× ✅ |
| Mean TPOT | 43.14 ms | 21.80 ms |It's 1.98x.|
| Mean TTFT | 893.20 ms | 294.13 ms |It's 3.04x.|
| Mean ITL | 42.97 ms | 72.82 ms |It looks like a slow 1.69 x.|
| Acceptance rate | — | 48.15% |Health|
| Acceptance length | — | 3.41 / 5 |Health|

After completing the same 50 spec_bench tasks, DFlash took half the time. This is what the spec decode should do.
