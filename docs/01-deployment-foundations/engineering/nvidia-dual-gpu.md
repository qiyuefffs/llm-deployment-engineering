# NVIDIA RTX 4080与A6000：双卡vLLM部署和调参记录

[工程实例索引](README.md) · [知识体系总目录](../SUMMARY.md)

技术标签：`CUDA / Docker / TP2 / GPTQ / FP8`

## 工程配置

| 实例 | 模型与资源 | 参数演进 | 原记录速度 |
| --- | --- | --- | --- |
| RTX4080×2 | 各16GB，RAM128GB；DeepSeek-R1-Distill-Qwen-32B GPTQ INT4 | ctx8192/seqs8/eager → ctx16384/seqs16/memory0.93 → v0.8.5/chunked/batched4096 | 35 → 55 → 52token/s |
| A6000×2 | 各48GB；DeepSeek-R1-Distill-Llama-70B FP8 dynamic | memory0.80 → 0.88、block32、batched4096 | 17.1 → 17.5token/s |

以上是原记录速度，缺统一负载与逐请求明细，不能解释为控制变量加速比。A6000优化段文字写并发8，命令实际`max-num-seqs16`，复建以保存的命令为准并记录差异。RTX4080没有NVLink接口；A6000的互连也须实际检查，不能套用另一设备拓扑。

## 部署适配过程

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
5. 服务ready后用chat端点发送`messages`；completion端点使用`prompt`。原末尾curl混用了端点/字段，按[API规范](../chapters/delivery/api-monitoring.md)修正后再压测。

## 加速优化与验收

先比较单请求，随后c1/c2/c4/c8固定长度。`--disable-custom-all-reduce`是通信路径选择，不是通用加速开关；同时保存NCCL日志与PCIe拓扑。`PYTORCH_CUDA_ALLOC_CONF`管理分配器，不等于PagedAttention，也不直接启用“动态KV”。

RTX4080的35/55/52和A6000的17.1/17.5都应作为历史观察保留。新验收须补总输出token、测试时长、TTFT/TPOT/p95/p99、成功数、每卡峰值和质量。下方保留两种GPU的完整原始调参过程与Docker命令。

## 完整技术记录的使用约定

以下直接保留相关FlowUs文章的技术正文、命令、表格、日志、失败和后续实验，不以摘要替代原过程。私人路径、节点、认证与附件地址脱敏；`<NODE_IP>`等占位符需要按当前环境填写。原建议或预测仍是建议或预测。上方执行顺序与技术修订用于解释历史记录中的冲突，历史GPU/NPU实验未在本轮重跑。

## R04 · 服务器：Nvidia显卡：Ubuntu22.04+VLLM+Docker双卡部署Deepseek-r1:32B(Int4)

硬件修订：RTX 4080没有NVLink接口。该双卡项目使用PCIe互连；通信性能应通过拓扑与集合通信实测，不能套用NVLink带宽。

系统：Ubuntu22.04 LTS ,  4080: 16GB*2GB双卡,   内存128GB

1. 安装NVIDIA驱动

 检查驱动命令：ubuntu-drivers devices

[原笔记图片：image.png；未公开转存]

选择标有recommended的版本安装

或者自动安装推荐版本：
sudo ubuntu-drivers autoinstall

安装cuda-nvidai-tool

```text
# 检查仓库是否已添加（应有输出）
grep -r "developer.download.nvidia.com" /etc/apt/sources.list.d/

# 若无输出，重新添加仓库
sudo add-apt-repository "deb https://developer.download.nvidia.com/compute/cuda/repos/ubuntu2204/x86_64/ /"
sudo apt-key adv --fetch-keys https://developer.download.nvidia.com/compute/cuda/repos/ubuntu2204/x86_64/3bf863cc.pub
sudo apt update

sudo apt install cuda-toolkit-12-4
配置变量环境
# 写入bashrc（永久生效）
echo 'export PATH=/usr/local/cuda-12.4/bin:$PATH' >> ~/.bashrc
echo 'export LD_LIBRARY_PATH=/usr/local/cuda-12.4/lib64:$LD_LIBRARY_PATH' >> ~/.bashrc

# 立即生效
source ~/.bashrc
```

[原笔记图片：image.png；未公开转存]

