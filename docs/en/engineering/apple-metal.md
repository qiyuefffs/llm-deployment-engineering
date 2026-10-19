# Apple M3 Ultra: Metal toolchain, GGUF compatible with the model

[简体中文](../../01-deployment-foundations/cases/C10-m3-metal/README.md) | **English**

[Index of engineering examples](README.md) · [General directory of knowledge systems](../SUMMARY.md)

Technical labels: `macOS / Xcode / Metal / llama.cpp / GGUF`

## Environment and Objectives

M3 Ultra/512GB,macOS26.3; The route is Xcode/clang/CMake/Ninja → llama.cpp Metal → GGUF. Special GGUF of the original branch commit9d36408 appeared `hc_head_base` With type 42 problems, the build passed but the model load failed and could not be rewritten as a success result.

## Complete deployment and adaptation process

1. Verified `xcode-select -p `, ` xcrun --find metal `, ` clang --version `, ` cmake --version`It is compatible with ARM64 architecture.
2. The same source code tree separately configuration Metal build directories, retaining CMake detection, shader compilation and dynamic library paths.
3. Metal execution with small supported GGUF verification and re-loading of the target model; Distinguish between missing tensors, unknown GGML types, kernel compilation and memory allocation.
4. Model Layer Number, KV and Temporary Buffer verify the actual Metal log; Unified memory should be left to the OS, not equal to weights.
5. Run the full CLI output, then convert the llama-server to the same calibre llama-bench; The original failed target requires a compatible converter and source branch first.

## Accelerated optimization and acceptance testing

Optimization sequence: Confirm the actual offloading → quantization Candidate→ctx/batch/ubatch→FA support→ service slot. Each time you retain pp/tg, first load, heat inference, system memory pressure and quality. The current source material has not completed load acceptance testing for the particular artifact, so the following is a complete preservation of the cause and error of the failure; Available for MLX services and concurrency records [Example of Apple MLX](apple-mlx.md).

## Agreement on the use of complete technical records

The following technical correctness, commands, tables, logs, failures and subsequent experiments of the relevant FlowUs articles are retained directly, without abbreviating the original process. private paths, nodes, authentication and sanitization of attached addresses; `<NODE_IP>` For example, the placeholder needs to be filled in the current environment. The original suggestion or prediction is still a suggestion or prediction. The above execution sequence and technical revisions are used to explain conflicts in historical records, and historical GPU/NPU experiments have not been repeated in this round.

## R39 · llama.cpp compilation guides on the Mac Studio (Apple Silicon)

> This document is based on 2026-05-12 **Mac Studio M3 Ultra / 512 GB / macOS 26.3** Compilation from zero up `[nisparks/llama.cpp](https://github.com/nisparks/llama.cpp)` ` wip/deepseek-v4-support `The measured process of branches is organized. Compilation Objectives: ` llama-cli ` / ` llama-server ` / ` llama-bench ` / ` llama-gguf-split `Activated **Metal GPU + Apple Accelerate** The back. Product runtime measured: identification ` Apple M3 Ultra ` GPU, ` unified memory = true`With the working set ≈ 487 GiB, DeepSeek V4 Flash fully offloads to the GPU.

---

#### 1. Summary

`llama.cpp` It is a pure C/C++ inference engine from the ggml team, passed on Apple Silicon. **The back of the metal** This is achieved through GPU acceleration with unified memory (CPU/GPU Shared Physical RAM). **Zero-copy** mmap is loaded with large language model.

**Why not use the official mainline?`nisparks` fork？**

