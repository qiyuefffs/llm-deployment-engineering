---
id: T42
title: "DeepSeek V4 Flash 部署与推理性能优化"
type: tutorial
volume: book
layer: 4
platform: "general"
device: "general"
status: historical
source_ids: []
updated: 2026-10-19
summary: "DeepSeek V4 Flash 在本工作区有两条完全不同的路径："
---

# DeepSeek V4 Flash 部署与推理性能优化

[项目索引](README.md) · [通用性能优化测试方法论](../edge-llm-performance-methodology.md)

> 验证基线：AMD Ryzen AI MAX+ 395 / Radeon 8060S / `gfx1151` / 128 GB UMA /
> ROCm 7.2.4。  
> 事实截止：2026-09-08 的本地实测记录；文档整理日期：2026-10-19。  
> 本文只描述可复核的部署路线。文中的“约 23 tok/s”是特定模型、特定
> profile、短输入 128-token 输出下的实测 Decode，不是所有请求的承诺值。

## 1. 先选对模型和运行路径

DeepSeek V4 Flash 在本工作区有两条完全不同的路径：

| 路径 | 权重/运行方式 | 适用硬件 | 本工作区结论 |
|---|---|---|---|
| Lucebox ROCmFPX | 约 96 GiB GGUF + ROCmFP2/ROCmFPX kernel | Ryzen AI MAX+ 395 `gfx1151` | 首选，单机 quality 约 23 tok/s |
| vLLM W4A16 | compressed-tensors W4A16 safetensors | 按量化 kernel、版本与设备组合验收 | 本篇侧重 Lucebox；395 的另一次 TP1/TP2 实测见 vLLM 项目章 |

需要特别区分：

- 官方基础模型是 `deepseek-ai/DeepSeek-V4-Flash`。
- 本工作区使用的 180B W4A16 是 REAP K160 剪枝再量化的实验衍生模型，
  不是官方原权重。
- 本工作区在 395 上验证的 GGUF 是 Lucebox 转换的 ROCmFP2/ROCmFPX 制品，
  也不是官方发布的原生 ROCmFP2 文件。
- 不要把约 100 GiB 的 Lucebox GGUF 与 97 GB 的 vLLM W4A16 safetensors
  混用，也不要把两者的 token/s 直接比较。

补充回链：[vLLM ROCm 文本专项](06-vllm-rocm.md)与 [E29](../../evidence/records/E29.md)
保留了 gfx1151 上 W4A16 TP1/TP2 的本地报告。这不改变本篇 Lucebox profile
的测试条件；不能将本篇的路线选择解释成“W4A16 在 395 上从未运行成功”。

## 2. 固定资产

### 2.1 推荐运行资产

```text
镜像 tag:
lucebox-dsv4-rocmfpx:<PINNED_TAG>

稳定别名:
lucebox-dsv4-rocmfpx:<PINNED_TAG>

发布 manifest digest:
<IMAGE_DIGEST>

Lucebox 源码:
c3b71e4b2ed2d08db96d55e7985f20035aa08d6f
```

主模型：

```text
DeepSeek-V4-Flash-ROCMFP2-STRIX.gguf
bytes: 102320631200
sha256: <MODEL_SHA256>
```

可选 DSpark drafter，仅 `speed`/`speed-exact` 需要：

```text
DeepSeek-V4-Flash-DSpark-draft-Q4RMFP4-denseF16.gguf
bytes: 11304737056
sha256: <MODEL_SHA256>
```

### 2.2 原始项目地址

```text
https://huggingface.co/deepseek-ai/DeepSeek-V4-Flash
https://github.com/Luce-Org/lucebox
https://huggingface.co/Lucebox/DeepSeek-V4-Flash-ROCMFPX
https://huggingface.co/Lucebox/DeepSeek-V4-Flash-DSpark-Drafter-GGUF
```

## 3. 硬件与宿主机前置条件

### 3.1 已验证平台

```text
CPU/APU: AMD Ryzen AI MAX+ 395
GPU: AMD Radeon 8060S
GPU arch: gfx1151
内存: 128 GB 统一内存，系统可用约 123 GiB
ROCm 用户态: 7.2.4
Docker: linux/amd64
```

稳定 `quality` 模式加载约 97 GB 主模型后，容器/UMA 占用接近 97-101 GiB。
建议只运行这一套大模型，不要再同时启动 ComfyUI、大语言模型或大型数据库。

### 3.2 磁盘

