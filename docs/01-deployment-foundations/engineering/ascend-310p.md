# 昇腾310P3：CANN容器、Qwen3部署与性能验收

[工程实例索引](README.md) · [知识体系总目录](../SUMMARY.md)

技术标签：`CANN / torch_npu / vLLM Ascend / TP2 / EvalScope`

## 工程配置

| 项目 | 原记录 |
| --- | --- |
| 设备 | 昇腾310P3，双设备 |
| 模型 | Qwen3-32B；Qwen3-235B-A22B作为另一配置探索 |
| 镜像 | quay.io/ascend/vllm-ascend:v0.10.0rc1-310p |
| 32B有效路线 | float16、TP2、mp、eager、block64、swap16 |
| 历史长输出 | 1请求、14336输出token、3120.88s、约4.5936token/s |

## 完整部署适配过程

1. `npu-smi info`核对芯片、驱动/固件，固定CANN、torch_npu、插件和镜像配套。310P的支持不能套用910系列。
2. 准备HF完整模型目录，显式挂载`davinci0/1`、manager、svm和驱动库。原文多种镜像、MindIE与插件版本属于不同实验分支，分别复建。
3. 进入容器先检查设备，再运行下方float16的32B路径。源材料另有bfloat16/235B命令，它们是尝试配置，不等于在双310P完成容量和算子验收。
4. 从可工作的目录启动，记录模块导入位置与`VLLM_USE_V1`的最终值；定位源码遮蔽后再切换执行模式。
5. 端点与字段匹配后做单请求、流式和长度验收，再进入EvalScope。原`parallel10/number1`实际上只提交一个请求。

## 加速优化与验收

先保证float16算子路径、TP2通信和短请求正确；再对ctx、活动序列、block、eager/图模式及插件支持的算子优化做分项实验。每次保存实际生效参数、NPU内存/利用率、输出token和墙钟时间。

现有14336token长生成只证明该样例，不能证明十并发或稳定p99。新并发测试应固定长度、足够请求数，检查超时、结束原因与质量。下面保留完整容器、源码、MindIE尝试、服务启动、压测和原日志；失败配置不改成成功。

## 完整技术记录的使用约定

以下直接保留相关FlowUs文章的技术正文、命令、表格、日志、失败和后续实验，不以摘要替代原过程。私人路径、节点、认证与附件地址脱敏；`<NODE_IP>`等占位符需要按当前环境填写。原建议或预测仍是建议或预测。上方执行顺序与技术修订用于解释历史记录中的冲突，历史GPU/NPU实验未在本轮重跑。

## R45 · 华为昇腾310P3推理Qwen3-32B

```text
# 镜像网站
https://quay.io/repository/ascend/vllm-ascend?tab=tags
# 镜像版本
docker pull quay.io/ascend/vllm-ascend:v0.10.0rc1-310p

# 创建容器,存在容器直接进入容器即可
docker run -it -d --net=host --shm-size=16g \
    --privileged \
    --name qwen3-32n-v010 \
    --device=/dev/davinci_manager \
    --device=/dev/hisi_hdc \
    --device=/dev/devmm_svm \
    --device=/dev/davinci0 \
    --device=/dev/davinci1 \
    -v /usr/local/Ascend/driver:/usr/local/Ascend/driver:ro \
    -v /usr/local/sbin:/usr/local/sbin:ro \
    -v /data/models/:/data/models:ro \
    quay.io/ascend/vllm-ascend:v0.10.0rc1-310p bash

# 进入容器
  docker exec -it qwen3-32n-v010 /bin/bash

# 设置环境变量，先进行推理，能推理成功就不需要设置
# export VLLM_USE_V1=1

# 进入vllm-workspace或者vllm目录运行推理命令
  cd vllm-workspace

# 推理命令
python -m vllm.entrypoints.openai.api_server   --model /data/models/Qwen3-32B   --served-model-name Qwen3-32B   --host 0.0.0.0   --port 8000   --tensor-parallel-size 2   --dtype float16   --max-model-len 32768   --gpu-memory-utilization 0.95   --distributed-executor-backend mp   --enforce-eager   --trust-remote-code   --block-size 64   --swap-space 16

#注：如果推理失败，退出并关闭容器，重新启动并进入容器，重新执行推理操作。

# 测试
curl [服务地址按本实例配置] \
   -H "Content-Type: application/json" \
   -d '{
     "model": "Qwen3-32B",
     "prompt": "请解释人工智能的未来发展趋势",
     "max_tokens": 200,
     "temperature": 0.7,
     "top_p": 0.9,
     "stream": true
   }'

# 使用conda创建一个虚拟环境
  conda create -n evalscope-test python=3.10
# 激活环境
  conda activate evalscope-test

安装以下模块
# 性能压测
pip install evalscope
# 压测模块
pip install 'evalscope[perf]'

# 性能压测命令 并发数10
evalscope perf \
  --url "http://127.0.0.1:8000/v1/completions" \
  --model "Qwen3-32B" \
  --api openai \
  --dataset openqa \
  --parallel 10 \
  --number 1 \
  --max-tokens 14336 \
  --min-tokens 1024 \
  --stream \
  --connect-timeout 60 \
  --read-timeout 120 \
  --log-every-n-query 1 \
  --name "Qwen3-32B"


# 打开新的终端，实时查看NPU占用
watch -n 1 "npu-smi info"
```

