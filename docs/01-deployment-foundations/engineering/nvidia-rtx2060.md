# NVIDIA RTX 2060 12GB：CUDA混合卸载与Qwen3量化推理

[工程实例索引](README.md) · [知识体系总目录](../SUMMARY.md)

技术标签：`CUDA / GGUF / CPU-GPU offload`

## 工程配置

| 项目 | 配置 |
| --- | --- |
| GPU / RAM | RTX 2060 12GB / 32GB主机内存 |
| 模型 | Qwen3-30B-A3B Q6；32B Q5作为容量对照 |
| 执行路径 | GGUF → llama.cpp CUDA → 部分层卸载 → OpenAI API |
| 主要约束 | 权重无法全部放入12GB；CPU端权重、KV和操作系统竞争32GB RAM |
| 原始测量 | Q6单次输入9token、输出182token；prefill约9.04token/s、decode约5.26token/s |

## 部署适配过程

1. `nvidia-smi`核对驱动与空闲显存；`free -h`、`vmstat 1`记录RAM与swap。该卡为Turing，不能按新卡假设具有原生FP8矩阵计算。
2. 按[CUDA构建说明](../chapters/frameworks/llama-cpp.md)固定源码，构建`llama-server/llama-bench/llama-cli`。RTX2060可使用`-DCMAKE_CUDA_ARCHITECTURES=75`，核对实际日志。
3. 准备完整GGUF与SHA256。先以`-ngl 0 -c 2048 -np 1`验证CPU加载，再按16、24等档位增加卸载，直到保留足够设备工作区；不要把`-ngl 99`当作12GB卡必然可用的配置。
4. 相同prompt、输出预算、采样和线程下运行每档，保存`load time/prompt eval/eval/total`与CPU/GPU buffer。模型加载耗时与热生成分开。
5. 确定不发生swap抖动的配置后启动HTTP服务，检查模型列表、短题、长题、SSE和取消。原配置含parallel8，只能说明配置值；活动并发能力需另外压测。

```bash
./build-cuda/bin/llama-server \
  -m /srv/models/Qwen3-30B-A3B-Q6_K.gguf \
  --host 127.0.0.1 --port 8080 -c 2048 -np 1 -ngl 16
```

这是重新验证用的小预算入口，不是下方历史成绩的原始命令。最终卸载数按原记录与设备实测确定。

## 加速优化与验收

| 实验 | 固定条件 | 检查结果 |
| --- | --- | --- |
| 增加GPU卸载层 | 同制品、ctx、prompt、输出、线程 | decode、PCIe传输、CPU负载、显存余量 |
| Q6→Q5/Q4 | 同模型与任务；制品变化单独记录 | 内存下降、速度、答案质量；不能直接等价于无损 |
| 线程数调整 | 同卸载和输入 | CPU端耗时、上下文切换；线程越多不一定越快 |
| 槽位1→2 | 同长度与总样本 | 总吞吐、单请求TPOT、p95、失败率和RAM峰值 |

保留原来约5.26token/s的观测，不包装成稳定HTTP吞吐。合格配置必须完成目标任务，且RAM/swap、VRAM和尾延迟满足预先设定的预算。完整原参数、计时和资源记录如下。

## 完整技术记录的使用约定

以下直接保留相关FlowUs文章的技术正文、命令、表格、日志、失败和后续实验，不以摘要替代原过程。私人路径、节点、认证与附件地址脱敏；`<NODE_IP>`等占位符需要按当前环境填写。原建议或预测仍是建议或预测。上方执行顺序与技术修订用于解释历史记录中的冲突，历史GPU/NPU实验未在本轮重跑。

## R01 · nvidai-llamacpp-qwen3:30-a3b-q6测试记录

硬件配置

CPU： 12th Gen Intel(R) Core(TM) i5-12400F

Memory: 32GB

GPU:  **RTX 2060 12GB**

软件环境
cuda加速框架

推理框架：llama.cpp(cuda版本)

推理方式：CPU+GPU混合推理

模型：qwen3:30b-a3b

格式及精度：Qwen3-30B-A3B-Q6_K.gguf

推理命令：

```text
llama-server.exe -m D:\xiangmu\llamacpp\model\dir\Qwen3-30B-A3B-Q6_K.gguf --top-k 1 -c 2048 -n 1000 -ngld 99 -ngl 99 --mlock --parallel 8

```

