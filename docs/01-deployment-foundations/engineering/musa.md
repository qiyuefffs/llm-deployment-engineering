# MUSA：llama.cpp部署适配与加速验证流程

[平台实例矩阵](README.md) · [硬件后端层](../02-capability-layers/01-hardware-backends.md)

## 状态与输入

已检索FlowUs的MUSA与摩尔线程相关资料，当前可读取记录没有完整设备运行证据。本页提供完整工程执行与验收步骤，不填写GPU型号、驱动、性能或“已跑通”结论。实际设备可用后，按下表逐项填入运行记录。

| 必须固定 | 记录内容 |
| --- | --- |
| 设备 | 具体GPU、卡数、物理显存与可用量 |
| 系统 | CPU架构、OS/kernel、驱动、MUSA Toolkit与编译器版本 |
| 引擎 | llama.cpp精确commit、GGML_MUSA支持、CMakeCache与完整构建日志 |
| 模型 | 可公开小GGUF、模型revision、文件名、SHA256、tokenizer/模板 |
| 负载 | 固定prompt、pp/tg、输出预算、线程、上下文、并发、缓存 |

## 1. 驱动与编译工具链

先按该GPU的官方支持表安装配套驱动和Toolkit。设备工具名称按所装版本确认，常见入口为`mthreads-gmi`和`mcc`，不要因命令名字相近套用CUDA包。

```bash
uname -a
lspci -nn
command -v mthreads-gmi
command -v mcc
mthreads-gmi
mcc --version
cmake --version
```

保存设备型号与显存；Toolkit自带最小算例应先完成分配、拷贝与计算。设备可枚举、可分配、可算、模型可执行分别留证。

## 2. 固定源码并构建

```bash
git clone https://github.com/ggml-org/llama.cpp.git
cd llama.cpp
# 检出已经选定并记录的commit后继续
git rev-parse HEAD
rg GGML_MUSA CMakeLists.txt ggml
cmake -S . -B build-musa \
  -DCMAKE_BUILD_TYPE=Release -DGGML_MUSA=ON
cmake --build build-musa --target llama-cli llama-server llama-bench -j 4
./build-musa/bin/llama-cli --version
./build-musa/bin/llama-cli --list-devices
```

若固定提交无该后端选项，先核对分支和官方适配说明，不能把CMake忽略未知变量当作MUSA构建成功。核对编译器、链接库、目标架构与设备枚举日志。

## 3. CPU基线与GPU卸载

模型使用小尺寸、引擎已支持的GGUF；可先复用[CPU演练](../practice/first-service/README.md)中的固定Qwen3-0.6B-Q8_0制品，再在目标设备核查该模型架构支持。将文件放到以下约定位置，校验与模型页面一致的摘要。

```bash
sha256sum /srv/models/Qwen3-0.6B-Q8_0.gguf
./build-musa/bin/llama-bench \
  -m /srv/models/Qwen3-0.6B-Q8_0.gguf -ngl 0 -p 512 -n 128 -r 3
./build-musa/bin/llama-bench \
  -m /srv/models/Qwen3-0.6B-Q8_0.gguf -ngl 99 -p 512 -n 128 -r 3
```

检查实际卸载、MUSA buffer、pp/tg和答案；不能只根据`-ngl99`认定执行在GPU。相同二进制的CPU回退与GPU路线要保持输入和线程可比。

## 4. 服务与API验收

```bash
./build-musa/bin/llama-server \
  -m /srv/models/Qwen3-0.6B-Q8_0.gguf \
  --alias musa-smoke --host 127.0.0.1 --port 8080 \
  -ngl 99 -c 2048 -np 1
```

第二终端执行：

```bash
curl --fail-with-body http://127.0.0.1:8080/health
curl --fail-with-body http://127.0.0.1:8080/v1/models
curl --fail-with-body http://127.0.0.1:8080/v1/chat/completions \
  -H 'Content-Type: application/json' \
  -d '{"model":"musa-smoke","messages":[{"role":"user","content":"计算12乘13，只输出数字。"}],"temperature":0,"max_tokens":128}'
```

验收156、完整正文和结束原因，再检查SSE、超长输入、错误模型、取消与持续健康。功能通过后才进入加速实验。

## 5. 加速优化矩阵

| 实验 | 变量 | 固定条件 | 通过标准 |
| --- | --- | --- | --- |
| 卸载 | ngl0/部分/全层 | 模型、prompt、线程、ctx | 执行位置正确，资源不超预算 |
| batch | b/ub档位 | 其他服务与负载 | pp、tg、峰值、错误同时记录 |
| Attention | 后端明确支持的FA off/on | 同长度和KV dtype | 结果与质量一致，完整保存日志 |
| 量化 | Q8/Q5/Q4 | 同任务/长度/采样 | 容量收益与质量代价分别判断 |
| 并发 | np1/2/4 | 固定长度、足够请求 | TTFT/TPOT/p95和总吞吐符合目标 |

## 6. 交付与回滚

保存环境、模型清单、构建、基线、每组命令、原始结果和最终验收。前台实例Ctrl+C停止，核对进程与端口释放；驱动和库变更保留原包与恢复步骤。没有实际输出的格子保持“待测”，不能填其他GPU数据。
