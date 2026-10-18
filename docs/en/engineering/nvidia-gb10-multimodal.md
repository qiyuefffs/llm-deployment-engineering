# NVIDIA GB10 Multimodals: Links for deployment of VL, Omni and document models

[简体中文](../../01-deployment-foundations/engineering/nvidia-gb10-multimodal.md) | **English**

[Index of engineering examples](README.md) · [General directory of knowledge systems](../SUMMARY.md)

Technical labels: `vLLM / processor / image / audio / SSE`

## Model and execution boundaries

|Model|Basic service configuration|Independent acceptance testing|
| --- | --- | --- |
| Qwen3-VL-8B |memory0.8, port 8007|Text, graphics, image tokens, encoders, and SSE|
| Qwen3-VL-30B-A3B |Context configuration See full text|Multi-chart/longchart input with memory that cannot be derived from max-model-len has passed length|
| Qwen2.5-VL-7B |ARM64 support container|Processor versions, image fields and complete answers|
| Qwen3-Omni-30B-A3B |memory0.9, port 8008|Testing of text/images/audio input and output respectively|
| granite-docling-258M | TP1/PP1,seqs512,batched8192 |DocTags, table sequences, leaks, 512 is not a proven valid concurrency|

## Full deployment and acceleration path

First, attach the image to the full directory of the model, run pure text, and then add the image. The image should preserve the byte abstract, size, preprocessing after-token and expected content; Original private images not public, rebuilt and reused [Public test cards and full client](../chapters/frameworks/vllm-service.md#seven-complete-links-from-image-files-to-streaming-answers).

Optimize button image resolution/cutting budget→ encoder batching → text scheduling → concurrency Reduced resolution may result in loss of small letters, cache life requires the same input as the processor, and cannot only look at text tokens/s. Audio records individual sampling rates, lead audio latency, continuous RTF and content accuracy.

The following is a complete description of the original installation, start, request, code and output of each model. The new test card does not include unimplemented model responses; The model has the capability and the ability to support current service inputs, respectively, acceptance testing.

## Agreement on the use of complete technical records

The following technical correctness, commands, tables, logs, failures and subsequent experiments of the relevant FlowUs articles are retained directly, without abbreviating the original process. private paths, nodes, authentication and sanitization of attached addresses; `<NODE_IP>` For example, the placeholder needs to be filled in the current environment. The original suggestion or prediction is still a suggestion or prediction. The above execution sequence and technical revisions are used to explain conflicts in historical records, and historical GPU/NPU experiments have not been repeated in this round.

## R13 · GB10 deploying Qwen 3-VL-8B model

```text
# 容器创建命令
docker run  -it \
  --name Qwen3-VL-8B-Instruct \
  --gpus all \
  --ipc=host \
  --shm-size=32g \
  -v /srv/llm/models/Qwen3-VL-8B-Instruct:/app/model:ro  \
  -v ~/.cache/huggingface:/root/.cache/huggingface:rw \
  -p 8007:8007 \
  nvcr.io/nvidia/vllm:25.12-py3 \
  /bin/bash


  # 推理命令
  vllm serve /app/model \
  --host 0.0.0.0 \
  --port 8007 \
  --served-model-name qwen3-vl-8b-instruct \
  --trust-remote-code \
  --tensor-parallel-size 1 \
  --pipeline-parallel-size 1 \
  --gpu-memory-utilization 0.8
```

```text
import base64
import requests
import json

def run_image_stream_inference(image_path):
    # -------- 配置 --------
    API_URL = "http://<NODE_IP>:8007/v1/chat/completions"
    MODEL_NAME = "qwen3-vl-8b-instruct"

    # -------- 读取图片并转 base64 --------
    try:
        with open(image_path, "rb") as f:
            image_bytes = f.read()
    except FileNotFoundError:
        print(f"[错误] 找不到文件: {image_path}")
        return
    except Exception as e:
        print("[错误] 打开图片失败:", e)
        return

    image_base64 = base64.b64encode(image_bytes).decode("utf-8")

    # -------- 构造请求体 --------
    payload = {
        "model": MODEL_NAME,
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": "请描述这张图片的内容，并指出图片中的重点元素。"
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{image_base64}"
                        }
                    }
                ]
            }
        ],
        "stream": True   # ⭐ 开启流式输出
    }

    headers = {
        "Content-Type": "application/json"
    }

    # -------- 发送请求 (流式) --------
    print("=== 请求已发送，开始接收流式输出... ===")
    try:
        with requests.post(API_URL, headers=headers, data=json.dumps(payload), stream=True, timeout=300) as response:
            print("HTTP Status:", response.status_code)

            # 如果状态不是 200，则直接打印错误
            if response.status_code != 200:
                print("[错误] 服务端返回:")
                print(response.text)
                return

            # 一行一行读取 SSE / chunk 流
            for line in response.iter_lines(decode_unicode=True):
                if not line:
                    continue

                try:
                    text = line.strip()
                    # 如果是 SSE 的 data: 开头
                    if text.startswith("data: "):
                        text = text[len("data: "):]

                    # 检查是否结束标记
                    if text == "[DONE]":
                        print("\n=== 流式输出结束 ===")
                        break

                    # 解析 JSON
                    chunk = json.loads(text)
                    if "choices" in chunk:
                        for c in chunk["choices"]:
                            delta = c.get("delta")
                            if delta and "content" in delta:
                                print(delta["content"], end="", flush=True)

                except json.JSONDecodeError:
                    # 不是 JSON 的部分也打印出来
                    print(line)

    except Exception as e:
        print("[错误] 网络请求过程中出现异常:", e)


if __name__ == "__main__":
    print("=== Qwen3-VL-8B-Instruct 图片解析 流式推理 ===")
    img_path = input("请输入要解析的本地图片路径: ").strip()
    run_image_stream_inference(img_path)

```

## R14 · nvidia GB10 deployed Qwen 2.5-VL-7B

```text
# 容器创建命令
docker run  -it \
  --name Qwen2.5-VL-7B \
  --gpus all \
  --ipc=host \
  --shm-size=32g \
  -v /srv/llm/models/Qwen2.5-VL-7B-Instruct:/app/model:ro  \
  -v ~/.cache/huggingface:/root/.cache/huggingface:rw \
  -p 8000:8000 \
  nvcr.io/nvidia/vllm:25.11-py3 \
  /bin/bash\


# vllm推理命令
vllm serve /app/model \
  --host 0.0.0.0 \
  --port 8000 \
  --tensor-parallel-size 1 \
  --pipeline-parallel-size 1 \
  --gpu-memory-utilization 0.8 \

```

Tests record first response, full response time, flow response control, image path input

```text
import base64
import time
import json
import requests

# -------------------------
API_BASE = "[服务地址按本实例配置]
MODEL_NAME = "/app/model"  # 根据 curl [服务地址按本实例配置] 确认

# 输入模式选择
mode = input("请选择输出模式 (1: 流式输出, 2: 非流式输出):\n> ").strip()

while mode not in ("1", "2"):
    mode = input("输入无效，请重新输入 (1 或 2):\n> ").strip()

is_stream = (mode == "1")

# 输入图片路径
IMAGE_PATH = input("请输入推理图片路径 (例如 /srv/llm/models/test.jpg):\n> ").strip()

# 读取并 Base64 编码
try:
    with open(IMAGE_PATH, "rb") as f:
        image_bytes = f.read()
except FileNotFoundError:
    print(f"错误：未找到图片 {IMAGE_PATH}")
    exit(1)

b64_str = base64.b64encode(image_bytes).decode("utf-8")
b64_uri = f"data:image/jpeg;base64,{b64_str}"

# 构造请求体
body = {
    "model": MODEL_NAME,
    "messages": [
        {
            "role": "user",
            "content": [
                {"type": "text", "text": "请描述这张图片的内容。"},
                {
                    "type": "image_url",
                    "image_url": {"url": b64_uri}
                }
            ],
        }
    ],
    "stream": is_stream
}

url = f"{API_BASE}/chat/completions"
headers = {"Content-Type": "application/json"}

print("开始发送请求到 vLLM ...")

start_total = time.time()
first_token_time = None
collected_text = ""

if is_stream:
    # 流式 SSE 处理
    with requests.post(url, headers=headers, data=json.dumps(body), stream=True) as resp:
        if resp.status_code != 200:
            print(f"错误 HTTP 状态码: {resp.status_code}")
            print(resp.text)
        else:
            print("\n--- 生成开始（流式输出）---")
            for line in resp.iter_lines(decode_unicode=True):
                if not line:
                    continue
                line = line.strip()
                # vLLM SSE 数据格式以 data: 开头
                if line.startswith("data: "):
                    data_str = line[len("data: "):]
                    if data_str == "[DONE]":
                        break
                    try:
                        chunk = json.loads(data_str)
                        # 获取 token delta
                        choices = chunk.get("choices", [])
                        if choices:
                            delta = choices[0].get("delta", {})
                            token_text = delta.get("content")
                            if token_text:
                                if first_token_time is None:
                                    first_token_time = time.time() - start_total
                                print(token_text, end="", flush=True)
                                collected_text += token_text
                    except json.JSONDecodeError:
                        continue
            print("\n--- 流式结束 ---")
else:
    # 非流式同步请求
    resp = requests.post(url, headers=headers, data=json.dumps(body))
    total_resp = time.time() - start_total
    print(f"HTTP 状态码: {resp.status_code}")
    if resp.status_code == 200:
        data = resp.json()
        # 提取文本
        choices = data.get("choices", [])
        if choices:
            msg = choices[0].get("message", {}).get("content", "")
            collected_text = msg
            print("\n生成内容:\n", msg)

    print(f"\n总响应时间: {total_resp:.3f} s")

# 输出时间统计
if is_stream:
    end_total = time.time() - start_total
    print(f"\n首响应时间: {first_token_time:.3f} s" if first_token_time else "未记录首响应时间")
    print(f"总响应时间: {end_total:.3f} s")
else:
    # already printed total
    pass

```

Test commands

```text
import base64
import json
import requests

# -------------------------
API_BASE = "[服务地址按本实例配置]
MODEL_NAME = "/app/model"  # 通过 curl [服务地址按本实例配置] 查看实际注册的模型名称

IMAGE_PATH = "/srv/llm/models/test.jpg"

# 读取并 Base64 编码图片
with open(IMAGE_PATH, "rb") as f:
    b64_bytes = base64.b64encode(f.read()).decode("utf-8")

# 构造 data:image/jpeg;base64 URI
b64_uri = f"data:image/jpeg;base64,{b64_bytes}"

payload = {
    "model": MODEL_NAME,
    "messages": [
        {
            "role": "user",
            "content": [
                {"type": "text", "text": "请描述这张图片的内容。"},
                {
                    "type": "image_url",
                    "image_url": {"url": b64_uri}
                }
            ],
        }
    ],
}

url = f"{API_BASE}/chat/completions"
headers = {"Content-Type": "application/json"}

print("Sending request to vLLM server...")
response = requests.post(url, headers=headers, data=json.dumps(payload))

print(f"Status: {response.status_code}")
print(response.text)

```

```text
cat <<EOF | curl -X POST "[服务地址按本实例配置]      -H "Content-Type: application/json"      -d @-
{
  "model": "/app/model",
  "messages": [
    {
      "role": "user",
      "content": [
        {"type": "text", "text": "请描述这张图片的内容。"},
        {
          "type": "image_url",
          "image_url": {
            "url": "data:image/jpeg;base64,$(base64 -w0 /srv/llm/models/test.jpg)"
          }
        }
      ]
    }
  ]
}
EOF

```

GB10 deploys Qwen3-VL-8B model (private page link not public)

GB10 deploys Qwen3-VL-32B

GB10 deploys Qwen3-VL-30B-A3B

## R15 · GB10 deployment Qwen3-VL-30B-A3B

```text
# 容器创建命令
docker run -it \
  --name Qwen3-VL-30B-A3B-Instruct \
  --gpus all \
  --ipc=host \
  --shm-size=48g \
  -v /srv/llm/models/Qwen3-VL-30B-A3B-Instruct:/app/model:ro \
  -v ~/.cache/huggingface:/root/.cache/huggingface:rw \
  -p 8006:8006 \
  nvcr.io/nvidia/vllm:25.12-py3 \
  /bin/bash


  # 推理命令
  vllm serve /app/model \
  --host 0.0.0.0 \
  --port 8006 \
  --served-model-name Qwen3-VL-30B-A3B-Instruct  \
  --trust-remote-code \
  --tensor-parallel-size 1 \
  --pipeline-parallel-size 1 \
  --gpu-memory-utilization 0.8 \
  --max-model-len 131072

  #推理命令，100K上下文，批处理4096 tokens
  vllm serve /app/model   --host 0.0.0.0   --port 8006   --served-model-name Qwen3-VL-30B-A3B-Instruct    --trust-remote-code   --tensor-parallel-size 1   --pipeline-parallel-size 1   --gpu-memory-utilization 0.8  --max-model-len  100000  --max-num-batched-tokens 4096
```

## R16 · NVIDIA GB10 release vllm deployment Qwen3‐Omni‐30B‐A3B‐Instruct

1. Draw the official image

```text
docker pull nvcr.io/nvidia/vllm:25.12-py3
```

1. Deployment of processes

```text
# 创建容器
docker run  -it \
  --name Qwen2.5-Omni-7B \
  --gpus all \
  --ipc=host \
  --shm-size=32g \
  -v /srv/llm/models/Qwen2.5-Omni-7B:/app/model:ro  \
  -v ~/.cache/huggingface:/root/.cache/huggingface:rw \
  -p 8008:8008 \
  nvcr.io/nvidia/vllm:25.12-py3 \
  /bin/bash

  # 推理命令
  vllm serve /app/model \
  --host 0.0.0.0 \
  --port 8008 \
  --served-model-name qwen2.5-omni-7b \
  --trust-remote-code \
  --tensor-parallel-size 1 \
  --pipeline-parallel-size 1 \
  --gpu-memory-utilization 0.8
```

```text
# 创建容器
docker run  -it \
  --name Qwen3-Omni-30B-A3B-Instruct \
  --gpus all \
  --ipc=host \
  --shm-size=32g \
  -v /srv/llm/models/Qwen3-Omni-30B-A3B-Instruct:/app/model:ro  \
  -v ~/.cache/huggingface:/root/.cache/huggingface:rw \
  -p 8008:8008 \
  nvcr.io/nvidia/vllm:25.12-py3 \
  /bin/bash

  # 推理命令
  vllm serve /app/model \
  --host 0.0.0.0 \
  --port 8008 \
  --served-model-name qwen3-omni-30b-a3b-Instruct \
  --trust-remote-code \
  --tensor-parallel-size 1 \
  --pipeline-parallel-size 1 \
  --gpu-memory-utilization 0.9


  python -m vllm.entrypoints.openai.api_server \
  --model /app/model \
  --host 0.0.0.0 \
  --port 8008 \
  --served-model-name qwen3-omni-30b-a3b-Instruct \
  --trust-remote-code \
  --tensor-parallel-size 1 \
  --pipeline-parallel-size 1 \
  --gpu-memory-utilization 0.9

```

## R17 · NVIDIA GB10 vllm deployment of granite-docling-258M

```text
# 容器创建命令
docker run  -it \
  --name granite-docling-258M\
  --gpus all \
  --ipc=host \
  --shm-size=32g \
  -v /srv/llm/models/granite-docling-258M:/app/model:ro  \
  -v ~/.cache/huggingface:/root/.cache/huggingface:rw \
  -p 8009:8009 \
  nvcr.io/nvidia/vllm:25.12-py3 \
  /bin/bash


  # 推理命令
  vllm serve /app/model \
  --host 0.0.0.0 \
  --port 8009 \
  --served-model-name granite-docling-258M \
  --trust-remote-code \
  --tensor-parallel-size 1 \
  --pipeline-parallel-size 1 \
  --max-num-seqs 512 \
  --max-num-batched-tokens 8192 \
  --enable-chunked-prefill \
  --gpu-memory-utilization 0.9

  vllm serve ibm-granite/granite-docling-258M \
  --host 127.0.0.1 --port 8000 \
  --max-num-seqs 512 \
  --max-num-batched-tokens 8192 \
  --enable-chunked-prefill \
  --gpu-memory-utilization 0.9
```
