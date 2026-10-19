---
id: T44
title: "Qwen3.8-27B 与 Qwen3.8 Flash-Next 部署与推理性能优化"
type: tutorial
volume: book
layer: 4
platform: "general"
device: "general"
status: historical
source_ids: []
updated: 2026-10-19
summary: "这是本文最重要的部分。Qwen3.8-27B 和 Qwen3.8 Flash-Next 不是同一套权重， 不能互相替代，也不能把性能数据混在一起。"
---

# Qwen3.8-27B 与 Qwen3.8 Flash-Next 部署与推理性能优化

[项目索引](README.md) · [通用性能优化测试方法论](../edge-llm-performance-methodology.md)

> 验证基线：AMD Ryzen AI MAX+ 395 / Radeon 8060S / `gfx1151` /
> 128 GB UMA / Vulkan RADV 26.1.7 / ROCm 7.2.4。  
> 补充验证：NVIDIA A10 24 GB / llama.cpp b10430 的 Qwen3.8-27B 对照。  
> 事实截止：2026-10-19。

## 1. 必须先区分两个模型

这是本文最重要的部分。Qwen3.8-27B 和 Qwen3.8 Flash-Next 不是同一套权重，
不能互相替代，也不能把性能数据混在一起。

| 项目 | Qwen3.8-27B | Qwen3.8 Flash-Next |
|---|---|---|
| 架构 | `qwen35` | `qwen4exp` |
| 参数量级 | 27B dense/hybrid | 约 176.94B MoE |
| 层数 | 65 | 48 |
| 专家 | 无 MoE 配置 | 512 experts，每 token 激活 10 |
| 上下文元数据 | 262144 | 262144 |
| 本工作区文件 | Q4_K_M 约 17.1 GB，Q8_0 约 29.0 GB | UD-Q4_K_XL 四分片约 104 GiB |
| 单机内存 | 27B Q4 可轻松放入 128 GB | 接近整机容量边界 |
| 典型用途 | 单机日常文本、较低成本 | 大 MoE、高能力、需要严格资源保护 |

本工作区中 `Qwen3.8 Flash Next` 的元数据明确写的是 `512x56B`、总参数约
176.94B，不是 27B。不要把 `.12` 上运行的 27B 服务结果当作 Flash-Next 的
基线，也不要把 Flash-Next 的 20 tok/s 当作 27B 的结果。

## 2. 已验证资产

### 2.1 Qwen3.8-27B

本机：

```text
实际目录: <LLAMA_CPP>/models

Qwen3.8-27B-Q4_K_M.gguf
bytes: 17106773984
sha256: <MODEL_SHA256>

Qwen3.8-27B-Q8_0.gguf
bytes: 29047085024
sha256: <MODEL_SHA256>
```

另一份远端 `UD-Q4_K_XL`：

```text
bytes: 17923394624
sha256: <MODEL_SHA256>
```

它不是本机 `Q4_K_M`，不要直接合并性能排序。

下文下载命令把新文件放到 `<MODEL_ROOT>/Qwen3.8-27B-GGUF`。
如果继续使用本机现有文件，把 `MODEL` 改为上面的实际目录即可。

### 2.2 Qwen3.8 Flash-Next

主模型四分片：

```text
Qwen3.8-Flash-Next-UD-Q4_K_XL-00001-of-00004.gguf
bytes: 10946624
sha256: <MODEL_SHA256>

Qwen3.8-Flash-Next-UD-Q4_K_XL-00002-of-00004.gguf
bytes: 49859583136
sha256: <MODEL_SHA256>

Qwen3.8-Flash-Next-UD-Q4_K_XL-00003-of-00004.gguf
bytes: 49376141504
sha256: <MODEL_SHA256>

Qwen3.8-Flash-Next-UD-Q4_K_XL-00004-of-00004.gguf
bytes: 12087983520
sha256: <MODEL_SHA256>
```

MTP draft：

```text
Qwen3.8-Flash-Next-MTP-Q4_K_M.gguf
bytes: 2622313344
sha256: <MODEL_SHA256>
```

已验证 MTP fork：

```text
commit: 322e5cdf4ccd1f18157ac322393d13e9ec60c74d
Vulkan server:
<LLAMA_CPP_MTP>/build-vulkan-mtp6/bin/llama-server
```

矩阵修复后的 cooperative-matrix 构建：

