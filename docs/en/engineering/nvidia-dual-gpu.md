# NVIDIA RTX 4080 and A6000: dual-GPU vLLM deployment and modeling records

[简体中文](../../01-deployment-foundations/cases/C02-dual-4080/README.md) | **English**

[Index of engineering examples](README.md) · [General directory of knowledge systems](../SUMMARY.md)

Technical labels: `CUDA / Docker / TP2 / GPTQ / FP8`

## Engineering configuration

|Examples|Models and resources|Parameters are evolving|Recorded speed|
| --- | --- | --- | --- |
| RTX4080×2 |It is also available in the form of 16GB and 128GB of RAM. DeepSeek-R1-Distill-Qwen-32B GPTQ INT4| ctx8192/seqs8/eager → ctx16384/seqs16/memory0.93 → v0.8.5/chunked/batched4096 | 35 → 55 → 52token/s |
| A6000×2 |Each of them is 48GB. DeepSeek-R1-Distill-Llama-70B FP8 dynamic| memory0.80 → 0.88,block32,batched4096 | 17.1 → 17.5token/s |

The above is the original record speed, the lack of a unified workload and the detail of each request, which cannot be explained as the control variable acceleration ratio. A6000 Optimize Paragraphs to write concurrency 8, command actual `max-num-seqs16` Rebuild and save commands to calibrate and record differences. RTX4080 has no NVLink interface; The A6000's interconnection also needs to be checked and cannot be adapted to another device topology.

## Deployment of adaptation processes

```bash
nvidia-smi
nvidia-smi topo -m
nvidia-ctk --version
docker info
```

1. The host driver recognizes two cards and configures the NVIDIA Container Toolkit. Docker reconfiguration will affect the host container, and will be arranged in the maintenance window.
2. Fixed vLLM image tag and record digest. Repeated in container `nvidia-smi` Two cards can be seen; In the image, CUDA, torch and quantization kernel are part of the same operating combination.
3. GPTQ/FP8 full model directory can be downloaded. Verified `quantization_config` You can't mix AWQ, GPTQ, FP8 with the same backend parameter.
4. Run the following historical baseline and then change the ctx, seqs, memory, eager, custom all-reduce or chunked prefill step by step. Each time an independent container name and result directory is run, the first model is released and the next set is started.
5. Chat endpoints after service ready `messages `; completion endpoint ` prompt`. At the end of the curl, the endpoint/field is mixed. [API specifications](../chapters/delivery/api-monitoring.md) It's been modified for load testing.

## Accelerated optimization and acceptance testing

First compare the single request, then c1/c2/c4/c8 fixed length.`--disable-custom-all-reduce ` It is the choice of the communication path, not the general acceleration switch. At the same time, the NCCL log and PCIe topology are stored.`PYTORCH_CUDA_ALLOC_CONF` The admin distributor is not the same as PagedAttention and does not directly enable the dynamic KV array.

Both the RTX 4080's 35/55/52 and the A6000's 17.1/17.5 should be preserved as historical observations. The new acceptance testing will include total output tokens, test duration, TTFT/TPOT/p95/p99, success rate, peak per card and quality. Below is the complete original modeling process for both GPUs with the Docker command.

## Agreement on the use of complete technical records

The following technical correctness, commands, tables, logs, failures and subsequent experiments of the relevant FlowUs articles are retained directly, without abbreviating the original process. private paths, nodes, authentication and sanitization of attached addresses; `<NODE_IP>` For example, the placeholder needs to be filled in the current environment. The original suggestion or prediction is still a suggestion or prediction. The above execution sequence and technical revisions are used to explain conflicts in historical records, and historical GPU/NPU experiments have not been repeated in this round.

## R04 · Server:Nvidia GPU:Ubuntu 22.04+VLLM+Docker dual-GPU deployment Deepseek-r1:32B ((Int4)

Hardware modification: RTX 4080 has no NVLink interface. The dual-GPU project uses PCIe interconnection; Communication performance should be passed topology with collective communication measured, and not with NVLink bandwidth.

System: Ubuntu 22.04 LTS , 4080: 16GB*2GB dual-GPU, memory 128GB

1. Installing the NVIDIA driver

 Check the driver command: Ubuntu-drivers devices