```text
主模型:      约 102.32 GB
DSpark:      约 11.30 GB
镜像展开后:  约 40 GB
临时和日志:  至少 20 GB
建议空闲:    190 GB 以上
```

检查：

```bash
df -h /home
docker system df
```

### 3.3 ROCm 设备节点

```bash
ls -l /dev/kfd
find /dev/dri -maxdepth 1 -name 'card*' -ls
find /dev/dri -maxdepth 1 -name 'renderD*' -ls
rocminfo | grep -m 5 -E 'Name:|gfx1151'
rocm-smi --showproductname
```

至少要有 `/dev/kfd` 和一个 `/dev/dri/card*`。不要设置
`HSA_OVERRIDE_GFX_VERSION` 伪装架构，驱动应原生识别 `gfx1151`。

### 3.4 GTT/TTM

395 的“显存”不是独立 HBM 显存。大模型主要通过 GTT 使用系统内存。
验证机使用过约 120 GB GTT：

```bash
cat /sys/module/ttm/parameters/pages_limit
cat /sys/module/ttm/parameters/page_pool_size
cat /sys/module/amdgpu/parameters/gttsize
free -h
rocm-smi --showmeminfo vram
rocm-smi --showmeminfo gtt
```

验证环境记录：

```text
ttm.pages_limit=30720000
ttm.page_pool_size=30720000
amdgpu.gttsize=120000
```

这些值不是可以无条件复制的通用配置。修改内核模块参数可能影响启动和系统
稳定性，必须在维护窗口内按目标机器的内核、initramfs、BIOS 和驱动定义操作。
本文不自动修改 GRUB、BIOS、initramfs 或 amdgpu 参数。

### 3.5 功耗和后台负载

```bash
powerprofilesctl get
powerprofilesctl set performance
rocm-smi --showperflevel
rocm-smi --showuse
```

实测 GPU `high` 比 `auto` 慢约 6.8%，所以不要盲目追求最高功耗档。先保持
`auto` 或机器验证过的 performance profile，再做 A/B。关闭不必要的桌面、
浏览器 GPU 加速、其他模型进程和大型编译任务。

## 4. 获取项目、镜像和权重

### 4.1 获取项目

如果使用本工作区：

```bash
cd <PROJECT_ROOT>
git status --short
```

如果从零复现，克隆 Lucebox 并固定 commit：

```bash
git clone https://github.com/Luce-Org/lucebox.git
cd lucebox
git checkout c3b71e4b2ed2d08db96d55e7985f20035aa08d6f
```

### 4.2 拉取已验证镜像

```bash
docker pull lucebox-dsv4-rocmfpx:<PINNED_TAG>
docker image inspect \
  lucebox-dsv4-rocmfpx:<PINNED_TAG> \
  --format '{{.Id}} {{json .Config.Labels}}'
```

应核对标签中的 Lucebox revision、ROCm 用户态和 `gfx1151` 信息。不要只凭
`latest` 或名字拉取未固定版本。

### 4.3 下载并校验权重

工作区脚本：

```bash
cd <PROJECT_ROOT>
MODEL_ROOT=<MODEL_ROOT>/Lucebox \
HF_ENDPOINT=https://hf-mirror.com \
./scripts/download_lucebox_dsv4.sh
```

如果已经有文件，只校验：

```bash
VERIFY_ONLY=1 \
MODEL_ROOT=<MODEL_ROOT>/Lucebox \
./scripts/download_lucebox_dsv4.sh
```

手工校验：

```bash
TARGET=<MODEL_ROOT>/Lucebox/DeepSeek-V4-Flash-ROCMFPX/DeepSeek-V4-Flash-ROCMFP2-STRIX.gguf
printf '%s  %s\n' \
  <MODEL_SHA256> \
  "$TARGET" | sha256sum -c -

DRAFT=<MODEL_ROOT>/Lucebox/DeepSeek-V4-Flash-DSpark-Drafter-GGUF/DeepSeek-V4-Flash-DSpark-draft-Q4RMFP4-denseF16.gguf
printf '%s  %s\n' \
  <MODEL_SHA256> \
  "$DRAFT" | sha256sum -c -
```

大文件哈希计算需要时间，终端暂时无输出不代表卡死。

### 4.4 可选：本地重建镜像

只有需要修改 kernel、排查构建问题或重新封装时才本地构建：

