# Apple M3 Ultra：Metal工具链、GGUF适配与模型加载排错

[工程实例索引](README.md) · [知识体系总目录](../SUMMARY.md)

技术标签：`macOS / Xcode / Metal / llama.cpp / GGUF`

## 环境与目标

M3 Ultra/512GB、macOS26.3；路线为Xcode/clang/CMake/Ninja → llama.cpp Metal → GGUF。原分支commit9d36408的特殊GGUF出现`hc_head_base`与type42问题，构建通过但模型加载未通过，不能改写为成功成绩。

## 完整部署与适配过程

1. 核对`xcode-select -p`、`xcrun --find metal`、`clang --version`、`cmake --version`与ARM64架构。
2. 同一源码树单独配置Metal构建目录，保留CMake检测、shader编译和动态库路径。
3. 先用已支持的小GGUF验证Metal执行，再加载目标模型；区分缺tensor、未知GGML类型、kernel编译与内存分配。
4. 模型层数、KV和临时buffer均核对实际Metal日志；统一内存还需留给OS，不能等额全部分给权重。
5. 运行CLI完整输出，再转llama-server与同口径llama-bench；原失败目标需先解决转换器/分支配套。

## 加速优化与验收

优化顺序：确认实际卸载→量化候选→ctx/batch/ubatch→FA支持→服务槽位。每次保留pp/tg、首次加载、热推理、系统memory pressure与质量。当前源材料对该特殊制品未完成加载验收，因此下方完整保存失败原因与排错；可用MLX服务与并发记录见[Apple MLX实例](apple-mlx.md)。

## 完整技术记录的使用约定

以下直接保留相关FlowUs文章的技术正文、命令、表格、日志、失败和后续实验，不以摘要替代原过程。私人路径、节点、认证与附件地址脱敏；`<NODE_IP>`等占位符需要按当前环境填写。原建议或预测仍是建议或预测。上方执行顺序与技术修订用于解释历史记录中的冲突，历史GPU/NPU实验未在本轮重跑。

## R39 · llama.cpp 在 Mac Studio (Apple Silicon) 上的编译指南

> 本文档基于 2026-05-12 在 **Mac Studio M3 Ultra / 512 GB / macOS 26.3** 上从零编译 `[nisparks/llama.cpp](https://github.com/nisparks/llama.cpp)` `wip/deepseek-v4-support` 分支的实测过程整理。 编译目标：`llama-cli` / `llama-server` / `llama-bench` / `llama-gguf-split`，启用 **Metal GPU + Apple Accelerate** 后端。 产物运行时实测：识别 `Apple M3 Ultra` GPU，`unified memory = true`，可用 working set ≈ 487 GiB，DeepSeek V4 Flash 全层 offload 到 GPU。

---

#### 1. 概述

`llama.cpp` 是 ggml 团队的纯 C/C++ 推理引擎，在 Apple Silicon 上通过 **Metal 后端**实现 GPU 加速，配合统一内存（CPU/GPU 共享物理 RAM）做到 **零拷贝** mmap 加载大模型。

**为什么不用官方 mainline 而用 `nisparks` fork？**

| 用途 | 选择 |
| --- | --- |
| 通用 GGUF（Llama / Qwen / Mistral / DeepSeek V2/V3 …） | 官方 ggml-org/llama.cpp |
| DeepSeek V4 Flash（hyper_connection / lightning_indexer / FP4-FP8 native） | nisparks/llama.cpp wip/deepseek-v4-support 分支 ★ |
| antirez 自家 GGUF（hc_head_base 张量命名，跑在 ds4 引擎里） | antirez/llama.cpp-deepseek-v4-flash |

> **fork 与 GGUF 必须匹配**——nisparks fork 只能加载 nsparks 仓库的 GGUF；用 antirez 的 GGUF 会报 `missing tensor 'hc_head_base'`。详见 § 9.3。

>

