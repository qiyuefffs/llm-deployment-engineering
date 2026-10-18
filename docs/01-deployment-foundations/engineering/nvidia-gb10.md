# NVIDIA GB10：ARM64构建、FP8、AWQ、MTP与DFlash

[工程实例索引](README.md) · [知识体系总目录](../SUMMARY.md)

技术标签：`CUDA 13 / ARM64 / vLLM / speculative decoding`

## 工程配置与实验分支

| 分支 | 环境 / 模型 | 适配问题 | 性能数据入口 |
| --- | --- | --- | --- |
| 基础构建 | GB10、ARM64、128GB、CUDA13 | x86 wheel不可直接使用；SM12.1与特定kernel构建 | 源码、依赖与构建日志 |
| Qwen FP8 | vLLM commit17d87168d；Qwen3.6-35B-A3B FP8 | FP8 KV、FlashInfer、prefix/chunked | 200请求、25600输出token、297.46s、86.06token/s |
| Gemma AWQ | 26B-A4B与31B各4/8bit | 打包、量化kernel、模型计算结构 | 四组TTFT/TPOT/ITL/E2E |
| Gemma MTP | 主模型＋assistant，3个候选 | 接受率、验证成本、batch | c1/c2/c4配对 |
| DFlash | 自定义分支、drafter、CUDA扩展 | 多套torch/CUDA/源码需配套 | 原两配置观察约2.03倍，非单变量归因 |

## 部署适配执行顺序

```text
ARM64/驱动/CUDA确认 → 固定源码及torch → 构建扩展
 → 小输入完成生成 → API与SSE → 无优化基线
 → AWQ或MTP或DFlash独立分支 → 同负载复测 → 质量及资源验收
```

1. 分别记录每个分支的`git rev-parse HEAD`、`pip freeze`、`torch.__version__`、`nvcc --version`与模板。下面多篇文章的环境不同，不能合并到一个虚拟环境再声称复现。
2. Qwen构建中曾把`TORCH_CUDA_ARCH_LIST`设为12.0绕过特定FP4 kernel错误；这不改变GB10计算能力12.1，也不是所有版本的默认编译参数。
3. 用[Qwen FP8完整服务步骤](../chapters/frameworks/vllm-service.md)完成启动、请求和输出保存，之后恢复历史性能预算。
4. AWQ四组统一输入目标2048、输出128、200请求、c2；比较前确认各制品配置与实际输出。MTP使用自己的512/256负载，不与AWQ绝对吞吐交叉排名。
5. DFlash先检查drafter匹配与草稿接受统计，再看TTFT/TPOT和目标模型质量；原配置同时改变ctx、seqs、memory与eager，组合收益不能归因给单一模块。

## 结果与验收

Qwen原200请求突发的平均TTFT为148430.70ms，P99为293115.24ms，吞吐86.06token/s并不代表交互体验好。验收应补有限到达率和并发，让TTFT与尾延迟达到目标。

MTP原吞吐增幅按c1/c2/c4约44.76%/32.68%/53.19%。保留原始数据，不把接受率或总吞吐当作质量等价证明。完整构建、参数、日志和所有对照表按原技术文章顺序置于下方。

## 完整技术记录的使用约定

以下直接保留相关FlowUs文章的技术正文、命令、表格、日志、失败和后续实验，不以摘要替代原过程。私人路径、节点、认证与附件地址脱敏；`<NODE_IP>`等占位符需要按当前环境填写。原建议或预测仍是建议或预测。上方执行顺序与技术修订用于解释历史记录中的冲突，历史GPU/NPU实验未在本轮重跑。

## R05 · NVIDIA GB10 ARM编译llamacpp

设备：NVIDIA GB10

架构：ARM64

GPU架构参数：12.1      编译时设置为121

系统： ubunut24

编译过程如下：


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

模型量化命令

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

加载Qwen3-30B-A3B模型FP16精度

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

## R06 · nvidia GB10设备（arm64架构）编译vllm

环境配置：

nvidia ：cuda12.8及以上

conda虚拟环境

