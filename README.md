# 端侧大模型部署适配与推理优化

从实际部署记录出发，按 **准备环境 → 准备模型 → 跑通服务 → 测试基线 → 优化排障 → 交付维护** 组织知识。面向需要把模型部署到电脑、边缘工作站和 GPU 服务器上的工程人员。

| 内容 | 入口 | 包含什么 |
| --- | --- | --- |
| 工程基础知识体系 | [13 章目录](docs/01-deployment-foundations/README.md) · [阅读指南](docs/01-deployment-foundations/00-engineering-handbook.md) | 概念解释、操作命令、实际记录、结果解读、检查方法 |
| 独立实战 Case | [Case 目录](cases/README.md) | A10 上的 llama.cpp 部署与 Flash Attention 对照 |
| 实验和交付记录 | [适配模板](docs/01-deployment-foundations/templates/adaptation-record.md) · [实验模板](docs/01-deployment-foundations/templates/experiment-record.md) · [项目复盘](templates/deployment-review.md) | 环境、参数、输入、结果、限制与恢复步骤 |

![大模型部署工程阅读路线](docs/01-deployment-foundations/assets/deployment-workflow.png)

图注：13 章按操作顺序排列。先通过环境、模型和功能检查，再建立基线、开展对照实验，最后整理交付材料。[查看矢量图](docs/01-deployment-foundations/assets/deployment-workflow.svg)。

## 知识体系中的实际实例

| 平台与记录 | 主要学习内容 |
| --- | --- |
| A10 24GB、llama.cpp、27B Q4 | 模型校验、固定版本构建、API、FA 对照、结果报告 |
| DGX Spark GB10、vLLM | ARM64 与新架构编译、FP8、200 请求压力、MTP 与 DFlash 对照条件 |
| Intel Core Ultra / Arc、OpenVINO | INT4/INT8 制品、Vulkan/SYCL 路线、NPU 编译失败 |
| Apple Silicon、Metal/MLX/oMLX | 模型类型、文本与视觉能力、并发吞吐与单请求延迟 |
| AMD 集显、ROCm/HIP、多机 RPC | gfx 识别、运行时内存上限、分布式容量与通信 |
| 双 RTX 4080、vLLM Docker | 模型挂载、双卡拓扑、并发与调度配置 |

实例取自作者的 FlowUs 部署技术笔记及仓库原有材料。正文区分历史实测、命令模板、教学估算与待验证项；技术数据以脱敏转录形式提供。来源及可复查范围见[证据说明](docs/01-deployment-foundations/evidence/README.md)。

## 获取与使用

```bash
git clone https://github.com/qiyuefffs/llm-serving-diagnosis.git
cd llm-serving-diagnosis
```

初次学习从 [01 明确部署目标](docs/01-deployment-foundations/01-engineering-and-request.md) 开始。只想核对已有公开记录，可在仓库根目录运行：

```bash
python docs/01-deployment-foundations/examples/verify_records.py
```

这条命令仅核对输入哈希、记录数量和指标计算，不下载模型、不运行 GPU 推理。需要实际部署时，先按章节确认系统与设备前提，再运行对应命令；不同平台不能共用所有安装步骤。

## 仓库结构

```text
llm-serving-diagnosis/
├── docs/01-deployment-foundations/
│   ├── 01-...md ～ 13-...md     按工程流程编排的正文
│   ├── assets/                 阅读路线图与原始知识框架图
│   ├── evidence/               可公开的技术测量转录与来源说明
│   ├── examples/               离线核对与设备通信示例
│   └── templates/              适配和实验记录模板
├── cases/llama-cpp-flash-attention/
│                               原有独立 Case：教程、脚本、输入、截图、汇总
├── templates/                  项目复盘模板
└── tools/                      图片生成脚本
```

## 版本与证据边界

知识章节更新于 **2026-10-18**。本轮完成笔记整理、命令核对、文档检查和离线算术核查，没有重新运行各平台的 GPU 实验。原有 Case 的完整成功构建日志、第二个干净实例复建记录和完整公开逐请求证据仍待补充。其他平台记录也按各章说明保留材料缺口。

原始知识框架图保留在[知识目录](docs/01-deployment-foundations/README.md)中。格式分类、后端支持和性能口径按当前正文解释；版本变化后应在目标设备重新验证。