##### ⚠️⚠️⚠️ Mac Metal × FP8 量化目前不可用（2026-05 实测）

nisparks fork 的 **Metal 后端没有实现 FP8_E4M3 量化的 MoE matmul kernel**（`mul_mat_id`），导致 `[nsparks/DeepSeek-V4-Flash-FP4-FP8-GGUF](https://huggingface.co/nsparks/DeepSeek-V4-Flash-FP4-FP8-GGUF)`（145 GiB，含 365 个 `f8_e4m3_b128` expert 张量）**在 Mac 上启动即崩溃**：

```Markdown
ggml-metal-device.cpp:876: not implemented
Asserting on type 42
ggml_metal_library_get_pipeline_mul_mm_id_map0
```

详见 § 10.9。如果你在 **Mac Studio / MacBook 上跑 DeepSeek V4 Flash**，请用 **antirez/ds4** 路线（详见 `ds4-部署指南.md`）：模型用 `antirez/deepseek-v4-gguf` 的 Q4 GGUF（153 GiB），引擎用 antirez/ds4，实测 29.4 t/s 稳定。

本指南后续步骤（§ 3 ~ § 8 编译流程）仍然有效，**只是当前 commit + nsparks GGUF 在 Metal 上跑不起来**——只能跑通用 GGUF（Llama / Qwen / 非 V4-Flash 的 DeepSeek）。

---

#### 2. 实测硬件 & 工具链版本

| 项目 | 实测版本 |
| --- | --- |
| 机型 | Mac Studio M3 Ultra（8E + 24P CPU / 80 GPU） |
| 内存 | 512 GB 统一内存（Metal recommendedMaxWorkingSetSize ≈ 498 GB） |
| 系统 | macOS 26.3（25D125） |
| Xcode | 26.3（17C529） |
| Apple clang | 17.0.0（1700.6.4.2） |
| cmake | 4.3.2 |
| ninja | 1.13.2 |
| Python | 3.12.13（uv 创建的虚拟环境） |
| uv | 0.11.13 |
| llama.cpp commit | 9d36408 (wip/deepseek-v4-support) |

---

#### 3. 环境准备

##### 3.1 安装 Xcode Command Line Tools

```text
xcode-select --install        # 弹窗按"安装"
xcode-select -p               # 验证: /Applications/Xcode.app/Contents/Developer
clang --version | head -1     # 验证: Apple clang version 17.x
```

> macOS 26+ 需要完整 Xcode（不只是 CLT），因为 Metal4 shader 编译器在 Xcode.app 里。可在 App Store 装 Xcode 26.x。

##### 3.2 切换 Homebrew 国内镜像 + 禁用 auto-update

国内访问 `formulae.brew.sh` 极慢，**当前 shell 生效**：

```text
export HOMEBREW_NO_AUTO_UPDATE=1
export HOMEBREW_NO_ENV_HINTS=1
export HOMEBREW_API_DOMAIN=https://mirrors.tuna.tsinghua.edu.cn/homebrew-bottles/api
export HOMEBREW_BOTTLE_DOMAIN=https://mirrors.tuna.tsinghua.edu.cn/homebrew-bottles
export HOMEBREW_BREW_GIT_REMOTE=https://mirrors.tuna.tsinghua.edu.cn/git/homebrew/brew.git
export HOMEBREW_CORE_GIT_REMOTE=https://mirrors.tuna.tsinghua.edu.cn/git/homebrew/homebrew-core.git
```

> 如需永久生效写入 `~/.zshrc`。

##### 3.3 安装编译工具链

```text
brew install cmake ninja git git-lfs
git lfs install                 # 一次性，初始化 git-lfs hook

cmake --version | head -1       # 期望: cmake version >= 3.20（实测 4.3.2）
ninja --version                 # 期望: 1.10+（实测 1.13.2）
```

##### 3.4 安装 `uv` 管理 Python 虚拟环境

```text
brew install uv

uv --version                    # 期望: uv 0.11.x
```