|Useful|Choosing|
| --- | --- |
|General GGUF models (Llama / Qwen / Mistral / DeepSeek V2/V3 …)|This is the official website of ggml-org/llama.cpp|
| DeepSeek V4 Flash(hyper_connection / lightning_indexer / FP4-FP8 native) |nisparks/llama.cpp, wip/deepseek-v4-support branch ★|
|Antirez is named after his home GGUF ((hc_head_base tensor, running on the ds4 engine)| antirez/llama.cpp-deepseek-v4-flash |

> **The fork must match the GGUF** The Nnisparks fork can only load the GGUF of the nsparks repository; GGUF reports with antirez `missing tensor 'hc_head_base'`. See section 9.3 below.

>

##### ⚠️⚠️⚠️ Mac Metal × FP8 quantization was unavailable in the tested configuration (measured in 2026-05)

It's the Nisparks fork. **The MoE matmul kernel does not quantize FP8_E4M3 on the backend of the Metal.**(`mul_mat_id ` It is `[nsparks/DeepSeek-V4-Flash-FP4-FP8-GGUF](https://huggingface.co/nsparks/DeepSeek-V4-Flash-FP4-FP8-GGUF)` It's about 145 GiB and 365 GiB.`f8_e4m3_b128` expert tensor )** Starting on Mac, it crashes**:

```Markdown
ggml-metal-device.cpp:876: not implemented
Asserting on type 42
ggml_metal_library_get_pipeline_mul_mm_id_map0
```