注：如果推理出现以下错误，就不要在源码目录下使用推理命令，直接在workspace目录下执行推理命令即可；

取消使用V1模式：unset VLLM_USE_V1

[原笔记图片：image.png；未公开转存]

执行成功：

[原笔记图片：image.png；未公开转存]

[原笔记图片：图片.png；未公开转存]

## R46 · 华为昇腾310p3：qwen3-32b与qwen3-235b-a22b-2507测试

1. 模型下载

```text
# qwen3-32b下载
modelscope download --model Qwen/Qwen3-32B --local_dir ./

# qwen3-235b-a22b模型
modelscope download --model Qwen/Qwen3-235B-A22B-Instruct-2507 --local_dir ./

# 拉取vllm-ascend源码，编译docker镜像
git clone https://github.com/vllm-project/vllm-ascend.git
cd vllm-ascend
docker build -t vllm-ascend-dev-image:latest -f ./Dockerfile .

# 创建容器
docker run --name qwen3-32b-vllm     --device /dev/davinci0     --device /dev/davinci1     --device /dev/davinci_manager     --device /dev/devmm_svm     --device /dev/hisi_hdc     -v /srv/models/qwen3-32b:/models/qwen3-32b     -v /usr/local/dcmi:/usr/local/dcmi     -v /usr/local/bin/npu-smi:/usr/local/bin/npu-smi     -v /usr/local/Ascend/driver/lib64:/usr/local/Ascend/driver/lib64  -v /usr/local/Ascend/driver/version.info:/usr/local/Ascend/driver/version.info   -v /etc/ascend_install.info:/etc/ascend_install.info     -p 8000:8000     -it quay.nju.edu.cn/ascend/vllm-ascend/vllm-ascend:main-310p bash

# 进入容器
docker exec -it qwen3-32b-vllm /bin/bash

# 使用vllm推理qwen3-32b
python -m vllm.entrypoints.openai.api_server \
  --model /models/qwen3-32b \
  --served-model-name Qwen3-32B \
  --host 0.0.0.0 \
  --port 8000 \
  --tensor-parallel-size 2 \
  --dtype bfloat16 \
  --max-model-len 32768 \
  --gpu-memory-utilization 0.85 \
  --distributed-executor-backend mp \
  --enforce-eager \
  --trust-remote-code \
  --block-size 64 \
  --swap-space 16

命令2：
python -m vllm.entrypoints.api_server \
    --model /models/qwen3-32b \
    --tensor-parallel-size 2 \
    --max-model-len 8192 \
    --dtype float16 \
    --trust-remote-code \
    --port 8000 \
    --compilation-config '{"custom_ops":["+rms_norm", "+rotary_embedding"]}'
```