> `uv` 比 `python -m venv + pip` 快 10~100 倍，且能精准锁定 Python 版本。本指南所有 Python 操作都用 `uv`。

---

#### 4. 拉取源码

##### 4.1 选择目标 fork 与分支

```text
WORKSPACE="$HOME/Desktop/llm-workspace"
mkdir -p "$WORKSPACE" && cd "$WORKSPACE"

REPO=https://github.com/nisparks/llama.cpp.git
BRANCH=wip/deepseek-v4-support
```

##### 4.2 国内加速：用 GitHub 镜像

直连 `github.com` 在国内不稳定（中途 `curl 56` / `curl 92` 断流），且 `wip/deepseek-v4-support` 历史不大但仍有几十 MiB。**推荐 `ghfast.top` 反代**（实测最稳定，速度 5~30 MiB/s）：

```text
MIRROR=https://ghfast.top/https://github.com/nisparks/llama.cpp.git

git clone --depth=1 --single-branch -b "$BRANCH" "$MIRROR" llama.cpp
cd llama.cpp

git remote set-url origin "$MIRROR"
git log -1 --oneline            # 验证: 9d36408 deepseek4: ...
git branch --show-current        # wip/deepseek-v4-support
```

**镜像备选**（任一不通切下一个）：

| 镜像 | URL 前缀 | 备注 |
| --- | --- | --- |
| ghfast.top ★ | https://ghfast.top/https://github.com/... | 实测最稳 |
| kkgithub.com | https://kkgithub.com/<owner>/<repo>.git | 直接替换 host |
| gh-proxy.com | https://gh-proxy.com/https://github.com/... | 反代风格同 ghfast |
| github.akams.cn | https://github.akams.cn/https://github.com/... | 元信息快、clone 偶尔空 |

##### 4.3 浅克隆 vs 全量克隆

| 场景 | 命令 | 体积 |
| --- | --- | --- |
| 只想编译 + 跑模型 ★ | git clone --depth=1 --single-branch -b <branch> <mirror> | ~30 MiB |
| 想看历史 / 切其他分支 | git clone <mirror> | ~500 MiB |

> 如果首次浅克隆后还要切别的分支，用 `git fetch --depth=1 origin <other-branch>` 增量加。

---

#### 5. 创建 Python 虚拟环境

llama.cpp 自带的 `convert_hf_to_gguf.py` / `convert_lora_to_gguf.py` 等转换脚本依赖 PyTorch / transformers / sentencepiece，必须在独立 venv 里装。**编译过程本身不依赖 Python**，但模型转换/量化/测试要用。

```text
cd "$WORKSPACE/llama.cpp"

uv venv --python 3.12 llamacpp-build

source llamacpp-build/bin/activate

python --version                # 期望: Python 3.12.13
which python                    # 期望: .../llama.cpp/llamacpp-build/bin/python
```

> 命名为 `llamacpp-build` 是为了和 ds4 那边的 `model-eval` venv 区分开。

---

#### 6. 安装 Python 依赖（**重要：踩坑预警**）

##### 6.1 标准命令

```text
uv pip install -r requirements.txt --index-strategy unsafe-best-match
```

##### 6.2 ⚠️ 必须加 `--index-strategy unsafe-best-match` 的原因

`requirements.txt` 拉了多个子文件（`requirements-convert_*.txt`），其中部分依赖（如 `torch`）配置了 PyTorch 的多个 index URL（CPU / nightly / metal）。`uv` 默认 `first-index` 策略：在第一个 index 找到包名就停止搜索后续 index，导致 `transformers==<指定版本>` 在 nightly index 里只找到包名但版本不匹配，**直接报错而不会回退到 PyPI**：

```Markdown
error: Distribution `transformers==5.5.1` was not found in any of the configured indexes
       (Hint: try `--index-strategy unsafe-best-match` to search all indexes)
```

`unsafe-best-match` 会扫所有 index 找最佳匹配，是这种"多 index + 版本固定"项目的正确策略。