See section 10.9 for details. If you are **Mac Studio / MacBook running the DeepSeek V4 Flash** Please. **antirez/ds4** Routes: See details `ds4-部署指南.md ` Models used `antirez/deepseek-v4-gguf` The Q4 GGUF ((153 GiB), engine with antirez/ds4, measured 29.4 t/s stable.

The following steps in this guide (§§ 3 ~ § 8 compilation process) are still in effect, **It's just that the current commit + nsparks GGUF can't run on Metal.** The game can only run with GGUF (Llama / Qwen / DeepSeek for non-V4-Flash).

---

#### 2. measured Hardware & toolchain

|Projects|measured version|
| --- | --- |
|Aircraft| Mac Studio M3 Ultra(8E + 24P CPU / 80 GPU) |
|memory|512 GB unified memory (Metal recommendedMaxWorkingSetSize ≈ 498 GB)|
|The system| macOS 26.3(25D125) |
| Xcode | 26.3（17C529） |
| Apple clang | 17.0.0（1700.6.4.2） |
| cmake | 4.3.2 |
| ninja | 1.13.2 |
| Python |3.12.13 ((uv created virtual environment)|
| uv | 0.11.13 |
| llama.cpp commit | 9d36408 (wip/deepseek-v4-support) |

---

#### 3. Environmental preparedness

##### 3.1 Install the Xcode Command Line Tools

```text
xcode-select --install        # 弹窗按"安装"
xcode-select -p               # 验证: /Applications/Xcode.app/Contents/Developer
clang --version | head -1     # 验证: Apple clang version 17.x
```

> MacOS 26+ requires full Xcode (not just CLT) because the Metal4 shader compiler is in Xcode.app. Xcode 26.x is available on the App Store.

##### 3.2 Switch to Homebrew Home image + disable auto-update

Internal visits `formulae.brew.sh` Very slow. **The current shell is effective**:

```text
export HOMEBREW_NO_AUTO_UPDATE=1
export HOMEBREW_NO_ENV_HINTS=1
export HOMEBREW_API_DOMAIN=https://mirrors.tuna.tsinghua.edu.cn/homebrew-bottles/api
export HOMEBREW_BOTTLE_DOMAIN=https://mirrors.tuna.tsinghua.edu.cn/homebrew-bottles
export HOMEBREW_BREW_GIT_REMOTE=https://mirrors.tuna.tsinghua.edu.cn/git/homebrew/brew.git
export HOMEBREW_CORE_GIT_REMOTE=https://mirrors.tuna.tsinghua.edu.cn/git/homebrew/homebrew-core.git
```

> If it is permanently written `~/.zshrc`.

##### 3.3 Install compilation toolchain

```text
brew install cmake ninja git git-lfs
git lfs install                 # 一次性，初始化 git-lfs hook

cmake --version | head -1       # 期望: cmake version >= 3.20（实测 4.3.2）
ninja --version                 # 期望: 1.10+（实测 1.13.2）
```

##### 3.4 Installed `uv` Manage the Python virtual environment

```text
brew install uv

uv --version                    # 期望: uv 0.11.x
```

> `uv ` It's not.`python -m venv + pip ` It's 10 to 100 times faster and more accurate at locking Python versions. This guide uses all Python operations.`uv`.

---

#### 4. Draw the source code

##### 4.1 Select the target fork and branch

```text
WORKSPACE="$HOME/Desktop/llm-workspace"
mkdir -p "$WORKSPACE" && cd "$WORKSPACE"

REPO=https://github.com/nisparks/llama.cpp.git
BRANCH=wip/deepseek-v4-support
```

##### 4.2 Domestic acceleration: with GitHub image

Directly connected `github.com ` In the midst of domestic instability `curl 56 ` / ` curl 92 `and ` wip/deepseek-v4-support `It's not very old, but there are still dozens of MiBs. **Recommended ` ghfast.top`Reversed**(measured most stable, speeds 5 to 30 MiB/s):

```text
MIRROR=https://ghfast.top/https://github.com/nisparks/llama.cpp.git

git clone --depth=1 --single-branch -b "$BRANCH" "$MIRROR" llama.cpp
cd llama.cpp

git remote set-url origin "$MIRROR"
git log -1 --oneline            # 验证: 9d36408 deepseek4: ...
git branch --show-current        # wip/deepseek-v4-support
```

**Image selected**(Never miss the next one):

|image|URL prefix|Notes|
| --- | --- | --- |
| ghfast.top ★ | https://ghfast.top/https://github.com/... |measured most stable|
| kkgithub.com | https://kkgithub.com/<owner>/<repo>.git |Direct replacement of host|
| gh-proxy.com | https://gh-proxy.com/https://github.com/... |Anti-Gypsy style and ghfast|
| github.akams.cn | https://github.akams.cn/https://github.com/... |It's fast, clone, and sometimes empty.|

##### 4.3 Asha clones versus full-size clones

|The scene|Orders|The volume|
| --- | --- | --- |
|Just want to compilation + run model ★| git clone --depth=1 --single-branch -b <branch> <mirror> | ~30 MiB |
|Looking at history / Cutting other branches| git clone <mirror> | ~500 MiB |

> If you have to cut branches after the first cloning, you can use the first branch.`git fetch --depth=1 origin <other-branch>` It's a lot more than that.

---

#### 5. Create a Python virtual environment

It's called llama.cpp.`convert_hf_to_gguf.py ` / ` convert_lora_to_gguf.py`For example, dependency PyTorch / transformers / sentencepiece must be installed in a separate venv. **The compilation process itself doesn't depend on Python.** But model conversion/quantisation/testing is needed.

```text
cd "$WORKSPACE/llama.cpp"

uv venv --python 3.12 llamacpp-build

source llamacpp-build/bin/activate

python --version                # 期望: Python 3.12.13
which python                    # 期望: .../llama.cpp/llamacpp-build/bin/python
```

> Named after `llamacpp-build ` is intended to match the ds4 `model-eval` The venv is separated.

---

#### 6. Install Python dependency **It's important to step on the crater warning**)

##### 6.1 Standard commands

```text
uv pip install -r requirements.txt --index-strategy unsafe-best-match
```

##### 6.2 You have to add `--index-strategy unsafe-best-match` Why?

`requirements.txt ` downloaded several component files (`requirements-convert_*.txt ` In some cases, dependency is the result of a combination of factors.`torch ` The configuration includes multiple index URLs for PyTorch (CPU/nightly/metal).`uv ` Default `first-index ` Strategy: Stop searching for a subsequent index when you find a package name in the first index, which leads to `transformers==<指定版本>` In the nightly index, only the pack names were found, but the version did not match. **Direct error without fallback to PyPI**:

```Markdown
error: Distribution `transformers==5.5.1` was not found in any of the configured indexes
       (Hint: try `--index-strategy unsafe-best-match` to search all indexes)
```

`unsafe-best-match` This is the correct strategy for this "multi-index + version fixed" project.

##### 6.3 Verifying critical dependency

```text
python -c "import torch, transformers, sentencepiece, gguf; \
  print('torch', torch.__version__); \
  print('transformers', transformers.__version__); \
  print('gguf', gguf.__version__)"
```

> Compilation processes are not dependent on these, but follow-up should be `convert_hf_to_gguf.py` It's used when changing models. If you just want to compile, run models, not convert, **§ 5 / § 6 Can be jumped**.

---

#### 7. CMake configuration + compilation (core)

##### 7.1 configuration (generated Ninja build system)

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

**Details of options**:

|The CMake variable|Value|The role|
| --- | --- | --- |
| CMAKE_BUILD_TYPE | Release |- O3 Optimized, disabled assert! Debug slowly 5 to 10 times)|
| GGML_METAL | ON ★ |Activate the backend of the Metal GPU, compilation libggml-metal.dylib|
| GGML_METAL_EMBED_LIBRARY | ON ★ |Embed default.metallib in binary, without having to carry external .metallib when deployed|
| GGML_NATIVE | ON |Create optimum NEON/AMX instructions for the current CPU architecture|
| GGML_ACCELERATE | ON |Apple Accelerate framework is enabled (CPU fallback with vDSP)|
| GGML_BLAS + GGML_BLAS_VENDOR=Apple | ON / Apple |The CPU end matrix goes by Apple BLAS (cblas_sgemm, etc.)|
| LLAMA_BUILD_TESTS=OFF | OFF |Jump the unit test, save 2-3 minutes.|
| LLAMA_BUILD_EXAMPLES=OFF | OFF |For example, skip the simple/passkey program.|

##### 7.2 You have to take the build command **It's the most common crater.**)

`cmake -S . -B build ` **It's just the configuration phase.** It's not going to generate any binaries. I see.`-- Generating done ` / `-- Build files have been written to: ...build ` That doesn't mean it's finished. **must be run again `cmake --build`**:

```text
cmake --build build --config Release -j \
  --target llama-cli llama-server llama-bench llama-gguf-split
```

|Parameters|The role|
| --- | --- |
| --config Release |Multi-configuration Generator required (Ninja single configuration can be omitted, plus harmless)|
| -j |Parallelism (default full core, M3 Ultra 24P measured ~ 3-5 minutes complete)|
| --target |It's just a waste of time. If you want to get rid of all the products -- target.|

**Expected output**(Final lines):

```Markdown
[342/342] Linking CXX executable bin/llama-server
```

##### 7.3 compilation List of products

```text
ls -lh build/bin/llama-* build/bin/libggml-metal.dylib
```

Expect to see:

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

#### 8. Verify the compilation results (three paragraphs)

##### 8.1 Static: Check the link library

```text
otool -L build/bin/llama-server | grep -i ggml
```

Looking forward to seeing `libggml-metal.0.dylib ` and `libggml-cpu.0.dylib ` / ` libggml-blas.0.dylib`:

```Markdown
@rpath/libggml.0.dylib
@rpath/libggml-cpu.0.dylib
@rpath/libggml-blas.0.dylib
@rpath/libggml-metal.0.dylib   ← 必须有这一行
@rpath/libggml-base.0.dylib
```

##### 8.2 Static: CMakeCache Reviewed

```text
grep -E "^GGML_METAL|^GGML_NATIVE|^CMAKE_BUILD_TYPE" build/CMakeCache.txt | grep -v "^//"
```

Expectations are:

```Markdown
CMAKE_BUILD_TYPE:STRING=Release
GGML_METAL:BOOL=ON
GGML_METAL_EMBED_LIBRARY:BOOL=ON
GGML_NATIVE:BOOL=ON
```

##### 8.3 Runtime: Metal device initialized

```text
./build/bin/llama-server --version 2>&1 | head -25
```

Expected output (6 key lines):

```Markdown
ggml_metal_library_init: using embedded metal library         ← shader 嵌入成功
ggml_metal_device_init: GPU name:   MTL0 (Apple M3 Ultra)
ggml_metal_device_init: GPU family: MTLGPUFamilyApple9 (1009)
ggml_metal_device_init: GPU family: MTLGPUFamilyMetal4 (5002)  ← Metal4 支持
ggml_metal_device_init: has unified memory    = true           ← 统一内存
ggml_metal_device_init: recommendedMaxWorkingSetSize  = 498216.21 MB  ← 487 GiB 可寻址
```

If you **No such thing.`ggml_metal_*` Going **It's a compilation.`GGML_METAL=OFF`; reconfigure and rebuild.

---

#### 9. Loading models with compilation products

##### 9.1 Activate the llama-server (production parameter)

```text
cd "$WORKSPACE/llama.cpp"

MODEL=<MODEL_VOLUME>/modeldown/models/DeepSeek-V4-Flash-FP4-FP8-native.gguf

./build/bin/llama-server \
  -m "$MODEL" \
  -ngl 999 \
  --host 0.0.0.0 --port 8080 \
  --alias deepseek-v4-flash \
  -c 65536 \
  --jinja \
  -fa on
```

##### 9.2 ⚠️ `-ngl 999` It must be transmitted or degraded to the CPU

|Parameters|Practical actions|
| --- | --- |
|Not transmitted -ngl or -ngl 0|Pure CPU inference (24 P-core fully open, 5 to 10 times slower)|
|-ngl 999 ((or the number of explicit layers)|All layers offloaded to Metal GPU ★|

After launching, check the log to confirm the successful offload:

```Markdown
load_tensors: offloaded 64/64 layers to GPU       ← 全部层都到 GPU 了
load_tensors:        Metal model buffer size = ... MiB
```

If there is `offloaded 0/64 layers to GPU ` or `CPU buffer size` It's a decaying processor, and it's decaying into the CPU.

##### 9.3 Forks × GGUF × Platform Compatibility Matrix

|The fork of your compilation|Compatible with GGUF| Mac Metal | NVIDIA CUDA |
| --- | --- | --- | --- |
|nisparks/llama.cpp, wip/deepseek-v4-support ★ (this guide)| nsparks/DeepSeek-V4-Flash-FP4-FP8-GGUF |It collapsed.| ✅ |
| antirez/llama.cpp-deepseek-v4-flash | antirez/deepseek-v4-gguf | ✅ | ✅ |
|This is the official website of ggml-org/llama.cpp|Any other non-V4-Flash model (Llama / Qwen / DSv2/v3)| ✅ | ✅ |

**Typical mismatch symptoms**:

|Symptoms|Why?|
| --- | --- |
| load_tensors: missing tensor 'hc_head_base' |It's called a nisparks fork with an antirez GGUF (a different name for tensor).|
| Asserting on type 42 + ggml_metal_library_get_pipeline_mul_mm_id_map0 |With nsparks FP8 GGUF running on Mac Metal, the FP8_E4M3 kernel was not implemented on the backend of the Metal)→ See § 10.9|

> Mac users are currently optimising DeepSeek V4 Flash: **antirez/ds4 engine + antirez Q4 GGUF** See also `ds4-部署指南.md`. The llama.cpp compilation of this guide is currently only available for non-V4-Flash general GGUF running on Mac.

##### 9.4 Real-time verification of GPU workload with asitop

```text
sudo asitop                 # 另开终端
```

In order to make inference requests, observe:

|Indicators|GPU inference (right)|CPU inference (degraded)|
| --- | --- | --- |
| GPU Usage | 70~95% |Continued 0%|
| GPU Power | 30~55 W | <1 W |
| P-CPU Usage | <30% | 800~1800% |

---

#### 10. Failure screening

##### 10.1 `cmake -S . -B build ` No running `build/bin/llama-server`

**Not running.`cmake --build build ...`**; configuration ≠ compilation. Return to § 7.2.

##### 10.2 `error: Distribution 'transformers==X.Y.Z' was not found in any of the configured indexes`

`uv pip install ` No more.`--index-strategy unsafe-best-match`. Return to § 6.2.

##### 10.3 `git clone ` Frequently `curl 56 ` / ` curl 92 ` / ` RPC failed`

GitHub's direct connection is unstable. Changing the image (§ 4.2); If you put Clash Verge on, **The TUN mode hijacks git traffic.**, first stop the core process:

```text
sudo pkill -9 -f verge-mihomo
sudo dscacheutil -flushcache
sudo killall -HUP mDNSResponder
```

##### 10.4 `load_tensors: missing tensor 'hc_head_base'`

Forks are not compatible with GGUF. Return to § 9.3 Select the combination.

##### 10.5 `ggml_metal_*` The line doesn't appear at all.`ggml: backend cpu only`

CMake doesn't start Metal. Check it out `build/CMakeCache.txt`:

```text
grep GGML_METAL build/CMakeCache.txt | grep -v "^//"
```

If it is `GGML_METAL:BOOL=OFF`, **Clean up and come back**:

```text
rm -rf build
# 然后重跑 § 7.1 + § 7.2
```

##### 10.6 Linked news `ld: framework 'Metal' not found`

Xcode CLT is incomplete or does not refer to Xcode.app:

```text
sudo xcode-select -s /Applications/Xcode.app/Contents/Developer
xcode-select -p           # 确认
```

##### 10.7 Compilation period `error: 'simdgroup_*' is unavailable`

Metal shader compiler version is too old (macOS <14): This guide requires macOS 26.x; The old system recommended upgrading or deleting Metal4 features:

```text
cmake -S . -B build -G Ninja ... -DGGML_METAL_USE_BF16=OFF
```

##### 10.8 `incompatible mac OS X version` Warning

`GGML_METAL_MACOSX_VERSION_MIN` It's not. Generally ignored; To eliminate:

```text
cmake -S . -B build -G Ninja ... -DGGML_METAL_MACOSX_VERSION_MIN=14.0
```

##### 10.9 ⚠️ `Asserting on type 42 ` / ` mul_mm_id_map0`It's not implemented (FP8 × Metal is not compatible)

**The whole stack**:

```Markdown
common_init_from_params: warming up the model with an empty run
ggml/src/ggml-metal/ggml-metal-device.cpp:876: not implemented
Asserting on type 42
ggml_metal_library_get_pipeline_mul_mm_id_map0 + 0
ggml_metal_op_mul_mat + 1016
...
zsh: abort  ./build/bin/llama-server ...
```

**The root cause**:

- **type 42** = `GGML_TYPE_F8_E4M3`(FP8 E4M3 quantization, native to the NVIDIA H100/H200/B100 tensor type)

- **`mul_mm_id_map0`**= Indirect batch matrix by kernel routed by MoE experts

- In your GGUF **So 365 tensors are `f8_e4m3_b128`** Weighs of 256 experts**The backend of metal doesn't have this kind of quantization. **

**Three backend FP8 matrix implemented**(Search)`F8_E4M3` The source file is obtained from:

|The backend|FP8_E4M3 Implemented|Status|
| --- | --- | --- |
| CPU | quants.c / ops.cpp / ggml-cpu.c |It's complete.|
| CUDA |Quantize / mmvq / convert / common ... 6 files|It's complete.|
| Metal |0 files|It's completely unrealized.|

The back of the metal `mul_mat_id ` List of currently supported quantization types: `F32 / F16 / BF16 / Q1_0 / Q4_0~Q5_1 / Q8_0 / MXFP4 / Q2_K~Q6_K / IQ2_XXS~IQ4_XS`, **Not including F8_E4M3**.

**Why can't it be fixed = nisparks doesn't give priority to Mac** Fork: There have been 20 commits in recent years.`ggml-cuda ` with `server` The target hardware for this fork is the NVIDIA server (FP8 native tensor core) and Apple Silicon is not on the roadmap.

**The solution (as recommended)**:

|Programs|Model|Engine|The workload|Mac speed estimate|
| --- | --- | --- | --- | --- |
|A. Cut back on the antirez/ds4| antirez/deepseek-v4-gguf Q4(153 GiB) | ds4-server |0(Compilation completed)|29.4 t/s measured|
|B. compilation antirez/llama.cpp-deepseek-v4-flash|Same as above| antirez fork |Rebuild (~5 min)|Equivalent to|
|C. -ot expert = CPU to lose the expert CPU| nsparks FP8(145 GiB) | nisparks llama-server |Adjustments|1 to 3 t/s (slow 10 to 30 x)|
|D. and nisparks write the Metal FP8 kernel| nsparks FP8 | nisparks llama-server |Uncontrollable|Unknown|

**Conclusions of Mac users** This guide is a compilation of nisparks.`llama-server ` If you can't run nsparks' FP8 GGUF on macOS, please leave. **Project A**(reference)`ds4-部署指南.md`).

---

#### 11. Keeping commands regularly

##### 11.1 Increased compilation (after modification of source code)

```text
cmake --build build --config Release -j --target llama-server
```

> Ninja automatically increases, only reprogrammed affected `.o`+ re-linking. Small changes to the M3 Ultra usually take 5 to 15 seconds.

##### 11.2 Clean up the build directory

```text
rm -rf build              # 全清，下次需要重跑 § 7.1 配置
cmake --build build --target clean   # 软清，保留 CMakeCache，只删 .o
```

##### 11.3 Re-compilation after branch switching

```text
cd "$WORKSPACE/llama.cpp"
git fetch --depth=1 origin <other-branch>
git checkout <other-branch>

rm -rf build && \
  cmake -S . -B build -G Ninja -DCMAKE_BUILD_TYPE=Release -DGGML_METAL=ON \
        -DGGML_METAL_EMBED_LIBRARY=ON -DGGML_NATIVE=ON && \
  cmake --build build --config Release -j --target llama-server
```

##### 11.4 Draws the latest commit

```text
git pull --depth=1 origin "$(git branch --show-current)"
cmake --build build --config Release -j --target llama-server
```

---

#### Appendix A: Full keyboard script

Save the following as `~/bin/llamacpp-build.sh ` After the execution of the authorization `llamacpp-build.sh` One key pulls the source code + configuration + compilation.

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

#### Appendix B: Compilation options quick check (scenario selected)

|The scene|Increased CMake variables|
| --- | --- |
|Apple Silicon Metal (This is the guide)| -DGGML_METAL=ON -DGGML_METAL_EMBED_LIBRARY=ON -DGGML_NATIVE=ON |
|Apple Silicon is a pure CPU (not metal)| -DGGML_METAL=OFF -DGGML_ACCELERATE=ON -DGGML_BLAS=ON -DGGML_BLAS_VENDOR=Apple |
| CUDA（Linux + NVIDIA） | -DGGML_CUDA=ON -DCMAKE_CUDA_ARCHITECTURES=native |
|Vulkan (cross-platform GPU)| -DGGML_VULKAN=ON |
| OpenCL（Adreno / Mali） | -DGGML_OPENCL=ON |
| HIP / ROCm（AMD GPU） | -DGGML_HIP=ON |
|OpenMP multi-thread CPU| -DGGML_OPENMP=ON |
|Static links: deployment of single files| -DBUILD_SHARED_LIBS=OFF |
|Server enabled SSL|-DLLAMA_SERVER_SSL=ON( dependency OpenSSL)|
|Includes mtmd multi-mode|-DLLAMA_BUILD_TOOLS=ON (default opened)|

---

**Documented version**:v1.1
**Finally updated**:2026-05-13
**Summary of changes**:v1.1 Added § 1 Top Mac × FP8 incompatibility warning § 9.3 Compatibility matrix Added Mac Metal / NVIDIA CUDA column § 10.9 Fault screening Added `Asserting on type 42` Detailed diagnosis and solutions.
**Measured environment**:Mac Studio M3 Ultra / 512 GB / macOS 26.3 / Xcode 26.3 / Apple clang 17 / cmake 4.3.2 / ninja 1.13.2 / uv 0.11.13 / Python 3.12.13
**How to verify**: `llama-server --version` Metal 4 was successfully initialized. nsparks FP8 GGUF crashes on Mac (see section 10.9); General GGUF is loaded with inference correct on Mac.