主要BUG：
NVIDIA驱动安装：nvidia-driver-550最合适,

nvidia驱动工具：需要安装，名字暂时忘了，nvidia-cli工具库，一定要安装好，注意对应版本，不然无法将设置Nvidia GPU版本的docker。

使用nvidia-ctk --version命令，检查NVIDIA Container Toolkit 是否正确安装（大坑，大坑，一定要注意！！！）

[原笔记图片：image.png；未公开转存]

1. NVIDIA驱动安装好之后，下载docker，并进行环境配置

docker镜像替换为国内源最好，
拉取vllm/openai docker镜像，使用不了外网，使用的国内镜像源：
拉取链接：[https://docker.aityp.com/image/docker.io/vllm/vllm-openai:v0.8.5](https://docker.aityp.com/image/docker.io/vllm/vllm-openai:v0.8.5)

1. 下载模型

无法使用外网情况下，拉取模型，可以去魔塔社区，搜索Deepseek-R1:32B  int4量化的模型；

可以使用外网，去huggingface拉取模型Deepseek-r1:32b  int4量化的模型；

32GB显存，使用Int4量化模型token生成速度较快；

1. 创建docker镜像

创建docker参数命令：并发数量：8，上下文长度：8K, 没将GPU算力提高，35tokens/s:，

双卡GPU利用率：84%

```text
sudo docker run --name vllm \
     --gpus all \
     --mount type=bind,source="/srv/llm/model/DeepSeek-R1:32B_GPTQ_Int4",target=/root/model \
     -p 8000:8000 \
     --ipc=host \
     swr.cn-north-4.myhuaweicloud.com/ddn-k8s/docker.io/vllm/vllm-openai:v0.6.4.post1 \
     --model /root/model/deepseek-r1-distill-qwen-32b-gptq-int4 \
     --enforce-eager \
     --max-model-len 8192 \
     --max-num-seqs 8 \
     --tensor-parallel-size 2
```

```text
sudo docker run --name vllm \
     --gpus all \
     --mount type=bind,source="/srv/llm/model/deepseek-r1-distill-qwen-32b-gptq-int4",target=/root/model \
     -p 8000:8000 \
     --ipc=host \
     swr.cn-north-4.myhuaweicloud.com/ddn-k8s/docker.io/vllm/vllm-openai:v0.6.4.post1 \
     --model /root/model/deepseek-r1-distill-qwen-32b-gptq-int4 \
     --enforce-eager \
     --max-model-len 8192 \
     --max-num-seqs 8 \
     --tensor-parallel-size 2
```

vllm_test1:并发数：16，上下文16K，int4量化32b模型，GPU利用率设置较高0.93, 55tokens/s，双卡GPU利用率：94%

```text
sudo docker run --name vllm_test1 --gpus all --mount type=bind,source="/srv/llm/model/DeepSeek-r1-32B_GPTQ_Int4",target=/root/model -p 8001:8000 --ipc=host swr.cn-north-4.myhuaweicloud.com/ddn-k8s/docker.io/vllm/vllm-openai:v0.6.4.post1 --model /root/model/deepseek-r1-distill-qwen-32b-gptq-int4 --max-model-len 16384 --max-num-seqs 16 --tensor-parallel-size 2 --gpu-memory-utilization 0.93 --disable-custom-all-reduce
```

docker镜像名称：vllm_test1

```text
sudo docker run --name vllm_test1 --gpus all --mount type=bind,source="/srv/llm/model/DeepSeek-r1-32B_GPTQ_Int4",target=/root/model -p 8001:8000 --ipc=host swr.cn-north-4.myhuaweicloud.com/ddn-k8s/docker.io/vllm/vllm-openai:v0.6.4.post1 --model /root/model/deepseek-r1-distill-qwen-32b-gptq-int4 --max-model-len 16384 --max-num-seqs 16 --tensor-parallel-size 2 --gpu-memory-utilization 0.93 --disable-custom-all-reduce

```

vllm_test2:使用动态KV方法运行模型，速度52tokens/s，镜像版本：swr.cn-north-4.myhuaweicloud.com/ddn-k8s/docker.io/vllm/vllm-openai:v0.8.5

```text
 sudo docker run --name vllm_test2   --gpus all   --mount type=bind,source="/srv/llm/model/DeepSeek-r1-32B_GPTQ_Int4",target=/root/model   -p 8001:8000   --ipc=host   -e PYTORCH_CUDA_ALLOC_CONF="expandable_segments:True,garbage_collection_threshold:0.8"   swr.cn-north-4.myhuaweicloud.com/ddn-k8s/docker.io/vllm/vllm-openai:v0.8.5   --model /root/model/deepseek-r1-distill-qwen-32b-gptq-int4   --max-model-len 16384   --tensor-parallel-size 2   --gpu-memory-utilization 0.85  --max-num-seqs 8   --max-num-batched-tokens 4096   --enable-chunked-prefill   --disable-custom-all-reduce   --block-size 32

```

vllm_ds70: DeepSeek-R1-Distill-Llama-70B-FP8-dynamic模型（FP8动态量化），[GPU: A6000 48*2GB](GPU: A6000 48*2GB)，并发16，上下文长度16K，速度17.1tokens/s，双卡GPU占有率：98%，镜像版本：swr.cn-north-4.myhuaweicloud.com/ddn-k8s/docker.io/vllm/vllm-openai:v0.8.5

```text
sudo docker run --name vllm_ds70   --gpus all   --mount type=bind,source="/srv/llm/model/Deepseek-r1-70b-fp8",target=/root/model   -p 8002:8000   --ipc=host   swr.cn-north-4.myhuaweicloud.com/ddn-k8s/docker.io/vllm/vllm-openai:v0.8.5   --model /root/model/DeepSeek-R1-Distill-Llama-70B-FP8-dynamic   --max-model-len 16384   --max-num-seqs 16   --tensor-parallel-size 2   --gpu-memory-utilization 0.80   --disable-custom-all-reduce

```

vllm_ds70_optimized:  DeepSeek-R1-Distill-Llama-70B-FP8-dynamic模型（FP8动态量化），[GPU: A6000 48*2GB](GPU: A6000 48*2GB)，并发8，上下文长度16K，速度17.5tokens/s，双卡GPU占有率：99%，镜像版本：swr.cn-north-4.myhuaweicloud.com/ddn-k8s/docker.io/vllm/vllm-openai:v0.8.5

```text
sudo docker run --name vllm_ds70_16 --gpus all \
--mount type=bind,source="/srv/llm/model/Deepseek-r1-70b-fp8",target=/root/model \
-p 8002:8000 --ipc=host \
swr.cn-north-4.myhuaweicloud.com/ddn-k8s/docker.io/vllm/vllm-openai:v0.8.5 \
--model /root/model/DeepSeek-R1-Distill-Llama-70B-FP8-dynamic \
--max-model-len 16384 \
--max-num-seqs 16 \
--max-num-batched-tokens 4096 \
--tensor-parallel-size 2 \
--gpu-memory-utilization 0.88 \
--block-size 32 \
--scheduling-policy fcfs \
```

注意事项：

注意：创建文件夹时，文件名不要添加特俗符号：比如冒号“”：“”

注意：挂载模型文件时，路径一定要正确。

注意：每个模型，单独创建一个docker，不要在一个docker中使用多个模型。

```text
curl -N [服务地址按本实例配置]   -H "Content-Type: application/json"   -H "Accept: text/event-stream"   -d '{
    "model": "/root/model/DeepSeek-R1-Distill-Llama-70B-FP8-dynamic",
    "prompt": "讲一下大唐历史",
    "max_tokens": 10000,
    "temperature": 0.9,
    "stream": true
  }'

```

```text
watch -n 1 nvidia-smi
```

**注：Docker配置NVIDIA 运行时**

/usr/local/nvidia/toolkit/nvidia-container-runtime

如果启动的时候报错是因为没有配置NVIDIA Container Toolkit

1. 首先检查 NVIDIA Container Toolkit 是否正确安装：

```text
nvidia-ctk --version
```

1. 验证 NVIDIA Docker 运行时：

```text
sudo docker info | grep nvidia
```

1. 如果只是没有运行，执行第一步有一串字符就说明没有问题，然后配置一下docker就可以了

```text
# 配置 Docker 使用 NVIDIA 运行时
sudo nvidia-ctk runtime configure --runtime=docker

# 重启 Docker 服务
sudo systemctl restart docker
```