##### 6.3 验证关键依赖

```text
python -c "import torch, transformers, sentencepiece, gguf; \
  print('torch', torch.__version__); \
  print('transformers', transformers.__version__); \
  print('gguf', gguf.__version__)"
```

> 编译流程不依赖这些，但后续要 `convert_hf_to_gguf.py` 转模型时会用到。如果你只想编译跑模型、不转换，**§ 5 / § 6 可以跳过**。

---

#### 7. CMake 配置 + 编译（核心）

##### 7.1 配置（生成 Ninja build 系统）

```text
cd "$WORKSPACE/llama.cpp"

cmake -S . -B build -G Ninja \
  -DCMAKE_BUILD_TYPE=Release \
  -DGGML_METAL=ON \
  -DGGML_METAL_EMBED_LIBRARY=ON \
  -DGGML_NATIVE=ON \
  -DGGML_ACCELERATE=ON \
  -DGGML_BLAS=ON \
  -DGGML_BLAS_VENDOR=Apple \
  -DLLAMA_BUILD_TESTS=OFF \
  -DLLAMA_BUILD_EXAMPLES=OFF
```

**选项详解**：

| CMake 变量 | 值 | 作用 |
| --- | --- | --- |
| CMAKE_BUILD_TYPE | Release | -O3 优化，禁用 assert（务必！Debug 慢 5~10 倍） |
| GGML_METAL | ON ★ | 启用 Metal GPU 后端，编译 libggml-metal.dylib |
| GGML_METAL_EMBED_LIBRARY | ON ★ | 把 default.metallib 嵌入二进制，部署时无需带外部 .metallib |
| GGML_NATIVE | ON | 针对当前 CPU 架构生成最优 NEON/AMX 指令 |
| GGML_ACCELERATE | ON | 启用 Apple Accelerate framework（CPU fallback 用 vDSP） |
| GGML_BLAS + GGML_BLAS_VENDOR=Apple | ON / Apple | CPU 端矩阵乘走 Apple BLAS（cblas_sgemm 等） |
| LLAMA_BUILD_TESTS=OFF | OFF | 跳过 unit test，省 2~3 分钟 |
| LLAMA_BUILD_EXAMPLES=OFF | OFF | 跳过 example 程序（如 simple / passkey） |

##### 7.2 ⚠️ 必须接 build 命令（**最常踩坑**）

`cmake -S . -B build` **只是配置阶段**，不会产生任何二进制。看到 `-- Generating done` / `-- Build files have been written to: ...build` 不代表编完了。**必须再跑一次 `cmake --build`**：

```text
cmake --build build --config Release -j \
  --target llama-cli llama-server llama-bench llama-gguf-split
```

| 参数 | 作用 |
| --- | --- |
| --config Release | 多配置生成器需要（Ninja 单配置可省略，加上无害） |
| -j | 并行（默认全核，M3 Ultra 24P 实测 ~3-5 分钟编完） |
| --target | 只编需要的，省时间。如果想编所有产物去掉 --target |

**预期输出**（最后几行）：

```Markdown
[342/342] Linking CXX executable bin/llama-server
```

##### 7.3 编译产物清单

```text
ls -lh build/bin/llama-* build/bin/libggml-metal.dylib
```

期望看到：

```Markdown
build/bin/llama-cli              1.4 MiB
build/bin/llama-server           8.7 MiB
build/bin/llama-bench            277 KiB
build/bin/llama-gguf-split        58 KiB
build/bin/libggml-metal.dylib    796 KiB    ← Metal 后端
build/bin/libggml-blas.dylib      57 KiB
build/bin/libggml-cpu.dylib      929 KiB
build/bin/libggml-base.dylib     737 KiB
+ 一堆 symlink (.0.dylib / .0.10.0.dylib)
```

---

#### 8. 验证编译结果（三段式）

##### 8.1 静态：链接库检查

