---
id: C07
title: "AMD 395五机HIP RPC：GTT修复、构建、分发与Kimi加载"
type: case
volume: cases
layer: 1
platform: "AMD"
device: "Ryzen AI Max+ 395"
status: historical
source_ids: [R23, R24, R25]
updated: 2026-10-19
summary: "技术标签：ROCm / HIP / GTT / TTM / RPC / split"
---

# AMD 395五机HIP RPC：GTT修复、构建、分发与Kimi加载

[工程实例索引](../README.md) · [知识体系总目录](../../SUMMARY.md)

技术标签：`ROCm / HIP / GTT / TTM / RPC / split`

## 结论

历史五机链路首先解决 GTT/TTM 容量：dmesg 显示 120000 MiB，但设备实际
仅见约 63215 MiB；修复后再确认约 120000 MiB。Kimi 的初始 ctx512、
batch32、ubatch8 是加载验收预算，不是正式长上下文性能结果。

## 适用边界

主节点加四个 RPC worker，使用配套 HIP 运行库。驱动、TTM 模块与内核参数
共同决定可分配量；不能仅照抄 GRUB 值就认定容量已经可用。无单机同模型
基线时，本章不计算五机加速比。

## 环境与制品

| 项目 | 配置 |
| --- | --- |
| 节点 | 5台Ryzen AI Max+395 / Radeon8060S，主节点＋4个RPC节点 |
| 软件 | ROCm7.2.1、HIP7.2.53211、Kernel6.17.0-35、llama.cpp b9557-0f7fada56 |
| 容量问题 | dmesg显示GTT120000MiB，但DKMS TTM实际约63215MiB；修复后设备可见约120000MiB |
| 模型 | Kimi-K2.5-Q2；模型revision与各分片需另行固定 |
| 首次预算 | ctx512、batch32、ubatch8、FA off；先验证容量与加载 |

## 执行路径

```text
BIOS UMA预算 → /proc/cmdline → amdgpu模块来源 → GTT/TTM
 → 本机HIP枚举 → 同commit编译RPC → 同版本分发
 → 4个RPC进程 → 主机list-devices → 小模型 → Kimi小上下文
 → 内存/连接/进度观察 → llama-server与API → 正式负载
```

GTT/TTM修复涉及驱动模块与重启，先记录模块来源和恢复方式；它只解决可分配内存，不代表五机已获得速度提升。原文有完整排错、DKMS处理与加载过程，保留在下方。

为避免泄露节点，原私有地址替换成`<NODE_IP>`。新运行需明确设置`RPC_NODE_1`到`RPC_NODE_4`，四个值各对应一个节点；不要把所有占位符替换成同一机器。程序版本与依赖库在五机保持一致。

### 构建时实际启用哪些后端

R24 的配置为：

```bash
cmake -B build \
  -DGGML_HIP=ON -DGGML_RPC=ON -DGGML_HIP_ROCWMMA_FATTN=ON \
  -DAMDGPU_TARGETS=gfx1151 -DCMAKE_BUILD_TYPE=Release \
  -DGGML_LTO=ON -DGGML_CCACHE=ON -DGGML_BACKEND_DL=ON \
  -DGGML_NATIVE=OFF -DLLAMA_OPENSSL=ON
```

这是一份构建记录，不是 rocWMMA 性能已优于普通 HIP 的证明。配置后仍需
完成实际 build，确认 worker 程序、HIP/RPC 动态库和依赖路径一致。
R23 与 R24 的安装阶段提及不同 ROCm 版本，复建按所选那次运行锁定，
不把各段安装命令混成一套环境。

### 容量检查点

读取 `/proc/cmdline`、TTM 的 pages_limit/page_pool_size、amdgpu 模块来源，
再看 dmesg 与 `llama-cli --list-devices`。R23 的冲突正发生在“参数看似
正确、实际驱动模块未按预期分配”这一步。

驱动模块修订与重启是历史操作，需先记录恢复方案；容量恢复后重新做小模型
GPU smoke，再启动四个 RPC worker。主机枚举每个远端设备，确认四个 endpoint
各自对应一台机器，再用目标分片入口加载 Kimi。

### 初始预算与逐步放大

先使用 `tensor-split=14,21.5,21.5,21.5,21.5`，主机少分权重以保留映射和
系统空间。目标小上下文加载后，核对每节点实际 buffer、RPC 传输、主机
RSS 和 GPU 活动；然后才分别放大 ctx、batch、ubatch。模型能加载与长请求
可完成是两项不同验收。

## 结果

原tensor-split为`14,21.5,21.5,21.5,21.5`，主机少分配以保留映射、状态与系统空间。先用同模型调整split，检查各节点实际buffer和主机峰值；再增大ctx/batch/ubatch，每次只改变一个主变量。

容量验收与速度验收分开：五机能加载目标模型是容量结果；没有单机同口径基线就不报告多机加速比。记录RPC网络吞吐、加载时间、prefill/decode、API TTFT和失败恢复。

| 阶段 | 历史记录 | 尚不能推出 |
| --- | --- | --- |
| GTT 表面配置 | dmesg 120000 MiB，设备约63215 MiB | 内核参数已经实际生效 |
| 修订后设备预算 | 设备约120000 MiB | 任意大小的单次分配必然成功 |
| 五机小上下文加载 | ctx512、batch32、ubatch8、FA off | 正式上下文与并发性能 |
| R25 功能脚本 | 设备、RPC、环境检查流程 | 脚本存在等于本轮执行通过 |

## 失败与修订

最关键的负例是 dmesg 的 GTT ready 不等于应用可分配预算。排障按驱动模块
来源、TTM 值、应用枚举依次定位，不能只重复增加上下文参数。模型与分片
未锁定 revision 时，还需要独立补齐制品校验。

## 证据

- [R23 完整技术正文](../../evidence/sources/R23.md)
- [R24 完整技术正文](../../evidence/sources/R24.md)
- [R25 完整技术正文](../../evidence/sources/R25.md)

## 未验证

同模型单机基线、正式请求长度、受控的 split 消融、长期并发和失败恢复
尚缺统一结果。没有原始时序的测试不补填加载时间或 TTFT。

数据来源与边界见[证据使用说明](../../meta/evidence-policy.md)。
