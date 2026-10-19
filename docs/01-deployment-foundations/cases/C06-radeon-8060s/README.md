---
id: C06
title: "AMD Radeon 8060S：Vulkan全层卸载、Q4与BF16优化对照"
type: case
volume: cases
layer: 1
platform: "AMD"
device: "Radeon 8060S"
status: historical
source_ids: [R21, R22]
updated: 2026-10-19
summary: "技术标签：Ryzen AI Max+395 / gfx1151 / UMA / Vulkan"
---

# AMD Radeon 8060S：Vulkan全层卸载、Q4与BF16优化对照

[工程实例索引](../README.md) · [知识体系总目录](../../SUMMARY.md)

技术标签：`Ryzen AI Max+395 / gfx1151 / UMA / Vulkan`

## 结论

- Q4 路线的 CPU 基线为 22.9 token/s，口径为原记录中的引擎 decode 单请求观察。
- 同一 Q4 制品改为 Vulkan 全层卸载后为 47.2 token/s，CPU→GPU 观察比值约 2.06 倍。
- 恢复较小 ctx 并调整 batch、ubatch 与线程后为 58.4 token/s，相对 GPU 初版约 1.24 倍。
- BF16 基础配置约 10.8 token/s；增大工作区后为 10.1 token/s，compute buffer 从 1172MiB 增至 2312MiB。
- 上述结果均为组合观察，缺误差条和完整质量对照，不能作为其他模型或任意 Vulkan 设备的保证值。

## 适用边界

| 项目 | 边界 |
| --- | --- |
| 设备 | Ryzen AI Max+395，Radeon 8060S/gfx1151；统一内存设备 |
| 系统 | Ubuntu24.04.4、Kernel6.17.0-19、Mesa25.2.8、ROCm7.2.0 |
| 模型 | Qwen3.6-35B-A3B；Q4_K_M 与 BF16 两条制品路线 |
| 后端 | llama.cpp Vulkan；结论不外推到 HIP 或其他 Vulkan 驱动组合 |
| 负载 | 原记录的单请求 decode 与参数组合观察；不证明高并发容量 |

## 环境与制品

| 项目 | 记录 |
| --- | --- |
| 设备 | Ryzen AI Max+395，16核32线程；Radeon8060S/gfx1151 |
| 系统 | Ubuntu24.04.4、Kernel6.17.0-19、Mesa25.2.8、ROCm7.2.0 |
| 主路线 | llama.cpp Vulkan；Qwen3.6-35B-A3B Q4_K_M约20.60GiB |
| 对照 | BF16约64.60GiB；同系列MoE，256专家、激活8个 |

原环境表同时写“系统内存30GB”和“GPU可用约110GB”，口径不一致。它可能混用了当前系统可见量与UMA分配，但原文没有完整证据；复建必须以`free -h`、BIOS与驱动实际可分配量重新记录，不能当作30GB物理内存容纳65GB模型。

## 执行路径

1. 完成 Vulkan 编译与设备枚举，固定 GGUF 摘要、程序 commit、RADV 和 Mesa 版本。
2. 保持模型与输入相同，先以 `-ngl 0` 获得 CPU 基线，再以 `-ngl 99` 检查实际 `offloaded 41/41` 与 GPU buffer。
3. 恢复原 ctx32768 配置，再逐步改为 ctx16384、batch4096、ubatch1024、threads16/threads-batch32、np1。
4. 每组保存启动命令、模型加载预算、prompt/eval 时间和资源峰值；不同时修改质量题集。
5. API 检查使用同一个模型别名，保存 usage 与 finish_reason；引擎 eval 速度与 HTTP 墙钟吞吐分别记录。

### 原Q4服务命令与加载检查点

R21最终配置如下，路径统一为公开约定位置；这是一组参数组合，不表示每个
开关都已经分别证明有效。

```bash
LD_LIBRARY_PATH=/srv/llm/llamaCPP \
/srv/llm/llamaCPP/llama-server \
  --model /srv/llm/models/Qwen3.6-35B-A3B-GGUF/Qwen3.6-35B-A3B-UD-Q4_K_M.gguf \
  --host 0.0.0.0 --port 8080 --ctx-size 16384 --n-gpu-layers 99 \
  --parallel 1 --threads 16 --threads-batch 32 \
  --ubatch-size 1024 --batch-size 4096 --cache-ram 0 --poll 50 --mlock
```

日志需确认实际卸载41/41层，并分别核对权重20583 MiB、CPU映射515 MiB、
KV320 MiB、循环状态63 MiB和compute1172 MiB。权重文件大小与运行总预算
不是同一个量，不能只按GGUF体积判断还能增加多少上下文。

### 性能复测怎样保持归因

原历史从CPU、GPU初版到参数组合逐步变化，缺逐项消融。复测时保存原始
prompt、输出、采样和热状态，恢复一套基线，再只改变ctx或batch等一项；
逐请求保存prompt/eval timing及输出完整性。这个新复测方案不补写成已经
存在的历史测量，也不将cache-ram、poll或mlock分别冠以确定的加速倍数。

## 结果

| 阶段 | 配置变化 | decode token/s |
| --- | --- | --- |
| CPU基线 | GPU层0 | 22.9 |
| Vulkan卸载 | GPU层99，原ctx32K | 47.2 |
| 参数组合 | ctx16K、batch4096、threads-batch32 | 58.4 |
| 后续组合 | cache-ram0、mlock、poll50 | 58.3 |
| BF16基础 | 约64.60GiB、原预算 | 10.8 |
| BF16增大工作区 | ctx8K、ubatch2048、batch8192、threads-batch64 | 10.1 |

Q4的CPU→GPU观察比值约2.06；GPU初版→参数组合约1.24。每组同时变更多个条件，保留为组合观察，未提供误差条和质量对照。BF16加大batch没有改善decode，compute buffer从1172MiB增至2312MiB；不是参数越大越快。

表中速度沿用原记录的单请求引擎观察，不作为 HTTP 并发吞吐。Q4 与 BF16 的模型体积、工作区和量化收益必须分开解释。

## 失败与修订

- MoE每步不必读取所有专家，不能用65GB文件体积假定每token读取65GB。Roofline需按实际数据流和有效带宽计算。
- 原文关于“到达带宽极限”“所有SSM的Flash Attention无效”等表述范围过大。本次保留测量，结论限于固定模型、后端和已测配置。
- `--cache-ram 0`控制相应版本的主机prompt缓存，不等于关闭所有KV或必然节省GPU带宽；`--mlock`防止换出，不能凭启用就宣称加速。
- 原“Q4比BF16快5.8倍”使用圆整数，且缺同任务质量与完整计时；不作为无损量化结论。

## 证据

- [R21 完整技术正文](../../evidence/sources/R21.md)
- [R22 完整技术正文](../../evidence/sources/R22.md)
- [指标口径](../../meta/metrics.md)与[已知冲突](../../meta/known-conflicts.md)

## 未验证

- 原环境缺少可核对的物理内存、UMA 可分配量与完整资源采样。
- Q4 与 BF16 未提供同任务质量集、完整逐请求文件和误差统计。
- 参数组合同时改变多个变量，尚未拆分单项贡献。
- 高并发、长时间稳定性和不同 Mesa/RADV 版本仍需重新测试。

数据来源与边界见[证据使用说明](../../meta/evidence-policy.md)。