```text
<PROJECT_ROOT>/tools/qwen38-vulkan-coopmat-20260907/bin/llama-server
```

### 2.3 原始项目

```text
https://huggingface.co/Qwen/Qwen3.8-27B
https://huggingface.co/unsloth/Qwen3.8-27B-GGUF
https://huggingface.co/unsloth/Qwen3.8-Flash-Next-GGUF
https://github.com/ggml-org/llama.cpp
```

## 3. 硬件和公共前置条件

### 3.1 gfx1151

```bash
vulkaninfo --summary
rocminfo | grep -m 5 -E 'Name:|gfx1151'
free -h
awk '/MemAvailable|SwapFree/ {print $1,$2,$3}' /proc/meminfo
powerprofilesctl set performance
rocm-smi --showperflevel
```

建议检查：

```text
GPU: AMD Radeon Graphics / RADV GFX1151
MemTotal: 约 123 GiB
Swap: 保留可观测余量，不要在压力下主动清空 swap
```

不要设置 `HSA_OVERRIDE_GFX_VERSION` 伪装架构，驱动应原生识别 `gfx1151`。

### 3.2 资源预算

| 模型 | 权重 | 运行时最低建议余量 |
|---|---:|---:|
| 27B Q4 | 约 16 GiB | 至少 8 GiB 可用内存 |
| 27B Q8 | 约 27 GiB | 至少 12 GiB 可用内存 |
| Flash-Next Q4 | 约 104 GiB | 至少 8 GiB，长上下文建议更多 |
| Flash-Next + MTP | 约 106 GiB | 建议至少 10 GiB，且不保证 256K 长输入 |

Flash-Next 的启动脚本把 `MemAvailable < 2 GiB` 或 `SwapFree < 2 GiB`
当作紧急停止线。这是最低保护线，不是舒适生产余量。benchmark 中还使用
“加载后至少 4 GiB available”作为额外门槛。

### 3.3 32GB A10

Qwen3.8-27B Q4 在 A10 24 GB 上可使用 `-ngl 99` 全层 offload。
需要 CUDA 12.4 工具链，且要确认 16.8 GB 权重、KV cache 和计算 buffer
不会把 24 GB 显存吃满。A10 路线与 gfx1151 的 tok/s 不能直接比较。

## 4. 下载权重

### 4.1 Qwen3.8-27B

如果没有 `hf` 命令，先安装 `pip install -U huggingface_hub`。

```bash
mkdir -p <MODEL_ROOT>/Qwen3.8-27B-GGUF
hf download unsloth/Qwen3.8-27B-GGUF \
  Qwen3.8-27B-Q4_K_M.gguf \
  --local-dir <MODEL_ROOT>/Qwen3.8-27B-GGUF
```

需要质量对照时再下载 Q8：

```bash
hf download unsloth/Qwen3.8-27B-GGUF \
  Qwen3.8-27B-Q8_0.gguf \
  --local-dir <MODEL_ROOT>/Qwen3.8-27B-GGUF
```

校验：

```bash
sha256sum \
  <MODEL_ROOT>/Qwen3.8-27B-GGUF/Qwen3.8-27B-Q4_K_M.gguf \
  <MODEL_ROOT>/Qwen3.8-27B-GGUF/Qwen3.8-27B-Q8_0.gguf
```

如果上游文件与本机哈希不同，重新做基线，不要复用本文数值。

### 4.2 Flash-Next

工作区已有下载脚本：

```bash
cd <PROJECT_ROOT>
OUT_DIR=<PROJECT_ROOT>/models/Lucebox/Qwen3.8-Flash-Next-GGUF/UD-Q4_K_XL \
bash models/Lucebox/Qwen3.8-Flash-Next-GGUF/UD-Q4_K_XL/download_from_hf_mirror.sh
```

该脚本会按固定字节数下载四个分片，并检查 `.aria2` 控制文件。下载后手工校验：

```bash
cd <PROJECT_ROOT>/models/Lucebox/Qwen3.8-Flash-Next-GGUF/UD-Q4_K_XL
sha256sum *.gguf
```

启动时只需要指向分片 1，llama.cpp 会按 GGUF split 元数据读取后续分片。
四分片必须放在同一目录，不能只复制第一片。

## 5. 构建 llama.cpp

Vulkan 构建依赖：