```bash
cd <PROJECT_ROOT>
SOURCE_DIR=<PROJECT_ROOT>/vendor/lucebox \
EXPECTED_COMMIT=c3b71e4b2ed2d08db96d55e7985f20035aa08d6f \
ROCM_VERSION=7.2.4 \
HIP_ARCH=gfx1151 \
./scripts/build_lucebox_dsv4.sh
```

脚本会检查：

```text
上游 commit
vendored llama.cpp/ggml
宿主机 ROCm 7.2.4
基础镜像 digest
ROCmFP2/3/4 MMQ 数值测试
Flash-Prefill kernel 数值测试
```

关键 CMake 项：

```text
DFLASH27B_GPU_BACKEND=hip
DFLASH27B_HIP_ARCHITECTURES=gfx1151
DFLASH27B_HIP_SM80_EQUIV=ON
DFLASH27B_FA_ALL_QUANTS=OFF
DFLASH27B_ENABLE_BSA=OFF
CMAKE_DISABLE_FIND_PACKAGE_CURL=TRUE
```

`DFLASH27B_HIP_SM80_EQUIV=ON` 启用 gfx1151 的 rocWMMA Phase-2 Prefill。
数值测试通过不代表 OpenAI API 端到端吞吐已经达标，必须继续做真实生成。

## 5. 启动稳定 quality 服务

### 5.1 一条命令启动

```bash
cd <PROJECT_ROOT>
MODEL_ROOT=<MODEL_ROOT>/Lucebox \
./scripts/start_lucebox_dsv4.sh quality
```

脚本执行以下关键动作：

- 检查 `/dev/kfd` 和 `/dev/dri/card*`；
- 取得宿主机设备节点 GID；
- 检查旧容器和端口；
- 设置 performance profile 或报告失败；
- 只读挂载模型目录；
- 等待 `/health`；
- 自动发送一次 128-token 真实 warm-up；
- 打印 `/v1/models`。

### 5.2 等价的 docker run

```bash
MODEL_ROOT=<MODEL_ROOT>/Lucebox
IMAGE=lucebox-dsv4-rocmfpx:<PINNED_TAG>
VIDEO_NODE=$(find /dev/dri -maxdepth 1 -name 'card*' -print -quit)
VIDEO_GID=$(stat -c '%g' "$VIDEO_NODE")
RENDER_GID=$(stat -c '%g' /dev/kfd)

docker run -d --name rocm395-lucebox-dsv4 \
  --network host \
  --device /dev/kfd --device /dev/dri \
  --group-add "$VIDEO_GID" --group-add "$RENDER_GID" \
  --ipc host --shm-size 16g \
  --ulimit memlock=-1:-1 \
  --security-opt seccomp=unconfined \
  --restart unless-stopped \
  --health-cmd "curl --noproxy '*' --fail --silent --max-time 3 http://127.0.0.1:8000/health >/dev/null || exit 1" \
  --health-interval 30s --health-timeout 5s \
  --health-start-period 180s --health-retries 3 \
  -e PROFILE=quality \
  -e PORT=8000 \
  -e MAX_CTX=8192 \
  -e MODEL_NAME=deepseek-v4-flash-rocmfp2-strix \
  -e NO_PROXY=localhost,127.0.0.1 \
  -e no_proxy=localhost,127.0.0.1 \
  -v "$MODEL_ROOT:/models:ro" \
  "$IMAGE"
```

### 5.3 等待就绪

```bash
for i in $(seq 1 120); do
  if curl --noproxy '*' -fsS http://127.0.0.1:8000/health; then
    break
  fi
  docker logs --tail 5 rocm395-lucebox-dsv4
  sleep 10
done
docker inspect rocm395-lucebox-dsv4 \
  --format 'restart={{.RestartCount}} health={{.State.Health.Status}}'
```

首次加载通常约 1-2 分钟。`/health` 返回 `ok` 只表示 API 就绪，不代表
GPU kernel 已经热。必须做真实生成 warm-up。

### 5.4 启动参数的含义

容器入口实际执行：

```text
PROFILE=quality
  -> prefill=exact
  -> expert_top_k=0（模型默认 top-6）
  -> DSpark off
  -> fused decode on
  -> chunk=512
  -> prefix-cache-slots=0
  -> prefill-cache-slots=0
```

`quality` 是稳定默认。不要把当前 `quality` 与 `speed` 的参数写成等价。

## 6. API 验收

### 6.1 健康与模型列表

