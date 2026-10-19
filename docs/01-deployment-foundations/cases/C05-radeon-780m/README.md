---
id: C05
title: "AMD Radeon 780M：Windows HIP运行库、Ollama与模型适配"
type: case
volume: cases
layer: 1
platform: "AMD"
device: "Radeon 780M"
status: historical
source_ids: [R18, R19, R20]
updated: 2026-10-19
summary: "技术标签：gfx1103 / Windows / HIP SDK / rocBLAS"
---

# AMD Radeon 780M：Windows HIP运行库、Ollama与模型适配

[工程实例索引](../README.md) · [知识体系总目录](../../SUMMARY.md)

技术标签：`gfx1103 / Windows / HIP SDK / rocBLAS`

## 结论

历史路线是 Radeon 780M / gfx1103 上用 Windows HIP SDK、配套社区
rocBLAS 库和 Ollama 分支运行模型。R18 指向 Ollama 分支 v0.5.1；
原文没有可复核的完整速度表，本章不新增性能数字。

## 适用边界

这是指定 Windows、SDK、社区 DLL 和分支的适配流程，不等于所有当前
Ollama/ROCm 版本都需要替换库。驱动能识别 GPU 不表示运行库已含 gfx1103 kernel。

## 环境与制品

| 项目 | 配置 |
| --- | --- |
| 硬件 | Ryzen7 8845HS / Radeon780M，gfx1103 |
| 系统路线 | Windows AMD Software＋HIP SDK＋社区rocBLAS库＋Ollama分支 |
| 模型 | 原Llama3.1 8B；其他模型与参数见完整记录 |
| 适配点 | 驱动识别≠运行库有对应gfx kernel；DLL搜索路径与版本要一致 |

## 执行路径

1. 记录驱动、HIP SDK版本和安装目录。社区运行库不等于AMD对所有780M组合的官方支持，先保存当前`library`与`rocblas.dll`的可恢复副本。
2. 按原文指定release准备gfx1103库，替换目标版本的运行库，避免把不同HIP SDK的DLL混用。检查进程实际加载的DLL路径，而不是仅看PATH包含了某个目录。
3. 使用原Ollama分支，在第一终端`ollama serve`，第二终端执行`ollama run llama3.1:8b`。原文出现`llama3.1 8b`拼写，实际tag应按所用版本核对。
4. 查看服务日志的GPU发现、buffer与卸载比例，用`ollama ps`及任务管理器核对。再调用`/api/generate`或对应OpenAI入口保存真实响应。

### 原项目如何替换库和启动

R18 在 HIP 目录将原 `library` 改为 `librarybak`，将 `rocblas.dll`
改为 `rocblas.dllbak`，再放入配套社区库。必须保留成对备份，不能混用不同
SDK 的 DLL。重启服务后检查进程实际加载的 DLL 路径，PATH 有目录不代表
该进程已经用上正确版本。

两个终端分别运行：

```text
ollama serve
ollama run llama3.1:8b
```

模型 tag 的冒号按 R20 客户端中的 `llama3.1:8b` 纠正；R18 的空格写法
不能直接作为同一个模型标识。启动后核对日志中的设备发现和模型卸载，
再做文本完整性和流式结束验收。

### 流式测试不能数空格当 token

R20 请求 `/api/generate`，逐行解析 JSON 的 `response` 字段并显示文本。
它使用 `len(output.split())` 估算 token；对中文和 tokenizer 都不准确，
不能把客户端打印的估算速度当作引擎 benchmark。

复测应保存实际服务返回的计数和 duration；若所用版本缺字段，就明确
标注缺失或估算，并保留原始响应。先测冷加载，再测模型常驻时的同一 prompt，
避免把下载和加载混进持续生成速度。

## 结果

以同一模型、prompt、num_predict和缓存状态比较CPU回退与GPU路径。调节上下文与活动模型数，观察UMA总预算、预填充速度、生成速度及冷加载。若替换运行库后失败，恢复原DLL而不是继续叠加多个社区补丁。

原文章有实际部署过程，未保存同口径完整吞吐表，因此本实例保留步骤和功能证据，不添加速度。

| 环节 | 记录状态 | 可得结论 |
| --- | --- | --- |
| HIP/社区库安装 | 有步骤和截图引用 | 有历史适配流程 |
| Ollama 启动与 Llama 调用 | 有命令和代码 | 有功能操作材料 |
| 流式计时 | 空白估算 token | 不能作为精确 tok/s |
| CPU/GPU 严格对照 | 未保存完整结果 | 不能计算卸载加速比 |

## 失败与修订

R20 的 Python 原样例还包含 `//` 行注释，这是 Python 语法错误；移植时
应改成 Python 注释。不能因后端曾部署成功就认为客户端粘贴后可以直接运行。
框架建议中的 FastAPI 封装属于方案，不是已完成接口交付。

## 证据

- [R18 完整技术正文](../../evidence/sources/R18.md)
- [R19 完整技术正文](../../evidence/sources/R19.md)
- [R20 完整技术正文](../../evidence/sources/R20.md)

## 未验证

当前驱动与 SDK 的兼容组合、真实 token 统计、逐请求响应、量化质量和
长期内存压力尚未独立复测。原截图附件不公开，也不据截图补填具体性能。

数据来源与边界见[证据使用说明](../../meta/evidence-policy.md)。
