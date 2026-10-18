# 大模型部署知识体系

![大模型部署适配知识体系框架](docs/01-deployment-foundations/assets/edge-llm-deployment-framework-original.png)

面向部署工程师，介绍从硬件与运行时、模型与量化、推理引擎，到性能优化和服务交付的通用知识。先理解每层软件负责什么、一次推理怎样执行，再进入平台配置与实际工程实例。

## 从这里开始

| 内容 | 入口 | 说明 |
| --- | --- | --- |
| **最新知识体系** | [大模型部署知识体系](docs/01-deployment-foundations/README.md) | 硬件与软件栈入门、五层知识框架和技术专题 |
| 硬件与运行时入门 | [CPU/GPU/NPU与软件调用关系](docs/01-deployment-foundations/02-capability-layers/01-hardware-backends.md) | 从驱动、运行时、计算库理解部署环境 |
| 完整目录 | [五层能力目录](docs/01-deployment-foundations/SUMMARY.md) | 按硬件、模型、框架、性能和交付查看全部章节 |
| 硬件工程实例 | [GPU / NPU / Apple 实例矩阵](docs/01-deployment-foundations/engineering/README.md) | 每个平台按适配、基线、优化、结果和限制组织 |
| 独立 Case | [Case 目录](cases/README.md) | Case 的教程、脚本、输入、截图和结果单独保存 |
| CPU 顺序演练 | [完整服务实跑](docs/01-deployment-foundations/practice/first-service/README.md) | 从模型校验到 API、压测和验收的可公开演练 |

## 内容范围

- 五层工程主线：硬件与运行时、模型格式与量化、推理框架、显存与性能、工程交付。
- 平台基础：[NVIDIA与CUDA](docs/01-deployment-foundations/chapters/hardware/nvidia.md)、[AMD与ROCm](docs/01-deployment-foundations/chapters/hardware/amd.md)、[Mac/Metal/MLX](docs/01-deployment-foundations/chapters/hardware/apple.md)、[Intel与OpenVINO](docs/01-deployment-foundations/chapters/hardware/intel.md)、[昇腾与CANN](docs/01-deployment-foundations/chapters/hardware/ascend.md)。
- 每个硬件入口都记录环境、模型制品、启动参数、基线、优化实验、性能数据、失败原因和验收边界。
- FlowUs 中整理出的公开技术记录保留在对应实例中；私人路径、账号、凭据和内部地址已移除。

## 获取仓库

```bash
git clone https://github.com/qiyuefffs/llm-serving-diagnosis.git
cd llm-serving-diagnosis
```

源码和 Markdown 页面适合直接在 GitHub 阅读。`docs/01-deployment-foundations/book.html` 是可下载后离线检索的单文件版本；模型权重、缓存和运行日志不随仓库提交。

## 资料状态

CPU 顺序演练有公开运行结果。GPU、NPU 和多机记录按原始测试条件保留，并在页面中标明历史测试、缺失证据和未验证项目；这些数字不能直接视为当前设备的保证值。MUSA 页面提供适配与验证流程，实测结果待补充。

更新时间：**2026-10-18**