```text
docker run --name qwen3-32b-dev-vllm   --device /dev/davinci0   --device /dev/davinci1   --device /dev/davinci_manager   --device /dev/devmm_svm   --device /dev/hisi_hdc   -v /srv/models/qwen3-32b:/models/qwen3-32b   -v /usr/local/dcmi:/usr/local/dcmi   -v /usr/local/bin/npu-smi:/usr/local/bin/npu-smi   -v /usr/local/Ascend/driver/lib64:/usr/local/Ascend/driver/lib64   -v /etc/ascend_install.info:/etc/ascend_install.info -v /usr/local/Ascend/driver/version.info:/usr/local/Ascend/driver/version.info  -p 8000:8000   -it vllm-ascend-dev-image:latest   bash


docker run --name qwen3-32b-073   --device /dev/davinci0   --device /dev/davinci1   --device /dev/davinci_manager   --device /dev/devmm_svm   --device /dev/hisi_hdc   -v /srv/models/qwen3-32b:/models/qwen3-32b   -v /usr/local/dcmi:/usr/local/dcmi   -v /usr/local/bin/npu-smi:/usr/local/bin/npu-smi   -v /usr/local/Ascend/driver/lib64:/usr/local/Ascend/driver/lib64   -v /etc/ascend_install.info:/etc/ascend_install.info -v /usr/local/Ascend/driver/version.info:/usr/local/Ascend/driver/version.info  -p 8000:8000   -it quay.io/ascend/vllm-ascend:v0.7.3.post1   bash


# mindie镜像
docker run -it -d --net=host --shm-size=16g \
    --name Qwen3-32B-Mindie \
    --device=/dev/davinci_manager \
    --device=/dev/hisi_hdc \
    --device=/dev/devmm_svm \
    --device=/dev/davinci0 \
    --device=/dev/davinci1 \
    -v /usr/local/dcmi:/usr/local/dcmi \
    -v /usr/local/bin/npu-smi:/usr/local/bin/npu-smi \
    -v /usr/local/Ascend/driver/lib64/:/usr/local/Ascend/driver/lib64/ \
    -v /usr/local/Ascend/driver/version.info:/usr/local/Ascend/driver/version.info \
    -v /etc/ascend_install.info:/etc/ascend_install.info \
    -v /data/models/:/data/models/ \
    -it swr.cn-south-1.myhuaweicloud.com/ascendhub/mindie:1.0.0-300I-Duo-py311-openeuler24.03-lts bash


cd /usr/local/Ascend/mindie/latest/mindie-service

./mindieservice_daemon > output.log 2>&1 & tail -f output.log

```

confog.json

```text
{
    "Version" : "1.1.0",
    "LogConfig" :
    {
        "logLevel" : "Info",
        "logFileSize" : 20,
        "logFileNum" : 20,
        "logPath" : "logs/mindservice.log"
    },

    "ServerConfig" :
    {
        "ipAddress" : "127.0.0.1",
        "managementIpAddress" : "127.0.0.2",
        "port" : 1025,
        "managementPort" : 1026,
        "metricsPort" : 1027,
        "allowAllZeroIpListening" : false,
        "maxLinkNum" : 1000,
        "httpsEnabled" : false,
        "fullTextEnabled" : false,
        "tlsCaPath" : "security/ca/",
        "tlsCaFile" : ["ca.pem"],
        "tlsCert" : "security/certs/server.pem",
        "tlsPk" : "security/keys/server.key.pem",
        "tlsPkPwd" : "security/pass/key_pwd.txt",
        "tlsCrlPath" : "security/certs/",
        "tlsCrlFiles" : ["server_crl.pem"],
        "managementTlsCaFile" : ["management_ca.pem"],
        "managementTlsCert" : "security/certs/management/server.pem",
        "managementTlsPk" : "security/keys/management/server.key.pem",
        "managementTlsPkPwd" : "security/pass/management/key_pwd.txt",
        "managementTlsCrlPath" : "security/management/certs/",
        "managementTlsCrlFiles" : ["server_crl.pem"],
        "kmcKsfMaster" : "tools/pmt/master/ksfa",
        "kmcKsfStandby" : "tools/pmt/standby/ksfb",
        "inferMode" : "standard",
        "interCommTLSEnabled" : true,
        "interCommPort" : 1121,
        "interCommTlsCaPath" : "security/grpc/ca/",
        "interCommTlsCaFiles" : ["ca.pem"],
        "interCommTlsCert" : "security/grpc/certs/server.pem",
        "interCommPk" : "security/grpc/keys/server.key.pem",
        "interCommPkPwd" : "security/grpc/pass/key_pwd.txt",
        "interCommTlsCrlPath" : "security/grpc/certs/",
        "interCommTlsCrlFiles" : ["server_crl.pem"],
        "openAiSupport" : "vllm"
    },

    "BackendConfig" : {
        "backendName" : "mindieservice_llm_engine",
        "modelInstanceNumber" : 1,
        "npuDeviceIds" : [[0,1]],
        "tokenizerProcessNumber" : 8,
        "multiNodesInferEnabled" : false,
        "multiNodesInferPort" : 1120,
        "interNodeTLSEnabled" : true,
        "interNodeTlsCaPath" : "security/grpc/ca/",
        "interNodeTlsCaFiles" : ["ca.pem"],
        "interNodeTlsCert" : "security/grpc/certs/server.pem",
        "interNodeTlsPk" : "security/grpc/keys/server.key.pem",
        "interNodeTlsPkPwd" : "security/grpc/pass/mindie_server_key_pwd.txt",
        "interNodeTlsCrlPath" : "security/grpc/certs/",
        "interNodeTlsCrlFiles" : ["server_crl.pem"],
        "interNodeKmcKsfMaster" : "tools/pmt/master/ksfa",
        "interNodeKmcKsfStandby" : "tools/pmt/standby/ksfb",
        "ModelDeployConfig" :
        {
            "maxSeqLen" : 2560,
            "maxInputTokenLen" : 2048,
            "truncation" : false,
            "ModelConfig" : [
                {
                    "modelInstanceType" : "Standard",
                    "modelName" : "Qwen3-32b",
                    "modelWeightPath" : "/data/models/qwen3-32b",
                    "worldSize" : 2,
                    "cpuMemSize" : 5,
                    "npuMemSize" : -1,
                    "backendType" : "atb",
                    "trustRemoteCode" : false
                }
            ]
        },

        "ScheduleConfig" :
        {
            "templateType" : "Standard",
            "templateName" : "Standard_LLM",
            "cacheBlockSize" : 128,

            "maxPrefillBatchSize" : 200,
            "maxPrefillTokens" : 8192,
            "prefillTimeMsPerReq" : 150,
            "prefillPolicyType" : 0,

            "decodeTimeMsPerReq" : 50,
            "decodePolicyType" : 0,

            "maxBatchSize" : 200,
            "maxIterTimes" : 512,
            "maxPreemptCount" : 0,
            "supportSelectBatch" : true,
            "maxQueueDelayMicroseconds" : 5000
        }
    }
}
```

