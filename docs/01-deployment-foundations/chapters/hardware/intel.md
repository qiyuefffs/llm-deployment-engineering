# 1.2.3 Intel：GPU、NPU与执行制品

## 本节概览

一台Intel设备可能同时提供CPU、GPU和NPU。它们使用的执行插件、支持算子和制品条件不同。本节依据16GB Lunar Lake工程说明怎样选择和验证路线，完整IR运行在框架章展开。

## 一、三条常见路线

llama.cpp Vulkan使用Vulkan驱动执行受支持GGUF；SYCL路线依赖oneAPI与相应运行时；OpenVINO GenAI使用配套IR和设备插件。XPU框架路线也需要核对特定模型和kernel。

| 路线 | 主要制品 | 先检查 |
| --- | --- | --- |
| Vulkan | GGUF | 设备、驱动、shader与卸载 |
| SYCL | GGUF | oneAPI、Level Zero与框架构建 |
| OpenVINO GenAI | IR与配套文件 | Pipeline、插件、模型图和精度 |

同一个“OpenVINO”名称也不能省略执行器。llama.cpp OpenVINO＋GGUF，与GenAI＋IR，是不同链路。

## 二、环境采集

作者测试设备为Core Ultra7 256V、Arc Lunar Lake、16GB统一内存，Ubuntu24.04.4；Mesa26.1.4、oneAPI2026.1.0、OpenVINO2026.2.1、GenAI/Tokenizers2026.2.1.0。

```bash
vulkaninfo --summary
sycl-ls
icpx --version
```

这些命令用于已经安装对应软件栈的环境，保留实际设备与版本。使用OpenVINO时再枚举插件：

```python
import openvino as ov
core = ov.Core()
print(ov.__version__)
for device in core.available_devices:
    print(device, core.get_property(device, 'FULL_DEVICE_NAME'))
```

枚举只证明设备可发现，下一步应加载匹配IR并真正生成token。

## 三、先选择一个可完成任务的入口

原工程中，GenAI GPU完成了Qwen3.5-9B的INT4和INT8短生成；NPU INT4在编译阶段失败，INT8编译420秒后超时退出124。这里可以使用已通过的GPU路线继续测试完整答案，同时保留NPU失败条件。

另一条llama.cpp OpenVINO尝试可以构建和枚举，却在GGUF建图遇到CPY/cache_r等问题。它不能被GenAI GPU成功覆盖。

## 四、16GB资源怎样判断

Vulkan/SYCL记录采用GPU23层、CPU10层，属于混合执行。应同步观察主机内存、swap和设备分配。IR路线的内存组织和计时不同，需要单独建立基线。

原记录中Vulkan引擎生成11.54±0.13token/s，SYCL为10.22±0.19；OpenVINO INT4管线21.1599token/s。后者使用不同制品和计时边界，不能直接相除宣称框架加速。

## 五、进入完整操作

按[OpenVINO IR完整运行](../frameworks/openvino.md)准备独立环境、固定revision、下载文件、枚举GPU、预热、生成并保存指标。该教程把CPU/GPU/NPU目标写清楚，默认沿用原记录的GPU入口。

完成后再准备业务长度和质量集。原19输入/128输出记录在思考阶段到达上限，因此完整答案质量仍需单独验收。

来源：作者《Qwen3.5-9B Intel OpenVINO平台推理对比报告》与Intel视觉记录，见[文章对应表](../../evidence/chapter-sources.md)。
