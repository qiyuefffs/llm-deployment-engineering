# vLLM：从模型目录到可测量的推理服务

[总目录](../../SUMMARY.md) · [所属总章：推理框架](../../02-capability-layers/03-inference-frameworks.md) · [压测方法](../performance/benchmarking.md)

## 本章概览

服务部署的目标，是让应用通过稳定接口得到完整答案，并知道当前服务能承受什么负载。安装成功只是起点。还要检查制品、后端、模板、内存、正常与异常请求，最后才进入压测。

本章沿用作者FlowUs的GB10/Qwen FP8工程。历史环境为DGX Spark GB10、ARM64、128GB、Ubuntu24.04、CUDA13，以及vLLM提交`17d87168d`。它提供真实构建问题、启动参数和200请求汇总；模型revision和完整依赖锁没有随原记录保存，因此以下是历史工程的操作整理，不承诺在任意新环境逐字复现旧数字。本轮没有重新执行该GPU工程。

## 1. 先固定环境与模型身份

先看CPU架构、驱动与工具链，再决定使用配套镜像还是源码。ARM64设备不能直接套用x86_64的wheel；CUDA驱动兼容也不表示所有依赖库、kernel或模型结构都已经支持。

```bash
uname -m
nvidia-smi
nvcc --version
python --version
python -m pip show torch vllm
```

源码路线要先按该提交的构建要求准备PyTorch、编译器和CUDA依赖。原笔记没有完整安装锁，因此这里不能凭空补成“只运行一条pip命令就能安装全部环境”。在可工作环境里至少保存`pip freeze`、PyTorch版本、编译配置和CMake日志。

历史源码准备顺序如下：

```bash
git clone https://github.com/vllm-project/vllm.git
cd vllm
git checkout 17d87168d
git submodule update --init --recursive
export CUDA_HOME=/usr/local/cuda-13.0
export PATH="$CUDA_HOME/bin:$PATH"
export LD_LIBRARY_PATH="$CUDA_HOME/lib64:${LD_LIBRARY_PATH:-}"
export VLLM_TARGET_DEVICE=cuda
export MAX_JOBS=8
```

原记录为绕开特定FP4 kernel的编译错误，使用`TORCH_CUDA_ARCH_LIST="12.0"`后执行`python -m pip install --no-build-isolation -e .`。设备本身的计算能力仍为12.1。这个绕过属于特定提交和kernel路径，不应复制成所有GB10的默认构建规则。详细错误见[NVIDIA专题](../hardware/nvidia.md)。

模型放在`/srv/models/Qwen3.6-35B-A3B-FP8`。这是本文统一改写的公开目录，需包含权重、配置与匹配tokenizer；不是下载地址。新复现应先从模型的公开页面确认准确仓库、revision和许可，保存制品清单后继续。

## 2. 用小预算完成首次启动

首次启动的目标是加载、短请求和日志检查，先不把最大上下文、活动序列和内存比例同时拉高。下面保留同一模型别名，使用较小的起步预算：

```bash
vllm serve /srv/models/Qwen3.6-35B-A3B-FP8 \
  --served-model-name Qwen3.6-35B-A3B-FP8 \
  --host 127.0.0.1 --port 8001 \
  --tensor-parallel-size 1 \
  --max-model-len 4096 \
  --max-num-seqs 1 \
  --gpu-memory-utilization 0.80
```

这是教学起步配置，不是后面历史性能表对应的配置。前台启动可以直接看到错误；在第二个终端发请求。出现加载错误时，先保存首次异常与环境，避免立刻加入多个优化参数让问题更难定位。

依次检查：实际识别的模型结构与dtype、量化kernel、attention后端、权重内存、KV容量、图编译与warm-up是否完成、服务是否ready。`gpu-memory-utilization`是引擎内存预算比例，不是设备算力利用率，也不是严格限制其他进程内存的隔离机制。

## 3. API 检查要分四步

第一步检查健康与模型身份：

```bash
curl --fail-with-body http://127.0.0.1:8001/health
curl --fail-with-body http://127.0.0.1:8001/v1/models
```

第二步保存一条非流式请求的完整响应：