```text
# 镜像网站
https://quay.io/repository/ascend/vllm-ascend?tab=tags
# 镜像版本
docker pull quay.io/ascend/vllm-ascend:v0.10.0rc1-310p

# 创建容器
docker run -it -d --net=host --shm-size=16g \
    --privileged \
    --name qwen3-32n-v010 \
    --device=/dev/davinci_manager \
    --device=/dev/hisi_hdc \
    --device=/dev/devmm_svm \
    --device=/dev/davinci0 \
    --device=/dev/davinci1 \
    -v /usr/local/Ascend/driver:/usr/local/Ascend/driver:ro \
    -v /usr/local/sbin:/usr/local/sbin:ro \
    -v /data/models/:/data/models:ro \
    quay.io/ascend/vllm-ascend:v0.10.0rc1-310p bash

# 设置环境变量
  export VLLM_USE_V1=1


# 推理命令
python -m vllm.entrypoints.openai.api_server   --model /data/models/Qwen3-32B   --served-model-name Qwen3-32B   --host 0.0.0.0   --port 8000   --tensor-parallel-size 2   --dtype float16   --max-model-len 32768   --gpu-memory-utilization 0.95   --distributed-executor-backend mp   --enforce-eager   --trust-remote-code   --block-size 64   --swap-space 16

# benchmark测试
进入benchmarks目录安装必备库：
cd /vllm-workspace/vllm-ascend/benchmarks
pip install -r requirements-bench.txt

```

华为昇腾310P3推理Qwen3-32B（私人页面链接不公开）

昇腾310P3部署Qwen3-32B benchmark记录（私人页面链接不公开）

## R47 · 昇腾310P3部署Qwen3-32B benchmark记录

1. 并发数10 ，对话轮次1，最大上下文16384