```bash
sudo apt-get update
sudo apt-get install -y build-essential cmake ninja-build git \
  libvulkan-dev vulkan-tools glslc
```

HIP 构建还需要匹配 `gfx1151` 的 ROCm 工具链。A10 路线需要 CUDA 12.4
工具链和可用驱动。

### 5.1 27B 的 Vulkan 或 HIP 构建

```bash
cd /path/to/llama.cpp
git checkout 86b351fd64d5ebbf1ba795ffd60c8f4a8c958613

cmake -S . -B build-vulkan-gfx1151 \
  -DCMAKE_BUILD_TYPE=Release \
  -DGGML_VULKAN=ON \
  -DLLAMA_BUILD_UI=OFF \
  -DLLAMA_USE_PREBUILT_UI=OFF \
  -DLLAMA_CURL=OFF
cmake --build build-vulkan-gfx1151 --target llama-server llama-bench -j"$(nproc)"
```

HIP：

```bash
cmake -S . -B build-hip-gfx1151 \
  -DCMAKE_BUILD_TYPE=Release \
  -DGGML_HIP=ON \
  -DGGML_HIP_ROCWMMA_FATTN=ON \
  -DGGML_HIP_MMQ_MFMA=ON \
  -DCMAKE_HIP_ARCHITECTURES=gfx1151 \
  -DAMDGPU_TARGETS=gfx1151 \
  -DLLAMA_BUILD_UI=OFF \
  -DLLAMA_USE_PREBUILT_UI=OFF \
  -DLLAMA_CURL=OFF
cmake --build build-hip-gfx1151 --target llama-server llama-bench -j"$(nproc)"
```

27B 的历史最佳数据是 Q4 Kaggle 混合负载下的 Vulkan+MTP。建议先用当前
commit 重跑一次，不要盲目把旧数据当成当前二进制结果。

### 5.2 Flash-Next 的 cooperative-matrix 构建

Flash-Next 必须验证 Vulkan cooperative matrix。若 `glslc` 找不到
`libshaderc.so.1`，CMake feature test 会失败，最终二进制显示
`matrix cores: none`，Prefill 会慢约 23%-26%。

```bash
export LD_LIBRARY_PATH=/path/to/shaderc/lib:${LD_LIBRARY_PATH:-}
glslc --version
```

构建：

```bash
cd <LLAMA_CPP_MTP>
git checkout 322e5cdf4ccd1f18157ac322393d13e9ec60c74d

cmake -S . -B build-vulkan-mtp6 \
  -DCMAKE_BUILD_TYPE=Release \
  -DGGML_VULKAN=ON \
  -DLLAMA_BUILD_UI=OFF \
  -DLLAMA_USE_PREBUILT_UI=OFF \
  -DLLAMA_CURL=OFF

cmake --build build-vulkan-mtp6 \
  --target llama-server llama-bench \
  -j"$(nproc)"
```

检查设备能力：

```bash
build-vulkan-mtp6/bin/llama-server --list-devices
```

应看到 AMD Radeon / RADV GFX1151，并确认 cooperative matrix 可用。
`GGML_VK_DISABLE_COOPMAT=1` 只能作为消融变量，不应作为生产默认。

整数点积构建已实际测试，但没有稳定超过旧 cooperative-matrix 构建。
`GGML_VK_FORCE_MMVQ=1` 也没有稳定收益，不要默认开启。

## 6. Qwen3.8-27B 部署

### 6.1 gfx1151 默认单路配置

```bash
MODEL=<MODEL_ROOT>/Qwen3.8-27B-GGUF/Qwen3.8-27B-Q4_K_M.gguf
BIN=<LLAMA_CPP>/build-vulkan-gfx1151/bin/llama-server

"$BIN" \
  -m "$MODEL" \
  --alias qwen38-27b \
  -ngl 999 \
  --fit off \
  -c 32768 \
  -np 1 \
  -cb \
  -b 2048 \
  -ub 512 \
  -t 16 \
  -tb 16 \
  -fa on \
  -ctk f16 \
  -ctv f16 \
  --device Vulkan0 \
  --host 127.0.0.1 \
  --port 8390 \
  --metrics \
  --slots \
  --no-ui \
  --spec-type draft-mtp \
  --spec-draft-n-max 2 \
  --spec-draft-p-min 0.20
```

说明：

