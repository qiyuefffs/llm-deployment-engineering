# 05 llama.cpp：从固定版本到可测量服务

[返回总目录](README.md) · [上一章](04-memory-and-kv-cache.md) · [下一章](06-edge-platforms.md)

## 1. 三个程序分别做什么

`llama-cli` 用于本地文本生成与最小功能检查；`llama-server` 提供 HTTP 服务、槽位与批处理；`llama-bench` 测引擎层的 Prefill/Decode 计算性能。三者可共享核心推理能力，但输入路径、服务调度和计时口径不同。bench 的 tokens/s 不能直接当作 HTTP 服务吞吐。

本章给出 **Linux Bash、受支持文本 GGUF、本地回环服务** 的模板。需要事先有目标设备驱动；CUDA 路线还需匹配 Toolkit、C++ 编译器。命令不构成新增的已实测 Case。模型、commit、包版本与容量参数应由项目记录固定，先读该 commit 的 `--help`。

## 2. 建立独立目录并记录环境

```bash
mkdir -p /mnt/workspace/edge-llm-lab/{models,logs,results,inputs}
cd /mnt/workspace/edge-llm-lab
uname -a > logs/os.txt
cat /etc/os-release >> logs/os.txt
lscpu > logs/cpu.txt
free -h > logs/memory.txt
```

这里使用 `/mnt/workspace` 便于 Notebook；本地设备可换到自己有写权限的目录。不要把实验文件散放在系统路径。Ubuntu/Debian 环境可通过系统包管理器准备 `git`、`cmake`、`ninja-build`、C/C++ 构建工具、`pkg-config`、开发依赖和 `aria2`。先核对系统与现有工具，不在所有设备上盲目执行同一条 apt 命令。安装后记录实际版本。

```bash
git --version
cmake --version
ninja --version
c++ --version
aria2c --version
```

## 3. 固定源码，而不是只写“最新版”

以下要求调用前已设置 `LLAMA_REF` 为经核对的 release tag 或完整 commit。它是待填写的项目配置，不提供一个未经本章运行验证的固定值。

```bash
: "${LLAMA_REF:?请先设置 LLAMA_REF 为目标 tag 或完整 commit}"
cd /mnt/workspace/edge-llm-lab
git clone https://github.com/ggml-org/llama.cpp.git
cd llama.cpp
git checkout --detach "$LLAMA_REF"
git rev-parse HEAD > ../logs/llama-commit.txt
```

已有源码目录时检查来源与工作区，不重复克隆覆盖。网络下载耗时不计入模型推理性能。更新 commit 后使用新的构建目录，并重新验证模型、参数与质量；默认值变化会让“相同命令”产生不同配置。

## 4. CPU 与 CUDA 分开构建

在源码根目录，CPU 起点如下。`-j 4` 是保守示例，应按 RAM 和核心数调整；并行编译过高可能使主机内存耗尽。

```bash
set -o pipefail
cmake -S . -B build-cpu -G Ninja \
  -DCMAKE_BUILD_TYPE=Release -DGGML_CUDA=OFF -DGGML_METAL=OFF \
  2>&1 | tee ../logs/configure-cpu.log
cmake --build build-cpu --config Release -j 4 \
  2>&1 | tee ../logs/build-cpu.log
```

跨设备分发 CPU 二进制时，核对 `GGML_NATIVE` 与目标 ISA，不能默认构建机支持的指令在另一台机器上也存在。CPU-only 运行可显式选择 `--device none`；仅 `-ngl 0` 在某些后端仍可能允许其他 GPU 算子卸载，需查该版本文档。

CUDA 路线先保存 `nvidia-smi`、`nvcc --version`。下例要求 `CUDA_ARCH` 是经厂商表确认的架构值；例如 A10 的 Compute Capability 为 8.6，对应 CMake 常写 `86`，不能将它照搬到所有 GPU。

```bash
: "${CUDA_ARCH:?请先设置目标 GPU 的 CMake CUDA 架构值}"
cmake -S . -B build-cuda -G Ninja \
  -DCMAKE_BUILD_TYPE=Release -DGGML_CUDA=ON \
  -DCMAKE_CUDA_ARCHITECTURES="$CUDA_ARCH" \
  2>&1 | tee ../logs/configure-cuda.log
cmake --build build-cuda --config Release -j 4 \
  2>&1 | tee ../logs/build-cuda.log

./build-cuda/bin/llama-server --version > ../logs/server-version.txt
./build-cuda/bin/llama-server --help > ../logs/server-help.txt 2>&1
./build-cuda/bin/llama-server --list-devices \
  > ../logs/devices.txt 2>&1
```

有多个 Toolkit 时，可显式指定 `CMAKE_CUDA_COMPILER` 为目标 `nvcc` 的绝对路径。更换后端、编译器或架构后使用新目录，避免旧 CMakeCache 混入。`tee` 保存日志时配合 `pipefail`，否则可能把日志管道成功误当成编译成功。检查构建退出码、可执行文件与实际设备识别三项。

## 5. 用 aria2 下载，并保留模型身份

