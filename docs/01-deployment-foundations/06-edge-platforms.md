# 06 从云端基线迁移到真实端侧

[返回总目录](README.md) · [上一章](05-llama-cpp-practice.md) · [下一章](07-serving-and-scheduling.md)

## 1. 迁移时，保留什么、重新验证什么

可以保留任务样例、验收规则、模型身份、模板与测量口径；必须重新确认二进制、后端、精度、上下文容量、线程、设备卸载与持续性能。A10 上验证的方法可以迁移，A10 上的并发和速度不能直接迁移。

先做一个最小矩阵：目标设备与 OS → 推荐起点后端 → 受支持模型 → 短请求正确性 → 长输入与多轮 → 冷启动 → 长时间负载 → 包装交付。每换后端都重新做质量检查，尤其关注量化、位置编码和回退算子。

端侧还应设置设备可用性目标：推理运行时用户能否正常操作界面；休眠、切后台、插拔电源和磁盘空间不足时如何响应；是否允许后台常驻，如何卸载模型。它们不会出现在一个普通 GPU benchmark 的吞吐表里，却决定产品能否使用。

## 2. Windows PC：二进制、驱动与进程环境

Windows 可从可信的 llama.cpp 发布二进制开始验证，也可使用官方支持的编译工具链。选择 CPU、CUDA、Vulkan、SYCL 等路线前先确认硬件与驱动。原生 Windows 与 WSL 是两个部署环境，设备暴露、文件 I/O、动态库和网络行为要分别记录。

常见问题是下载到不匹配的 CPU 指令集版本、CUDA DLL 来源混乱，或程序实际调用了 CPU 后端。保存 `--version`、`--list-devices`、启动日志和任务期间资源状态。PowerShell 调 HTTP 时可显式使用 `curl.exe`，避免旧版本别名行为造成参数差异。

路径有空格时加引号；二进制目录和模型路径写成明确配置。性能报告记录 Windows 版本、驱动、电源模式、笔记本是否接电、显示器是否占用独显，以及安全软件是否造成模型首次读取延迟。不要为取得 benchmark 数字长期关闭系统保护。

若用 WSL，先核对厂商官方 GPU 支持路线；不要按普通 Linux 主机方式在 WSL 内重复安装一套不适用的内核显示驱动。跨 Windows/WSL 文件系统读取大模型也可能影响冷启动，应分别记录存储位置。

## 3. Apple Silicon：统一内存与 Metal / MLX

llama.cpp 的 Metal 路线通常可直接使用 GGUF；MLX-LM 使用其支持的模型表示与量化机制。两者不能通过改后缀互换模型，也不能只比较同为“4bit”的名称。应匹配原始 revision、任务质量、输入输出条件，再比较体验与资源。

固定源码版本后，可按官方构建文档使用 CMake。以下是 macOS 模板，要求已经具备 Apple 开发工具与 CMake，在 llama.cpp 源码根目录运行：

```bash
cmake -S . -B build-metal -DCMAKE_BUILD_TYPE=Release -DGGML_METAL=ON
cmake --build build-metal --config Release -j 4
./build-metal/bin/llama-server --list-devices
```

先用较小模型和短输入确认 Metal 工作，再扩大容量。统一内存没有“RAM + 同容量 VRAM”可叠加的空间。关注内存压力、压缩内存、swap、系统保留、进程限制，以及其他应用的带宽竞争。不要把设备总内存全部给模型。

便携设备应分别测接电与电池、冷机与持续负载。首次模型读盘/编译、暖启动与复用缓存后的运行要分开。采样功率时写清是 SoC、设备还是插座口径，不把某个域的功耗当作整机能耗。

## 4. Android：先 CPU 最小链路，再考虑加速

Android 需要同时处理 ABI、API level、NDK、C++ Runtime、应用沙箱、文件权限、生命周期与系统内存回收。能在桌面 Linux ARM 上运行，不代表直接复制到 Android 就能执行。

