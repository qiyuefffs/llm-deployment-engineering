# 1.2.2 AMD GPU与ROCm软件栈

[总目录](../../SUMMARY.md) · [硬件与运行时总览](../../02-capability-layers/01-hardware-backends.md)

## 硬件基础

AMD的大模型部署主要涉及Radeon独立显卡、Instinct数据中心加速卡，以及Ryzen处理器中的集成GPU。它们的内存组织、架构和软件支持范围不同，不能只看“AMD显卡”这一个标签。

| 硬件类别 | 典型特点 | 部署重点 |
| --- | --- | --- |
| Radeon消费/专业独显 | 通常有独立显存，面向PC或工作站 | 型号与OS支持、显存、gfx目标、kernel覆盖 |
| Instinct加速卡 | 面向计算与数据中心，部分采用HBM和xGMI互联 | ROCm配套、矩阵计算、带宽、RCCL与拓扑 |
| Ryzen集成GPU/APU | CPU与GPU使用系统内存，容量受设备预算约束 | 共享内存带宽、可分配量、驱动、系统余量 |

`gfx`是AMD GPU的代码目标标识。RDNA/CDNA等架构家族与精确gfx目标影响指令和预编译kernel；同系列产品也应读取实际设备信息。CUDA的`sm_XX`不能转换成一个通用的AMD编号。

## ROCm与HIP是什么关系

ROCm是一整套GPU计算软件平台，包括运行时、编译器、数学库、通信库和分析工具。HIP是其中常用的C++编程接口和kernel语言，用来申请设备内存、提交计算和进行同步；`hipcc`是编译驱动工具。

```text
模型/推理引擎 → PyTorch ROCm或HIP后端
             → HIP运行时 ＋ 计算库
             → 底层运行时/设备驱动 → AMD GPU
```

| 组件 | 职责 | 常见使用位置 |
| --- | --- | --- |
| amdgpu与相关设备接口 | Linux下的设备、内存和计算接入 | 主机驱动、容器设备访问；其他OS按对应驱动 |
| ROCr/HSA Runtime | 支持平台上的底层执行与内存机制 | HIP等上层运行时的设备执行基础 |
| HIP / hipcc | GPU编程API、kernel语言和编译入口 | llama.cpp HIP、PyTorch ROCm及源码扩展 |
| rocBLAS / hipBLAS / hipBLASLt | BLAS矩阵运算、API接口与灵活GEMM | 模型线性层、受支持精度与布局 |
| MIOpen | 深度学习算子库 | 框架所需神经网络算子，不代表所有LLM算子都由它实现 |
| RCCL | 多GPU、多节点集合通信 | TP等并行执行中的AllReduce、AllGather等 |
| 专用kernel与编译工具 | attention、MoE、量化和融合计算 | 由框架、配套库或项目实现，覆盖范围随版本变化 |

HIP支持源码层面的可移植编程；已有CUDA二进制不会因为安装了ROCm就自动在AMD设备上运行。PyTorch ROCm仍沿用`torch.cuda`等接口名称，包的构建信息中则可检查`torch.version.hip`。

## HIP、Vulkan与平台支持怎样选

HIP路线使用ROCm/HIP及配套计算库；Vulkan路线通过Vulkan驱动与对应shader执行。二者是不同后端，Vulkan不要求先安装完整ROCm，但需要引擎实现该后端以及相应驱动能力。

先查精确GPU、OS、ROCm/HIP与框架支持矩阵，再选择后端。Linux、Windows与WSL的驱动、库、框架和设备覆盖不能视为完全相同；社区补丁也应标明来源与适用版本。

对于集成GPU，扩大可分配内存并不会增加内存带宽。模型虽然能加载，如果持续换页、CPU争用严重或某精度没有高效kernel，速度仍可能较低。量化和后端选择要同时比较容量、速度与输出质量。