- `Qwen3.8-27B` 的 GGUF 有 `nextn_predict_layers=1`，MTP 头内嵌在模型中，
  历史命令只写 `--spec-type draft-mtp`，没有单独 draft 文件。
- 不要随便给它配另一个模型的 draft。
- `draft-mtp` 若不支持，先去掉整个 MTP 相关参数，保留 no-spec 基线。
- `-fa on` 是当前推荐；历史机器曾使用 `auto`，两者需在同一二进制上复核。

### 6.2 长上下文

32K 以上优先 Q8 KV：

```bash
  -c 65536 \
  -ctk q8_0 \
  -ctv q8_0
```

如果目标是 128K/256K，必须单独验证：

```bash
  -c 131072
  # 或
  -c 262144
```

历史记录中 128K/256K 主要证明“可以加载并处理短请求”，不是填满窗口
的长输入吞吐。不要用短 prompt 的 20+ tok/s 宣传 256K 长文档性能。

### 6.3 Q8 质量对照

```bash
MODEL=<MODEL_ROOT>/Qwen3.8-27B-GGUF/Qwen3.8-27B-Q8_0.gguf
```

Q8 适合做量化误差和质量对照，不适合追求速度。历史 Q8 Vulkan+MTP
约 13.12 tok/s，明显低于 Q4 Vulkan。

### 6.4 性能基线

历史真实请求对比：

| 模型 | 后端 | Decode | Prompt | MTP 接受率 |
|---|---|---:|---:|---:|
| Q4_K_M | Vulkan | 21.56 tok/s | 33.35 tok/s | 65.7% |
| Q4_K_M | HIP | 16.86 tok/s | 95.65 tok/s | 64.5% |
| Q8_0 | Vulkan | 13.12 tok/s | 33.35 tok/s | 62.5% |
| Q8_0 | HIP | 12.31 tok/s | 87.48 tok/s | 51.2% |

MTP 长度扫描：

| `n-max` | Decode | 接受率 |
|---:|---:|---:|
| 1 | 17.71 | 75.0% |
| 2 | 20.90 | 66.7% |
| 3 | 19.26 | 50.7% |
| 4 | 18.72 | 45.8% |

结论：

- 日常单路优先 Q4_K_M + Vulkan + `n-max=2`。
- HIP 的 Prefill 更快，但 Decode 低于 Vulkan；并发场景需要重新测。
- Q8 是质量/对照 profile，不是速度 profile。
- 32K Prompt 使用 Q8 KV 比 F16 KV 快约 14.6%：

```text
F16/F16: 180.85 tok/s
Q8/Q8:   207.19 tok/s
64K F16: 110.99 tok/s
```

### 6.5 NVIDIA A10 24GB CUDA 路线

使用 ModelScope 的 Abiray Q4_K_M 文件：

```text
模型: Qwen3.8-27B-Q4_K_M.gguf
bytes: 16810714400
sha256: <MODEL_SHA256>
```

这不是本机 Unsloth Q4_K_M 的哈希，不能混用性能数据。

快速启动：

```bash
export LD_LIBRARY_PATH="$PWD/cuda12/cuda_nvcc-linux-x86_64-12.4.131-archive/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"

./build-cuda12/bin/llama-server \
  -m models/Qwen3.8-27B-Q4_K_M.gguf \
  --host 127.0.0.1 \
  --port 8000 \
  -ngl 99 \
  -c 4096 \
  -np 2 \
  -fa on
```

`-c 4096 -np 2` 表示每槽约 2048 token。A10 24GB 下不要把上下文和并发
同时拉高。Flash Attention A/B 的历史结果：

| 配置 | 长档并发 2 | TTFT p95 | 输出 token/s | 峰值显存 |
|---|---:|---:|---:|---:|
| FA off | 20/20 | 1.7893 s | 26.8582 | 16111 MiB |
| FA on | 20/20 | 1.5740 s | 28.1866 | 16063 MiB |

该 A10 结果不能迁移到 395，但说明 Flash Attention 应在目标机器上单独 A/B。

### 6.6 27B 优化顺序