```bash
curl --noproxy '*' -fsS http://127.0.0.1:8000/health
curl --noproxy '*' -fsS http://127.0.0.1:8000/v1/models | jq
```

### 6.2 中文请求

```bash
curl --noproxy '*' -fsS \
  http://127.0.0.1:8000/v1/chat/completions \
  -H 'Content-Type: application/json' \
  -d '{
    "model": "deepseek-v4-flash-rocmfp2-strix",
    "messages": [
      {"role":"user","content":"请用中文简洁解释 Prefill 和 Decode 的区别。"}
    ],
    "temperature": 0,
    "max_tokens": 128,
    "stream": false,
    "thinking": {"type":"disabled"}
  }' | jq
```

重点读取：

```text
.usage.timings.prefill_ms
.usage.timings.decode_ms
.usage.timings.decode_tokens_per_sec
.usage.accept_rate
```

### 6.3 四项部署正确性检查

每次更换镜像、驱动或 profile 后至少执行：

1. 中文回答包含正常中文，不是空串、乱码或重复退化；
2. 生成一个可执行的 Python Fibonacci 函数；
3. 严格 JSON 请求必须解析为 `{"status":"ok","value":42}`；
4. 两轮对话能记住数字 `731`。

工作区验收：

```bash
cd <PROJECT_ROOT>
./scripts/test_lucebox_curl.sh
```

这四项只用于部署 smoke，不代替业务质量集、困惑度或长期稳定性测试。

## 7. 性能基线与优化

### 7.1 实测基线

测试口径：41 个输入 token、128 个输出 token、temperature=0、
thinking disabled、预热一次后连续 5 次。

| Profile | Decode 均值 | Prefill 均值 | TTFT 均值 | 正确性 | 状态 |
|---|---:|---:|---:|---:|---|
| quality: exact/top-6/无 DSpark | 23.08 tok/s | 22.89 tok/s | 1.924 s | 4/4 | 稳定默认 |
| speed: adaptive/top-4/sparse | 24.18 tok/s | 45.45 tok/s | 1.061 s | 4/4 | 实验配置 |
| speed: fixed q4/top-4/sparse | 23.68 tok/s | 46.11 tok/s | 1.061 s | 4/4 | 实验配置 |
| speed: adaptive/top-4/sparse/high | 22.54 tok/s | 45.17 tok/s | 1.074 s | 4/4 | 不推荐 high |

解释：

- 从 quality 切到 speed，Decode 只提升约 4.77%，Prefill 提升约 98.6%，
  TTFT 降低约 44.9%。
- 收益最大的是 Prefill/TTFT，不是 Decode。
- `high` 比 `auto` 慢，说明功耗档位不能替代算法和内存路径优化。
- 首次完全冷请求可能只有约 12.8 tok/s，预热后会稳定到 20+ tok/s。
- 短 prompt Prefill 不能外推到 2K/8K 长上下文。

### 7.2 优化顺序

按下面顺序做，不要同时改多个变量：

1. 固定镜像 digest、模型 SHA、ROCm 版本、power profile 和上下文；
2. 先跑 `quality`，确认 4/4 正确性和 warm Decode；
3. 单独测量 `speed-exact`，隔离 sparse prefill 的影响；
4. 再测 `speed`，确认 adaptive DSpark 的 Decode 收益；
5. 比较 `DSPARK_ADAPTIVE=0` 与默认 adaptive；
6. 比较 GPU `auto` 与 `high`，大多数情况下保留 `auto`；
7. 最后才考虑 `chunk`、上下文和缓存 slot 实验。

### 7.3 speed-exact 和 speed

```bash
# 隔离 sparse prefill：top-4 + exact prefill + DSpark
./scripts/start_lucebox_dsv4.sh speed-exact

# 完整实验配置：top-4 + sparse prefill + DSpark
./scripts/start_lucebox_dsv4.sh speed

# 固定 q=4，关闭 adaptive width
DSPARK_ADAPTIVE=0 ./scripts/start_lucebox_dsv4.sh speed
```

`speed` 曾在空闲约 2 小时后第一条请求触发 `dflash_server` 段错误。Docker
`unless-stopped` 自动重启了容器，但重新加载约 100 GB 模型会产生短暂连接
拒绝。因此不要把 `speed` 当作默认生产 profile。

### 7.4 参数优先级

