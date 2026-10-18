# DGX Spark / GB10：ARM64、统一内存与低位宽推理

[总目录](../../SUMMARY.md) · [NVIDIA与CUDA](nvidia.md) · [GB10历史工程](../../engineering/nvidia-gb10.md) · [量化选择](../models/quantization.md)

**资料核查：2026-10-18。** 本章说明硬件特性和当前部署流程；已有性能数据仍引用原GB10记录，新配置没有补写GPU实测结果。

## 1. 先分清容量、带宽和算力

DGX Spark使用GB10 Grace Blackwell方案，20核Arm CPU，CPU/GPU共享128GB LPDDR5x统一内存，官方内存带宽为273GB/s。它适合桌面开发、容量较大的模型试验和本地推理，但不能按服务器HBM设备的带宽与并发能力理解。

官方FP4峰值包含特定低精度与稀疏条件。模型能放入内存、kernel能够执行，以及某个服务满足延迟，是三项不同的结论。

教学估算：若每步decode理想化地需要从内存读取20GB权重，只计算273GB/s带宽，则上限约13.65步/秒。它忽略缓存复用、MoE激活路径、KV、量化解包和所有其他开销，不能作为具体模型token/s预测；其作用是说明低并发decode为什么不由峰值FLOPS单独决定。

## 2. ARM64环境先检查这些项

```bash
uname -m
cat /etc/os-release
nvidia-smi
free -h
docker version
```

`uname -m`应与ARM64/aarch64软件包匹配。x86_64 wheel、扩展so和容器不能因为“同样使用CUDA”就直接复制过来。检查宿主驱动、容器架构、CUDA/PyTorch构建及FlashInfer等扩展的配套关系。

优先使用官方Spark playbook为精确模型生成的recipe。复制时保留同一recipe中的镜像、模型、精度、环境变量、parser与启动参数；不要混用另一模型的工具解析器和kernel变量。

## 3. 当前官方vLLM路线怎样固定

核查时官方单Spark示例为`nvidia/Qwen3.8-27B-NVFP4`，配套镜像标签`vllm/vllm-openai:qwen38`。标签会变化，下载后固定digest：

```bash
mkdir -p records/spark
docker pull vllm/vllm-openai:qwen38
docker image inspect vllm/vllm-openai:qwen38 \
  --format '{{json .RepoDigests}}' > records/spark/image-digests.json
docker image inspect vllm/vllm-openai:qwen38 \
  --format '{{.Architecture}}' > records/spark/image-architecture.txt
```

随后在[官方单设备recipe](https://build.nvidia.com/spark/vllm/instructions)进入该模型的launch script，保存完整脚本与模型revision，再按该脚本启动。这里引用官方整套启动配置，避免将本章的通用预算与模型专用选项拼成另一套未经验证的recipe。

服务启动后依次检查：

1. 日志确认NVFP4实际走的linear/MoE backend，记录是否fallback。
2. `/health`就绪，`/v1/models`模型ID正确。
3. 短题、reasoning/content分离、工具调用分别验收。
4. c1开始，再测c2/c4；记录实际输出长度、TTFT、TPOT和内存压力。
5. 最后独立加入MTP/DFlash/DSpark等受支持的草稿，不能认为硬件名称Spark自带DSpark加速。

## 4. UMA的内存怎么记录

128GB是系统共享总量，需要留给OS、CPU程序、模型、KV、workspace和图。vLLM的内存预算比例不等于“128GB都可给权重”。统一内存计数可能重叠，不能把主机RSS与GPU报告直接相加。

部分`nvidia-smi --query-gpu`内存字段在UMA上可能为N/A；保留普通`nvidia-smi`、`free -h`、进程RSS、引擎分项buffer和swap。若加载后开始持续swap，容量表面足够也可能产生很高的尾延迟。

旧记录中的drop_caches是特定内存压力排错措施，不作为每次启动的默认优化。先定位文件页缓存、实际驻留和引擎分配，不用清缓存后的瞬时结果冒充稳定性能。

## 5. GB10的精度与kernel要单独验证

Blackwell名称不代表所有SM100服务器kernel可在GB10上使用。先读取`torch.cuda.get_device_capability()`，再检查目标kernel支持的精确架构；不要用改写计算能力数字来伪装另一块GPU。

NVFP4、MXFP4、FP8是不同表示，检查权重格式、scale、activation和kernel。原生低精度路径、W4A16 fallback、普通BF16执行属于不同方案，日志和压测应说明实际走哪一条。

旧GB10工程里有源码patch和编译绕过，按历史commit阅读。新部署先评估官方配套镜像；确需源码改动时保留diff，完成最小生成与质量回归后再压测。

## 6. 两台Spark如何判断收益

两台设备通常分别拥有各自的统一内存，不是一块透明共享256GB的GPU。官方多节点recipe使用指定网络、并行和容器，先验证控制面与实际collective链路。

模型单台已能运行时，比较双独立副本与跨机TP；模型单台放不下时，可以报告容量扩展，但单请求生成可能受通信影响。两台可运行的模型规模上限也不代表所有精度与上下文都能装入。

验收按[多卡并行](../performance/parallelism.md)记录每rank内存、有效带宽、实际token和尾延迟，再决定是否采用跨节点配置。

## 7. 官方资料

- [DGX Spark硬件参数](https://docs.nvidia.com/dgx/dgx-spark/hardware.html)。
- [Spark移植指南](https://docs.nvidia.com/dgx/dgx-spark-porting-guide/overview.html)。
- [vLLM recipe选择](https://build.nvidia.com/spark/vllm/choose-recipe)与[单设备操作](https://build.nvidia.com/spark/vllm/instructions)。
