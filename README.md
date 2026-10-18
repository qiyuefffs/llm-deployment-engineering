# 大模型部署适配与推理优化

面向模型部署、推理优化和多硬件适配工程，按作者原有的“一条主线、七个模块、五层能力”组织知识，并用实际部署记录说明操作、结果和限制。

| 内容 | 阅读入口 | 用途 |
| --- | --- | --- |
| 基础知识体系 | [完整目录](docs/01-deployment-foundations/README.md) | 按原知识框架学习硬件、模型、框架、性能和交付 |
| 独立实战 Case | [Case 目录](cases/README.md) | 完整实战教程、脚本、截图与结果，按项目单独保存 |
| 工程记录模板 | [适配记录](docs/01-deployment-foundations/templates/adaptation-record.md) · [实验记录](docs/01-deployment-foundations/templates/experiment-record.md) | 记录设备、版本、输入、参数、结果和验收 |

![大模型部署适配知识地图](docs/01-deployment-foundations/assets/deployment-workflow.png)

## 知识体系怎样组织

1. **整体知识体系地图**：先理解模型到服务的主线及各模块的关系。
2. **五层能力详细框架**：硬件后端、模型格式与量化、推理框架、显存与性能、工程交付。每层都有独立章节与细分主题。
3. **核心概念解释库**：按“一句话解释 → 工程解释 → 如何验证”查阅常见概念。
4. **项目复盘模板**：保存背景、方案、问题、排查、优化和结果。
5. **个人知识库目录设计**：把项目、概念、故障和实验分别维护，再建立关联。
6. **故障排查速查表与附录**：按失败阶段查问题，集中查询命令和资料。

实际参考包括 AMD 集显与多机 HIP RPC、DGX Spark 编译和服务、Intel OpenVINO/Vulkan/SYCL、Mac Metal/MLX/oMLX、双卡 vLLM 与昇腾适配记录。实例只在对应知识点出现，完整参数和测量转录集中在[来源与数据](docs/01-deployment-foundations/evidence/README.md)。

## 获取代码

```bash
git clone https://github.com/qiyuefffs/llm-serving-diagnosis.git
cd llm-serving-diagnosis
```

知识体系可以直接阅读。部署命令按目标系统、固定版本和模型制品执行；历史测量不保证在另一台设备得到相同数值。独立 Case 的运行文件位于各自目录。

更新日期：**2026-10-18**。本轮整理工程笔记并完成本机文档、脚本语法和历史数据核算，没有重跑笔记中的 GPU/NPU 实验。公开内容不含私人知识库链接、内部地址、凭据或私人输入。