推荐顺序是先按官方 [Android 文档](https://github.com/ggml-org/llama.cpp/blob/master/docs/android.md)构建 arm64 CPU 程序，用小模型验证；再测试 Vulkan 或厂商后端；最后集成 JNI/应用。`adb` 只在用户开启并授权调试后使用，不需要为基线测试获取 root。

以下为 **主机构建模板**，不是手机上的安装命令。要求已设置指向实际 SDK/NDK 的 `ANDROID_NDK`，并固定源码 commit；工具选项以该 commit 文档为准。

```bash
: "${ANDROID_NDK:?请设置已安装 Android NDK 的目录}"
cmake -S . -B build-android \
  -DCMAKE_TOOLCHAIN_FILE="$ANDROID_NDK/build/cmake/android.toolchain.cmake" \
  -DANDROID_ABI=arm64-v8a -DANDROID_PLATFORM=android-28 \
  -DGGML_NATIVE=OFF -DGGML_OPENMP=OFF -DGGML_LLAMAFILE=OFF \
  -DLLAMA_OPENSSL=OFF
cmake --build build-android --config Release -j 4
```

这是可移植 CPU 起点，不包含 GPU/NPU 加速配置。检查产物 ABI、动态库依赖与目标 API；若依赖 `libc++_shared.so` 或后端库，需按 NDK 与许可证要求一起打包。应用内部的模型路径和命令行临时目录也不是同一路径。

GPU 验证要看驱动、Vulkan 能力、模型算子和量化 kernel 是否支持，不能因为手机能玩 3D 游戏就推断能高效运行某个 LLM。厂商 NPU 路线还可能需要专用 SDK、受支持模型和图编译流程，未验证前不要对 27B 模型作容量承诺。

移动端验收至少覆盖切后台、取消请求、内存压力、连续对话、屏幕亮灭、电量与温度。首次几十秒的速度可能随后因温控下降；持续性能和完成任务的能耗比冷机峰值更有意义。

## 5. Jetson 与其他嵌入式 NVIDIA

Jetson 通常使用 ARM64 与特定 JetPack 软件栈，驱动、CUDA、系统库相互关联。云端 x86 CUDA 容器不能直接推导为可用；架构与版本都需要匹配。统一内存与有限散热进一步改变容量和优化目标。

先记录 Jetson 型号、JetPack、功耗模式、内存与散热，再按所用框架官方路线构建。可用设备工具如 `tegrastats` 观察系统状态；具体字段按平台版本解释。不要为了短期数据擅自超出设备额定功耗或修改系统保护。

若模型与摄像头/音频共享内存和算力，应在整个应用运行时测量。视觉编码器、解码器和预处理可能形成峰值；纯文本 benchmark 留出的余量不足以证明多模态应用稳定。

## 6. Intel 与其他 NPU：不要跨路线混用制品

Intel 的 SYCL GPU、OpenVINO CPU/GPU、OpenVINO GenAI NPU，以及 llama.cpp 特定版本的 OpenVINO 后端，是相关但不同的路径。某条路径可执行某种 GGUF，并不保证另一条路径可读取同一文件。

以 OpenVINO GenAI NPU 为例，官方特定版本文档对模型导出、权重压缩、group size、硬件代际与上下文设置有要求，并存在静态形状和分块输入等实现约束。应完整固定 OpenVINO、GenAI、转换工具、模型与驱动版本，不只安装一个最新版包。资料入口见 [13](13-glossary-and-references.md)。

适配 NPU 时重点验证四件事：模型图是否能编译；哪些算子回退 CPU；Prefill 与 Decode 的状态是否能高效衔接；预编译上下文/形状对短输入和长输入分别有什么代价。只有算子编译成功，仍无法证明整条服务链路能效达标。

其他嵌入式 NPU 也应沿厂商的精确芯片/SDK 路线验证。不要用一个“国产 NPU 通用安装命令”替代兼容性核对。

## 7. 跨平台公平对比

对比要固定模型来源、任务集、模板、采样条件、输入与实际输出 token。无法用同一权重表示时，应把它作为“部署方案比较”，同时报告质量差异，不只称为硬件速度比较。

| 测试 | 观察内容 | 端侧意义 |
| --- | --- | --- |
| 冷启动/暖启动 | 读盘、后端初始化、图编译、首请求 | 用户首次使用等待 |
| 单请求/目标并发 | 首个可见答案、TPOT、总完成时间 | 交互体验 |
| 长输入/多轮 | 内存、KV、停止行为、质量 | 实际容量边界 |
| 持续负载 | 温度、时钟、功率、延迟趋势 | 温控与稳定性 |
| 取消/休眠/恢复 | 资源释放、服务状态和重试 | 应用生命周期 |

**本章产物：**目标端侧的独立兼容记录与性能/质量报告。没有设备实测的格子保持“未测”，不借用云端数字补齐。
