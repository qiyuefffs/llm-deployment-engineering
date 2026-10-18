# 1.2.5 昇腾：芯片、CANN与框架插件

## 本节概览

昇腾适配先核对芯片代际、驱动/固件、CANN与框架插件，再验证模型、精度和图执行。本节依据作者310P3部署Qwen3-32B的记录，说明实际准备与检查顺序。

## 一、固定已知组合

原笔记使用`quay.io/ascend/vllm-ascend:v0.10.0rc1-310p`，模型为Qwen3-32B，双设备、float16。镜像标签属于历史组合，当前环境重做应先核对该芯片与版本的配套说明，并记录镜像digest。

```bash
npu-smi info
```

继续记录驱动、固件、CANN、Python、PyTorch/torch_npu及vLLM Ascend版本。设备名称相近不能直接复用另一代的支持结论。

## 二、容器先验证设备可访问

需要按当前镜像文档提供设备节点和驱动库，再挂载模型。模型目录优先只读，端口与共享内存明确配置。原笔记使用过高权限、host网络与较广挂载，交付时应根据实际需要缩小范围。

先在容器中执行设备检查与小计算，再运行目标模型。这样模型加载失败时，能够区分容器接入、插件初始化和权重问题。

## 三、启动目标模型

下面是原服务的公开路径节选，前提是配套容器环境已经通过；长度与内存预算需按当前设备重新验收。

```bash
python -m vllm.entrypoints.openai.api_server   --model /srv/models/Qwen3-32B   --served-model-name Qwen3-32B   --host 127.0.0.1 --port 8000   --tensor-parallel-size 2 --dtype float16   --max-model-len 32768 --gpu-memory-utilization 0.95   --distributed-executor-backend mp --enforce-eager   --block-size 64 --swap-space 16
```

不要把历史高预算作为首次冒烟起点。先用资源可承受的长度验证，随后逐步恢复目标配置。模型需要远程代码时单独审阅与固定，不默认加入所有命令。

## 四、接口与压测检查

服务ready后，先检查模型列表，再用匹配的chat或completion端点提交请求。提示字段必须与端点一致：`messages`用于chat，`prompt`用于completion。

原压测曾设置`parallel=10`而`number=1`，最终只有1个请求。记录约14336输出token、3120.88秒、4.5936token/s。它是一次长输出观察，无法证明十路同时服务，也无法提供可靠尾延迟。

重测时应给各并发组足够样本，保留实际请求与输出，长度、采样和缓存一致。具体方法见[压测教程](../performance/benchmarking.md)。

## 五、导入位置与环境变量

原笔记提到在源码目录运行与在工作目录运行出现差异。遇到这类问题时，检查`python`路径、模块来源和环境变量，防止当前目录遮蔽已安装包。V1/V0等开关按该固定版本支持情况设置，记录最终生效值。

## 六、完成检查

设备、插件和目标模型分别有证据；单请求、功能和负载分别验收；依赖与镜像可追溯。当前资料没有保存完整的干净复建链，因此本节将历史命令与已知结果保留为工程参考。

来源：作者《华为昇腾310P3推理Qwen3-32B》《昇腾310P3部署Qwen3-32B benchmark记录》，见[文章对应表](../../evidence/chapter-sources.md)。