```text
otool -L build/bin/llama-server | grep -i ggml
```

期望同时看到 `libggml-metal.0.dylib` 和 `libggml-cpu.0.dylib` / `libggml-blas.0.dylib`：

```Markdown
@rpath/libggml.0.dylib
@rpath/libggml-cpu.0.dylib
@rpath/libggml-blas.0.dylib
@rpath/libggml-metal.0.dylib   ← 必须有这一行
@rpath/libggml-base.0.dylib
```

##### 8.2 静态：CMakeCache 复核

```text
grep -E "^GGML_METAL|^GGML_NATIVE|^CMAKE_BUILD_TYPE" build/CMakeCache.txt | grep -v "^//"
```

期望：

```Markdown
CMAKE_BUILD_TYPE:STRING=Release
GGML_METAL:BOOL=ON
GGML_METAL_EMBED_LIBRARY:BOOL=ON
GGML_NATIVE:BOOL=ON
```

##### 8.3 运行时：Metal 设备初始化

```text
./build/bin/llama-server --version 2>&1 | head -25
```

期望看到（关键 6 行）：

```Markdown
ggml_metal_library_init: using embedded metal library         ← shader 嵌入成功
ggml_metal_device_init: GPU name:   MTL0 (Apple M3 Ultra)
ggml_metal_device_init: GPU family: MTLGPUFamilyApple9 (1009)
ggml_metal_device_init: GPU family: MTLGPUFamilyMetal4 (5002)  ← Metal4 支持
ggml_metal_device_init: has unified memory    = true           ← 统一内存
ggml_metal_device_init: recommendedMaxWorkingSetSize  = 498216.21 MB  ← 487 GiB 可寻址
```

如果 **没有这些 `ggml_metal_*` 行**，说明编译时 `GGML_METAL=OFF`，需要重新配置 + 编译。

---

#### 9. 用编译产物加载模型

##### 9.1 启动 llama-server（生产参数）

```text
cd "$WORKSPACE/llama.cpp"

MODEL=/Volumes/990pro/modeldown/models/DeepSeek-V4-Flash-FP4-FP8-native.gguf

./build/bin/llama-server \
  -m "$MODEL" \
  -ngl 999 \
  --host 0.0.0.0 --port 8080 \
  --alias deepseek-v4-flash \
  -c 65536 \
  --jinja \
  -fa on
```

##### 9.2 ⚠️ `-ngl 999` 必传，否则退化到 CPU

| 参数 | 实际行为 |
| --- | --- |
| 不传 -ngl 或 -ngl 0 | 纯 CPU 推理（24 P-core 全开，速度慢 5~10 倍） |
| -ngl 999（或显式传层数） | 全部层 offload 到 Metal GPU ★ |

启动后看日志确认 offload 成功：

```Markdown
load_tensors: offloaded 64/64 layers to GPU       ← 全部层都到 GPU 了
load_tensors:        Metal model buffer size = ... MiB
```

如果出现 `offloaded 0/64 layers to GPU` 或 `CPU buffer size`，说明退化到 CPU。

##### 9.3 ⚠️ fork × GGUF × 平台 兼容性矩阵

| 你编译的 fork | 兼容的 GGUF | Mac Metal | NVIDIA CUDA |
| --- | --- | --- | --- |
| nisparks/llama.cpp wip/deepseek-v4-support ★（本指南） | nsparks/DeepSeek-V4-Flash-FP4-FP8-GGUF | ❌ 崩溃 | ✅ |
| antirez/llama.cpp-deepseek-v4-flash | antirez/deepseek-v4-gguf | ✅ | ✅ |
| 官方 ggml-org/llama.cpp | 任意非 V4-Flash 模型（Llama / Qwen / DSv2/v3） | ✅ | ✅ |

**两类典型错配症状**：