1. 固定模型文件、后端、context、batch、线程和采样；
2. 先建立 no-spec 基线；
3. 比较 `n-max=1/2/3/4`，当前历史最优点是 2；
4. 比较 `p-min=0/0.1/0.2`，历史长输出最优点是 0.2；
5. 短上下文用 `f16/f16` KV，32K 以上比较 `q8_0/q8_0`；
6. 比较 Vulkan/HIP，按 Prompt/Decode 目标选择；
7. Q8 仅用于质量对照；
8. 正式结论至少 3 次重复，并同时看 Decode、TTFT 和 E2E。

## 7. Qwen3.8 Flash-Next 部署

### 7.1 启动前检查

```bash
MODEL_DIR=<PROJECT_ROOT>/models/Lucebox/Qwen3.8-Flash-Next-GGUF
MODEL=$MODEL_DIR/UD-Q4_K_XL/Qwen3.8-Flash-Next-UD-Q4_K_XL-00001-of-00004.gguf
DRAFT=$MODEL_DIR/MTP/Qwen3.8-Flash-Next-MTP-Q4_K_M.gguf

ls -lh "$MODEL_DIR"/UD-Q4_K_XL/*.gguf "$DRAFT"
sha256sum "$MODEL_DIR"/UD-Q4_K_XL/*.gguf "$DRAFT"
free -h
```

四分片合计约 104 GiB，draft 约 2.44 GiB。加载前至少确认没有其他模型进程：

```bash
pgrep -af 'llama-server|llama-bench|llama-cli|rpc-server|dflash_server'
```

### 7.2 推荐默认：8K 或 16K 窗口，no-spec

```bash
BIN=<PROJECT_ROOT>/tools/qwen38-vulkan-coopmat-20260907/bin/llama-server

"$BIN" \
  -m "$MODEL" \
  --device Vulkan0 \
  -ngl all \
  --split-mode none \
  -c 16384 \
  -np 1 \
  -fa on \
  -ctk q4_0 \
  -ctv q4_0 \
  -t 16 \
  -tb 16 \
  -b 2048 \
  -ub 1024 \
  --cache-ram 1024 \
  --host 127.0.0.1 \
  --port 8109 \
  --no-webui \
  --metrics \
  --slots \
  --alias qwen38-flash-next
```

注意：

- `-c 16384` 是窗口，不是实际输入长度；
- `-np 1` 是当前安全默认，Flash-Next 内存余量很小；
- `q4_0/Q4 KV` 是当前已验证的长上下文省内存配置；
- `--cache-ram 1024` 用于重复长前缀，若不需要缓存可设为 0；
- `GGML_VK_DENSE_WAVE32=0`，不要使用未通过的 Wave32 配置；
- 不要与 27B 服务同时运行在同一台 128 GB 机器上。

### 7.3 可选 MTP3

MTP 需要 draft 文件：

```bash
"$BIN" \
  -m "$MODEL" \
  --device Vulkan0 \
  -ngl all \
  --split-mode none \
  -c 16384 \
  -np 1 \
  -fa on \
  -ctk q4_0 \
  -ctv q4_0 \
  -t 16 \
  -tb 16 \
  -b 2048 \
  -ub 1024 \
  --cache-ram 1024 \
  --host 127.0.0.1 \
  --port 8109 \
  --no-webui \
  --alias qwen38-flash-next-mtp \
  --model-draft "$DRAFT" \
  --n-gpu-layers-draft all \
  --spec-type draft-mtp \
  --spec-draft-n-max 3 \
  --spec-draft-n-min 0 \
  --spec-draft-p-min 0.75 \
  --spec-draft-backend-sampling \
  --spec-draft-type-k q4_0 \
  --spec-draft-type-v q4_0
```

使用条件：

- 输出较长；
- 已有较深上下文；
- 单 slot；
- 内存余量足够；
- 已经验证 MTP 的 E2E，而不只是 Decode。

256K 窗口下不要直接启用 MTP3，当前机器在 draft 加载阶段就会触发资源保护。

### 7.4 使用现成受保护启动器

```bash
cd <PROJECT_ROOT>

# 只打印命令
python3 tools/start_qwen38_decode.py --dry-run

# 默认 MTP3
python3 tools/start_qwen38_decode.py

# no-spec
python3 tools/start_qwen38_decode.py --profile baseline

# 指定端口
python3 tools/start_qwen38_decode.py --profile baseline --port 8110
```

该启动器会：