| 参数 | 建议 | 说明 |
|---|---|---|
| `PROFILE` | production 用 `quality` | 稳定优先 |
| `MAX_CTX` | 从 8192 开始 | 长上下文需单独测内存和 TTFT |
| `CHUNK_SIZE` | 512 | 已验证；单双机 A/B 没有显示 256 更好 |
| `PREFIX_CACHE_SLOTS` | 默认 0 | 未验证前不要把它当生产优化 |
| `PREFILL_CACHE_SLOTS` | 默认 0 | 同上 |
| `DSPARK_ADAPTIVE` | 保持 1 | 固定 q4 比 adaptive 慢约 2% |
| GPU perf level | `auto` | `high` 实测更慢 |
| 并发 | 先 1，再看 UMA 余量 | 约 100 GB 权重后余量很窄 |

## 8. 可复现 benchmark

```bash
cd <PROJECT_ROOT>
python3 scripts/benchmark_lucebox_dsv4.py \
  --profile quality \
  --repetitions 5 \
  --max-tokens 128 \
  --report-dir reports/lucebox-dsv4-quality-recheck
```

脚本使用 OpenAI-compatible streaming API，保存每次请求的：

```text
TTFT、端到端时间、prompt/completion tokens
服务端 Prefill/Decode 时间和 tok/s
DSpark accept rate、finish reason、生成文本
```

压测原则：

- 先预热 1 次，不把冷加载和前几个 JIT shape 混入正式均值；
- 至少 3 次，建议 5 次；
- 记录 `MemAvailable`、`SwapFree`、`vmstat` 和容器 restart/OOM；
- 失败请求单独保存，不按 0 tok/s 混入均值；
- 报告 Decode、Prefill、TTFT、E2E 四个指标，不能只报一个 tok/s。

## 9. 稳定性检查

```bash
docker inspect rocm395-lucebox-dsv4 \
  --format 'restart={{.RestartCount}} oom={{.State.OOMKilled}} health={{.State.Health.Status}}'

journalctl -k --since today | rg -i \
  'dflash_server|segfault|amdgpu|gpu reset|timeout|oom'
```

建议观察：

```bash
while sleep 10; do
  date '+%F %T'
  awk '/MemAvailable|SwapFree/ {print $1,$2,$3}' /proc/meminfo
  grep -E 'pswpin|pswpout|pgmajfault' /proc/vmstat
done
```

quality 已通过短时连续请求和 45 秒空闲恢复，但尚未完成 24 小时 soak。
生产上线前至少做：

- 30 分钟持续请求；
- 30 分钟空闲后的第一条请求；
- 容器健康检查连续 3 次失败后的恢复；
- 主机内存压力下的拒绝策略；
- API 进程崩溃后的自动重启和客户端重试。

## 10. 双机与替代后端

### 10.1 双机 Lucebox layer split

本工作区有实验性的 22+21 层 TCP target-shard bridge：

```bash
MAX_CTX=4096 CHUNK_SIZE=512 ./scripts/start_lucebox_dsv4_dual_node.sh
./scripts/stop_lucebox_dsv4_dual_node.sh
```

实测严格同输入：

| 拓扑 | Decode | Prefill |
|---|---:|---:|
| 单机 quality | 23.00 tok/s | 23.06 tok/s |
| 双机 22+21 层 | 18.10 tok/s | 20.69 tok/s |

双机 Decode 低约 21.3%，Prefill 低约 10.3%。原因是 layer split 强制关闭
fused decode、expert top-k 和 sparse prefill，并且每 token 都要跨机同步
F32 HC state。它适合验证容量扩展，不适合普通对话提速。

### 10.2 vLLM W4A16 在 gfx1151

本工作区曾用 vLLM 0.23.1rc1 单机 TP1 和双机 TP2 跑通 180B W4A16，
但单机真实 Decode 约 4.7 tok/s，远低于 Lucebox 的 23 tok/s。原因是
gfx1151 上 MLA Prefill 使用 Torch SDPA 回退，且没有 Lucebox 的 fused
decode 和 ROCmFPX kernel。除非你明确需要 vLLM 的调度或吞吐特性，否则
395 上优先 Lucebox。

### 10.3 NVIDIA 4×V100 32GB 路线

这条路线对应 `Israeli-AI/DeepSeek-v4-flash-180b-W4A16-VOLTA-Ampere`，
不是 395 GGUF。需要 1Cat-vLLM 和 `sm70-port/apply-port.sh`：