```text
Benchmarking summary:
+-----------------------------------+------------+
| Key                               |      Value |
+===================================+============+
| Time taken for tests (s)          |  3120.88   |
+-----------------------------------+------------+
| Number of concurrency             |    10      |
+-----------------------------------+------------+
| Total requests                    |     1      |
+-----------------------------------+------------+
| Succeed requests                  |     1      |
+-----------------------------------+------------+
| Failed requests                   |     0      |
+-----------------------------------+------------+
| Output token throughput (tok/s)   |     4.5936 |
+-----------------------------------+------------+
| Total token throughput (tok/s)    |     4.5984 |
+-----------------------------------+------------+
| Request throughput (req/s)        |     0.0003 |
+-----------------------------------+------------+
| Average latency (s)               |  3120.88   |
+-----------------------------------+------------+
| Average time to first token (s)   |     0.2364 |
+-----------------------------------+------------+
| Average time per output token (s) |     0.2177 |
+-----------------------------------+------------+
| Average inter-token latency (s)   |     0.2177 |
+-----------------------------------+------------+
| Average input tokens per request  |    15      |
+-----------------------------------+------------+
| Average output tokens per request | 14336      |
+-----------------------------------+------------+
2025-08-21 15:04:35,755 - evalscope - INFO -
Percentile results:
+-------------+----------+---------+----------+-------------+--------------+---------------+----------------+---------------+
| Percentiles | TTFT (s) | ITL (s) | TPOT (s) | Latency (s) | Input tokens | Output tokens | Output (tok/s) | Total (tok/s) |
+-------------+----------+---------+----------+-------------+--------------+---------------+----------------+---------------+
|     10%     |  0.2364  |  0.21   |  0.2177  |  3120.8792  |      15      |     14336     |     4.5936     |    4.5984     |
|     25%     |  0.2364  |  0.213  |  0.2177  |  3120.8792  |      15      |     14336     |     4.5936     |    4.5984     |
|     50%     |  0.2364  | 0.2176  |  0.2177  |  3120.8792  |      15      |     14336     |     4.5936     |    4.5984     |
|     66%     |  0.2364  | 0.2207  |  0.2177  |  3120.8792  |      15      |     14336     |     4.5936     |    4.5984     |
|     75%     |  0.2364  | 0.2225  |  0.2177  |  3120.8792  |      15      |     14336     |     4.5936     |    4.5984     |
|     80%     |  0.2364  | 0.2234  |  0.2177  |  3120.8792  |      15      |     14336     |     4.5936     |    4.5984     |
|     90%     |  0.2364  | 0.2254  |  0.2177  |  3120.8792  |      15      |     14336     |     4.5936     |    4.5984     |
|     95%     |  0.2364  | 0.2264  |  0.2177  |  3120.8792  |      15      |     14336     |     4.5936     |    4.5984     |
|     98%     |  0.2364  |  0.227  |  0.2177  |  3120.8792  |      15      |     14336     |     4.5936     |    4.5984     |
|     99%     |  0.2364  | 0.2273  |  0.2177  |  3120.8792  |      15      |     14336     |     4.5936     |    4.5984     |
+-------------+----------+---------+----------+-------------+--------------+---------------+----------------+---------------+
2025-08-21 15:04:35,755 - evalscope - INFO - Save the summary to: outputs/20250821_141231/Qwen3-32B
```

1. 并发数10 ，对话轮次5，最大上下文8192

