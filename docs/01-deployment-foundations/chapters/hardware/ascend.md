---
id: T27
title: "1.2.5 昇腾：芯片、CANN与框架插件"
type: tutorial
volume: book
layer: 1
platform: "Ascend"
device: "general"
status: historical
source_ids: []
updated: 2026-10-19
summary: "昇腾是面向AI计算的加速器平台，常在工具中使用NPU设备名称。不同芯片面向的场景、设备内存、支持精度、算子和并行能力存在差异，不能把某个310P实例推广到所有昇腾设备。"
---

# 1.2.5 昇腾：芯片、CANN与框架插件

[总目录](../../SUMMARY.md) · [硬件与运行时总览](../../02-capability-layers/01-hardware-backends.md)

## 硬件基础

昇腾是面向AI计算的加速器平台，常在工具中使用NPU设备名称。不同芯片面向的场景、设备内存、支持精度、算子和并行能力存在差异，不能把某个310P实例推广到所有昇腾设备。

硬件选型先看精确型号和资源，再确认模型架构、目标精度、输入长度与并发是否有配套实现。设备峰值算力只描述特定条件下的能力，实际LLM速度还取决于kernel、KV、图编译、内存和通信。

## CANN和上层框架的关系

| 组件 | 职责 | 部署时确认什么 |
| --- | --- | --- |
| 驱动与固件 | 设备管理、底层执行和硬件配套 | 芯片与系统支持、设备节点、版本关系 |
| CANN | 包含运行时、算子、编译及开发工具的AI计算软件栈 | 与芯片、框架插件和模型实现配套 |
| AscendCL及配套API | 内存、执行与模型/算子调用等接口 | 程序链接的接口与运行库版本 |
| 算子库与图编译 | 实现或编译矩阵、attention、量化等计算 | 模型图、shape、dtype和实际kernel覆盖 |
| HCCL | 设备间集合通信 | 多卡rank、拓扑、网络与并行策略 |
| torch_npu | PyTorch面向昇腾的适配层 | PyTorch、插件、CANN与设备组合 |
| vLLM Ascend / MindIE | 推理调度、模型执行和服务能力 | 当前芯片、模型、精度和版本支持 |

```text
应用 → 推理引擎/框架插件 → CANN运行时与算子 → 驱动/固件 → 昇腾设备
```

安装CANN后还要选择支持目标模型的执行框架。容器中的插件、算子与用户态库也必须能与宿主设备和驱动配合，镜像名称中包含“ascend”不构成完整兼容结论。

## 部署路线怎样确定

先查设备、CANN与上层框架的配套矩阵，然后验证小计算和单请求。需要的算子或精度没有实现时，优先选择受支持的模型、制品或版本；单纯增加内存不会补齐算子。

单请求正确后再增加上下文、活动序列和卡数。图编译/预热、通信和服务排队要分别测量，才能判断首token慢、逐token慢或吞吐不足的原因。

基础资料：[CANN](https://www.hiascend.com/en/software/cann) · [vLLM Ascend](https://github.com/vllm-project/vllm-ascend)。

## 部署操作与工程参考

后续使用310P3记录说明具体容器、模型、接口和压测检查。完整材料见[310P3部署与排错记录](../../cases/C12-ascend-310p/README.md)。

## 一、固定已知组合

原笔记使用`quay.io/ascend/vllm-ascend:v0.10.0rc1-310p`，模型为Qwen3-32B，双设备、float16。镜像标签属于历史组合，当前环境重做应先核对该芯片与版本的配套说明，并记录镜像digest。

```bash
npu-smi info
```

继续记录驱动、固件、CANN、Python、PyTorch/torch_npu及vLLM Ascend版本。设备名称相近不能直接复用另一代的支持结论。

## 二、容器先验证设备可访问

需要按当前镜像文档提供设备节点和驱动库，再挂载模型。模型目录优先只读，端口与共享内存明确配置。原笔记使用过高权限、host网络与较广挂载，交付时应根据实际需要缩小范围。

先在容器中执行设备检查与小计算，再运行目标模型。这样模型加载失败时，能够区分容器接入、插件初始化和权重问题。

## 三、启动目标模型

下面是原服务的公开路径节选，前提是配套容器环境已经通过；长度与内存预算需按当前设备重新验收。

```bash
python -m vllm.entrypoints.openai.api_server   --model /srv/models/Qwen3-32B   --served-model-name Qwen3-32B   --host 127.0.0.1 --port 8000   --tensor-parallel-size 2 --dtype float16   --max-model-len 32768 --gpu-memory-utilization 0.95   --distributed-executor-backend mp --enforce-eager   --block-size 64 --swap-space 16
```

不要把历史高预算作为首次冒烟起点。先用资源可承受的长度验证，随后逐步恢复目标配置。模型需要远程代码时单独审阅与固定，不默认加入所有命令。

## 四、接口与压测检查

服务ready后，先检查模型列表，再用匹配的chat或completion端点提交请求。提示字段必须与端点一致：`messages`用于chat，`prompt`用于completion。

原压测曾设置`parallel=10`而`number=1`，最终只有1个请求。记录约14336输出token、3120.88秒、4.5936token/s。它是一次长输出观察，无法证明十路同时服务，也无法提供可靠尾延迟。

重测时应给各并发组足够样本，保留实际请求与输出，长度、采样和缓存一致。具体方法见[压测教程](../performance/benchmarking.md)。

## 五、导入位置与环境变量

原笔记提到在源码目录运行与在工作目录运行出现差异。遇到这类问题时，检查`python`路径、模块来源和环境变量，防止当前目录遮蔽已安装包。V1/V0等开关按该固定版本支持情况设置，记录最终生效值。

## 六、完成检查

设备、插件和目标模型分别有证据；单请求、功能和负载分别验收；依赖与镜像可追溯。当前资料没有保存完整的干净复建链，因此本节将历史命令与已知结果保留为工程参考。

来源：作者《华为昇腾310P3推理Qwen3-32B》《昇腾310P3部署Qwen3-32B benchmark记录》，见[文章对应表](../../evidence/chapter-sources.md)。
