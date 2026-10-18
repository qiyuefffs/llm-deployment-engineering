# 第一部分：整体知识体系地图

[总目录](SUMMARY.md) · [平台实例矩阵](engineering/README.md)

## 1. 一条主线

```text
模型到服务的完整交付链路
```

| 工程模块 | 输入 | 核心操作 | 输出 / 检查关口 |
| --- | --- | --- | --- |
| 1.硬件后端适配 | 设备、OS、驱动、框架 | 识别arch/gfx、配套Runtime、构建、算子和通信 | 真正完成设备计算；目标模型支持范围 |
| 2.模型格式与量化 | 原始模型、引擎支持、资源 | 固定revision、转换、量化、模板与校验 | 可加载制品、哈希、质量基线 |
| 3.推理框架选型 | 制品、设备、API与任务 | kernel、KV/调度、启动、协议验证 | 可调用且完整生成的服务 |
| 4.显存与KV Cache | 模型结构、dtype、长度与活动序列 | 预算权重、KV、状态、图、工作区 | 启动/执行/负载峰值与安全余量 |
| 5.性能压测与调优 | 固定输入、SLO、基线 | 受控到达率/并发、资源采样、逐项对照 | 原始明细、统计、质量与结论 |
| 6.多卡/多节点 | 单机基线、拓扑、通信库 | TP/PP/DP/EP/RPC、rank和设备映射 | 容量变化、通信成本、速度与恢复 |
| 7.工程服务化与交付 | 已验证运行组合 | API/SSE、监控、限流、环境、回滚 | 七项交付材料及执行入口 |

### 1.1 任务约束先于参数

```yaml
task: text_generation
input: public-prompts.jsonl
model_revision: REQUIRED
input_tokens: 2048
max_output_tokens: 128
load:
  mode: controlled_concurrency
  concurrency: [1, 2, 4]
  requests_per_group: 200
acceptance:
  quality: REQUIRED
  ttft_p95_ms: DEFINE_BEFORE_TEST
  e2e_p99_ms: DEFINE_BEFORE_TEST
  error_rate: DEFINE_BEFORE_TEST
  memory_peak: DEFINE_BEFORE_TEST
```

这是任务模板，不是已运行数据。性能阈值先确定，测量后不能为“达标”修改门槛。长输入、长输出、突发与稳定流量分别建负载。

## 2. 五层能力模型

```text
第1层 硬件后端：设备 / 驱动 / Runtime / 编译 / 通信
第2层 模型制品：架构 / 格式 / 数值表示 / 模板 / 校验
第3层 推理框架：加载 / KV管理 / 调度 / kernel / API
第4层 性能优化：容量 / 负载 / 指标 / 瓶颈 / 实验
第5层 工程交付：环境 / 接口 / 监控 / 验收 / 回滚
```

| 层间接口 | 必须传递的材料 |
| --- | --- |
| 硬件→制品 | 支持的架构、dtype/量化kernel、可用容量 |
| 制品→引擎 | 完整模型清单、tokenizer/模板、量化与processor配置 |
| 引擎→压测 | 最终命令、有效参数、健康/功能/异常结果 |
| 压测→优化 | 逐请求数据、资源采样、失败样例、SLO差距 |
| 优化→交付 | 经验收的参数、收益与代价、已知边界、恢复入口 |

### 2.1 问题到章节的路由

| 问题 | 第一检查层 | 证据 |
| --- | --- | --- |
| GPU可见但kernel失败 | 第1层 | arch、实际kernel、工具链和首个异常 |
| 张量/分片/模板错误 | 第2层 | 清单、索引、GGUF元数据、tokenizer/模板 |
| 无正文、SSE/取消异常 | 第3层 | 原始响应、结束原因、API与引擎日志 |
| OOM、TTFT/TPOT、并发差 | 第4层 | 内存分项、排队、每请求时间与资源 |
| 升级后失败、无法复建 | 第5层 | 运行组合、digest、导入路径、回滚记录 |

### 2.2 工程实例入口

[各GPU实例矩阵](engineering/README.md)按具体设备进入完整适配和优化记录。共同机制在五层主框架定义，平台差异、命令与数据在各设备原记录中展开。