| 症状 | 原因 |
| --- | --- |
| load_tensors: missing tensor 'hc_head_base' | 用 antirez GGUF 配 nisparks fork（张量命名不同） |
| Asserting on type 42 + ggml_metal_library_get_pipeline_mul_mm_id_map0 | 用 nsparks FP8 GGUF 在 Mac Metal 上跑（Metal 后端没实现 FP8_E4M3 kernel）→ 详见 § 10.9 |

> Mac 用户跑 DeepSeek V4 Flash 的当前最优解：**antirez/ds4 引擎 + antirez Q4 GGUF**，详见 `ds4-部署指南.md`。本指南编译出的 llama.cpp 在 Mac 上目前只适合跑非 V4-Flash 的通用 GGUF。

##### 9.4 用 asitop 实时验证 GPU 负载

```text
sudo asitop                 # 另开终端
```

发出推理请求时观察：

| 指标 | GPU 推理（正确） | CPU 推理（退化） |
| --- | --- | --- |
| GPU Usage | 70~95% | 持续 0% |
| GPU Power | 30~55 W | <1 W |
| P-CPU Usage | <30% | 800~1800% |

---

#### 10. 故障排查

##### 10.1 `cmake -S . -B build` 跑完没有 `build/bin/llama-server`

**没跑 `cmake --build build ...`**，配置 ≠ 编译。回到 § 7.2。

##### 10.2 `error: Distribution 'transformers==X.Y.Z' was not found in any of the configured indexes`

`uv pip install` 没加 `--index-strategy unsafe-best-match`。回到 § 6.2。

##### 10.3 `git clone` 频繁 `curl 56` / `curl 92` / `RPC failed`

GitHub 直连不稳定。换镜像（§ 4.2）；如果挂了 Clash Verge，**TUN 模式会劫持 git 流量**，先杀核心：

```text
sudo pkill -9 -f verge-mihomo
sudo dscacheutil -flushcache
sudo killall -HUP mDNSResponder
```

##### 10.4 `load_tensors: missing tensor 'hc_head_base'`

fork 与 GGUF 不匹配。回到 § 9.3 选对组合。

##### 10.5 `ggml_metal_*` 行完全不出现 / `ggml: backend cpu only`

CMake 没启 Metal。检查 `build/CMakeCache.txt`：

```text
grep GGML_METAL build/CMakeCache.txt | grep -v "^//"
```

如果是 `GGML_METAL:BOOL=OFF`，**清干净重来**：

```text
rm -rf build
# 然后重跑 § 7.1 + § 7.2
```

##### 10.6 链接报 `ld: framework 'Metal' not found`

Xcode CLT 不完整或未指向 Xcode.app：

```text
sudo xcode-select -s /Applications/Xcode.app/Contents/Developer
xcode-select -p           # 确认
```

##### 10.7 编译期 `error: 'simdgroup_*' is unavailable`

Metal shader 编译器版本太老（macOS < 14）。本指南要求 macOS 26.x；旧系统建议升级或关掉 Metal4 特性：

```text
cmake -S . -B build -G Ninja ... -DGGML_METAL_USE_BF16=OFF
```

##### 10.8 `incompatible mac OS X version` 警告

`GGML_METAL_MACOSX_VERSION_MIN` 未设。一般可忽略；想消除：

```text
cmake -S . -B build -G Ninja ... -DGGML_METAL_MACOSX_VERSION_MIN=14.0
```

##### 10.9 ⚠️ `Asserting on type 42` / `mul_mm_id_map0` not implemented（FP8 × Metal 不兼容）

**完整堆栈**：

```Markdown
common_init_from_params: warming up the model with an empty run
ggml/src/ggml-metal/ggml-metal-device.cpp:876: not implemented
Asserting on type 42
ggml_metal_library_get_pipeline_mul_mm_id_map0 + 0
ggml_metal_op_mul_mat + 1016
...
zsh: abort  ./build/bin/llama-server ...
```

**根因**：

- **type 42** = `GGML_TYPE_F8_E4M3`（FP8 E4M3 量化，原生 NVIDIA H100/H200/B100 张量类型）