```text
2025-08-21 15:43:59,292 - evalscope - INFO -
Benchmarking summary:
+-----------------------------------+-----------+
| Key                               |     Value |
+===================================+===========+
| Time taken for tests (s)          | 1816.71   |
+-----------------------------------+-----------+
| Number of concurrency             |   10      |
+-----------------------------------+-----------+
| Total requests                    |    5      |
+-----------------------------------+-----------+
| Succeed requests                  |    5      |
+-----------------------------------+-----------+
| Failed requests                   |    0      |
+-----------------------------------+-----------+
| Output token throughput (tok/s)   |    9.8376 |
+-----------------------------------+-----------+
| Total token throughput (tok/s)    |    9.8882 |
+-----------------------------------+-----------+
| Request throughput (req/s)        |    0.0028 |
+-----------------------------------+-----------+
| Average latency (s)               |  790.009  |
+-----------------------------------+-----------+
| Average time to first token (s)   |    0.4526 |
+-----------------------------------+-----------+
| Average time per output token (s) |    0.2158 |
+-----------------------------------+-----------+
| Average inter-token latency (s)   |    0.2209 |
+-----------------------------------+-----------+
| Average input tokens per request  |   18.4    |
+-----------------------------------+-----------+
| Average output tokens per request | 3574.4    |
+-----------------------------------+-----------+
2025-08-21 15:43:59,305 - evalscope - INFO -
Percentile results:
+-------------+----------+---------+----------+-------------+--------------+---------------+----------------+---------------+
| Percentiles | TTFT (s) | ITL (s) | TPOT (s) | Latency (s) | Input tokens | Output tokens | Output (tok/s) | Total (tok/s) |
+-------------+----------+---------+----------+-------------+--------------+---------------+----------------+---------------+
|     10%     |  0.2374  | 0.2125  |  0.2111  |   19.9255   |      12      |      93       |     4.5092     |    4.5181     |
|     25%     |  0.5052  | 0.2146  |  0.2118  |   87.1425   |      15      |      410      |     4.5098     |    4.5219     |
|     50%     |  0.5068  | 0.2205  |  0.2127  |  209.7766   |      21      |      985      |     4.6674     |    4.7956     |
|     66%     |  0.5068  | 0.2244  |  0.2217  |  1816.4916  |      21      |     8192      |     4.6955     |    4.8426     |
|     75%     |  0.5068  | 0.2267  |  0.2217  |  1816.4916  |      21      |     8192      |     4.6955     |    4.8426     |
|     80%     |  0.5069  |  0.228  |  0.2217  |  1816.7107  |      23      |     8192      |     4.7049     |    5.7213     |
|     90%     |  0.5069  | 0.2306  |  0.2217  |  1816.7107  |      23      |     8192      |     4.7049     |    5.7213     |
|     95%     |  0.5069  | 0.2317  |  0.2217  |  1816.7107  |      23      |     8192      |     4.7049     |    5.7213     |
|     98%     |  0.5069  | 0.2326  |  0.2217  |  1816.7107  |      23      |     8192      |     4.7049     |    5.7213     |
|     99%     |  0.5069  | 0.2332  |  0.2217  |  1816.7107  |      23      |     8192      |     4.7049     |    5.7213     |
+-------------+----------+---------+----------+-------------+--------------+---------------+----------------+---------------+
2025-08-21 15:43:59,305 - evalscope - INFO - Save the summary to: outputs/20250821_151340/Qwen3-32B
```

1. 并发数30 ，对话轮次5，最大上下文8192

```text
2025-08-21 17:12:29,348 - evalscope - INFO -
Benchmarking summary:
+-----------------------------------+-----------+
| Key                               |     Value |
+===================================+===========+
| Time taken for tests (s)          | 1817.25   |
+-----------------------------------+-----------+
| Number of concurrency             |   30      |
+-----------------------------------+-----------+
| Total requests                    |    5      |
+-----------------------------------+-----------+
| Succeed requests                  |    5      |
+-----------------------------------+-----------+
| Failed requests                   |    0      |
+-----------------------------------+-----------+
| Output token throughput (tok/s)   |    9.8346 |
+-----------------------------------+-----------+
| Total token throughput (tok/s)    |    9.8853 |
+-----------------------------------+-----------+
| Request throughput (req/s)        |    0.0028 |
+-----------------------------------+-----------+
| Average latency (s)               |  790.213  |
+-----------------------------------+-----------+
| Average time to first token (s)   |    0.4398 |
+-----------------------------------+-----------+
| Average time per output token (s) |    0.2159 |
+-----------------------------------+-----------+
| Average inter-token latency (s)   |    0.221  |
+-----------------------------------+-----------+
| Average input tokens per request  |   18.4    |
+-----------------------------------+-----------+
| Average output tokens per request | 3574.4    |
+-----------------------------------+-----------+
2025-08-21 17:12:29,361 - evalscope - INFO -
Percentile results:
+-------------+----------+---------+----------+-------------+--------------+---------------+----------------+---------------+
| Percentiles | TTFT (s) | ITL (s) | TPOT (s) | Latency (s) | Input tokens | Output tokens | Output (tok/s) | Total (tok/s) |
+-------------+----------+---------+----------+-------------+--------------+---------------+----------------+---------------+
|     10%     |  0.2363  | 0.2125  |  0.2114  |   19.9356   |      12      |      93       |     4.5079     |    4.5167     |
|     25%     |  0.4895  | 0.2146  |  0.2118  |   87.1266   |      15      |      410      |     4.5084     |    4.5206     |
|     50%     |  0.4905  | 0.2206  |  0.2126  |  209.7156   |      21      |      985      |     4.665      |     4.797     |
|     66%     |  0.4909  | 0.2246  |  0.2218  |  1817.0339  |      21      |     8192      |     4.6968     |    4.8435     |
|     75%     |  0.4909  | 0.2268  |  0.2218  |  1817.0339  |      21      |     8192      |     4.6968     |    4.8435     |
|     80%     |  0.4918  | 0.2279  |  0.2218  |  1817.2529  |      23      |     8192      |     4.7058     |    5.7184     |
|     90%     |  0.4918  | 0.2307  |  0.2218  |  1817.2529  |      23      |     8192      |     4.7058     |    5.7184     |
|     95%     |  0.4918  |  0.232  |  0.2218  |  1817.2529  |      23      |     8192      |     4.7058     |    5.7184     |
|     98%     |  0.4918  | 0.2328  |  0.2218  |  1817.2529  |      23      |     8192      |     4.7058     |    5.7184     |
|     99%     |  0.4918  | 0.2333  |  0.2218  |  1817.2529  |      23      |     8192      |     4.7058     |    5.7184     |
+-------------+----------+---------+----------+-------------+--------------+---------------+----------------+---------------+
2025-08-21 17:12:29,361 - evalscope - INFO - Save the summary to: outputs/20250821_164209/Qwen3-32B
```

