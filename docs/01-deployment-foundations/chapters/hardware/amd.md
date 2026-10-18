# 1.2.2 AMD：gfx、运行库与共享内存

## 本节概览

AMD适配先确认实际GPU目标，再确认系统、ROCm/HIP、算子库和框架后端。作者资料同时包含Windows集显社区路线和Linux395多机工程，本节将两条路线分开说明。

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

修复后的设备可见总量约120000MiB。该修复与特定内核、DKMS及驱动有关，本书保留原因与检查路径，不把系统级修改写成通用一键优化。

## 五、五机RPC的后续验证

容量恢复后，原工程先以小上下文测试。Kimi生成约8.2token/s，另有Qwen冒烟约21.3token/s。没有单机基线与长期API记录，因此这些数字说明短测观察，不能计算五机加速比。

多机应按单机设备→通信→小模型→目标短输入→长输入→服务负载逐级推进。完整切分、TCP/RDMA判断与控制面排查见[多设备专题](../performance/parallelism.md)。

## 六、完成检查

保存实际gfx、系统与Runtime、框架commit、模型、后端分配、功能和负载。统一内存同时记录系统可用内存与swap；增加上下文和并发前先确认Runtime可用量。

来源：作者780M适配、AMD ROCm编译与395五机HIP RPC文章，见[文章对应表](../../evidence/chapter-sources.md)。