```bash
export CUDA_DEVICE_ORDER=PCI_BUS_ID
export CUDA_VISIBLE_DEVICES=0,1,2,3
export NCCL_P2P_DISABLE=1
export VLLM_WORKER_MULTIPROC_METHOD=spawn
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
export VLLM_SM70_QUANT_BACKEND=turbomind
export VLLM_SM70_COMPRESSED_TENSORS_TURBOMIND=1

vllm serve /data/dsv4-180b-w4a16 \
  --host 0.0.0.0 --port 8090 \
  --served-model-name dsv4-180b \
  --tensor-parallel-size 4 \
  --disable-custom-all-reduce \
  --gpu-memory-utilization 0.93 \
  --kv-cache-memory-bytes 1395864371 \
  --max-model-len 4096 \
  --max-num-seqs 2 \
  --max-num-batched-tokens 2048 \
  --kv-cache-dtype fp8_e4m3 \
  --reasoning-parser deepseek_v4 \
  --enable-auto-tool-choice \
  --tool-call-parser deepseek_v4 \
  --compilation-config '{"cudagraph_mode":"full_and_piecewise","cudagraph_capture_sizes":[1,2]}'
```

关键点：

- 每卡约 26.5 GiB 权重，必须 pin `--kv-cache-memory-bytes`；
- 需要 proprietary NVIDIA driver，V100 不能使用 open module；
- 不要关闭 CUDA graph，`--enforce-eager` 约慢 2.5 倍；
- 参考性能约 16 tok/s 单流、21 tok/s 4 并发，不是 395 的 23 tok/s；
- Hopper/Blackwell 可直接用支持 `deepseek_v4` 的上游 vLLM，不需要 SM70 port。

## 11. 常见故障

| 现象 | 优先检查 | 处理 |
|---|---|---|
| `/health` 长时间不 ok | `docker logs`、`MemAvailable`、`SwapFree` | 等待加载；确认 GTT 和模型 SHA |
| `container exited during model load` | 日志尾部 200 行 | 检查模型路径、大小、权限、设备节点 |
| `permission denied /dev/kfd` | 设备 GID | 用节点实际 GID 加入容器 |
| 启动后立刻 OOM 或 kernel OOM | UMA 余量、其他模型进程 | 停止其他大内存任务，降低上下文 |
| API 返回空内容 | warm-up、模型输出格式 | 先跑固定 smoke，检查 finish reason |
| 正常请求很慢 | 冷启动、JIT、power profile | 做 128-token warm-up；保持 GPU auto |
| 长空闲后第一条请求失败 | Docker restart count | 回退 quality；检查 DSpark 段错误 |
| 输出 CJK 乱码/重复 | 并发 shape、profile | 降低并发，回退 quality，保留失败请求 |
| 客户端 connection refused | 容器重启窗口 | 等健康检查恢复，客户端做有限重试 |
| 镜像拉取超时 | Docker daemon 代理 | 配置 daemon 代理或镜像源，不要只设置 shell 变量 |

## 12. 生产上线清单

- [ ] 固定镜像 digest、模型 SHA、Lucebox commit 和 ROCm 版本。
- [ ] 记录 `/dev/kfd`、`/dev/dri`、GTT/TTM 和主机内存。
- [ ] 使用 `quality` 作为默认 profile。
- [ ] 完成 `/health`、`/v1/models`、OpenAI Chat 和四项 smoke。
- [ ] 完成 5 次固定 prompt 的 Decode/Prefill/TTFT 基线。
- [ ] 预热一次再计入正式数据。
- [ ] 开启容器 healthcheck 和 restart policy。
- [ ] 记录 restart count、OOM、kernel amdgpu 错误。
- [ ] 只监听内网或通过有认证的反向代理暴露。
- [ ] 保留质量集、长上下文和空闲恢复测试结果。
- [ ] 把 `speed` 标记为实验，不在没有业务质量评估时上线。

## 13. 证据索引

本地关键文件：

```text
docs/lucebox_dsv4_rocmfpx.md
docs/dockerhub_lucebox_dsv4_rocmfpx.md
docs/lucebox_dsv4_dual_node.md
scripts/download_lucebox_dsv4.sh
scripts/build_lucebox_dsv4.sh
scripts/start_lucebox_dsv4.sh
scripts/start_lucebox_dsv4_dual_node.sh
scripts/benchmark_lucebox_dsv4.py
reports/lucebox-dsv4-rocmfpx-20260728/README.md
models/Israeli-AI/DeepSeek-v4-flash-180b-W4A16-VOLTA-Ampere/README.md
```