- **`mul_mm_id_map0`** = MoE 专家路由的 indirect 批量矩阵乘 kernel

- 你的 GGUF 里 **365 个张量是 `f8_e4m3_b128`**（256 个专家的权重），**Metal 后端没有这个量化类型的实现**

**三个后端 FP8 实现矩阵**（搜 `F8_E4M3` 出现的源文件得到）：

| 后端 | FP8_E4M3 实现 | 状态 |
| --- | --- | --- |
| CPU | quants.c / ops.cpp / ggml-cpu.c | ✅ 完整 |
| CUDA | quantize / mmvq / convert / common ... 6 个文件 | ✅ 完整 |
| Metal | 0 个文件 | ❌ 完全未实现 |

Metal 后端 `mul_mat_id` 当前支持的量化类型清单：`F32 / F16 / BF16 / Q1_0 / Q4_0~Q5_1 / Q8_0 / MXFP4 / Q2_K~Q6_K / IQ2_XXS~IQ4_XS`，**不含 F8_E4M3**。

**为什么修不了 = nisparks 不优先做 Mac**：fork 最近 20 个 commit 全是 `ggml-cuda` 与 `server` 层，零 Metal 改动——这个 fork 的目标硬件是 NVIDIA 服务器（FP8 native tensor core），Apple Silicon 不在 roadmap 上。

**解决方案（按推荐度）**：

| 方案 | 模型 | 引擎 | 工作量 | Mac 速度估计 |
| --- | --- | --- | --- | --- |
| A. 切回 antirez/ds4 ★★★★★ | antirez/deepseek-v4-gguf Q4（153 GiB） | ds4-server | 0（已编译过） | 29.4 t/s 实测 |
| B. 编译 antirez/llama.cpp-deepseek-v4-flash | 同上 | antirez fork | 重编（~5 min） | 同量级 |
| C. -ot expert=CPU 把 expert 丢 CPU | nsparks FP8（145 GiB） | nisparks llama-server | 调参 | 1~3 t/s（慢 10~30×） |
| D. 等 nisparks 写 Metal FP8 kernel | nsparks FP8 | nisparks llama-server | 不可控 | 未知 |

**Mac 用户结论**：本指南编译出的 nisparks `llama-server` 在 macOS 上跑不了 nsparks 的 FP8 GGUF，请改走 **方案 A**（参考 `ds4-部署指南.md`）。

---

#### 11. 常用维护命令

##### 11.1 增量编译（修改源码后）

```text
cmake --build build --config Release -j --target llama-server
```

> Ninja 自动增量，只重编受影响的 `.o` + 重链接。M3 Ultra 上小改动通常 5~15 秒。

##### 11.2 清理 build 目录

```text
rm -rf build              # 全清，下次需要重跑 § 7.1 配置
cmake --build build --target clean   # 软清，保留 CMakeCache，只删 .o
```

##### 11.3 切换分支后重新编译

```text
cd "$WORKSPACE/llama.cpp"
git fetch --depth=1 origin <other-branch>
git checkout <other-branch>

rm -rf build && \
  cmake -S . -B build -G Ninja -DCMAKE_BUILD_TYPE=Release -DGGML_METAL=ON \
        -DGGML_METAL_EMBED_LIBRARY=ON -DGGML_NATIVE=ON && \
  cmake --build build --config Release -j --target llama-server
```

##### 11.4 拉分支最新 commit

```text
git pull --depth=1 origin "$(git branch --show-current)"
cmake --build build --config Release -j --target llama-server
```

---

#### 附录 A：完整一键脚本

把下面保存为 `~/bin/llamacpp-build.sh`，加可执行权限后 `llamacpp-build.sh` 一键拉源码 + 配置 + 编译。