基础资料：[ROCm概览](https://rocm.docs.amd.com/en/latest/what-is-rocm.html) · [HIP](https://rocm.docs.amd.com/projects/HIP/en/latest/) · [Radeon/Ryzen支持](https://rocm.docs.amd.com/projects/radeon-ryzen/en/latest/) · [RCCL](https://rocm.docs.amd.com/projects/rccl/en/latest/)。

## 部署操作与工程参考

先确认设备目标和软件栈，再进行单机生成、内存预算和负载测试。以下保留Windows集显与Linux多机的不同操作路径。

实例：[780M Windows HIP](../../engineering/amd-780m.md) · [8060S Q4/BF16优化](../../engineering/amd-8060s.md) · [395五机RPC](../../engineering/amd-395-rpc.md) · [W7900多卡多机](../../engineering/amd-w7900.md)。

## 一、理解软件层次

内核驱动负责设备与内存接口；HIP提供执行接口和编译能力；rocBLAS、hipBLASLt等库实现矩阵与相关计算；RCCL负责集合通信。编译某个库不等于重新安装了整个驱动。

```bash
uname -m
uname -r
rocminfo > rocminfo.txt
hipconfig --full > hipconfig.txt 2>&1
hipcc --version
```

`gfx`是设备代码目标。780M记录涉及gfx1103，395/8060S有设备证据的记录使用gfx1151。产品名称相近也要重新检查，不能照抄另一台机器的架构变量。

## 二、Linux路线：先单机，再多机

在受支持的ROCm环境中，先用框架小算子或小模型验证。llama.cpp HIP构建使用独立目录：

```bash
cmake -S . -B build-hip   -DGGML_HIP=ON -DAMDGPU_TARGETS=gfx1151   -DCMAKE_BUILD_TYPE=Release
cmake --build build-hip --target llama-server llama-bench llama-cli -j 4
```

此处gfx1151只对应395实例。完整源码和小模型步骤见[llama.cpp教程](../frameworks/llama-cpp.md)。如果CMake提示变量未使用，先核对该提交的选项；启动后确认后端和设备分配。

需要比较Vulkan时另建`build-vulkan`，保留同一模型、卸载、线程和长度。两个后端依赖不同，性能差异应由实际任务验证。

## 三、Windows路线：运行库按版本隔离

780M旧工程使用HIP SDK、社区适配库和Ollama分支。它提供了真实兼容经验，但旧DLL不能随意混入新程序，也不能自动推广到890M等其他设备。

先检查设备与驱动，再核对当前官方或社区发行说明。把程序、配套库和日志放在独立版本目录，保留上一套可以恢复的组合。

```powershell
Get-CimInstance Win32_VideoController | Select-Object Name, DriverVersion
Get-ChildItem -LiteralPath '.\bin' -Filter '*.dll' | Select-Object Name, Length
```

随后启动服务，观察日志中的后端和设备，再做短请求与业务请求。任务管理器的GPU曲线只能辅助判断，输出和执行日志仍需保存。

## 四、实例：395物理内存够大，为什么还会分配失败？

五机HIP RPC记录使用Ryzen AI Max+395/8060S，ROCm7.2.1、HIP7.2.53211-e1a6bc5663、内核6.17.0-35，llama.cpp b9557。某阶段设备只报告63215MiB，一次87013675008字节的分配失败。

排查发现，GTT请求125829120000字节，但TTM实际约66286690304字节。需要比较物理容量、驱动预算与Runtime可见量，而不是只调大模型上下文。

修复后的设备可见总量约120000MiB。该修复与特定内核、DKMS及驱动有关，本体系保留原因与检查路径，不把系统级修改写成通用一键优化。

## 五、五机RPC的后续验证

容量恢复后，原工程先以小上下文测试。Kimi生成约8.2token/s，另有Qwen冒烟约21.3token/s。没有单机基线与长期API记录，因此这些数字说明短测观察，不能计算五机加速比。

多机应按单机设备→通信→小模型→目标短输入→长输入→服务负载逐级推进。完整切分、TCP/RDMA判断与控制面排查见[多设备专题](../performance/parallelism.md)。

## 六、完整操作：把395五机HIP RPC记录展开

前面的实例说明了故障原因，这一节沿真实工程顺序把环境、修复、构建、分发、加载与观察连起来。五台设备分别记为`NODE_A`到`NODE_E`；A运行主程序并参与本地计算，B—E运行RPC。模型分片保存在A，远端接收框架分配的张量，不需要每台再保存一整套350G模型。

### 6.1 环境与目标

| 项目 | 原工程配置 |
| --- | --- |
| 单机CPU/APU | Ryzen AI Max+395 |
| GPU/目标 | Radeon8060S / gfx1151 |
| 单机内存 | 128GB级LPDDR5 |
| 系统 | Ubuntu24.04，6.17.0-35-generic |
| ROCm | 7.2.1 |
| HIP | 7.2.53211-e1a6bc5663 |
| llama.cpp | b9557-0f7fada56 |
| 互连 | USB4/Thunderbolt直连桥接，TCP RPC |
| 目标模型 | Kimi-K2.5-Q2 GGUF，目录约350G |

先做单机记录，再看五机是否一致。CPU型号相同不代表运行中的内核模块相同；该故障恰好发生在相同Runtime、不同内核驱动模块的设备之间。

```bash
uname -r
hipcc --version
dpkg-query -W rocm-core hip-runtime-amd hsa-rocr
modinfo amdgpu
ls -l /dev/kfd /dev/dri/renderD*
id
cat /proc/cmdline
```

记录`modinfo`的filename、version和vermagic，核对是否来自当前内核目录或`updates/dkms`。设备权限不足先修复当前用户对设备的访问，避免一遇到设备不可见就重装全部软件栈。

### 6.2 BIOS、GTT与TTM怎样对应

这批设备BIOS的`iGPU Memory Size`最低是2GB。运行日志出现`2048M of VRAM memory ready`与`120000M of GTT memory ready`，说明预留显存较小仍能走通共享内存路线。没有必要为追求另一份教程的512MB而判断此设备不兼容。

原工程采用以下内核参数：

```text
ttm.pages_limit=30720000
ttm.page_pool_size=30720000
amdgpu.gttsize=120000
amdgpu.cwsr_enable=0
```

这是该内核/驱动组合的系统调优记录，应先检查当前支持文档和已有参数，再在可恢复启动配置下变更。`pages_limit`使用页数；在4KiB页条件下，30720000页对应125829120000字节，与原GTT请求值一致。页大小应以`getconf PAGESIZE`确认。GTT预算也不是新增物理内存，系统与应用仍要共享实际容量。

真正的异常证据是：

```text
GTT size has been set as 125829120000
but TTM size has been set as 66286690304, this is unusual
```

再往执行器看，`llama-cli --list-devices`只报告63215MiB。随后一个87013675008字节、约81.04GiB的RPC缓冲分配失败。此时调小HTTP输出上限无法解决权重缓冲放不下的问题，先修Runtime可分配量。

### 6.3 原工程如何修复

故障节点加载的是`amdgpu-dkms 1:6.16.13.30300100-2303411.24.04`，模块来自：

```text
/lib/modules/6.17.0-35-generic/updates/dkms/amdgpu.ko.zst
```

正常节点使用同内核自带模块。原工程先检查包移除预览，再只移除冲突DKMS包，保留Runtime与固件，重启后核对实际生效模块：

```bash
sudo apt-get -s remove amdgpu-dkms
# 确认变更范围后，原工程执行：
sudo apt-get remove amdgpu-dkms
sudo reboot
```

这段用于说明已完成的修复，不能推广为“所有AMD设备都应该卸载DKMS”。新设备如依赖DKMS提供支持，应采用匹配的内核/驱动组合。重启后的验收包括模块来自`kernel/drivers/gpu/drm/amd/amdgpu/`、不再出现TTM钳制告警，以及HIP执行器报告120000MiB。三项要相互印证。

原日志一度出现free大于total的不一致值，因此容量判断不能取两个字段中较大的那个。先核对驱动记账、执行器可见总量与一次实际分配，再推进大模型。

### 6.4 构建同一套HIP＋RPC程序

在已固定到`0f7fada56`的llama.cpp源码中：

```bash
cmake -S . -B build-hip-rpc \
  -DCMAKE_BUILD_TYPE=Release \
  -DGGML_HIP=ON -DGGML_RPC=ON \
  -DGGML_HIP_ROCWMMA_FATTN=ON \
  -DAMDGPU_TARGETS=gfx1151
cmake --build build-hip-rpc --config Release -j 4
rg 'GGML_HIP|GGML_RPC|ROCWMMA|AMDGPU_TARGETS' build-hip-rpc/CMakeCache.txt
./build-hip-rpc/bin/llama-cli --version
./build-hip-rpc/bin/llama-cli --list-devices
```

原构建自动发现libibverbs并启用了`GGML_RPC_RDMA`。这只能证明编译了相关能力，本次USB4桥接实际走TCP；不能把构建开关当成RDMA运行证据。是否使用某条传输路径，需要运行日志和接口计数共同确认。

分发时把同一build的`bin`目录和所需共享库作为一个整体保存，记录摘要；不要只复制rpc-server可执行文件，再从另一版本目录补库。每个远端节点先运行`--version`与设备枚举，再启动服务。

```bash
tar -C build-hip-rpc -czf llama-hip-rpc-bin.tgz bin
sha256sum llama-hip-rpc-bin.tgz
```

复制、解压到B—E后，每个节点在自己的`bin`目录前台运行。`NODE_B_ADDRESS`应配置为该节点用于实验的受控接口，C—E同理：

```bash
export LD_LIBRARY_PATH="$PWD:${LD_LIBRARY_PATH:-}"
./rpc-server --host "$NODE_B_ADDRESS" -p 50053 -c
```

RPC端点需要限制在可信测试网络；不要照抄原笔记的全接口监听并暴露到公网。`-c`对应该版本RPC缓存选项，保留其存储路径与首次/再次加载条件，测量时不要把热缓存加载与首次传输混比。

### 6.5 先查设备，再跑小模型

在A配置四个远端地址，设备列表中应有本地ROCm0和四个RPC设备：

```bash
export RPC_ENDPOINTS="${NODE_B_ADDRESS}:50053,${NODE_C_ADDRESS}:50053,${NODE_D_ADDRESS}:50053,${NODE_E_ADDRESS}:50053"
./llama-cli --rpc "$RPC_ENDPOINTS" --list-devices
```

五个设备都达到该工程确认的120000MiB之后，再测试Qwen3.5-9B小模型：

```bash
./llama-cli -m "$QWEN_GGUF" -ngl 999 --rpc "$RPC_ENDPOINTS" \
  -c 512 -b 64 -ub 16 -fa off \
  --single-turn --simple-io --no-display-prompt \
  -p '你好，请用一句话介绍你自己。' -n 8
```

原记录prompt40.3token/s、generation21.3token/s。这是短冒烟，输出预算只有8，主要确认计算路径与连接；不能充当长答案质量集或高并发服务验收。

### 6.6 加载Kimi：分配比例为何不均匀

指定所有GGUF分片中的首文件，先核对分片数量、大小与摘要。文件名由实际下载制品决定，不在教程里杜撰一个分片名。主机变量`KIMI_GGUF_FIRST`指向首分片：

```bash
./llama-cli -m "$KIMI_GGUF_FIRST" -ngl 999 \
  --split-mode layer \
  --tensor-split 0.143,0.21425,0.21425,0.21425,0.21425 \
  --rpc "$RPC_ENDPOINTS" --no-mmap \
  -c 512 -b 32 -ub 8 -fa off \
  --single-turn --simple-io --no-display-prompt \
  -p '你好，请用一句话介绍你自己。' -n 8
```

五个比例相加为1。A除了本地计算，还读入约350G分片、调度RPC并运行系统，所以保留更大余量。比例需要按实际设备枚举顺序核对，它不是对整机物理内存的硬隔离，也不保证每个缓冲恰好按相同比例切开。

原配置使用`--no-mmap`，这属于已验证组合；不能据此概括成所有大模型关闭mmap更省内存。文件映射、页缓存、加载缓冲和后端复制方式不同，应在同一版本上测加载峰值与耗时。

### 6.7 十几分钟加载怎样判断仍有进展

首次加载包含主机读盘、RPC传输与远端大张量分配。原工程的读盘观察依次为101、147、174、236、306、358GB。它们反映进程I/O累计趋势，不能用作精确模型百分比，也不能保证缓存条件下`read_bytes`总与文件大小相同。

```bash
ps -p "$LLAMA_PID" -o pid,stat,etime,%cpu,%mem,rss,vsz,nlwp
cat "/proc/$LLAMA_PID/io"
ss -tinp
free -h
```

如果读入计数、连接bytes_sent/bytes_acked仍变化，且目标节点内存在增长，通常仍在推进。按layer分段传输时，可能某台接收完再轮到下一台。只有一条连接忙并不等于另外三台掉线。相反，长期无I/O进展、重传持续增加、远端进程消失或已有分配错误，需要保存当时状态后定位。

原加载阶段主机约123GiB总内存、81GiB已用、41GiB可用，swap为0；进程退出后约8.6GiB已用、114GiB可用。该组数据是阶段快照，用来说明加载与退出行为，不代表整个运行期间没有更高峰值。

### 6.8 结果、下一步与回退

| 项目 | 原实测 |
| --- | --- |
| Kimi小上下文prompt | 19.3token/s |
| Kimi小上下文generation | 8.2token/s |
| Qwen小模型prompt/generation | 40.3 / 21.3token/s |
| 成功范围 | 五机HIP RPC加载、短上下文、短输出 |

原文还给出ctx32768、FA on的服务建议，但缺相应结果。这部分应作为后续试验：从ctx4096开始，保持已验证切分，再逐项增加上下文、batch、ubatch和FA。失败时按最近改动回退，不同时改变所有开关。五机容量扩展成功，与五机是否比单机更快，是两项不同结论。

## 七、W7900八卡：容器、模型格式与OpenAI接口要对齐

另一组工程使用W7900×8，每卡48GB，镜像`ghcr.io/embeddedllm/vllm-rocm:v0.8.2-18ed313`，部署DeepSeek-R1 AWQ INT4。它采用vLLM/RCCL路径，与前面的llama.cpp RPC不同。

容器先挂入`/dev/kfd`与`/dev/dri`，核对video/render访问，再在容器内验证设备。模型与结果分别挂到`/srv/models`、`/srv/results`。原`--ipc=host`表示共用宿主IPC命名空间，不能再把`--shm-size=384g`解释为已分配384GB共享内存，更不是显存扩容。

原关键服务预算如下：TP8、ctx4096、seqs8、batched2048、memory0.95、eager、AWQ、BF16计算dtype。0.95为较激进的历史配置，新运行先做余量检查。原笔记调用了普通`api_server`后又请求OpenAI路径，本体系统一为OpenAI入口：

```bash
python -m vllm.entrypoints.openai.api_server \
  --model /srv/models/DeepSeek-R1-AWQ \
  --served-model-name deepseek-r1-awq \
  --host 127.0.0.1 --port 8001 \
  --tensor-parallel-size 8 \
  --max-model-len 4096 --max-num-seqs 8 \
  --max-num-batched-tokens 2048 \
  --gpu-memory-utilization 0.95 \
  --quantization awq --dtype bfloat16 --enforce-eager
```

模型目录需要符合该版本AWQ布局支持，卡数乘显存仅用于粗估，仍要核对每rank权重、KV与通信缓冲。原笔记没有完整吞吐成绩，本节保留部署参数和检查方法。

旧环境的`HSA_OVERRIDE_GFX_VERSION=11.0.0`、禁用某attention后端等属于兼容尝试。先确认设备实际gfx和支持矩阵，不把架构伪装、关闭P2P或关闭SDMA写成通用默认优化。

## 八、AMD故障如何从原记录提炼成判断方法

| 现象 | 有效的下一步 | 常见误判 |
| --- | --- | --- |
| 系统内存多、HIP分配仍失败 | 模块路径、TTM/GTT、Runtime总量、实际分配 | 只看物理容量 |
| safetensors文件很多但单rank仍OOM | 看TP/PP实际加载与每rank内存 | 把磁盘分片当成计算切分 |
| page fault | 查看首条内核/Runtime错误及访问上下文 | 直接定性为OOM |
| 容器看到设备却生成失败 | 模型算子、量化kernel与通信 | 设备枚举即全部兼容 |
| 多节点Ray alive | 继续测集合通信和模型分片 | 控制面成功即推理成功 |
| Vulkan曾跑过另一模型 | 对当前模型重新做功能与计时 | 将另一模型速度作为本模型保证 |

CUDA专用诊断变量不能不加判断搬到ROCm。改动通信或内存相关环境变量时，记录原值、适用版本和回退办法，并在同一负载复测；一个可以绕过故障的设置也可能降低最终性能。

## 九、完成检查

保存实际gfx、系统与Runtime、框架commit、模型、后端分配、功能和负载。统一内存同时记录系统可用内存与swap；增加上下文和并发前先确认Runtime可用量。

来源：作者780M适配、AMD ROCm编译与395五机HIP RPC文章，见[文章对应表](../../evidence/chapter-sources.md)。