先选择公开可获取、来源与许可证明确、和本 commit 架构兼容的 GGUF 文件。下面只在已填写 `MODEL_URL` 后执行；URL 必须指向目标文件，不是仓库网页。签名链接、凭证和私有镜像地址不要写入公开命令或日志。

```bash
: "${MODEL_URL:?请先设置公开模型文件直链}"
cd /mnt/workspace/edge-llm-lab
aria2c --continue=true --max-connection-per-server=8 --split=8 \
  --min-split-size=16M --max-concurrent-downloads=2 \
  --max-tries=5 --retry-wait=5 \
  --auto-file-renaming=false --allow-overwrite=false \
  --dir=models --out=model.Q4_K_M.gguf "$MODEL_URL"

stat -c '%n %s bytes' models/model.Q4_K_M.gguf
sha256sum models/model.Q4_K_M.gguf > logs/model-local.sha256
```

`-x/--max-connection-per-server` 限制单服务器连接，`-s/--split` 控制分段，`-j` 控制多个文件的并发；只有一个文件时，增加 `-j` 不会变成多个文件并发。是否提速取决于 Range 支持、服务器限制、网络与磁盘。不要持续增大连接数，应比较完整文件耗时并遵守服务端限制。

保存本地哈希后，如发布方提供可信 SHA256，另行逐项比对。分片 GGUF 必须下载齐全，并按该引擎支持方式加载；不能把分片随意拼成一个文件。已有模型可直接使用并记录路径与哈希，无需重复下载。

## 6. 先验证一条短请求

返回源码目录。以下 4096 上下文、512 logical batch、128 microbatch 是**初始示例**，不是最优参数。`-ngl 99` 是请求尽可能多卸载层的常见写法，实际卸载数量必须从日志核对，容量不够时降低。

```bash
cd /mnt/workspace/edge-llm-lab/llama.cpp
./build-cuda/bin/llama-cli \
  -m ../models/model.Q4_K_M.gguf \
  -ngl 99 -c 4096 -b 512 -ub 128 \
  -p '用一句话解释什么是 KV Cache。' -n 64 \
  2>&1 | tee ../logs/smoke-cli.log
```

某些模型/版本会默认进入对话模式，按该 commit 帮助选择单轮或 completion 模式。检查模型架构、量化类型、模板、GPU buffer、KV 大小与输出停止状态。不要只看“有中文输出”。CPU 对照用 CPU 构建及 `--device none -ngl 0`；其他采样参数和输入也要记录。

## 7. 启动本地服务并验证 API

在一个终端前台启动，便于看清错误；另开终端发请求。

```bash
./build-cuda/bin/llama-server \
  -m ../models/model.Q4_K_M.gguf \
  --alias edge-model \
  --host 127.0.0.1 --port 8080 \
  -ngl 99 -c 4096 -np 1 -b 512 -ub 128 \
  --flash-attn auto --metrics \
  2>&1 | tee ../logs/server-baseline.log
```

```bash
curl --fail-with-body http://127.0.0.1:8080/health
curl --fail-with-body http://127.0.0.1:8080/v1/models

curl --fail-with-body http://127.0.0.1:8080/v1/chat/completions \
  -H 'Content-Type: application/json' \
  -d '{"model":"edge-model","messages":[{"role":"user","content":"用一句话解释 KV Cache。"}],"temperature":0,"max_tokens":128,"stream":false}'
```

检查健康状态、模型别名、响应字段、usage（若实现提供）和 finish reason。改用 `stream:true` 配合 `curl -N` 可观察 SSE，但不能只用终端目测计算精确 TTFT。推理内容可能占用生成预算；不同模型的“关闭思考”方式需按模板和官方配置单独核对。

Notebook 文件面板与服务端口是不同能力。`/mnt/workspace` 文件不会自动变成公开下载链接，本地回环服务也不会自动供外网访问。远程查看应使用平台允许的代理/端口转发；没有 SSH 服务端、可达地址和平台支持时，仅输入 `ssh` 或安装客户端并不能建立入站访问。

## 8. 参数影响速查

| 参数 | 控制什么 | 主要代价与检查点 |
| --- | --- | --- |
| `-c` | 上下文/KV 容量相关配置 | 和槽位/统一池的语义随版本核对 |
| `-np` | 服务槽位数量 | 更多槽位需要状态容量，也可能拉长单请求延迟 |
| `-b` | logical token batch 上限 | 不是 HTTP 并发数，影响执行分批 |
| `-ub` | physical microbatch | 较大可能改善 Prefill，也增加临时空间 |
| `-t` / `-tb` | 生成/批处理相关 CPU 线程 | 核心、带宽、竞争与版本行为 |
| `-ngl` | 请求卸载到设备的模型层 | 记录实际 offload 和每设备内存 |
| `--flash-attn` | Attention 实现选择 | 支持与效果依架构、精度和后端 |
| `-ctk` / `-ctv` | K/V 缓存表示 | 兼容性、长上下文质量与 kernel |

`auto` 适合可用性起点，严格对照时应固定选项并从日志确认真实路径。新增并发前，先保存一条正确响应、空载和请求峰值内存、启动命令与最终有效配置。

**本章产物：**环境信息、commit、构建与启动日志、模型哈希、正常 API 响应、参数清单。接下来才进行多并发和优化实验。
