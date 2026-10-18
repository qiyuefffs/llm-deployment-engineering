# AMD Radeon 780M: Windows HIP operating library, Ollama and model compatible

[简体中文](../../01-deployment-foundations/engineering/amd-780m.md) | **English**

[Index of engineering examples](README.md) · [General directory of knowledge systems](../SUMMARY.md)

Technical labels: `gfx1103 / Windows / HIP SDK / rocBLAS`

## Engineering configuration

|Projects|Configuration|
| --- | --- |
|Hardware| Ryzen7 8845HS / Radeon780M,gfx1103 |
|System routes|Windows AMD Software+HIP SDK+ communityrocBLAS library+Ollama branch|
|Model|The original Llama 3.1 8B; Other models and parameters See full text|
|Appropriate|The driver identifies ≠ the running library has the corresponding gfx kernel; The DLL search path is consistent with the version|

## Complete deployment in order of adaptation

1. Record drivers, versions of the HIP SDK and installation directories. The Community Operating Library is not equivalent to AMD's official support for all 780M combinations, and is currently preserved.`library ` with `rocblas.dll` It's a recoverable copy.
2. Prepare the gfx1103 library according to the original release, replacing the target version of the operating library, and avoid mixing the DLLs of different HIP SDKs. Check the actual loaded DLL path of the process, rather than just looking at the path containing a certain directory.
3. Using the original Ollama branch, on the first terminal `ollama serve ` The second terminal executes `ollama run llama3.1:8b `. Originals appear ` llama3.1 8b`In other words, the actual tag should be verified according to the version used.
4. See the GPU detection, buffer and offloading examples of service logs.`ollama ps ` and cross-check with Task Manager. Recalled `/api/generate` Or the corresponding OpenAI input to save the real response.

## Accelerated optimization and acceptance testing

Compare CPU fallback and GPU paths with the same model, prompt, number_predict and cache status. Adjust the context with the number of activity models, observe UMA's overall budget, pre-filing speed, generation speed and cold load. If you replace the operating library after failure, restore the original DLL instead of continuing to overlay multiple community patches.

The original article had an actual deployment process and did not preserve the full throughput tables of the same calibre, so this example retains the proof of steps and functionality without adding speed. Below is the complete Windows installation, replacement library, model, call and relevant parameter material.

## Agreement on the use of complete technical records

The following technical correctness, commands, tables, logs, failures and subsequent experiments of the relevant FlowUs articles are retained directly, without abbreviating the original process. private paths, nodes, authentication and sanitization of attached addresses; `<NODE_IP>` For example, the placeholder needs to be filled in the current environment. The original suggestion or prediction is still a suggestion or prediction. The above execution sequence and technical revisions are used to explain conflicts in historical records, and historical GPU/NPU experiments have not been repeated in this round.

## R18 · AMD 780M-GPU Adaptation Tutorial