模型加载时memory占用：82~100%

模型常态加载memory占用：76%

磁盘交换：100%

[原笔记图片：image.png；未公开转存]

提问测试数据：

```text
1. 简单提问：“你好”

性能占比：
CPU: 21%
memory: 85%~89%
GPU: 98%~100%


```

[原笔记图片：image.png；未公开转存]

token数据：

| 指标 | 数值 | 说明 |
| --- | --- | --- |
| Prompt Eval Time | 995.30 ms | 首响应 prompt 的时间 |
| Tokens (Prompt) | 9 tokens | 输入的词元数目 |
| Time per Token (Prompt) | 110.59 ms/token | 每个词元处理的平均时间 |
| Tokens per Second (Prompt) | 9.04 tokens/sec | 模型每秒处理的词元数 |
| Eval Time | 34,618.63 ms | 整体评估（推理）时间 |
| Tokens (Eval) | 182 tokens | 推理过程中处理的词元数目 |
| Time per Token (Eval) | 190.21 ms/token | 每个词元处理的平均时间 |
| Tokens per Second (Eval) | 5.26 tokens/sec | 模型每秒处理的词元数 |
| Total Time | 35,613.93 ms | 总共处理时间，包括 prompt 和评估时间 |
| Tokens (Total) | 191 tokens | 总共处理的词元数，包括 prompt 和评估阶段的所有词元 |
| Slots Status | All slots are idle | 计算资源（slots）处于空闲状态，当前没有任务在处理 |

[原笔记图片：image.png；未公开转存]

## R02 · nvidai-llamacpp-qwen3:30-a3b-q6基准性能测试记录

硬件配置

CPU： 12th Gen Intel(R) Core(TM) i5-12400F

Memory: 32GB

GPU:  **RTX 2060 12GB**

软件环境
cuda加速框架

推理框架：llama.cpp(cuda版本)

推理方式：CPU+GPU混合推理

模型：qwen3:30b-a3b

格式及精度：Qwen3-30B-A3B-Q6_K.gguf

推理命令：

```text
llama-server.exe -m D:\xiangmu\model\Qwen3-30B-A3B-Q6_K\Qwen3-30B-A3B-Q6_K.gguf --top-k 1 -c 2048 -n 1000 --tensor-split 0.9,0.1 -ngl 99 --mlock --parallel 8

```

模型加载时memory占用：82~100%

模型常态加载memory占用：69%

磁盘交换：100%

[原笔记图片：image.png；未公开转存]

基准测试记录

evalscope测试工具-----性能测试

测试命令：

```text
evalscope perf --url http://127.0.0.1:8080/v1/chat/completions --model Qwen3-30B-A3B-Q6_K --api openai --parallel 8 --number 2 --stream
```

[原笔记图片：image.png；未公开转存]

[原笔记图片：image.png；未公开转存]

测试log

[benchmark.log]([附件地址不公开]

## R03 · nvidai-llamacpp-qwen3:32B-q5基准性能测试记录

硬件配置

CPU： 12th Gen Intel(R) Core(TM) i5-12400F

Memory: 32GB

GPU:  **RTX 2060 12GB**

软件环境
cuda加速框架

推理框架：llama.cpp(cuda版本)

推理方式：CPU+GPU混合推理

模型：[qwen3:30b-a3b](qwen3:32B-q5)

格式及精度：Qwen3-32B-Q5_K_M.gguf

推理命令：

```text
llama-server.exe -m D:\xiangmu\model\Qwen3-32B-Q5_K_M\Qwen3-32B-Q5_K_M.gguf --top-k 1 -c 2048 -n 1000 --tensor-split 0.6,0.4 -ngl 99 --mlock --parallel 4
```

模型加载时memory占用：82~100%

模型常态加载memory占用：59%

磁盘交换：69~79%

[原笔记图片：image.png；未公开转存]

基准测试记录

evalscope测试工具-----性能测试

测试命令：

```text
evalscope perf --url http://127.0.0.1:8080/v1/chat/completions --model Qwen3-32B-Q5_K_M --api openai --parallel 1 --number 5 --max-tokens 200 --stream
```

[原笔记图片：image.png；未公开转存]

[原笔记图片：image.png；未公开转存]

测试log

[benchmark.log]([附件地址不公开]
