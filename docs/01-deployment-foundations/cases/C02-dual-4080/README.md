---
id: C02
title: "NVIDIA RTX 4080与A6000：双卡vLLM部署和调参记录"
type: case
volume: cases
layer: 1
platform: "NVIDIA"
device: "RTX 4080 dual GPU"
status: historical
source_ids: [R04]
updated: 2026-10-19
summary: "技术标签：CUDA / Docker / TP2 / GPTQ / FP8"
---

# NVIDIA RTX 4080与A6000：双卡vLLM部署和调参记录

[工程实例索引](../README.md) · [知识体系总目录](../../SUMMARY.md)

技术标签：`CUDA / Docker / TP2 / GPTQ / FP8`

## 结论

R04 记录 RTX 4080 双卡三组历史速度 35、55、52 tok/s，以及 A6000 双卡
17.1、17.5 tok/s。它们是多参数、多版本组合观察；缺同负载逐请求记录，
不能将其中的差值归因给“提高 GPU 利用率”或某个缓存参数。

## 适用边界

4080×2 的 32B GPTQ INT4 与 A6000×2 的 70B FP8 是两套设备和制品。
RTX 4080 没有 NVLink；量化文件能被读取，也不等于在该设备执行了原生 FP8。
实际通信和 kernel 需从对应版本日志确认。

## 环境与制品

| 实例 | 模型与资源 | 参数演进 | 原记录速度 |
| --- | --- | --- | --- |
| RTX4080×2 | 各16GB，RAM128GB；DeepSeek-R1-Distill-Qwen-32B GPTQ INT4 | ctx8192/seqs8/eager → ctx16384/seqs16/memory0.93 → v0.8.5/chunked/batched4096 | 35 → 55 → 52token/s |
| A6000×2 | 各48GB；DeepSeek-R1-Distill-Llama-70B FP8 dynamic | memory0.80 → 0.88、block32、batched4096 | 17.1 → 17.5token/s |

以上是原记录速度，缺统一负载与逐请求明细，不能解释为控制变量加速比。A6000优化段文字写并发8，命令实际`max-num-seqs16`，复建以保存的命令为准并记录差异。RTX4080没有NVLink接口；A6000的互连也须实际检查，不能套用另一设备拓扑。

## 执行路径

```bash
nvidia-smi
nvidia-smi topo -m
nvidia-ctk --version
docker info
```

1. 主机驱动识别两卡，再配置NVIDIA Container Toolkit；Docker重新配置会影响主机容器，安排在维护窗口进行。
2. 固定vLLM镜像标签并记录digest。在容器中再次执行`nvidia-smi`，确认可见两卡；镜像内CUDA、torch与量化kernel属于同一运行组合。
3. 下载对应GPTQ/FP8完整模型目录。核对`quantization_config`，不能把AWQ、GPTQ、FP8混用同一后端参数。
4. 先运行下方历史基线，再逐次改变ctx、seqs、memory、eager、custom all-reduce或chunked prefill。每次运行独立容器名和结果目录，前一模型释放后再启动下一组。
5. 服务ready后用chat端点发送`messages`；completion端点使用`prompt`。原末尾curl混用了端点/字段，按[API规范](../../chapters/delivery/api-monitoring.md)修正后再压测。

### 保留一套完整的历史服务入口

以下参数来自 RTX 4080 的第一组配置；`${MODEL_ROOT}` 是需预先设置的
本地模型目录。镜像标签保留原记录版本，内部镜像镜像站地址不公开。

```bash
docker run --name vllm --gpus all \
  --mount "type=bind,source=${MODEL_ROOT},target=/root/model" \
  -p 8000:8000 --ipc=host vllm/vllm-openai:v0.6.4.post1 \
  --model /root/model/deepseek-r1-distill-qwen-32b-gptq-int4 \
  --enforce-eager --max-model-len 8192 --max-num-seqs 8 \
  --tensor-parallel-size 2
```

检查点是容器看到两卡、模型挂载路径真实存在、TP 两个 rank 正常加载、
API 返回完整正文。端口映射必须与客户端一致，后续组合有不同宿主端口。

### 参数变化怎样记录

第二组同时改为 ctx16384、seqs16、memory0.93、custom all-reduce 路径；
第三组又升级到 v0.8.5，改 memory0.85、seqs8、batched4096、chunked
prefill、block32，并设置 PyTorch allocator。因此三组只能按整套配置归档。

## 结果

先比较单请求，随后c1/c2/c4/c8固定长度。`--disable-custom-all-reduce`是通信路径选择，不是通用加速开关；同时保存NCCL日志与PCIe拓扑。`PYTORCH_CUDA_ALLOC_CONF`管理分配器，不等于PagedAttention，也不直接启用“动态KV”。

RTX4080的35/55/52和A6000的17.1/17.5都应作为历史观察保留。新验收须补总输出token、测试时长、TTFT/TPOT、成功数、每卡峰值和质量；足够样本后才报告尾部分位数。

## 失败与修订

原记录首先遇到宿主能识别 GPU、Docker 运行时未正确配置的问题，因此
使用 `nvidia-ctk --version` 与容器设备可见性分别确认。API 末尾样例又有
completion/chat 字段混用，协议正确性应先于性能比较。

`gpu-memory-utilization` 控制内存预算，不是 GPU 算力利用率目标。
`expandable_segments` 是分配器设置，不等于启用了新的 PagedAttention。

## 证据

- [R04 完整技术正文](../../evidence/sources/R04.md)

## 未验证

尚缺各组实际输入/输出、计时边界、每卡峰值、质量集、精确模型 revision
及通信日志；没有足够材料确定哪一项参数贡献了历史速度变化。

数据来源与边界见[证据使用说明](../../meta/evidence-policy.md)。
