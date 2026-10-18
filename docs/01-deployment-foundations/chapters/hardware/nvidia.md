# 1.2.1 NVIDIA：从环境检查到CUDA执行

## 本节概览

NVIDIA部署需要同时确认CPU架构、驱动、CUDA工具链、框架和GPU计算能力。本节依据作者RTX4090源码构建与GB10 vLLM工程，先讲检查方法，再用真实错误说明排查顺序。

## 一、先建立环境记录

RTX4090记录使用Ubuntu22.04、32GB主机内存、24GB设备内存与CUDA Toolkit12.9。GB10记录使用Ubuntu24.04 ARM64、128GB与CUDA13。两个环境的CPU架构和设备目标不同，软件包不能直接互换。

```bash
uname -m
nvidia-smi
nvcc --version
ptxas --version
nvidia-smi --query-gpu=name,compute_cap --format=csv
```

`nvidia-smi`中的CUDA字段反映驱动兼容能力，`nvcc`与`ptxas`属于当前工具链，`torch.version.cuda`反映PyTorch构建信息。数字不必完全一致，但组合应受支持。源码扩展还需要核对PyTorch ABI与构建依赖。

如果系统没有`nvcc`，先检查是否真的安装Toolkit，以及PATH指向哪里；不要只凭`nvidia-smi`推断完整编译环境已经存在。

## 二、安装与配置遵循什么顺序

先按操作系统和设备的官方支持准备驱动，重启要求按安装器说明完成；随后准备框架需要的Runtime或Toolkit。已有环境先记录，避免一次同时替换驱动、编译器和框架。

以已经安装在`/usr/local/cuda-12.9`的Toolkit为例，可在当前实验shell设置：

```bash
export CUDA_HOME=/usr/local/cuda-12.9
export PATH="$CUDA_HOME/bin:$PATH"
export LD_LIBRARY_PATH="$CUDA_HOME/lib64:${LD_LIBRARY_PATH:-}"
command -v nvcc
nvcc --version
```

这里先在当前终端验证，成功后再决定是否持久配置。多个Toolkit共存时，记录实际路径，防止构建与运行分别读到不同版本。

## 三、完成一次CUDA框架检查

PyTorch环境可以执行第1章的最小张量计算。llama.cpp路线则进入[构建与服务教程](../frameworks/llama-cpp.md)，使用`-DGGML_CUDA=ON`，通过日志确认设备和实际卸载，再运行小模型。

```bash
cmake -S . -B build-cuda   -DGGML_CUDA=ON -DCMAKE_BUILD_TYPE=Release
cmake --build build-cuda --target llama-server llama-bench llama-cli -j 4
```

先让CMake识别设备目标。需要显式架构时使用本机检查值：原4090记录为89，GB10需要按其实际支持组合核对。编译成功后保存版本与CMakeCache，再做生成。

## 四、实例：找到了nvcc，为什么还在链接时报错？

作者4090记录出现：

```text
No rule to make target '/usr/lib/x86_64-linux-gnu/libcudart.so'
```

错误指向构建缓存引用的库路径。该机器的库实际在Toolkit目录下。此时应检查安装文件和CMake配置，而不是把其他机器的动态库复制过来。

```bash
ls -l /usr/local/cuda-12.9/lib64/libcudart.so*
cmake -S . -B build-cuda-clean   -DGGML_CUDA=ON   -DCMAKE_CUDA_COMPILER=/usr/local/cuda-12.9/bin/nvcc   -DCMAKE_BUILD_TYPE=Release
cmake --build build-cuda-clean --target llama-server -j 4
```

新目录避免旧缓存继续保留错误路径。具体结果以本机配置和构建日志为准；原笔记没有保存可用于本轮完整复建的依赖锁。

## 五、实例：GB10的架构与低精度kernel

GB10工程的vLLM提交`17d87168d`遇到`cvt with .e2m1x2`不支持`sm_121`的错误。它说明框架构建涉及了不适用于该目标的指令路径。原记录曾用12.0目标进行特定尝试，不能把这个值设为所有GB10项目的默认值。

先定位失败kernel、精度和目标，再核对源码修复与CUDA要求。CPU架构正确、设备被识别、普通张量成功，都不足以证明所有低精度路径可用。

## 六、容器与多卡再增加哪些检查

宿主GPU正常而容器看不到设备时，检查NVIDIA Container Toolkit和Docker GPU接入。容器保存用户态环境，仍依赖宿主驱动。完整流程见[环境与容器](../delivery/environment-operations.md)。

多卡先检查`nvidia-smi topo -m`，再验证集合通信。RTX4080不支持NVLink，旧笔记中的桥接建议已修正。双卡总容量也不能直接当作单设备容量，切分与通信需要框架支持。

## 本节完成检查

环境记录能区分驱动、Toolkit和框架；最小计算完成；实际模型使用目标后端；构建与错误能追溯到固定版本。随后进入模型与服务章节。

来源：作者《linux编译llama.cpp-CUDA版本》《DGX Spark适配编译vLLM部署Qwen3.6-35B-A3B》及双卡部署记录，见[文章对应表](../../evidence/chapter-sources.md)。