1. 并发数1，对话5，最大上下文8192

```text
2025-08-22 15:17:58,603 - evalscope - INFO -
Benchmarking summary:
+-----------------------------------+-----------+
| Key                               |     Value |
+===================================+===========+
| Time taken for tests (s)          | 3814.46   |
+-----------------------------------+-----------+
| Number of concurrency             |    1      |
+-----------------------------------+-----------+
| Total requests                    |    5      |
+-----------------------------------+-----------+
| Succeed requests                  |    5      |
+-----------------------------------+-----------+
| Failed requests                   |    0      |
+-----------------------------------+-----------+
| Output token throughput (tok/s)   |    4.6853 |
+-----------------------------------+-----------+
| Total token throughput (tok/s)    |    4.7094 |
+-----------------------------------+-----------+
| Request throughput (req/s)        |    0.0013 |
+-----------------------------------+-----------+
| Average latency (s)               |  762.89   |
+-----------------------------------+-----------+
| Average time to first token (s)   |    0.2315 |
+-----------------------------------+-----------+
| Average time per output token (s) |    0.2106 |
+-----------------------------------+-----------+
| Average inter-token latency (s)   |    0.2134 |
+-----------------------------------+-----------+
| Average input tokens per request  |   18.4    |
+-----------------------------------+-----------+
| Average output tokens per request | 3574.4    |
+-----------------------------------+-----------+
2025-08-22 15:17:58,618 - evalscope - INFO -
Percentile results:
+-------------+----------+---------+----------+-------------+--------------+---------------+----------------+---------------+
| Percentiles | TTFT (s) | ITL (s) | TPOT (s) | Latency (s) | Input tokens | Output tokens | Output (tok/s) | Total (tok/s) |
+-------------+----------+---------+----------+-------------+--------------+---------------+----------------+---------------+
|     10%     |  0.2281  | 0.2087  |  0.208   |   19.3695   |      12      |      93       |     4.6755     |    4.6849     |
|     25%     |  0.2308  | 0.2103  |  0.2083  |   85.4368   |      15      |      410      |     4.6763     |    4.6887     |
|     50%     |  0.2315  | 0.2135  |  0.2088  |  205.7391   |      21      |      985      |     4.7876     |    4.8897     |
|     66%     |  0.2327  | 0.2154  |  0.2138  |  1751.802   |      21      |     8192      |     4.7989     |    4.9393     |
|     75%     |  0.2327  | 0.2164  |  0.2138  |  1751.802   |      21      |     8192      |     4.7989     |    4.9393     |
|     80%     |  0.2343  |  0.217  |  0.2139  |  1752.1015  |      23      |     8192      |     4.8014     |    5.8855     |
|     90%     |  0.2343  | 0.2181  |  0.2139  |  1752.1015  |      23      |     8192      |     4.8014     |    5.8855     |
|     95%     |  0.2343  | 0.2187  |  0.2139  |  1752.1015  |      23      |     8192      |     4.8014     |    5.8855     |
|     98%     |  0.2343  | 0.2192  |  0.2139  |  1752.1015  |      23      |     8192      |     4.8014     |    5.8855     |
|     99%     |  0.2343  | 0.2196  |  0.2139  |  1752.1015  |      23      |     8192      |     4.8014     |    5.8855     |
+-------------+----------+---------+----------+-------------+--------------+---------------+----------------+---------------+
2025-08-22 15:17:58,618 - evalscope - INFO - Save the summary to: outputs/20250822_141421/Qwen3-32B
(evalscope-test)
```