[Original note image: image.png; [Unpublished transcript]

Select the recommended version installed

Or install the recommended version automatically:
sudo ubuntu-drivers autoinstall

Install the cuda-nvidai tool

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

[Original note image: image.png; [Unpublished transcript]

The main BUG:
NVIDIA driver installed: NVIDIA-driver-550 is the most suitable.

Nvidia driver tools: need to be installed, name temporarily forgotten, Nvidia-cli toolbox, must be installed correctly, pay attention to the corresponding version, otherwise the Nvidia GPU version docker cannot be set.

Use the NVIDIA-CTK --version command to check that the NVIDIA Container Toolkit is installed correctly. ！ ！ )

[Original note image: image.png; [Unpublished transcript]

1. After the NVIDIA driver is installed, download the docker and set up the environment configuration.

Docker image replacement with domestic source is best.
To extract the vllm/openai docker image, do not use the external network, but use the internal image source:
Download link: [https://docker.aityp.com/image/docker.io/vllm/vllm-openai:v0.8.5](https://docker.aityp.com/image/docker.io/vllm/vllm-openai:v0.8.5)

1. Download the model

If you are unable to use the offline network, you can pull the model and go to the Morta community to search for the model for Deepseek-R1:32B int4 quantization;

You can use the external network to pull the model Deepseek-r1:32b int4 quantization to huggingface;

32GB of VRAM, faster to generate with Int4 quantization model tokens;

1. Creating a docker image

Create a docker parameter command: concurrency number: 8, context length: 8K, no GPU compute throughput increased, 35 tokens/s:

dual-GPU GPU utilization rate: 84%

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

vllm_test1: concurrency number:16, context 16K, int4 quantization 32b model, GPU utilization is set to 0.93, 55 tokens/s, dual-GPU GPU utilization is set to 94%.

```text
sudo docker run --name vllm_test1 --gpus all --mount type=bind,source="/srv/llm/model/DeepSeek-r1-32B_GPTQ_Int4",target=/root/model -p 8001:8000 --ipc=host swr.cn-north-4.myhuaweicloud.com/ddn-k8s/docker.io/vllm/vllm-openai:v0.6.4.post1 --model /root/model/deepseek-r1-distill-qwen-32b-gptq-int4 --max-model-len 16384 --max-num-seqs 16 --tensor-parallel-size 2 --gpu-memory-utilization 0.93 --disable-custom-all-reduce
```

Docker image name: vllm_test1

```text
sudo docker run --name vllm_test1 --gpus all --mount type=bind,source="/srv/llm/model/DeepSeek-r1-32B_GPTQ_Int4",target=/root/model -p 8001:8000 --ipc=host swr.cn-north-4.myhuaweicloud.com/ddn-k8s/docker.io/vllm/vllm-openai:v0.6.4.post1 --model /root/model/deepseek-r1-distill-qwen-32b-gptq-int4 --max-model-len 16384 --max-num-seqs 16 --tensor-parallel-size 2 --gpu-memory-utilization 0.93 --disable-custom-all-reduce

```

vllm_test2: using the dynamic KV method to run the model, speed 52 tokens/s, image version: swr.cn-north-4.myhuaweicloud.com/ddn-k8s/docker.io/vllm/vllm-openai: v0.8.5

```text
 sudo docker run --name vllm_test2   --gpus all   --mount type=bind,source="/srv/llm/model/DeepSeek-r1-32B_GPTQ_Int4",target=/root/model   -p 8001:8000   --ipc=host   -e PYTORCH_CUDA_ALLOC_CONF="expandable_segments:True,garbage_collection_threshold:0.8"   swr.cn-north-4.myhuaweicloud.com/ddn-k8s/docker.io/vllm/vllm-openai:v0.8.5   --model /root/model/deepseek-r1-distill-qwen-32b-gptq-int4   --max-model-len 16384   --tensor-parallel-size 2   --gpu-memory-utilization 0.85  --max-num-seqs 8   --max-num-batched-tokens 4096   --enable-chunked-prefill   --disable-custom-all-reduce   --block-size 32

```

vllm_ds70: DeepSeek-R1-Distill-Llama-70B-FP8-dynamic model (FP8 dynamic quantization), [GPU: A6000 48]*2GB](GPU: A6000 48*2GB), concurrency 16, context length 16K, speed 17.1 tokens/s, dual-GPU GPU occupancy rate: 98%, image version: swr.cn-north-4.myhuaweicloud.com/ddn-k8s/docker.io/vllm/vllm-openai: v0.8.5

```text
sudo docker run --name vllm_ds70   --gpus all   --mount type=bind,source="/srv/llm/model/Deepseek-r1-70b-fp8",target=/root/model   -p 8002:8000   --ipc=host   swr.cn-north-4.myhuaweicloud.com/ddn-k8s/docker.io/vllm/vllm-openai:v0.8.5   --model /root/model/DeepSeek-R1-Distill-Llama-70B-FP8-dynamic   --max-model-len 16384   --max-num-seqs 16   --tensor-parallel-size 2   --gpu-memory-utilization 0.80   --disable-custom-all-reduce

```

vllm_ds70_optimized: DeepSeek-R1-Distill-Llama-70B-FP8-dynamic model (FP8 dynamic quantization ), [GPU: A6000 48]*2GB](GPU: A6000 48*2GB), concurrency 8, context length 16K, speed 17.5 tokens/s, dual-GPU GPU occupancy rate: 99%, image version: swr.cn-north-4.myhuaweicloud.com/ddn-k8s/docker.io/vllm/vllm-openai: v0.8.5

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

Please note:

Note: When creating a folder name, do not add any special symbols: for example, pseudonyms:

Note: When installing a model file, the path must be correct.

Note: Each model creates a docker separately and does not use multiple models in a docker.

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

**Note: Docker configuration NVIDIA runtime**

/usr/local/nvidia/toolkit/nvidia-container-runtime

The error was caused by a lack of configuration of the NVIDIA Container Toolkit.

1. First, check if the NVIDIA Container Toolkit is installed correctly:

```text
nvidia-ctk --version
```

1. Verify the NVIDIA Docker runtime:

```text
sudo docker info | grep nvidia
```

1. If it just doesn't run, the first step is to execute a string of characters to show that there's no problem, and then the configuration is done.

```text
# 配置 Docker 使用 NVIDIA 运行时
sudo nvidia-ctk runtime configure --runtime=docker

# 重启 Docker 服务
sudo systemctl restart docker
```
