# 1.2.4 Apple：Metal、MLX与功能验证

## 本节概览

Apple Silicon的CPU和GPU共享物理内存，但框架、制品和任务仍有明确支持条件。本节把GGUF＋Metal、MLX与服务插件分开说明，并结合作者的实际失败记录解释验收边界。

## 一、先区分模型路线

llama.cpp使用GGUF与Metal kernel。MLX-LM使用对应文本模型实现，MLX-VLM还涉及视觉processor与encoder。oMLX等服务层在引擎上提供模型发现、调度与接口；vllm-metal属于另一套插件组合。

这些路线不能只靠相同模型名称互换文件。先检查模型制品和当前版本支持，再连接应用。

## 二、检查系统与开发工具

```bash
sw_vers
uname -m
xcode-select -p
clang --version
cmake --version
```

源码构建需要Xcode命令行工具与相应CMake。准备好后，固定llama.cpp提交，以独立目录构建Metal与Accelerate：

```bash
cmake -S . -B build-metal   -DGGML_METAL=ON -DGGML_ACCELERATE=ON   -DCMAKE_BUILD_TYPE=Release
cmake --build build-metal --target llama-cli llama-server llama-bench -j 4
./build-metal/bin/llama-server --version
```

小模型准备与服务请求复用[llama.cpp教程](../frameworks/llama-cpp.md)。检查Metal设备与实际层分配，再看生成内容和结束原因。

## 三、统一内存需要怎样观察

模型、KV、运行时、应用和系统共享容量。先测加载与短输入，再增加长度与并发；同步看系统内存压力、swap与持续速度。短时间能够生成，不保证长时间运行没有换页或温度影响。

不以取消系统保护或无上限分配作为默认步骤。应先建立预算，在可接受资源内比较模型与配置。

## 四、实例：引擎编译通过，特定模型仍失败

作者M3 Ultra512GB、macOS26.3记录使用特殊llama.cpp分支commit9d36408。后续执行特定FP4/FP8 GGUF时出现`Asserting on type 42`，涉及尚未实现的Metal MoE路径。

这项结论限定到该分支、制品和功能。排查先看张量类型与kernel，不把编译通过当成模型通过，也不扩大为所有Metal低精度模型失败。

## 五、实例：文本成功，视觉尚未接通

另一份记录使用Python3.12.13、vllm-metal0.2.0、vLLM0.21.0+cpu、MLX0.31.2。文本请求可用，图片请求报多模态encoder尚未接通。

因此文本、图片、工具调用和结构化输出应分别记录。增加内存和上下文不能补齐缺失的encoder，应该选择支持所需任务的实现或版本。

## 六、oMLX模型发现与服务检查

原操作记录中的`--model-dir`指向模型父目录，服务从中发现模型。启动后先看模型列表，确认应用使用的别名，再检查普通与流式请求。路径正确后才进入并发。

oMLX的历史并发结果放在[压测专题](../performance/benchmarking.md)，此处只确认模型发现与功能链路。缓存状态、环境和样本量限制会在结果旁说明。

来源：作者Mac Metal、vllm-metal、MLX及oMLX工程文章，见[文章对应表](../../evidence/chapter-sources.md)。
