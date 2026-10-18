# 大模型部署适配与推理优化

![大模型部署适配知识体系框架](docs/01-deployment-foundations/assets/edge-llm-deployment-framework-original.png)

面向模型部署、推理优化和多硬件适配工程。沿用原六部分、五层能力及节编号，按组件、参数、执行阶段和检查证据组织。每个设备入口包含部署适配、基线、优化过程及对应FlowUs完整技术记录，共保留50份技术文章。

**工程入口：[知识体系与首页框架图](docs/01-deployment-foundations/README.md) · [五层完整目录](docs/01-deployment-foundations/SUMMARY.md) · [各GPU完整部署优化实例](docs/01-deployment-foundations/engineering/README.md) · [离线检索页面](docs/01-deployment-foundations/book.html)**

| 内容 | 阅读入口 | 用途 |
| --- | --- | --- |
| 基础知识体系 | [完整目录](docs/01-deployment-foundations/SUMMARY.md) | 总章与详细操作分层，按模型到服务的链路阅读 |
| 本机CPU完整演练 | [顺序教程与实际文件](docs/01-deployment-foundations/practice/first-service/README.md) | 下载校验、部署、API、压测、失败记录和验收 |
| 独立实战 Case | [Case 目录](cases/README.md) | 完整实战教程、脚本、截图与结果，按项目单独保存 |
| 工程记录模板 | [适配记录](docs/01-deployment-foundations/templates/adaptation-record.md) · [实验记录](docs/01-deployment-foundations/templates/experiment-record.md) | 记录设备、版本、输入、参数、结果和验收 |

## 知识体系怎样组织

1. **整体知识体系地图**：先理解模型到服务的主线及各模块的关系。
2. **五层能力详细框架**：硬件后端、模型格式与量化、推理框架、显存与性能、工程交付。每层都有独立章节与细分主题。
3. **核心概念解释库**：沿用原来的十个主题，按“一句话解释 → 工程解释 → 工程分析”理解机制。
4. **项目复盘模板**：保存背景、方案、问题、排查、优化和结果。
5. **个人知识库目录设计**：保留原来的八个主题目录，作为对应正文的检索入口。
6. **故障排查速查表与附录**：按失败阶段查问题，集中查询命令和资料。

实际参考包括AMD集显与多机HIP RPC、DGX Spark编译和服务、Intel OpenVINO/Vulkan/SYCL、Mac Metal/MLX/oMLX、双卡vLLM与昇腾适配记录。[文章与章节对应表](docs/01-deployment-foundations/evidence/chapter-sources.md)说明各章来源，[历史数据](docs/01-deployment-foundations/evidence/README.md)集中保存条件与限制。

## 获取代码

```bash
git clone https://github.com/qiyuefffs/llm-serving-diagnosis.git
cd llm-serving-diagnosis
```

知识体系可以直接阅读。部署命令按目标系统、固定版本和模型制品执行；历史测量不保证在另一台设备得到相同数值。独立 Case 的运行文件位于各自目录。

本轮在Windows CPU上实际执行小模型完整链路，并公开12个结果文件；功能题2/3通过，畸形JSON返回500，总验收未通过。历史GPU/NPU工程没有重跑，操作说明与历史结果分别标明。

离线阅读版需下载后用浏览器打开，GitHub文件页主要用于查看源码；下载整个仓库可同时获得代码和结果。更新日期：**2026-10-18**。
