# 第5层：工程交付层

[总目录](../SUMMARY.md) · [环境/启停/回滚](../chapters/delivery/environment-operations.md) · [API/监控/验收](../chapters/delivery/api-monitoring.md)

## 5.1 这一层解决什么问题？

| 问题 | 工程要求 | 检查 |
| --- | --- | --- |
| 能否复建 | 固定模型、依赖、镜像/源码和输入 | 干净环境冷启动 |
| 能否服务 | 稳定模型ID、协议、功能和错误 | 健康、模型列表、正常/流式/异常/取消 |
| 能否观测 | 请求与资源使用同run-id/时间轴 | 指标、日志、逐请求明细对应 |
| 能否恢复 | 只停止目标实例，保留有效旧版 | 停止、端口/设备释放、回滚与回归 |
| 能否验收 | 功能、质量、性能、资源各有阈值 | 通过/失败/未测逐项填写 |

## 5.2 交付能力地图

```text
环境封装：Docker / uv或Conda / systemd / 按需求Kubernetes
服务接口：OpenAI协议 / 模型路由 / SSE / 认证与限流
可观测性：引擎metrics / Prometheus / 资源采样 / 日志
压力验证：引擎基准 / HTTP负载 / 质量集 / 稳态与故障恢复
运行文档：安装 / 配置 / 启动 / 停止 / 验收 / 回滚
```

| 子项 | 必须记录 | 常见缺陷 |
| --- | --- | --- |
| 容器 | image tag＋digest、设备、模型挂载、端口、IPC/共享内存 | 只有latest、宿主有GPU但容器不可访问 |
| Python环境 | 解释器、锁、torch/Runtime、扩展与导入路径 | pip装到另一环境、源码目录遮蔽 |
| 进程管理 | 目标PID或实例名、ready、退出码、日志 | pkill宽泛匹配、端口与设备残留 |
| SSE | 代理buffer、客户端流读取、结束、取消、超时 | role事件当正文、片段当token、缓冲假流式 |
| metrics | running/waiting、KV、请求延迟/错误、吞吐 | 不同版本metric名、单位与窗口混用 |
| 资源 | VRAM/RAM/RSS、swap、温度/功耗、每rank | UMA重叠相加、只看利用率 |
| 回滚 | 旧镜像/依赖/模型/模板/配置成套保留 | 只回滚Python不回滚原生扩展或模板 |

### 四类验收

1. 功能：输入处理、完整输出、API、SSE、取消和异常。
2. 质量：固定题集、结构字段、视觉/音频内容；与原精度/旧版对照。
3. 性能：实际token、SLO、并发/到达率、资源峰值、稳态。
4. 运维：冷启动、停止、重启、日志、升级/回滚与恢复。

Intel全NPU TTS性能达标但内容错误，因此回滚；Kokoro CPU实时性通过而RSS目标失败，因此总体不能只写“通过”。对应[完整工程记录](../engineering/intel-arc-npu.md)。

## 5.3 每个项目必须沉淀 7 个结果

| 交付项 | 文件 / 内容 | 审核问题 |
| --- | --- | --- |
| 1.硬件环境 | environment.json/txt、设备/驱动/Runtime/拓扑/容量 | 具体在哪套设备执行 |
| 2.模型信息 | manifest、revision、SHA256、模板、量化/processor | 使用哪份制品，文件是否完整 |
| 3.框架选择 | 版本/commit/digest、kernel、构建与兼容范围 | 为什么可执行，替代路线是什么 |
| 4.部署方案 | 安装、启动、健康、请求、停止、恢复 | 是否有完整执行顺序 |
| 5.参数配置 | final-command、配置、环境变量、有效日志 | 运行时实际用了什么 |
| 6.压测结果 | inputs、requests、responses、metrics、resource、summary | 数字能否从原始结果核算 |
| 7.问题与优化结论 | 基线、变更、失败、回滚、限制和待测 | 解决了什么，在哪些条件成立 |

结果目录以run-id区分。升级前保留旧组合，升级后重复相同输入与SLO检查；没有验证的功能标“未测”。模板：[适配记录](../templates/adaptation-record.md)、[实验记录](../templates/experiment-record.md)、[项目复盘](../04-project-review.md)。