1. Preparation and installation

     Install the AMD HIP SDK for Windows and update the AMD Software driver

     The following is a link to the AMD HIP installation link:

     [https://www.amd.com/zh-cn/developer/resources/rocm-hub/hip-sdk.html](https://www.amd.com/zh-cn/developer/resources/rocm-hub/hip-sdk.html)

[Original note image: image.png; [Unpublished transcript]

1. Download RocmLibs-for-gfx1103-AMD780M-APU and replace the files in the HIP directory

   Download the link: [https://github.com/likelovewant/ROCmLibs-for-gfx1103-AMD780M-APU/releases](https://github.com/likelovewant/ROCmLibs-for-gfx1103-AMD780M-APU/releases)

  [Original note image: image.png; [Unpublished transcript]

2.1 Downloading good documents

[Original note image: image.png; [Unpublished transcript]

2.2 Successfully renamed librarybak the library folder in HIP and replaced the library folder in RocmLibs-for-gfx1103-AMD780M-APU

[Original note image: image.png; [Unpublished transcript]

2.3 Modify therocblas.dll file in HIP torocblas.dllbak and replace the downloaded goodrocblas.dll

[Original note image: image.png; [Unpublished transcript]

1. Download the ollama-for-amd framework

   Link to: [https://github.com/likelovewant/ollama-for-amd/releases/tag/v0.5.1](https://github.com/likelovewant/ollama-for-amd/releases/tag/v0.5.1)

  [Original note image: image.png; [Unpublished transcript]

2. cmd starts the ollama service and commands: ollama serve

[Original note image: image.png; [Unpublished transcript]

  [Original note image: image.png; [Unpublished transcript]

1. Then reopen a cmd and start a model using ollama: command: ollama run llama3.1 8b

  [Original note image: image.png; [Unpublished transcript]

Running Effects

[Original note image: image.png; [Unpublished transcript]

## R19 · AMD adaptive model (GPU-780M, CPU-8845HS)

🤗 AMD official NPU/GPU configuration framework ((GPU used cautiously, more craters, NPU not yet tried)

Link to: [https://ryzenai.docs.amd.com/en/latest/](https://ryzenai.docs.amd.com/en/latest/)

Github demon modified tutorials

GPU 780M deployment model: [https://blog.joker2yue.cn/post/zai-ollama-shang-qi-yong-amd780m-gfx1103-gpu-jia-su/](https://blog.joker2yue.cn/post/zai-ollama-shang-qi-yong-amd780m-gfx1103-gpu-jia-su/)

1. **AMD Adapted Tutorials**

AMD 780M-GPU adapter tutorials (private page links are not public)

2.AMD-780M-gfx103 configuration file

AMD-780M-gfx1103 configuration file ((private page link not public))

[Originally recorded image: b4ab2c4b0a69aac52a5a6dd76ab2a0a.jpg; [Unpublished transcript]

Ollama tokens/s speed command: --verbose


```text
ollama run --verbose deepseek-r1:14b
```

[System prompts word.py]

Ollama - measuring speed

[ollama-token.py]

Ollama token speed: ((Code is problematic))

```text
import requests
import json
import time


def generate_response(prompt: str, model: str = "deepseek-r1:8b", url: str = "http://127.0.0.1:11434/api/generate",
                      system_prompt: str = ""):
    headers = {"Content-Type": "application/json"}

    data = {
        "model": model,
        "prompt": prompt,
        "system": system_prompt,
        "stream": True,
        "temperature": 0.8
    }

    # 发送 POST 请求
    response = requests.post(url, headers=headers, data=json.dumps(data), stream=True)

    complete_text = ""  # 存储完整文本
    first_token_time = None  # 第一个 token 生成时间
    start_time = time.time()  # 开始请求时间
    token_count = 0  # 记录 token 总数

    # 遍历流式响应
    for chunk in response.iter_lines():
        if chunk:
            try:
                # 解析 JSON
                line_data = json.loads(chunk.decode('utf-8'))

                # 记录第一个 token 生成时间
                if 'response' in line_data and first_token_time is None:
                    first_token_time = time.time() - start_time

                # 处理文本输出
                if 'response' in line_data:
                    text = line_data['response']
                    complete_text += text
                    print(text, end='', flush=True)
                    token_count += 1  # 每个 response 代表一个 token

            except json.JSONDecodeError:
                continue  # 跳过解析错误的行

    # 计算 token 生成总时间
    end_time = time.time()
    total_time = end_time - start_time
    tokens_per_second = token_count / total_time if total_time > 0 else 0

    # 输出统计信息
    print(f"\n\n🔹 第一个 token 生成时间: {first_token_time:.3f} 秒")
    print(f"🔹 总 token 数量: {token_count}")
    print(f"🔹 生成总时间: {total_time:.3f} 秒")
    print(f"🔹 生成速度: {tokens_per_second:.2f} token/s")

    return complete_text


def main():
    system_prompt = '''你是一个知识用户助手，可以帮助用户回答问题。'''
    """
      你是一个傲娇软萌的撒娇妹妹，可以可爱地回答用户哥哥的问题。
    """

    while True:
        # 用户输入
        prompt = input("\n请输入问题 (或输入 'exit' 退出): ")
        if prompt.lower() == 'exit':
            print("退出程序。")
            break

        # 生成响应
        print(f"\n正在生成响应：{prompt}\n")
        generate_response(prompt, system_prompt=system_prompt)


if __name__ == "__main__":
    main()

```

```text
import requests
import json
import time


def generate_response(prompt: str, model: str = "deepseek-r1:8b", url: str = "http://127.0.0.1:11434/api/generate",
                      system_prompt: str = ""):
    headers = {"Content-Type": "application/json"}

    data = {
        "model": model,
        "prompt": prompt,
        "system": system_prompt,
        "stream": True,
        "temperature": 0.8
    }

    # 发送POST请求
    response = requests.post(url, headers=headers, data=json.dumps(data), stream=True)

    # 用于存储拼接的文本
    complete_text = ""

    first_token_time = None
    start_time = time.time()

    # 遍历每一行
    for chunk in response.iter_lines():
        if chunk:
            try:
                # 解析每一行的JSON数据
                line_data = json.loads(chunk.decode('utf-8'))

                # 提取第一个token生成时间
                if 'response' in line_data and not first_token_time:
                    first_token_time = time.time() - start_time
                    # print(f"\n第一个 token 生成时间: {first_token_time:.3f} 秒")

                # 提取文本内容
                if 'response' in line_data:
                    text = line_data['response']
                    complete_text += text  # 拼接文本内容
                    print(text, end='', flush=True)

                # 提取生成速度相关数据并计算
                if 'eval_count' in line_data and 'eval_duration' in line_data:
                    eval_count = line_data['eval_count']
                    eval_duration = line_data['eval_duration']
                    speed = eval_count / (eval_duration / 1e9)  # 每秒token数
                    print(f"\n第一个 token 生成时间: {first_token_time:.3f} 秒")
                    print(f"\n生成速度: {speed:.2f} token/s")

            except json.JSONDecodeError:
                continue  # 跳过无法解析的行

    return complete_text


def main():
    system_prompt = '''你是一个知识用户助手，可以帮助用户回答问题。'''
    """
      你是一个傲娇软萌的撒娇妹妹，可以可爱地回答用户哥哥的问题。
    """

    while True:
        # 用户输入问题
        prompt = input("\n请输入问题 (或输入 'exit' 退出): ")
        if prompt.lower() == 'exit':
            print("退出程序。")
            break

        # 调用生成函数
        print(f"\n正在生成响应：{prompt}\n")
        generate_response(prompt, system_prompt=system_prompt)


if __name__ == "__main__":
    main()

```

AMD-llama3.1 8b python calls

```text
import requests
import json

OLLAMA_SERVER_URL = "http://127.0.0.1:11434/api/generate"

def send_prompt_to_ollama_stream(prompt, model="llama3.1:8b"):
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": True  # 启用流式模式
    }

    try:
        with requests.post(OLLAMA_SERVER_URL, json=payload, stream=True) as response:
            response.raise_for_status()

            # 流式读取响应内容
            print("生成结果（流式输出）：")
            for line in response.iter_lines(decode_unicode=True):
                if line:
                    try:
                        # 尝试解析为 JSON 格式
                        data = json.loads(line)
                        # 打印解析后的输出内容
                        print(data.get("response", ""), end="", flush=True)
                    except json.JSONDecodeError:
                        print("\n无法解析流式响应内容:", line)

            print("\n回答完毕。")  # 输出完成后的提示信息

    except requests.exceptions.RequestException as e:
        print(f"请求失败: {e}")

if __name__ == "__main__":
    while True:
        user_prompt = input("请输入您的 Prompt（输入 'exit' 退出）： ")
        if user_prompt.strip().lower() == "exit":
            print("程序已退出。")
            break
        send_prompt_to_ollama_stream(user_prompt, model="llama3.1:8b")
        print("\n")  # 每次输出之间添加一个空行

```

```text
import requests
import json
import time

OLLAMA_SERVER_URL = "http://127.0.0.1:11434/api/generate"

def send_prompt_to_ollama_stream(prompt, model="llama3.1:8b"):
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": True  # 启用流式模式
    }

    try:
        with requests.post(OLLAMA_SERVER_URL, json=payload, stream=True) as response:
            response.raise_for_status()

            # 流式读取响应内容
            print("生成结果（流式输出）：")

            token_count = 0
            start_time = time.time()

            for line in response.iter_lines(decode_unicode=True):
                if line:
                    try:
                        # 尝试解析为 JSON 格式
                        data = json.loads(line)
                        output = data.get("response", "")

                        if output:
                            print(output, end="", flush=True)
                            token_count += len(output.split())  # 估算 token 数量（按空格分割）
                    except json.JSONDecodeError:
                        print("\n无法解析流式响应内容:", line)

            end_time = time.time()
            elapsed_time = end_time - start_time

            # 计算 token/s
            if elapsed_time > 0:
                tokens_per_second = token_count / elapsed_time
                print(f"\n回答完毕。总生成 Token 数量: {token_count}, 时间: {elapsed_time:.2f} 秒, 平均速度: {tokens_per_second:.2f} Token/s")
            else:
                print("\n回答完毕。无法计算生成速度，时间太短。")

    except requests.exceptions.RequestException as e:
        print(f"请求失败: {e}")

if __name__ == "__main__":
    while True:
        user_prompt = input("请输入您的 Prompt（输入 'exit' 退出）： ")
        if user_prompt.strip().lower() == "exit":
            print("程序已退出。")
            break
        send_prompt_to_ollama_stream(user_prompt, model="llama3.1:8b")
        print("\n")  # 每次输出之间添加一个空行

```

```text
import requests
import json
import time
from transformers import LlamaTokenizer

# 加载 HuggingFace LlamaTokenizer
tokenizer = LlamaTokenizer.from_pretrained("llama3.1")  # 确保使用正确的 LLaMA 模型名称

OLLAMA_SERVER_URL = "http://127.0.0.1:11434/api/generate"

def send_prompt_to_ollama_stream(prompt, model="llama3.1:8b"):
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": True  # 启用流式模式
    }

    try:
        with requests.post(OLLAMA_SERVER_URL, json=payload, stream=True) as response:
            response.raise_for_status()

            # 流式读取响应内容
            print("生成结果（流式输出）：")

            token_count = 0  # 用于存储生成的 token 数量
            start_time = time.time()  # 记录开始时间

            for line in response.iter_lines(decode_unicode=True):
                if line:
                    try:
                        # 尝试解析为 JSON 格式
                        data = json.loads(line)
                        output = data.get("response", "")  # 获取响应内容

                        if output:
                            print(output, end="", flush=True)  # 输出模型生成的内容

                            # 使用 LlamaTokenizer 计算实际 token 数量
                            tokens = tokenizer.encode(output)  # 将文本编码为 token
                            token_count += len(tokens)  # 累加 token 数量

                    except json.JSONDecodeError:
                        print("\n无法解析流式响应内容:", line)

            end_time = time.time()  # 记录结束时间
            elapsed_time = end_time - start_time  # 计算总耗时

            # 计算 token/s
            if elapsed_time > 0:
                tokens_per_second = token_count / elapsed_time  # 计算生成速度
                print(f"\n回答完毕。总生成 Token 数量: {token_count}, 时间: {elapsed_time:.2f} 秒, 平均速度: {tokens_per_second:.2f} Token/s")
            else:
                print("\n回答完毕。无法计算生成速度，时间太短。")

    except requests.exceptions.RequestException as e:
        print(f"请求失败: {e}")

if __name__ == "__main__":
    while True:
        user_prompt = input("请输入您的 Prompt（输入 'exit' 退出）： ")
        if user_prompt.strip().lower() == "exit":
            print("程序已退出。")
            break
        send_prompt_to_ollama_stream(user_prompt, model="llama3.1:8b")
        print("\n")  # 每次输出之间添加一个空行

```

1. The code calls wrong, prints response, heads up the modulation

```text
import requests
import json

OLLAMA_SERVER_URL = "http://127.0.0.1:11434/api/generate"

def send_prompt_to_ollama_stream(prompt, model="llama3.1:8b"):
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": True  # 启用流式模式
    }

    try:
        with requests.post(OLLAMA_SERVER_URL, json=payload, stream=True) as response:
            response.raise_for_status()

            # 打印响应头
            print("\n响应头信息:")
            for key, value in response.headers.items():
                print(f"{key}: {value}")

            # 流式读取响应内容
            print("\n生成结果（流式输出）：")
            for line in response.iter_lines(decode_unicode=True):
                if line:
                    try:
                        # 尝试解析为 JSON 格式
                        data = json.loads(line)
                        # 打印解析后的输出内容
                        print(data.get("response", ""), end="", flush=True)
                    except json.JSONDecodeError:
                        print("\n无法解析流式响应内容:", line)

            print("\n回答完毕。")  # 输出完成后的提示信息

    except requests.exceptions.RequestException as e:
        print(f"请求失败: {e}")

if __name__ == "__main__":
    while True:
        user_prompt = input("请输入您的 Prompt（输入 'exit' 退出）： ")
        if user_prompt.strip().lower() == "exit":
            print("程序已退出。")
            break
        send_prompt_to_ollama_stream(user_prompt, model="llama3.1:8b")
        print("\n")  # 每次输出之间添加一个空行

```

## R20 · AMD: using the Ollama framework to deploy Llama3.1 8b on AMD's GPU

1. The Ollama framework that supports the corresponding AMD device GPU will be set up correctly

Link to: [https://github.com/likelovewant/ollama-for-amd/releases](https://github.com/likelovewant/ollama-for-amd/releases)

1. Using Ollama to deploy the Llama3.1 8b model

2. Start with Ollama serve

3. Then open a cmd window and start the Llama3.1 8b model in Ollama.

Python is implementing Llama3.1 8b model of flow output dialog

The code is:

```text
import requests
import json
import time

OLLAMA_SERVER_URL = "http://127.0.0.1:11434/api/generate"   //本地IP，Ollama框架默认端口11434，可修改


def send_prompt_to_ollama_stream(prompt, model="llama3.1:8b"):
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": True  # 启用流式模式
    }

    try:
        with requests.post(OLLAMA_SERVER_URL, json=payload, stream=True) as response:
            response.raise_for_status()

            # 流式读取响应内容
            print("生成结果（流式输出）：")

            token_count = 0
            start_time = time.time()

            for line in response.iter_lines(decode_unicode=True):
                if line:
                    try:
                        # 尝试解析为 JSON 格式
                        data = json.loads(line)
                        output = data.get("response", "")

                        if output:
                            print(output, end="", flush=True)
                            token_count += len(output.split())  # 估算 token 数量（按空格分割）
                    except json.JSONDecodeError:
                        print("\n无法解析流式响应内容:", line)

            end_time = time.time()
            elapsed_time = end_time - start_time

            # 计算 token/s
            if elapsed_time > 0:
                tokens_per_second = token_count / elapsed_time
                print(
                    f"\n回答完毕。总生成 Token 数量: {token_count}, 时间: {elapsed_time:.2f} 秒, 平均速度: {tokens_per_second:.2f} Token/s")
            else:
                print("\n回答完毕。无法计算生成速度，时间太短。")

    except requests.exceptions.RequestException as e:
        print(f"请求失败: {e}")


if __name__ == "__main__":
    while True:
        user_prompt = input("请输入您的 Prompt（输入 'exit' 退出）： ")
        if user_prompt.strip().lower() == "exit":
            print("程序已退出。")
            break
        send_prompt_to_ollama_stream(user_prompt, model="llama3.1:8b")
        print("\n")  # 每次输出之间添加一个空行

```

1. The code can be deployed as a server, the input and output interfaces can be packaged with Fastapi, and the input end can set parameters such as temperature, system prompt, role definition, flow output; The output is in JSON format, stream output;

     The client accepts Llama3.1 8b model output as the interface end and can also set model parameters on the interface.

1. When the client is started, use the bat script to call the server, load the model, enter the port number, refer to the sd1.5 typeface or the model call typeface of the flowy.