- 检查已存在的 llama 模型进程；
- 要求 `MemAvailable` 和 `SwapFree` 至少 2 GiB；
- 清除继承的 `GGML_VK_*` 和 `LLAMA_ARG_*` 实验变量；
- 设置 `GGML_VK_DENSE_WAVE32=0`；
- 运行期间每秒检查内存，触发压力时只终止自己启动的服务；
- 只允许 loopback 监听。

它默认不修改系统 swap，也不会替你清理其他进程。

## 8. Flash-Next 健康检查和 API

```bash
curl --noproxy '*' -fsS http://127.0.0.1:8109/health
curl --noproxy '*' -fsS http://127.0.0.1:8109/v1/models | jq
curl --noproxy '*' -fsS http://127.0.0.1:8109/props | jq
```

请求：

```bash
curl --noproxy '*' -fsS \
  http://127.0.0.1:8109/v1/chat/completions \
  -H 'Content-Type: application/json' \
  -d '{
    "model": "qwen38-flash-next",
    "messages": [
      {"role":"user","content":"用三句话解释 PagedAttention 和 Prefix Cache 的区别。"}
    ],
    "temperature": 1.0,
    "top_p": 0.95,
    "top_k": 20,
    "min_p": 0.05,
    "seed": 123,
    "max_tokens": 128,
    "stream": true
  }'
```

启动验收：

- `/health` 返回 ok；
- `/props` 的模型路径指向四分片目录；
- 请求实际返回 128 个 token；
- `prompt_n`、`cache_n`、`predicted_n` 与预期一致；
- 内存最低值不低于 2 GiB；
- 日志中没有 `VK_ERROR`、device lost、OOM 或 assert。

## 9. Flash-Next 性能基线

### 9.1 8K 窗口

真实采样，512 token 输入、128 token 输出：

| 配置 | 输入深度 | Prefill | Decode | TTFT | E2E |
|---|---:|---:|---:|---:|---:|
| 旧构建，无 MTP | 0 | 227.181 | 24.073 | 2.358 s | 7.634 s |
| 新构建，无 MTP | 0 | 285.541 | 24.302 | 1.895 s | 7.122 s |
| 新构建，ub1024 | 0 | 284.618 | 24.132 | 1.909 s | 7.173 s |
| 旧构建，无 MTP | 4096 | 267.834 | 20.398 | 17.326 s | 23.553 s |
| 新构建，无 MTP | 4096 | 328.878 | 20.421 | 14.133 s | 20.352 s |
| 新构建，ub1024 | 4096 | 354.720 | 20.311 | 13.110 s | 19.364 s |
| 新构建，MTP3+ub1024 | 4096 | 333.663 | 23.303 | 13.932 s | 19.396 s |

关键结论：

- cooperative matrix 修复主要提升 Prefill，Decode 基本不变；
- ub1024 对长输入 Prefill 有额外收益；
- MTP3 对约 4K 输入的 Decode 有约 14.6% 提升，但 E2E 几乎不变；
- 对短输入，MTP 可能因 draft 开销变慢。

### 9.2 16K 窗口，8K 输入，512 输出

| 配置 | Prefill | Decode | TTFT | E2E | 接受率 |
|---|---:|---:|---:|---:|---:|
| 旧构建，无 MTP | 361.080 | 20.480 | 22.691 s | 47.644 s | - |
| 旧构建，MTP3 | 341.778 | 22.095 | 23.971 s | 47.172 s | 72.99% |
| 新 intdot，无 MTP | 364.973 | 20.582 | 22.453 s | 47.283 s | - |
| 新 intdot，MTP3 | 338.684 | 21.832 | 24.190 s | 47.630 s | 70.15% |

旧构建 MTP3 相对无 MTP：

```text
Decode +7.89%
TTFT  +5.64%
E2E   -0.99%
```

因此 MTP3 是“持续生成优化”，不是“首响应优化”。默认部署建议 no-spec，
只有在业务输出足够长且实测 E2E 改善时才启用 MTP3。

### 9.3 长上下文

64K target-only 真实采样：

| 实际输入 | Prefill | Decode | TTFT |
|---:|---:|---:|---:|
| 512 | 228.074 | 23.253 | 2.414 s |
| 4,607 | 265.051 | 19.501 | 17.558 s |
| 16,896 | 213.306 | 16.802 | 79.376 s |
| 33,281 | 184.472 | 14.826 | 180.593 s |
| 61,953 | 161.315 | 11.740 | 384.229 s |