```text
#!/usr/bin/env bash
set -euo pipefail

WORKSPACE="$HOME/Desktop/llm-workspace"
BRANCH="${LLAMA_BRANCH:-wip/deepseek-v4-support}"
MIRROR="${LLAMA_MIRROR:-https://ghfast.top/https://github.com/nisparks/llama.cpp.git}"

export HOMEBREW_NO_AUTO_UPDATE=1
export HOMEBREW_API_DOMAIN=https://mirrors.tuna.tsinghua.edu.cn/homebrew-bottles/api
export HOMEBREW_BOTTLE_DOMAIN=https://mirrors.tuna.tsinghua.edu.cn/homebrew-bottles

for tool in cmake ninja git uv; do
  command -v "$tool" >/dev/null || brew install "$tool"
done

mkdir -p "$WORKSPACE" && cd "$WORKSPACE"
if [ ! -d llama.cpp/.git ]; then
  git clone --depth=1 --single-branch -b "$BRANCH" "$MIRROR" llama.cpp
fi
cd llama.cpp

if [ ! -d llamacpp-build ]; then
  uv venv --python 3.12 llamacpp-build
fi

cmake -S . -B build -G Ninja \
  -DCMAKE_BUILD_TYPE=Release \
  -DGGML_METAL=ON -DGGML_METAL_EMBED_LIBRARY=ON \
  -DGGML_NATIVE=ON -DGGML_ACCELERATE=ON \
  -DGGML_BLAS=ON -DGGML_BLAS_VENDOR=Apple \
  -DLLAMA_BUILD_TESTS=OFF -DLLAMA_BUILD_EXAMPLES=OFF

cmake --build build --config Release -j \
  --target llama-cli llama-server llama-bench llama-gguf-split

./build/bin/llama-server --version 2>&1 | grep -E "ggml_metal_device_init|version:" | head -10
echo ""
echo "[OK] llama.cpp built. Binaries at: $WORKSPACE/llama.cpp/build/bin/"
```

---

#### 附录 B：编译选项速查表（按场景选）

| 场景 | 增加的 CMake 变量 |
| --- | --- |
| Apple Silicon Metal（本指南）★ | -DGGML_METAL=ON -DGGML_METAL_EMBED_LIBRARY=ON -DGGML_NATIVE=ON |
| Apple Silicon 纯 CPU（不要 Metal） | -DGGML_METAL=OFF -DGGML_ACCELERATE=ON -DGGML_BLAS=ON -DGGML_BLAS_VENDOR=Apple |
| CUDA（Linux + NVIDIA） | -DGGML_CUDA=ON -DCMAKE_CUDA_ARCHITECTURES=native |
| Vulkan（跨平台 GPU） | -DGGML_VULKAN=ON |
| OpenCL（Adreno / Mali） | -DGGML_OPENCL=ON |
| HIP / ROCm（AMD GPU） | -DGGML_HIP=ON |
| OpenMP 多线程 CPU | -DGGML_OPENMP=ON |
| 静态链接（部署单文件） | -DBUILD_SHARED_LIBS=OFF |
| Server 启用 SSL | -DLLAMA_SERVER_SSL=ON（依赖 OpenSSL） |
| 包含 mtmd 多模态 | -DLLAMA_BUILD_TOOLS=ON（默认开） |

---

**文档版本**：v1.1
**最后更新**：2026-05-13
**变更摘要**：v1.1 新增 § 1 顶部 Mac × FP8 不兼容警告、§ 9.3 兼容性矩阵新增 Mac Metal / NVIDIA CUDA 列、§ 10.9 故障排查新增 `Asserting on type 42` 详细诊断与解决方案。
**实测环境**：Mac Studio M3 Ultra / 512 GB / macOS 26.3 / Xcode 26.3 / Apple clang 17 / cmake 4.3.2 / ninja 1.13.2 / uv 0.11.13 / Python 3.12.13
**验证方式**：`llama-server --version` 成功初始化 Metal4；nsparks FP8 GGUF 在 Mac 上启动崩溃（已记录到 § 10.9）；通用 GGUF 在 Mac 上加载推理正常。