```bash
curl --fail-with-body http://127.0.0.1:8001/v1/chat/completions \
  -H 'Content-Type: application/json' \
  -d '{"model":"Qwen3.6-35B-A3B-FP8","messages":[{"role":"user","content":"用三句话说明KV缓存的作用。"}],"max_tokens":256,"temperature":0,"stream":false}' \
  -o response.json
```

核对`choices`、正文、`finish_reason`与usage。若到达长度上限而没有最终答案，就增加合理预算或按模型支持的方法管理思考，不能将“生成了一段文本”当作完整任务通过。

第三步改成`stream:true`并使用`curl -N`，检查SSE事件、增量正文、结束事件和客户端取消。首个角色事件通常没有正文，客户端TTFT应采用明确口径。

第四步测试错误模型名、空消息、畸形JSON和超长输入，记录HTTP状态、错误类型及之后的健康。错误返回不能泄露路径；服务也不应因为一个坏请求退出。异常行为按固定版本实测，不凭接口兼容声明填写“通过”。

## 4. 再恢复历史负载配置

以下重现原记录的关键性能参数，主机监听改为本地回环；它们是已运行历史配置，不能代替每台设备的容量预算：

```bash
vllm serve /srv/models/Qwen3.6-35B-A3B-FP8 \
  --served-model-name Qwen3.6-35B-A3B-FP8 \
  --host 127.0.0.1 --port 8001 \
  --max-model-len 16184 \
  --max-num-batched-tokens 8192 \
  --max-num-seqs 4 \
  --gpu-memory-utilization 0.80 \
  --generation-config auto \
  --override-generation-config '{"temperature":0.6,"top_p":0.95,"top_k":20}' \
  --kv-cache-dtype fp8 \
  --load-format auto \
  --attention-backend flashinfer \
  --enable-prefix-caching \
  --enable-chunked-prefill
```

源命令另有`trust-remote-code`。它只在固定模型确有需要且已经审阅代码时启用，不作为通用默认。移除或增加这类选项都应记录到新运行，不能说改写后的命令已经重新测过。

这里同时启用了FP8 KV、Prefix Cache和Chunked Prefill。历史报告说明整套配置能够完成该负载，没有提供逐项关闭的对照，所以不能分别给每个开关分配提升百分比。

## 5. 跑一次有保存位置的压测

历史负载是200请求、随机输入目标2048、输出128、到达率inf、seed42。新运行补上结果目录与明细保存：

```bash
mkdir -p results/gb10-fp8-burst
vllm bench serve \
  --backend openai-chat \
  --base-url http://127.0.0.1:8001 \
  --endpoint /v1/chat/completions \
  --model Qwen3.6-35B-A3B-FP8 \
  --tokenizer /srv/models/Qwen3.6-35B-A3B-FP8 \
  --dataset-name random \
  --random-input-len 2048 --random-output-len 128 \
  --num-prompts 200 --request-rate inf --seed 42 \
  --save-result --save-detailed \
  --result-dir results/gb10-fp8-burst
```

根据固定版本的`vllm bench serve --help`核对参数。随机输入目标不等于模板处理后的实际输入总数，输出也可能被EOS、思考或长度上限影响，应以明细和usage为准。

原记录200成功、0失败，总输出25600token、总时间297.46秒，输出吞吐86.06token/s。平均TTFT148430.70ms，P99 TTFT293115.24ms。活动序列上限4与客户端突发200请求是两个层面，多余请求会等待；高TTFT提示该突发模式下交互体验很差。

不能把它写成“200并发都在GPU同时计算”，也不能用这个结果代表低负载首token延迟。下一步应补有限并发与受控到达率，找出满足目标TTFT和尾延迟的工作点。具体流程见[压测章节](../performance/benchmarking.md)。

## 6. 停止、恢复与完成标准

前台服务用Ctrl+C停止，确认端口与进程已经退出；不要用模糊进程名批量终止其他模型。服务由systemd或容器管理时，用对应实例的停止命令。

本章的可交付结果应包含：固定环境与模型身份、最终命令、启动日志、正常和异常请求、逐请求性能数据、资源采样与结论。历史工程提供了其中一部分，新部署时要补齐。部署成功应写明通过的模型、功能、长度和负载范围，让下一位工程师知道从哪里继续。