64K MTP 测试在长深度触发资源压力，没有完整结果。128K Q4 MTP 只完成了
约 564-token prompt 的容量 smoke test。256K：

```text
短输入可以启动
约 28K 输入、512 输出：TTFT 111.159 s，Decode 13.431 tok/s
最低 MemAvailable 约 3.10 GiB
MTP3 在 draft 加载阶段失败
```

结论：

- 64K 以上必须把 Prefill/TTFT 作为主指标；
- 256K 当前只是容量边界，不是生产速度；
- 256K + MTP3 不建议尝试；
- 要支持 256K 长输入生产，需要更小 target、更多内存、更低 KV 或更成熟
  的分段/PD 方案，继续调 `n-max` 不能解决容量。

## 10. Prefix Cache

### 10.1 原理

Prefix Cache 只复用完全相同的 prompt 前缀 KV。它不能减少最大 context
分配，也不能优化首次冷请求。请求必须带：

```json
{"cache_prompt": true}
```

服务端需要：

```bash
--cache-ram 1024
```

当同一文档被多轮提问，或 system prompt/RAG 前缀固定时，收益很大。

### 10.2 实测

8K 前缀、16K 窗口：

| 配置 | 阶段 | TTFT |
|---|---|---:|
| baseline | 冷前缀 | 22.403 s |
| baseline | 命中前缀 | 2.169 s |
| MTP3 | 冷前缀 | 23.688 s |
| MTP3 | 命中前缀 | 2.275 s |

256K 窗口、28K 前缀：

| `CACHE_RAM` | 冷 TTFT | 命中 TTFT |
|---:|---:|---:|
| 1024 MiB | 105.852 s | 2.863 s |
| 2048 MiB | 109.609 s | 2.728 s |
| 4096 MiB | 105.723 s | 2.858 s |

生产建议从 1024 MiB 开始。4096 MiB 在长请求下最低内存余量更小。

## 11. 双机部署

### 11.1 推荐：两个独立副本

Flash-Next 单机已能运行，双机默认应做两个完整副本，用 least-connections
或一致性哈希分摊请求。

四个 8K 输入、每个 256 输出的探索性结果：

| 部署 | 总耗时 | 吞吐 |
|---|---:|---:|
| .13 单机串行 | 146.296 s | 6.999 tok/s |
| .14 单机串行 | 138.553 s | 7.391 tok/s |
| 双机 PD 原型 | 106.895 s | 9.579 tok/s |
| 双机独立副本 | 73.286 s | 13.973 tok/s |

双副本比 PD 高约 45.9%，比单机高约 89.1%。这是当前推荐的多请求扩容方式。

### 11.2 PD 原型

PD 使用 `.13` Prefill、`.14` Decode，每台加载完整模型，通过
`/slots/0?action=save/restore` 迁移序列状态。

单请求：

| 输入 | .14 单机 E2E | PD E2E | 变化 |
|---:|---:|---:|---:|
| 2K | 16.047 s | 16.208 s | +1.0% |
| 8K | 34.412 s | 35.875 s | +4.2% |

状态文件：

```text
2K: 137.6 MB，导出/传输/恢复约 0.409 s
8K: 196.3 MB，导出/传输/恢复约 0.490 s
```

PD 不适合单流加速。四请求吞吐有提升，但双副本仍更快。

### 11.3 PD 的正确性风险

正式 PD 测试中：

- 状态保存数/恢复数和文件字节一致；
- D 端恢复后 `prompt_n=1`；
- 回答包含预期事实；
- 但同机重复恢复后输出 token 也不完全一致；
- 未证明逐 token 等价、质量等价或长期稳定。

因此 PD 脚本只能作为实验入口：

```bash
python3 tools/qwen38_pd_benchmark.py --out bench-results/qwen38-pd-NEW-single
python3 tools/qwen38_pd_pipeline.py \
  --out bench-results/qwen38-pd-NEW-pipeline \
  --prompts bench-results/qwen38-pd-NEW-single/prompts-8192.json
python3 tools/summarize_qwen38_pd.py \
  bench-results/qwen38-pd-NEW-single \
  --pipeline bench-results/qwen38-pd-NEW-pipeline
```

## 12. 性能优化顺序

### 12.1 27B