编译链接：[https://forums.developer.nvidia.com/t/run-vllm-in-spark/348862](https://forums.developer.nvidia.com/t/run-vllm-in-spark/348862)

编译流程

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

## R07 · DGX Spark适配编译vllm部署Qwen3.6-35B-A3B模型（bf16/fp8精度）

设备：DGX Spark GB10

Memory：128 GB

系统：ubuntu24.04

模型：

Qwen3.6-35B-A3B

Qwen3.6-35B-A3B-FP8

vllm版本：

Version：0.19.1rc1.dev337+g17d87168d.cu130

conda环境：vllm-qwen3.6

vllm编译过程:

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

推理：

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

## R08 · NVIDIA GB10部署Qwen3-30B-A3B-Instruct-2507

docker创建命令

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

vllm启动推理命令

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

测试命令：

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

本地部署，暴露端口给其他设备调用

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

docker创建命令

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

性能测试

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

## R09 · DGX GB10部署Gemma-4系列AWQ量化模型

设备：DGX Spark GB10

Memory：128 GB

系统：ubuntu24.04

模型：
it表示指令微调后的，未带it表示预训练模型；
量化方式：AWQ
量化精度：4bit、8bit


gemma-4-26B-A4B-it-AWQ-4bi

gemma-4-26B-A4B-it-AWQ-8bit

gemma-4-31B-it-AWQ-4bit

gemma-4-31B-it-AWQ-8bit

vllm版本：

python wheel: vllm-0.19.0+cu130

显存占用均为：81GB，GPU限制均为0.65

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

## R10 · DGX Spark GB10部署gemma-4系列模型及关闭MTP推理加速

1. 推理命令

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

进入容器：docker exec -it gemma4-26b-a4b-base-8016 bash

1. 性能压测

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

## R11 · DGX Spark GB10部署gemma-4系列模型及MTP推理加速

推理命令

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

进入容器：docker exec -it gemma4-26b-a4b-mtp-v3 bash

并发压测记录

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

## R12 · DGX Spark GB10编译DFlash推理加速模块集成到vllm中

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

## 2. 环境配置

### 2.1 系统依赖

```bash
sudo apt update && sudo apt install -y \
    build-essential gcc-13 g++-13 \
    python3.12 python3.12-dev python3.12-venv \
    cmake ninja-build ccache git git-lfs \
    libibverbs-dev rdma-core librdmacm-dev pkg-config
```

> 不要装 `libnvidia-cudnn9-cu13-dev` / `libnccl-dev`，会与 PyTorch wheel 自带的 NCCL/cuDNN 冲突。

### 2.2 conda 环境 + PyTorch cu130

```bash
conda create -n vllm-dflash-gb10 python=3.12 -y
conda activate vllm-dflash-gb10
pip install --upgrade pip setuptools wheel packaging ninja

pip install --index-url https://download.pytorch.org/whl/cu130 \
    torch==2.11.0 torchvision==0.26.0 torchaudio==2.11.0
```

验证 GB10 capability 必须为 `(12, 1)`：

```bash
python -c "import torch; print(torch.cuda.get_device_capability(0), torch.cuda.get_device_name(0))"
### (12, 1) NVIDIA GB10
```

### 2.3 编译环境变量脚本

在 `vllm/` 源码根写入 `source-build-env.sh`：

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

## 3. 编译流程

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

> **三个 `--no-` 缺一不可**：`--no-build-isolation`（防 pip 重装 torch）、flashinfer 安装时的 `--no-deps`（防拉错 torch 版本）、`cuda-tile` 不带 `[tileiras]` extra（要求 CUDA 13.1+）。

---

## 4. 推理命令

> 模型路径：
> - 主模型 `~/models/Qwen3.6-35B-A3B`（67 GB BF16）
> - DFlash drafter `~/models/DFlash/Qwen3.6-35B-A3B-DFlash`（905 MB）

### 4.1 启动前清理

```bash
sudo sync && echo 3 | sudo tee /proc/sys/vm/drop_caches
free -h        # available 必须 >= 100 GiB
nvidia-smi --query-compute-apps=pid,process_name,used_memory --format=csv
```

### 4.2 首次启动（保守、单并发）

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

### 4.3 高吞吐配置（跑通基线后切换）

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

### 4.4 接口烟测

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

### 4.5 确认 DFlash 在工作

```bash
grep -E "dflash|Mean acceptance length|accept" /tmp/vllm-qwen36-35b-dflash.log | tail -20
```

期望看到 `Mean acceptance length: 2.x` 与 `Per-position acceptance rate` 等指标。

---

## 5. 性能压测命令

### 5.1 ShareGPT 数据集压测（推荐）

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

### 5.2 随机长度压测（控制输入/输出 token 数）

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

### 5.3 关注指标

| 指标 | 含义 | DFlash 期望值 |
| --- | --- | --- |
| `Mean acceptance length` | 平均接受长度 | 2.4 – 3.1（5 spec tokens） |
| `Avg Draft acceptance rate` | 草稿整体接受率 | 28% – 42% |
| `Per-position acceptance rate` | 每个 spec 位置的接受率 | 第 1 位 0.7-0.9，第 5 位 0.05-0.13 |
| `Avg generation throughput` | 端到端生成吞吐 | 单并发 22-29 tok/s（eager） |

### 5.4 实时指标抓取

```bash
### 服务侧日志（每 10 秒一行 SpecDecoding metrics）
tail -F /tmp/vllm-qwen36-35b-dflash.log | grep -E "SpecDecoding|generation throughput"

### Prometheus 端点
curl -s [服务地址按本实例配置] | grep -E "^vllm_(spec|generation|prompt)"
```

### 5.5 调优顺序（每改一项压一次）

1. 去掉 `--enforce-eager` → 启用 CUDA Graph，吞吐 1.3–1.8x
2. `num_speculative_tokens` 5 → 10 → 15，看 acceptance rate 拐点
3. `--max-num-seqs` 1 → 2 → 4 → 8
4. `--gpu-memory-utilization` 0.70 → 0.80 → 0.85
5. `--max-model-len` 按业务上下文长度按需放开

---

## 6. 踩坑记录

| # | 现象 | 根因 | 解决 |
| --- | --- | --- | --- |
| 1 | `no kernel image is available for execution on the device` | `TORCH_CUDA_ARCH_LIST` 缺 `a` 后缀 | 必须 `12.1a`，重 `source` 后重编 |
| 2 | `TORCH_CUDA_ARCH_LIST` 验证为空 | 用了 `./source-build-env.sh`（子 shell） | 改 `source ./source-build-env.sh` |
| 3 | 编译卡死在 `git clone triton-lang/triton.git` | GitHub 直连 ~40 KB/s | 配 `gh-proxy.com` 镜像，`rm -rf vllm/.deps/triton_kernels-*` 重启 |
| 4 | `pip install` 把 torch 冲成 cu128 / nightly | 没跑 `use_existing_torch.py` 或没加 `--no-build-isolation` | 卸掉错误 torch，重做第 3 节 |
| 5 | flashinfer aarch64+cu13 找不到 wheel | PyPI 没有，必须走官方 index | `--index-url https://flashinfer.ai/whl/cu130/torch2.11/` 且 `--no-deps` |
| 6 | flashinfer 导入报 `ModuleNotFoundError: requests` | `--no-deps` 跳过了纯 Python 依赖 | 补装 `requests einops cuda-tile` |
| 7 | `cuda-tile [tileiras]` 报 CUDA 13.1 缺失 | extra 强制 13.1+，本机 13.0.88 | 只装 `cuda-tile` 主包，不带 extra |
| 8 | 编译 CPU 利用率仅 30% | `MAX_JOBS=6` 触发 `setup.py` 内部限流 | `MAX_JOBS=20, NVCC_THREADS=2` → 10×2=20 线程压满 |
| 9 | OOM 在权重加载阶段 | unified memory 不足（67GB 主模型 + 5GB drafter + KV cache） | `drop_caches`；`--gpu-memory-utilization 0.60`；降 `--max-model-len` |
| 10 | `linear_attention not supported by flash_attn` | 显式指定了 `--attention-backend flash_attn` | 移除该参数，让 vLLM 按层自动选 |
| 11 | `DFlashDraftModel not found` | drafter 用 `auto_map`，未启用远程代码 | 启动加 `--trust-remote-code` |
| 12 | CUDA Graph capture 阶段卡死/炸 | sm_121a + spec decode 兼容路径仍在收敛 | 首次必加 `--enforce-eager`，跑通后再去掉 |
| 13 | `Triton compile error` 运行时报错 | `TORCH_CUDA_ARCH_LIST` 在服务进程里丢了 | 启动前必须再 `source source-build-env.sh` |
| 14 | 启动 `OSError: Address already in use` | 端口被占 | 换端口或 `sudo fuser -k 18000/tcp` |
| 15 | `--enable-prefix-caching` 与 spec decode 同时开崩 | 已知 bug | 跑通后再单独评估，不要一起开 |
| 16 | 二次编译没命中 ccache | `CCACHE_DIR` 未导出 / 编译目录不一致 | 先 `ccache -s` 看命中率，确认 `CMAKE_*_COMPILER_LAUNCHER=ccache` |

---

## 附：版本锚点

| 项 | 版本 |
| --- | --- |
| vLLM commit | `2cc008e7b`（main, 2026-04-28） |
| PyTorch | `2.11.0+cu130` |
| Triton | `3.6.0` |
| flashinfer | `0.6.9` |
| transformers | `5.6.2` |
| CUDA Toolkit / 驱动 | `13.0.88` / `580.95.05` |
| Python / gcc | `3.12.13` / `13.3.0` |

---

## 附：日常维护

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

1. 无dflash模块

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

#### 二、对照表（同设置：单并发 / spec_bench / 50 个 prompt）

|  |  |  |  |
| --- | --- | --- | --- |
| 指标 | Baseline | DFlash | 变化 |
| Duration | 594.69 s | 292.62 s | 快 2.03× ✅ |
| Output tok/s | 21.52 | 43.74 | 2.03× ✅ |
| Total tok/s | 44.49 | 90.41 | 2.03× ✅ |
| Mean TPOT | 43.14 ms | 21.80 ms | 快 1.98× ✅ |
| Mean TTFT | 893.20 ms | 294.13 ms | 快 3.04× ✅ |
| Mean ITL | 42.97 ms | 72.82 ms | 看起来慢 1.69× ⚠️ |
| Acceptance rate | — | 48.15% | 健康 |
| Acceptance length | — | 3.41 / 5 | 健康 |

完成同样 50 条 spec_bench 任务，DFlash 用了一半的时间。这就是 spec decode 应该有的效果。