1. Vulkan vs HIP；
2. no-spec vs MTP；
3. MTP `n-max=1/2/3/4`；
4. `p-min=0/0.1/0.2`；
5. F16 vs Q8 KV；
6. context 32K/64K/128K/256K；
7. 长输出 512 token 的稳定性。

### 12.2 Flash-Next

1. 修复 cooperative matrix；
2. 用同一二进制做 coopmat on/off 消融；
3. baseline vs MTP2/3/4；
4. ubatch 512/1024/2048；
5. 8K/16K/64K 输入桶；
6. Q4/Q4 KV baseline；
7. Prefix Cache 1024/2048；
8. 多请求优先双副本，PD 只做研究；
9. 256K 只做容量边界，不作为生产承诺。

不要同时改 `ubatch`、`n-max`、KV 和采样。每次只改一个变量，并保留原始
JSON、server log、token 计数和内存采样。

## 13. 常见故障

| 现象 | 原因 | 处理 |
|---|---|---|
| 27B 输出慢于历史值 | 模型文件或 commit 不同 | 核对 SHA、backend、MTP、KV |
| 27B MTP 不生效 | 用了错误 draft 或后端不支持 | 检查 `--spec-type` 和模型 NextN |
| Flash-Next 加载失败 | 四分片不齐/路径只指向分片 1 的目录错误 | 检查四个分片和 split 元数据 |
| `matrix cores: none` | glslc/libshaderc feature test 失败 | 修 `LD_LIBRARY_PATH`，重建 |
| 8K 输入 Prefill 慢 20%+ | coopmat 未启用 | 检查设备能力和构建 |
| 短请求 MTP 更慢 | draft 开销 | 默认 no-spec |
| 256K MTP 加载失败 | 资源压力 | 关闭 MTP 或降低窗口 |
| 首个长请求 100+ 秒 | 冷 Prefill | 使用 prefix cache 或接受冷启动成本 |
| 重复文档仍很慢 | 请求没开 cache 或前缀变化 | `cache_prompt=true`，检查 cache hit |
| 双机 PD 输出不一致 | 状态迁移正确性未解决 | 不用于生产，优先双副本 |
| 内存低于 2 GiB | 接近 OOM/swap 边界 | 停止本轮服务，降低窗口或换更小量化 |
| 直接暴露端口有风险 | 无认证 | 绑定 loopback 或用反代认证 |

## 14. 生产清单

### 27B

- [ ] 固定 Q4_K_M 文件 SHA 和后端 commit。
- [ ] 确认 MTP 是模型内嵌 NextN。
- [ ] 先测 no-spec，再测 MTP n=2、p-min=0.2。
- [ ] 短上下文 F16 KV，长上下文 Q8 KV。
- [ ] 至少 3 次重复，记录 Decode、TTFT、E2E。
- [ ] Q8 只用于质量对照。

### Flash-Next

- [ ] 四分片完整，draft 单独保存并校验。
- [ ] 确认 cooperative matrix 已启用。
- [ ] 默认 8K/16K、单 slot、no-spec。
- [ ] 用 `start_qwen38_decode.py` 的资源和进程保护。
- [ ] 记录最低 MemAvailable、SwapFree、pswpin/pswpout。
- [ ] 长输出场景再验证 MTP3。
- [ ] 256K 只做容量测试，不承诺生产速度。
- [ ] 多请求优先双副本，PD 仅实验。

## 15. 证据索引

```text
<LLAMA_CPP>/qwen3.8-27b-performance-data-20260908.md
<LLAMA_CPP>/qwen3.8-27b-best-performance-20260908.md
<PROJECT_ROOT>/Qwen3.8-Flash-Next-优化结果-20260907.md
<PROJECT_ROOT>/Qwen3.8-Flash-Next-Decode优化-20260908.md
<PROJECT_ROOT>/Qwen3.8-Flash-Next-Vulkan-MTP优化复测-20260908.md
<PROJECT_ROOT>/Qwen3.8-Flash-Next-双机PD测试-20260908.md
<PROJECT_ROOT>/Qwen3.8-Flash-Next-MTP性能数据汇总-20260907.md
<LOCAL_ROOT>/Desktop/llm-deployment-engineering/cases/llama-cpp-flash-attention/CASE.md
<LOCAL_ROOT>/Desktop/llm-deployment-engineering/cases/llama-cpp-flash-attention/CASE_TECHNICAL.md
```
