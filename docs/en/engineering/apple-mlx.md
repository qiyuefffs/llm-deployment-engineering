# Apple M3 Ultra: vllm-metal, MLX-VLM, APC and oMLX optimized

[简体中文](../../01-deployment-foundations/cases/C11-m3-mlx/README.md) | **English**

[Index of engineering examples](README.md) · [General directory of knowledge systems](../SUMMARY.md)

Technical labels: `MLX / Metal / chat template / APC / batching`

## Environment and executive branch

|Branch|Adaptation focus|Results have been recorded|
| --- | --- | --- |
| vllm-metal |Python 3.12.13 MLX 0.31.2 vLLM 0.21.0 + cpu Plugins 0.2.0|Repair of text and templates; Visual encoder failure|
| MLX-VLM |It's a processor, it's a CLI, it's a server protocol.|Multi-visual model with full call code|
| APC |Block budgets, disk caches, tenants, cooling caches, KV quantization are mutually exclusive|Custom branch operations with no complete patch commit|
| oMLX |Father directory detection, model loading, unified memory, continuous batching|C1/c2/c4 Full latency and throughput|

## Complete deployment of adaptation processes

1. Record macOS, chips, physical/available unified memory, Python/MLX and frameworks versions, each in a separate branch environment.
2. Verify that the native extends the actual import path to avoid the current source code directory coverage installed `_rs` The module.
3. The text first checks the template, reasoning/content and finish_reason, and then enters the image. Services without a visual encoder should revert to support paths and cannot fix HTTP500 with max_tokens enlarged.
4. MLX-VLM uses the image schema required by its version; Test cards, base64 and SSE clients see [Full Input Link](../chapters/frameworks/vllm-service.md#seven-complete-links-from-image-files-to-streaming-answers).
5. oMLX checks the model parent directory and model ID, explicitly loading and testing. APC sets and checks stats according to the original variable, first cooling, reheating, then changing the prefix, then extruding and tenant isolation.

## Optimization of actual concurrency

|concurrency|Number of requests|Always generate tokens/s|TPOT for single request|Average latency|
| --- | --- | --- | --- | --- |
| 1 | 20 | 29.38 | 34.2ms | 7.582s |
| 2 | 10 | 41.11 | 47.5ms | 10.257s |
| 4 | 10 | 55.15 | 69.8ms | 13.459s |

Input goal 128, output ceiling 256; Cache and Environmental Lack of Origin Records concurrency 4 total throughput is highest, but single request slower; Workplaces are selected by interaction or batching objectives. The original c1/5 request is also preserved in full text, not derived from a small sample of stable p99.

The following are full preserved constructs, text/visual errors, MLX-VLM/APC, oMLX operations, test reports and frame positioning articles: The ability of each framework to declare a fixed version functionality is validated, and research suggests not to automatically record measured.

## Agreement on the use of complete technical records

The following technical correctness, commands, tables, logs, failures and subsequent experiments of the relevant FlowUs articles are retained directly, without abbreviating the original process. private paths, nodes, authentication and sanitization of attached addresses; `<NODE_IP>` For example, the placeholder needs to be filled in the current environment. The original suggestion or prediction is still a suggestion or prediction. The above execution sequence and technical revisions are used to explain conflicts in historical records, and historical GPU/NPU experiments have not been repeated in this round.

## R40 · vllm-metal compilation and inference records

> Recorded: 2026-05-18
> device :Mac Studio / Apple M3 Ultra / 512GB unified memory
> The work directory: `/srv/llm/Desktop/llm-workspace/vllm-metal`
> The model directory: `<MODEL_VOLUME>/modeldown/models`

This article is about the compilation installed on Mac Apple Silicon.`vllm-metal` Starting Qwen 3.6 text inference service, OpenAI API calls, and the network, template, multi-module issues that you're pressing.

#### 1. Current conclusions

This time.`vllm-metal` The compilation has been installed successfully:

```Markdown
vllm-metal  0.2.0
vllm        0.21.0+cpu
mlx         0.31.2
mlx-lm      0.31.3
mlx-metal   0.31.2
mlx-vlm     0.4.4
torch       2.11.0
Python      3.12.13
```

The results of the verification:

```Markdown
vllm CLI 可用
vllm_metal 可 import
vllm_metal._rs 原生扩展可 import
Qwen3.6-35B-A3B-bf16 文本推理可用
Qwen3.6-35B-A3B-bf16 图片识别在 vllm-metal 中不可用
```

Important restrictions:

```Markdown
vllm-metal 当前主要用于 text-only LLM 推理。
Qwen3.6-35B-A3B-bf16 虽然是 VLM / ConditionalGeneration 包装，但 vllm-metal 的多模态 encoder 链路尚未接通。
图片识别请走 mlx-vlm / oMLX，不要走 vllm-metal。
```

#### 2. Source code drag and drop after installation process

##### 2.1 Access to the source code directory

```text
cd /srv/llm/Desktop/llm-workspace/vllm-metal
```

##### 2.2 Creating and activating virtual environments

Installing scripts will be created automatically `.venv-vllm-metal` If there is already a direct activation:

```text
source /srv/llm/Desktop/llm-workspace/vllm-metal/.venv-vllm-metal/bin/activate
```

Confirm Python:

```text
which python
python -V
```

Expectations are:

```Markdown
/srv/llm/Desktop/llm-workspace/vllm-metal/.venv-vllm-metal/bin/python
Python 3.12.13
```

##### 2.3 Locally installed scripts run by official documentation

The official document recommends:

```text
curl -fsSL https://raw.githubusercontent.com/vllm-project/vllm-metal/main/install.sh | bash
```

This time, because the source code has been pulled, it runs directly in the local source code directory:

```text
cd /srv/llm/Desktop/llm-workspace/vllm-metal
./install.sh
```

The effect of running the script locally:

```Markdown
创建 / 使用 .venv-vllm-metal
下载 vllm-0.21.0.tar.gz
安装 vllm 0.21.0+cpu
编译并安装 vllm-metal 0.2.0
生成 vllm_metal/_rs.cpython-312-darwin.so
```

The main process in the installation script:

```text
local vllm_v="0.21.0"
local url_base="https://github.com/vllm-project/vllm/releases/download"
local filename="vllm-$vllm_v.tar.gz"

curl -OL $url_base/v$vllm_v/$filename
tar xf $filename
cd vllm-$vllm_v

uv pip install -r requirements/cpu.txt --index-strategy unsafe-best-match
CXXFLAGS="-Wno-parentheses" uv pip install .

cd -
uv pip install .
```

#### 3 - download the crater

##### 3.1 curl HTTP/2 framing layer error

It was first installed in the United States.

```Markdown
curl: (16) Error in the HTTP2 framing layer
```

The phenomenon:

```Markdown
下载 vllm-0.21.0.tar.gz 时长时间 0 字节
约 90 秒后失败
```

The reason for this is:

```Markdown
GitHub release asset 下载链路不稳定。
系统 curl 默认走 HTTP/2，遇到代理/网络链路异常。
```

How to deal with thoughts:

```text
curl --http1.1 --retry 8 --retry-delay 3 --retry-all-errors ...
```

##### 3.2 curl connection reset by peer

Subsequent downloads can be started, but interrupted in the middle:

```Markdown
36 32.8M   36 11.9M
curl: (56) Recv failure: Connection reset by peer
```

Notes:

```Markdown
HTTP/1.1 后已经能下载，但链路仍然会被对端重置。
```

It is recommended to use interrupted transmission:

```text
curl --http1.1 \
  --retry 20 \
  --retry-delay 5 \
  --retry-all-errors \
  -fL \
  -C - \
  -O https://github.com/vllm-project/vllm/releases/download/v0.21.0/vllm-0.21.0.tar.gz
```

If it's still too slow, turn on the proxy:

```text
export HTTPS_PROXY=http://127.0.0.1:7890
export HTTP_PROXY=http://127.0.0.1:7890
export ALL_PROXY=socks5://127.0.0.1:7890

./install.sh
```

The port is adjusted according to the actual port of the native agent.

#### 4. Installation of successful verification

##### 4.1 See the package version

```text
cd /srv/llm/Desktop/llm-workspace/vllm-metal
source .venv-vllm-metal/bin/activate

python -m pip list | grep -E '^(vllm|vllm-metal|mlx|mlx-lm|mlx-vlm|mlx-metal|torch|transformers|nanobind)\b'
```

The result is:

```Markdown
mlx                                      0.31.2
mlx-lm                                   0.31.3
mlx-metal                                0.31.2
mlx-vlm                                  0.4.4
nanobind                                 2.10.2
torch                                    2.11.0
transformers                             5.8.1
vllm                                     0.21.0+cpu
vllm-metal                               0.2.0
```

##### 4.2 Check the Vllm CLI

```text
source /srv/llm/Desktop/llm-workspace/vllm-metal/.venv-vllm-metal/bin/activate
which vllm
vllm --version
```

Expectations are:

```Markdown
/srv/llm/Desktop/llm-workspace/vllm-metal/.venv-vllm-metal/bin/vllm
0.21.0+cpu
```

##### 4.3 Expanded natives

Don't check the root directory in the source code `_rs ` Otherwise, the current directory `./vllm_metal/` It'll cover up the installed packaging in the venv.

The right thing to do:

```text
cd /private/tmp
source /srv/llm/Desktop/llm-workspace/vllm-metal/.venv-vllm-metal/bin/activate

python - <<'PY'
import vllm
import vllm_metal
import vllm_metal._rs

print("vllm:", vllm.__version__)
print("vllm-metal:", vllm_metal.__version__)
print("vllm_metal._rs import: OK")
PY
```

This test:

```Markdown
vllm_metal: import OK
vllm_metal._rs: import OK
```

If the source code is executed in the root directory, you may see:

```Markdown
ModuleNotFoundError: No module named 'vllm_metal._rs'
```

This is not a compilation failure, but a Python import priority that causes the source code directory to obscure site-packages.

#### 5. Local model directories and support

The current model directory:

```text
cd <MODEL_VOLUME>/modeldown/models
ls
```

List of models:

```Markdown
DeepSeek-V4-Flash
DeepSeek-V4-Flash-FP4-FP8-native.gguf
DeepSeek-V4-Flash-Q4KExperts-F16HC-F16Compressor-F16Indexer-Q8Attn-Q8Shared-Q8Out-chat-v2.gguf
gemma-4-26b-a4b-it-bf16
gemma-4-26b-a4b-it-mxfp8
gemma-4-31B-it-assistant-bf16
gemma-4-31b-it-bf16
gemma-4-31b-it-mxfp8
MiniCPM-V-4.6-bf16
Qwen3.6-35B-A3B-bf16
```

According to vllm-metal, current capabilities:

|Model|Vllm-metal is a good judge.|Notes|
| --- | --- | --- |
| Qwen3.6-35B-A3B-bf16 |Text is available, visual is not.|Qwen 3.5 / Qwen 3.6 MoE / ConditionalGeneration packaging is included. Text can run, image encoder not connected|
| gemma-4-26b-a4b-it-bf16 |Testing and experimentation|Gemma4 for experimental support in vllm-metal|
| gemma-4-31b-it-bf16 |Testing and experimentation|Same as above|
| gemma-4-26b-a4b-it-mxfp8 |needs to be measured|Gemma4 architecture is supported, but the mxfp8 quantization form is not used as a clear validation mainline|
| gemma-4-31b-it-mxfp8 |needs to be measured|Same as above|
| MiniCPM-V-4.6-bf16 |Not recommended|VLM, multi-mode not vllm-metal current stable mainline|
| DeepSeek-V4-Flash |Not recommended|Deepseek_v4 does not currently support matrix|
| *.gguf |Not supported|vllm-metal does not run GGUF, applies ds4 / llama.cpp|

#### 6. Qwen 3.6 Start command for the text service

Important: Do not start the service in the source code root directory to avoid import blocking; Recommended in `/private/tmp` It's on.

```text
cd /private/tmp

source /srv/llm/Desktop/llm-workspace/vllm-metal/.venv-vllm-metal/bin/activate

export VLLM_METAL_USE_MLX=1
export VLLM_MLX_DEVICE=gpu
export VLLM_METAL_USE_PAGED_ATTENTION=1
export VLLM_METAL_MEMORY_FRACTION=0.90
export VLLM_METAL_GDN_LAZY_DECODE=1
export VLLM_METAL_MULTIMODAL_MODE=auto
export VLLM_METAL_PREFIX_CACHE=1
export VLLM_METAL_PREFIX_CACHE_FRACTION=0.05
export VLLM_WORKER_MULTIPROC_METHOD=spawn
export TOKENIZERS_PARALLELISM=false

vllm serve <MODEL_VOLUME>/modeldown/models/Qwen3.6-35B-A3B-bf16 \
  --host 0.0.0.0 \
  --port 18092 \
  --served-model-name qwen3.6-35b-a3b-bf16 \
  --trust-remote-code \
  --dtype bfloat16 \
  --kv-cache-dtype bfloat16 \
  --max-model-len 8192 \
  --max-num-seqs 16 \
  --max-num-batched-tokens 32768 \
  --block-size 16 \
  --enable-prefix-caching \
  --chat-template <MODEL_VOLUME>/modeldown/models/Qwen3.6-35B-A3B-bf16/chat_template.jinja \
  --default-chat-template-kwargs '{"enable_thinking": false}' \
  --generation-config vllm \
  --override-generation-config '{"do_sample": false, "temperature": 0, "top_p": 1}' \
  --scheduler-reserve-full-isl \
  --disable-uvicorn-access-log \
  --disable-fastapi-docs \
  --uvicorn-log-level warning
```

Parameter explains:

|Parameters|The role|
| --- | --- |
| VLLM_METAL_USE_PAGED_ATTENTION=1 |Enable paged KV cache to improve concurrency|
| VLLM_METAL_MEMORY_FRACTION=0.90 |Paged KV has a larger memory budget.|
| VLLM_METAL_GDN_LAZY_DECODE=1 |Qwen 3.6 hybrid/GDN decode Optimized|
| --max-num-seqs 16 |Maximum single-wheel scheduling 16 series|
| --max-num-batched-tokens 32768 |The single-wheel processor has a maximum of 32768 tokens|
| --chat-template .../chat_template.jinja |Qwen chat template in directory|
| --default-chat-template-kwargs '{"enable_thinking": false}' |Turn off the default thinking mode|
| --generation-config vllm |Do not read models with high temperature sampling configuration|
| --override-generation-config ... |Default shutdown of samples, improving stability|

#### 7. Examples of text calls

##### 7.1 Call of duty

```text
curl -s http://127.0.0.1:18092/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "qwen3.6-35b-a3b-bf16",
    "messages": [
      {
        "role": "system",
        "content": "你是一个简洁、有帮助的助手。请使用用户最新一条消息的语言回答。不要输出推理过程、思考步骤、分析过程、计划或草稿，只输出最终答案。"
      },
      {
        "role": "user",
        "content": "用三句话介绍一下 Apple Silicon 上本地推理的优势。"
      }
    ],
    "temperature": 0,
    "max_tokens": 128,
    "stop": ["<|im_end|>", "<|endoftext|>"],
    "chat_template_kwargs": {
      "enable_thinking": false
    },
    "stream": false
  }'
```

##### 7.2 Other device calls

Mac device IP:

```Markdown
<NODE_IP>
```

Other devices called:

```text
curl -s http://<NODE_IP>:18092/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "qwen3.6-35b-a3b-bf16",
    "messages": [
      {
        "role": "system",
        "content": "你是一个简洁、有帮助的助手。请使用用户最新一条消息的语言回答。不要输出推理过程、思考步骤、分析过程、计划或草稿，只输出最终答案。"
      },
      {
        "role": "user",
        "content": "请用一句话回答：你现在能正常响应吗？"
      }
    ],
    "temperature": 0,
    "max_tokens": 64,
    "chat_template_kwargs": {
      "enable_thinking": false
    },
    "stream": false
  }'
```

#### 8. Inference Crashing and solving

##### 8.1 Output `Here's a thinking process`

The phenomenon:

```text
"content": "Here's a thinking process:\n\n1. **Analyze User Input:** ..."
```

In the meantime:

```Markdown
finish_reason: "length"
```

The reason:

```Markdown
模型目录的 tokenizer_config.json 中 chat_template 为 None。
真实模板文件是 chat_template.jinja。
该模板默认会在 assistant 开头插入 <think>。
如果没有显式传 enable_thinking=false，模型容易进入思考输出模式。
```

Template key sections:

```Markdown
{%- if add_generation_prompt %}
    {{- '<|im_start|>assistant\n' }}
    {%- if enable_thinking is defined and enable_thinking is false %}
        {{- '<think>\n\n</think>\n\n' }}
    {%- else %}
        {{- '<think>\n' }}
    {%- endif %}
{%- endif %}
```

The solution:

When the service is launched, add:

```text
--chat-template <MODEL_VOLUME>/modeldown/models/Qwen3.6-35B-A3B-bf16/chat_template.jinja \
--default-chat-template-kwargs '{"enable_thinking": false}'
```

The request can also include:

```text
"chat_template_kwargs": {
  "enable_thinking": false
}
```

##### 8.2 Default generation_config at the service end

in the model directory `generation_config.json`:

```text
{
  "do_sample": true,
  "temperature": 1.0,
  "top_p": 0.95
}
```

This will lead to more dispersion of output.

The solution:

Use when launching:

```text
--generation-config vllm \
--override-generation-config '{"do_sample": false, "temperature": 0, "top_p": 1}'
```

The request also recommends:

```text
"temperature": 0
```

##### 8.3 Image recognition request triggers 500

When the request image is identified, the server returns:

```text
{
  "error": {
    "message": "EngineCore encountered an issue. See stack trace (above) for the root cause.",
    "type": "InternalServerError",
    "code": 500
  }
}
```

Key error on the Mac end log:

```Markdown
NotImplementedError: Multimodal encoder execution is not wired on Metal yet.
Metal currently registers multimodal runtime state, but image encoding and embedding splice are not connected to the runner.
```

Notes:

```Markdown
图片已经被 vLLM 前端解析并预处理。
日志中能看到 mm_features、pixel_values、image_grid_thw。
但 vllm-metal runner 没有接通 image encoder 和 embedding splice。
```

In conclusion:

```Markdown
vllm-metal 当前不能用于该 Qwen3.6 模型的图片识别。
这不是编译错误。
这是框架当前能力边界。
```

How to deal with it:

```Markdown
Qwen3.6 文本推理继续用 vllm-metal。
Qwen3.6 图片识别请走 mlx-vlm / oMLX。
```

Note: After the image request triggers a fatal error, logs appear:

```Markdown
EngineCore encountered a fatal error
EngineDeadError
```

It is necessary.`Ctrl+C` Stop the current service and restart.

##### 8.4 here-doc JSON spelling error

The wrong command finally appears:

```Markdown
EOFstream": false
```

The reason:

```Markdown
here-doc 结束符 EOF 必须单独一行。
EOF 后不能粘任何 JSON 字段。
```

The correct format:

```text
curl -sS http://<NODE_IP>:18092/v1/chat/completions \
  -H "Content-Type: application/json" \
  --data-binary @- <<EOF
{
  "model": "qwen3.6-35b-a3b-bf16",
  "messages": [
    {
      "role": "user",
      "content": "请用一句话回答：你现在能正常响应吗？"
    }
  ],
  "temperature": 0,
  "max_tokens": 64,
  "stream": false
}
EOF
```

Recommended for use `python3 -m json.tool` Check the request file:

```text
python3 -m json.tool /tmp/request.json >/dev/null && echo "JSON OK"
```

##### 8.5 Codex in a sandbox `No Metal device available`

Some commands can be seen running in the Codex/Sandbox environment:

```Markdown
RuntimeError: [metal::load_device] No Metal device available.
This typically occurs in headless, sandboxed, or virtualized macOS sessions where the GPU is not accessible.
```

Notes:

```Markdown
这是沙盒环境拿不到 Metal GPU。
不是本机 Terminal 中的编译失败。
```

In real terms, `vllm serve` After launching, normal text inference can be made, indicating the availability of Metal links.

#### 9. Image recognition alternative route:mlx-vlm

Since vllm-metal is currently unable to execute a multimodal encoder, image recognition is recommended.`mlx-vlm`.

If the image is on a Linux device:

```text
scp "/srv/llm/图片/1.jpg" <USER>@<NODE_IP>:/tmp/1.jpg
```

Testing on Mac:

```text
cd /private/tmp
source /srv/llm/Desktop/llm-workspace/vllm-metal/.venv-vllm-metal/bin/activate

python -m mlx_vlm.generate \
  --model <MODEL_VOLUME>/modeldown/models/Qwen3.6-35B-A3B-bf16 \
  --image /tmp/1.jpg \
  --prompt "请识别这张图片，描述图片中的主要内容、场景、物体和可能的文字。" \
  --max-tokens 512 \
  --temperature 0.0
```

#### 10. Subsequent recommendations

1. `vllm-metal` Qwen 3.6 continues to be used for text concurrency, prefix cache, throughput testing.

2. Image recognition is gone `mlx-vlm ` or `oMLX` Please do not send the image request on the current vllm-metal service.

3. Gemma4 bf16 can be tested as a second group vllm-metal text model.

4. DeepSeek-V4 GGUF is on its way `ds4 ` / ` llama.cpp`The route.

5. If the next vllm-metal officially connects the multimodal encoder, re-test the Qwen 3.6 VLM.

## R41 · mlx-vlm Multi-visual model inference and API call guidance

This documentary is based on the current Mac Studio recording.`mlx-vlm` The source code environment for multi-modal model loading, command line inference, API service launch, remote calling, OCR/map request operation process.

Applicable model:

- `MiniCPM-V-4.6-bf16`

- `Qwen3.6-35B-A3B-bf16`

- `gemma-4-26b-a4b-it-bf16`

- `gemma-4-31b-it-bf16`

Current source code environment:

```text
/srv/llm/Desktop/llm-workspace/oMLX-vlm/mlx-vlm
```

Virtual environments:

```text
/srv/llm/Desktop/llm-workspace/oMLX-vlm/oMLX-vlm
```

#### 1. Environmental preparedness

Access the source code directory and activation Virtual environment:

```text
cd /srv/llm/Desktop/llm-workspace/oMLX-vlm/mlx-vlm
source ../oMLX-vlm/bin/activate
```

Confirm the current installed `mlx-vlm` From the source code:

```text
uv pip list | grep mlx-vlm
python -c "import mlx_vlm; print(mlx_vlm.__file__)"
```

Confirm that MLX/Metal is available:

```text
python -c "import mlx.core as mx; print(mx.default_device()); print(mx.device_info())"
```

If you `python` The command is unavailable and can be used directly by a virtual environment interpreter:

```text
/srv/llm/Desktop/llm-workspace/oMLX-vlm/oMLX-vlm/bin/python
```

#### 2. Model path

The current model is by default located at:

```text
<MODEL_VOLUME>/modeldown/models
```

There are four model paths:

```text
<MODEL_VOLUME>/modeldown/models/MiniCPM-V-4.6-bf16
<MODEL_VOLUME>/modeldown/models/Qwen3.6-35B-A3B-bf16
<MODEL_VOLUME>/modeldown/models/gemma-4-26b-a4b-it-bf16
<MODEL_VOLUME>/modeldown/models/gemma-4-31b-it-bf16
```

The following commands can be used to confirm the integrity of the model file:

```text
ls <MODEL_VOLUME>/modeldown/models/MiniCPM-V-4.6-bf16
ls <MODEL_VOLUME>/modeldown/models/Qwen3.6-35B-A3B-bf16
ls <MODEL_VOLUME>/modeldown/models/gemma-4-26b-a4b-it-bf16
ls <MODEL_VOLUME>/modeldown/models/gemma-4-31b-it-bf16
```

Key configuration:

- `MiniCPM-V-4.6-bf16 `: ` model_type=minicpmv4_6`It is suitable for lightweight OCR/Mapping.

- `Qwen3.6-35B-A3B-bf16 `: ` model_type=qwen3_5_moe`It is suitable for complex textual understanding, but heavier.

- `gemma-4-26b-a4b-it-bf16 `: ` model_type=gemma4`This is the most common type of inference, and it is suitable for general multimodal inference.

- `gemma-4-31b-it-bf16 `: ` model_type=gemma4`It is more suitable for general polymorphic inference than 26B.

#### 3. Direct inference of the command line

##### 3.1 MiniCPM-V-4.6-bf16

This is not the case.

```text
python -m mlx_vlm.generate \
  --model <MODEL_VOLUME>/modeldown/models/MiniCPM-V-4.6-bf16 \
  --prompt "你好，请做一个简短自我介绍。" \
  --max-tokens 512 \
  --temperature 0.0
```

Image understanding:

```text
python -m mlx_vlm.generate \
  --model <MODEL_VOLUME>/modeldown/models/MiniCPM-V-4.6-bf16 \
  --image /path/to/image.jpg \
  --prompt "请详细描述这张图片。" \
  --max-tokens 1024 \
  --temperature 0.0
```

OCR：

```text
python -m mlx_vlm.generate \
  --model <MODEL_VOLUME>/modeldown/models/MiniCPM-V-4.6-bf16 \
  --image /path/to/image.jpg \
  --prompt "请对图片进行OCR识别，逐行输出所有可见文字，保留原始顺序和表格结构，不要编造。" \
  --max-tokens 4096 \
  --temperature 0.0
```

OCR details priority mode:

```text
python -m mlx_vlm.generate \
  --model <MODEL_VOLUME>/modeldown/models/MiniCPM-V-4.6-bf16 \
  --image /path/to/image.jpg \
  --prompt "请对图片进行OCR识别，逐行输出所有可见文字，保留原始顺序和表格结构，不要编造。" \
  --max-tokens 4096 \
  --temperature 0.0 \
  --processor-kwargs '{"downsample_mode": "4x", "max_slice_nums": 36}'
```

##### 3.2 Qwen3.6-35B-A3B-bf16

This is not the case.

```text
python -m mlx_vlm.generate \
  --model <MODEL_VOLUME>/modeldown/models/Qwen3.6-35B-A3B-bf16 \
  --prompt "你好，请做一个简短自我介绍。" \
  --max-tokens 512 \
  --temperature 0.0
```

Image understanding:

```text
python -m mlx_vlm.generate \
  --model <MODEL_VOLUME>/modeldown/models/Qwen3.6-35B-A3B-bf16 \
  --image /path/to/image.jpg \
  --prompt "请详细描述这张图片。" \
  --max-tokens 1024 \
  --temperature 0.0
```

OCR：

```text
python -m mlx_vlm.generate \
  --model <MODEL_VOLUME>/modeldown/models/Qwen3.6-35B-A3B-bf16 \
  --image /path/to/image.jpg \
  --prompt "请对图片进行OCR识别，逐行输出所有可见文字，保留原始顺序和表格结构，不要编造。" \
  --max-tokens 4096 \
  --temperature 0.0
```

High-resolution input attempt:

```text
python -m mlx_vlm.generate \
  --model <MODEL_VOLUME>/modeldown/models/Qwen3.6-35B-A3B-bf16 \
  --image /path/to/image.jpg \
  --prompt "请对图片进行OCR识别，逐行输出所有可见文字，保留原始顺序和表格结构，不要编造。" \
  --max-tokens 4096 \
  --temperature 0.0 \
  --processor-kwargs '{"max_pixels": 3211264}'
```

##### 3.3 gemma-4-26b-a4b-it-bf16

This is not the case.

```text
python -m mlx_vlm.generate \
  --model <MODEL_VOLUME>/modeldown/models/gemma-4-26b-a4b-it-bf16 \
  --prompt "你好，请做一个简短自我介绍。" \
  --max-tokens 512 \
  --temperature 0.0
```

##### 3.4 gemma-4-31b-it-bf16

This is not the case.

```text
python -m mlx_vlm.generate \
  --model <MODEL_VOLUME>/modeldown/models/gemma-4-31b-it-bf16 \
  --prompt "你好，请做一个简短自我介绍。" \
  --max-tokens 512 \
  --temperature 0.0
```

Image understanding:

```text
python -m mlx_vlm.generate \
  --model <MODEL_VOLUME>/modeldown/models/gemma-4-31b-it-bf16 \
  --image /path/to/image.jpg \
  --prompt "请详细描述这张图片。" \
  --max-tokens 1024 \
  --temperature 0.0
```

OCR：

```text
python -m mlx_vlm.generate \
  --model <MODEL_VOLUME>/modeldown/models/gemma-4-31b-it-bf16 \
  --image /path/to/image.jpg \
  --prompt "请对图片进行OCR识别，逐行输出所有可见文字，保留原始顺序和表格结构，不要编造。" \
  --max-tokens 4096 \
  --temperature 0.0
```

Image understanding:

```text
python -m mlx_vlm.generate \
  --model <MODEL_VOLUME>/modeldown/models/gemma-4-26b-a4b-it-bf16 \
  --image /path/to/image.jpg \
  --prompt "请详细描述这张图片。" \
  --max-tokens 1024 \
  --temperature 0.0
```

OCR：

```text
python -m mlx_vlm.generate \
  --model <MODEL_VOLUME>/modeldown/models/gemma-4-26b-a4b-it-bf16 \
  --image /path/to/image.jpg \
  --prompt "请对图片进行OCR识别，逐行输出所有可见文字，保留原始顺序和表格结构，不要编造。" \
  --max-tokens 4096 \
  --temperature 0.0
```

#### 4. API service started

API services are provided by `mlx_vlm.server` It offers an OpenAI-compatible interface style:

```text
/v1/chat/completions
```

Passed when the service started `--model ` Pre-loaded model.`mlx_vlm.server ` There is no `/v1/models/{id}/load` This is a runtime loaded interface.

##### 4.1 Addresses for listening

It's just a phone call:

```text
--host 127.0.0.1
```

Other local area network devices call:

```text
--host 0.0.0.0
```

Or bind to a specified local area network IP:

```text
--host <NODE_IP>
```

See the local area network IP of Mac Studio:

```text
ipconfig getifaddr en0
ipconfig getifaddr en1
```

##### 4.2 MiniCPM-V-4.6-bf16 API services

OCR/Mapping Stability:

```text
python -m mlx_vlm.server \
  --host <NODE_IP> \
  --port 8080 \
  --model <MODEL_VOLUME>/modeldown/models/MiniCPM-V-4.6-bf16 \
  --max-tokens 4096 \
  --max-kv-size 32768 \
  --prefill-step-size 2048 \
  --vision-cache-size 64 \
  --log-level INFO
```

The following is a list of some of the most common types of memory:

```text
python -m mlx_vlm.server \
  --host <NODE_IP> \
  --port 8080 \
  --model <MODEL_VOLUME>/modeldown/models/MiniCPM-V-4.6-bf16 \
  --max-tokens 2048 \
  --max-kv-size 262144 \
  --prefill-step-size 4096 \
  --vision-cache-size 64 \
  --kv-bits 4 \
  --kv-quant-scheme uniform \
  --kv-group-size 64 \
  --quantized-kv-start 4096 \
  --log-level INFO
```

##### 4.3 Qwen 3.6-35B-A3B-bf16 API services

8081 is recommended to avoid conflicts with MiniCPM services.

Stable release:

```text
python -m mlx_vlm.server \
  --host <NODE_IP> \
  --port 8081 \
  --model <MODEL_VOLUME>/modeldown/models/Qwen3.6-35B-A3B-bf16 \
  --max-tokens 4096 \
  --max-kv-size 32768 \
  --prefill-step-size 2048 \
  --vision-cache-size 32 \
  --log-level INFO
```

Memory-saving configuration:

```text
python -m mlx_vlm.server \
  --host <NODE_IP> \
  --port 8081 \
  --model <MODEL_VOLUME>/modeldown/models/Qwen3.6-35B-A3B-bf16 \
  --max-tokens 4096 \
  --max-kv-size 32768 \
  --prefill-step-size 2048 \
  --vision-cache-size 32 \
  --kv-bits 4 \
  --kv-quant-scheme uniform \
  --kv-group-size 64 \
  --quantized-kv-start 4096 \
  --log-level INFO
```

##### 4.4 Gemma-4-26b-a4b-it-bf16 API services

It is recommended to use 8082 to avoid conflicts with other services.

Stable release:

```text
python -m mlx_vlm.server \
  --host <NODE_IP> \
  --port 8082 \
  --model <MODEL_VOLUME>/modeldown/models/gemma-4-26b-a4b-it-bf16 \
  --max-tokens 4096 \
  --max-kv-size 32768 \
  --prefill-step-size 2048 \
  --vision-cache-size 32 \
  --log-level INFO
```

##### 4.5 gemma-4-31b-it-bf16 API service

It is recommended to use 8083 to avoid conflicts with other services.

Stable release:

```text
python -m mlx_vlm.server \
  --host <NODE_IP> \
  --port 8083 \
  --model <MODEL_VOLUME>/modeldown/models/gemma-4-31b-it-bf16 \
  --max-tokens 4096 \
  --max-kv-size 32768 \
  --prefill-step-size 2048 \
  --vision-cache-size 32 \
  --log-level INFO
```

Memory-saving configuration:

```text
python -m mlx_vlm.server \
  --host <NODE_IP> \
  --port 8083 \
  --model <MODEL_VOLUME>/modeldown/models/gemma-4-31b-it-bf16 \
  --max-tokens 4096 \
  --max-kv-size 32768 \
  --prefill-step-size 2048 \
  --vision-cache-size 32 \
  --kv-bits 4 \
  --kv-quant-scheme uniform \
  --kv-group-size 64 \
  --quantized-kv-start 4096 \
  --log-level INFO
```

Memory-saving configuration:

```text
python -m mlx_vlm.server \
  --host <NODE_IP> \
  --port 8082 \
  --model <MODEL_VOLUME>/modeldown/models/gemma-4-26b-a4b-it-bf16 \
  --max-tokens 4096 \
  --max-kv-size 32768 \
  --prefill-step-size 2048 \
  --vision-cache-size 32 \
  --kv-bits 4 \
  --kv-quant-scheme uniform \
  --kv-group-size 64 \
  --quantized-kv-start 4096 \
  --log-level INFO
```

#### 5. API health checks

MiniCPM services include:

```text
curl http://<NODE_IP>:8080/health
```

Qwen：

```text
curl http://<NODE_IP>:8081/health
```

Gemma：

```text
curl http://<NODE_IP>:8082/health
```

Gemma 31B：

```text
curl http://<NODE_IP>:8083/health
```

#### 6. API text calls

A mini-CPM example:

```text
curl http://<NODE_IP>:8080/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "<MODEL_VOLUME>/modeldown/models/MiniCPM-V-4.6-bf16",
    "messages": [
      {
        "role": "user",
        "content": "你好，请做一个简短自我介绍。"
      }
    ],
    "max_tokens": 512,
    "temperature": 0.0
  }'
```

Qwen's example:

```text
curl http://<NODE_IP>:8081/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "<MODEL_VOLUME>/modeldown/models/Qwen3.6-35B-A3B-bf16",
    "messages": [
      {
        "role": "user",
        "content": "你好，请做一个简短自我介绍。"
      }
    ],
    "max_tokens": 512,
    "temperature": 0.0
  }'
```

Gemma's example:

```text
curl http://<NODE_IP>:8082/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "<MODEL_VOLUME>/modeldown/models/gemma-4-26b-a4b-it-bf16",
    "messages": [
      {
        "role": "user",
        "content": "你好，请做一个简短自我介绍。"
      }
    ],
    "max_tokens": 512,
    "temperature": 0.0
  }'
```

The Gemma 31B example:

```text
curl http://<NODE_IP>:8083/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "<MODEL_VOLUME>/modeldown/models/gemma-4-31b-it-bf16",
    "messages": [
      {
        "role": "user",
        "content": "你好，请做一个简短自我介绍。"
      }
    ],
    "max_tokens": 512,
    "temperature": 0.0
  }'
```

#### 7. API image recognition calls

When calling from other Linux devices, do not put the large image base64 directly into the command-line parameter, otherwise:

```Markdown
bash: /usr/bin/curl: 参数列表过长
```

Recommended to write temporary JSON files and use them again `curl -d @file` Calling in.

This is the case with MiniCPM.

```text
IMG_B64=$(base64 -w 0 "/srv/llm/图片/1.jpg")

cat > /tmp/vlm_image_request.json <<EOF
{
  "model": "<MODEL_VOLUME>/modeldown/models/MiniCPM-V-4.6-bf16",
  "messages": [
    {
      "role": "user",
      "content": [
        {
          "type": "image_url",
          "image_url": {
            "url": "data:image/jpeg;base64,$IMG_B64"
          }
        },
        {
          "type": "text",
          "text": "请详细描述这张图片，并识别所有可见文字。"
        }
      ]
    }
  ],
  "max_tokens": 2048,
  "temperature": 0.0
}
EOF

curl http://<NODE_IP>:8080/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d @/tmp/vlm_image_request.json
```

Alternate port and model paths when calling Qwen:

```Markdown
端口: 8081
模型: <MODEL_VOLUME>/modeldown/models/Qwen3.6-35B-A3B-bf16
```

Alternate port and model paths when calling Gemma:

```Markdown
端口: 8082
模型: <MODEL_VOLUME>/modeldown/models/gemma-4-26b-a4b-it-bf16
```

When using Gemma 31B, replace the port and model path:

```Markdown
端口: 8083
模型: <MODEL_VOLUME>/modeldown/models/gemma-4-31b-it-bf16
```

#### 8. API OCR calls

It's a common OCR:

```text
IMG_B64=$(base64 -w 0 "/srv/llm/图片/1.jpg")

cat > /tmp/vlm_ocr_request.json <<EOF
{
  "model": "<MODEL_VOLUME>/modeldown/models/MiniCPM-V-4.6-bf16",
  "messages": [
    {
      "role": "user",
      "content": [
        {
          "type": "image_url",
          "image_url": {
            "url": "data:image/jpeg;base64,$IMG_B64"
          }
        },
        {
          "type": "text",
          "text": "请对图片进行OCR识别。逐行输出所有可见文字，保留原始顺序和表格结构。不要总结，不要编造。无法确认的文字标为[不确定]。"
        }
      ]
    }
  ],
  "max_tokens": 4096,
  "temperature": 0.0
}
EOF

curl http://<NODE_IP>:8080/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d @/tmp/vlm_ocr_request.json
```

OCR JSON output:

```text
IMG_B64=$(base64 -w 0 "/srv/llm/图片/1.jpg")

cat > /tmp/vlm_ocr_json_request.json <<EOF
{
  "model": "<MODEL_VOLUME>/modeldown/models/MiniCPM-V-4.6-bf16",
  "messages": [
    {
      "role": "user",
      "content": [
        {
          "type": "image_url",
          "image_url": {
            "url": "data:image/jpeg;base64,$IMG_B64"
          }
        },
        {
          "type": "text",
          "text": "请对图片进行OCR识别。只返回合法JSON，不要返回Markdown、解释或代码块。JSON字段：language、full_text、lines、tables、notes。lines按图片从上到下逐行排列；tables按表格行列输出；无法确认的文字标为[不确定]；不要编造图片中不存在的内容。"
        }
      ]
    }
  ],
  "max_tokens": 4096,
  "temperature": 0.0,
  "response_format": {
    "type": "json_object"
  }
}
EOF

curl http://<NODE_IP>:8080/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d @/tmp/vlm_ocr_json_request.json
```

The content structure of the model is expected to return:

```text
{
  "language": "zh-CN",
  "full_text": "完整识别文本",
  "lines": [
    {
      "index": 1,
      "text": "第一行文字",
      "confidence": "high"
    }
  ],
  "tables": [
    {
      "index": 1,
      "rows": [
        ["列1", "列2"],
        ["内容1", "内容2"]
      ]
    }
  ],
  "notes": "模糊区域说明"
}
```

#### 9. Examples of Python calls

```text
import base64
import requests

server = "http://<NODE_IP>:8080/v1/chat/completions"
model = "<MODEL_VOLUME>/modeldown/models/MiniCPM-V-4.6-bf16"
image_path = "/srv/llm/图片/1.jpg"

with open(image_path, "rb") as f:
    image_b64 = base64.b64encode(f.read()).decode("utf-8")

payload = {
    "model": model,
    "messages": [
        {
            "role": "user",
            "content": [
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/jpeg;base64,{image_b64}"
                    },
                },
                {
                    "type": "text",
                    "text": "请对图片进行OCR识别，只返回JSON，包含 full_text、lines、tables、notes。",
                },
            ],
        }
    ],
    "max_tokens": 4096,
    "temperature": 0.0,
    "response_format": {"type": "json_object"},
}

resp = requests.post(server, json=payload, timeout=300)
resp.raise_for_status()
print(resp.json()["choices"][0]["message"]["content"])
```

#### 10. OCR image preprocessing Recommended

OCR images should not be overcompressed. Documents, snippets, tables, and small-scale images are recommended to be converted, maintained in higher resolution, and slightly enhanced contrast.

It is available on Linux calling devices:

```text
python3 - <<'PY'
from PIL import Image, ImageOps, ImageEnhance

src = "/srv/llm/图片/1.jpg"
dst = "/tmp/ocr_ready.jpg"

img = Image.open(src)
img = ImageOps.exif_transpose(img).convert("RGB")
img.thumbnail((2400, 2400))
img = ImageEnhance.Contrast(img).enhance(1.15)
img.save(dst, quality=95)

print(dst)
PY
```

Then use `/tmp/ocr_ready.jpg` It's based on base 64.

```text
IMG_B64=$(base64 -w 0 "/tmp/ocr_ready.jpg")
```

#### 11. processor-kwargs warnings

`mlx_vlm.generate` CLI supports:

```text
--processor-kwargs '{"downsample_mode": "4x", "max_slice_nums": 36}'
```

This is usually helpful for MiniCPM-V 4.6's OCR subtitles, tables, and document class tasks, but will be slower and more memory-intensive.

Currently `mlx_vlm.server ` of `/v1/chat/completions ` API is only explicitly dealt with `resize_shape ` It's not a request.`processor_kwargs ` All of it sent to the bottom `generate/prepare_inputs`. So, directly in the JSON API, add:

```text
{
  "processor_kwargs": {
    "downsample_mode": "4x",
    "max_slice_nums": 36
  }
}
```

It will not come into force unless it is amended.`mlx_vlm/server.py` add forwarding logic.

Currently, the image-related parameters available in the API are:

```text
{
  "resize_shape": [2000, 2000]
}
```

Example:

```text
{
  "model": "<MODEL_VOLUME>/modeldown/models/MiniCPM-V-4.6-bf16",
  "messages": [],
  "max_tokens": 4096,
  "temperature": 0.0,
  "resize_shape": [2000, 2000]
}
```

#### 12. Parameter Recommended

OCR is a stable priority:

```text
--max-tokens 4096
--max-kv-size 32768
--prefill-step-size 2048
--vision-cache-size 64
```

Long context/provincial memory:

```text
--max-kv-size 262144
--prefill-step-size 4096
--kv-bits 4
--kv-quant-scheme uniform
--kv-group-size 64
--quantized-kv-start 4096
```

Please note:

- `max_tokens` It is the maximum output token number, not the context length.

- `max_kv_size` Only the KV cache/token context of the server end configuration is the upper limit.

- The text context of the three model configurations is limited to: `262144` tokens.

- 35B/26B bf16 model is recommended to start with `32768 ` or `65536` In this context, don't start with 256K.

- Recommended by OCR `temperature=0.0`, reducing fabricated answers.

#### 13. Common Questions

##### 13.1 Access to services by other devices

Check whether the service is binding to the IP of the local area network:

```text
--host <NODE_IP>
```

Or:

```text
--host 0.0.0.0
```

Check the health interfaces:

```text
curl http://<NODE_IP>:8080/health
```

If a Mac firewall intercepts Python, it will require permission to connect to the station.

##### 13.2 curl newspaper parameters List is too long

Don't put the base64 directly into the command line parameter. Write to a JSON file:

```text
curl http://<NODE_IP>:8080/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d @/tmp/request.json
```

##### 13.3 How to write model path

In the API request `model ` Field recommendations and service start parameters `--model` It's perfectly consistent, for example:

```text
"<MODEL_VOLUME>/modeldown/models/MiniCPM-V-4.6-bf16"
```

##### 13.4 of the API `/v1/models` Not showing local models

`mlx_vlm.server ` of `/v1/models ` Major scan of Hugging Face cache, not necessarily listing past local paths `--model ` The model is pre-loaded. Just start the log.`Model and processor loaded successfully ` and `/v1/chat/completions` The content can be returned to show that the service is available.

##### 13.5 o Difference between MLX and mlx-vlm

`oMLX serve ` It is another multi-modal service entrance. Previously `oMLX 0.3.9.dev1 ` Built-in `mlx_vlm-0.4.5 ` Not supported `MiniCPM-V-4.6`, the following error is reported:

```Markdown
Model type minicpmv4_6 not supported.
```

The current independent source code environment installed is:

```Markdown
mlx-vlm 0.5.0
```

So it can be loaded directly.`MiniCPM-V-4.6-bf16`.

## R42 · oMLX Mac inference operation process

Current environment and memory baseline

The recording time:

```text
2026-05-13 17:52:35 CST
```

Hardware environment:

```text
Apple M3 Ultra (8E + 24P + 80GPU)
统一内存：512GB
```

Models: Follow-up data:

```text
RAM Usage: 183.5 / 512.0GB
swap inactive
GPU Usage: 3% @ 683 MHz
E-CPU Usage: 17%~21% @ 1237 MHz
P-CPU Usage: 0% @ 0 MHz
CPU+GPU+ANE Power: 0.37W
```

Explanation: The above data is from `sudo asitop` It is used to describe the verification environment of the process and the occupancy of memory after loading.

#### 1. Model directory

Model Father's Catalogue:

```text
<MODEL_VOLUME>/models/mlx-community
```

The target model directory:

```text
<MODEL_VOLUME>/models/mlx-community/DeepSeek-V4-Flash-4bit
```

Notes: `omlx serve --model-dir` Fill in the parent directory, not the model subdirectory.

#### 2. Start the oMLX

```text
omlx serve \
  --model-dir <MODEL_VOLUME>/models/mlx-community \
  --host 127.0.0.1 \
  --port 8000 \
  --max-model-memory disabled \
  --max-process-memory disabled \
  --paged-ssd-cache-dir <MODEL_VOLUME>/omlx-cache \
  --paged-ssd-cache-max-size 100GB \
  --hot-cache-max-size 8GB \
  --log-level info
```

Starting with success signs:

```text
Uvicorn running on http://127.0.0.1:8000
```

#### 3. API Key

The current actual API Key:

```text
<API_TOKEN>
```

Sources:

```text
~/.omlx/settings.json
```

All subsequent requests must include:

```text
[认证配置已脱敏；按当前实例配置]
```

#### 4. Look at the model

```text
[认证配置已脱敏；按当前实例配置]
  http://127.0.0.1:8000/v1/models | jq
```

Confirmation returns include:

```text
DeepSeek-V4-Flash-4bit
```

#### 5. Loading model

```text
curl -X POST \
[认证配置已脱敏；按当前实例配置]
  http://127.0.0.1:8000/v1/models/DeepSeek-V4-Flash-4bit/load | jq
```

#### 6. Non-flowing inference

```text
curl http://127.0.0.1:8000/v1/chat/completions \
[认证配置已脱敏；按当前实例配置]
  -H "Content-Type: application/json" \
  -d '{
    "model": "DeepSeek-V4-Flash-4bit",
    "messages": [
      {"role": "user", "content": "你好，请简要介绍一下你自己。"}
    ],
    "max_tokens": 512,
    "temperature": 0.7,
    "top_p": 0.95,
    "stream": false
  }' | jq
```

#### 7. Fluidic inference

```text
curl -N http://127.0.0.1:8000/v1/chat/completions \
[认证配置已脱敏；按当前实例配置]
  -H "Content-Type: application/json" \
  -d '{
    "model": "DeepSeek-V4-Flash-4bit",
    "messages": [
      {"role": "user", "content": "写一个 Python 快速排序函数。"}
    ],
    "max_tokens": 1024,
    "temperature": 0.7,
    "top_p": 0.95,
    "stream": true
  }'
```

#### 8. Common Questions

`Invalid API key`

Reason: The key in the request's head is wrong. Currently used `<API_TOKEN>`.

`address already in use`

The reason: the port is occupied. How to deal with:

```text
lsof -nP -iTCP:8000 -sTCP:LISTEN
```

Or change the port directly, for example:

```text
--port 8001
```

`首次加载较慢`

The reason for this is that the model has a large volume and is a normal phenomenon.

#### 9. Modify the API Key

If you want to change it to your own key, when you restart the service explicitly specify:

```text
omlx serve \
  --model-dir <MODEL_VOLUME>/models/mlx-community \
  --host 127.0.0.1 \
  --port 8000 \
[认证配置已脱敏；按当前实例配置]
  --max-model-memory disabled \
  --max-process-memory disabled \
  --paged-ssd-cache-dir <MODEL_VOLUME>/omlx-cache \
  --paged-ssd-cache-max-size 100GB \
  --hot-cache-max-size 8GB \
  --log-level info
```

The request was then changed to:

```text
[认证配置已脱敏；按当前实例配置]
```

#### 10. MLX-VLM Gemma MXFP8: prefix/prompt caching

> This section is used `mlx_vlm.server ` It's not.`omlx serve`. Applicable model:

  - `<MODEL_VOLUME>/modeldown/models/gemma-4-26b-a4b-it-mxfp8`

  - `<MODEL_VOLUME>/modeldown/models/gemma-4-31b-it-mxfp8`

Caching uses MLX-VLM's APC (Automatic Prefix Caching). It caches repeated prompts, long system prompts, long document context, and multiple historical prefixes. The request side must be repeated.`X-APC-Tenant` It's easy to isolate and hit the same group of caches.

Please note: Do not add at the same time when starting APC `--kv-bits` The server will skip the APC when the KV cache quantization is enabled.

##### 10.1 Start 26B-A4B MXFP8 (recommended for daily use)

```text
cd /srv/llm/Desktop/llm-workspace/oMLX-vlm/mlx-vlm

APC_ENABLED=1 \
APC_NUM_BLOCKS=8192 \
APC_BLOCK_SIZE=16 \
APC_DISK_PATH=<MODEL_VOLUME>/mlx-vlm-apc-cache/gemma-4-26b-a4b-it-mxfp8 \
APC_DISK_MAX_GB=80 \
APC_DISK_SHARD_MAX_BLOCKS=256 \
APC_LAYER_MAJOR_MEMORY_MIN_TOKENS=50000 \
APC_HASH=fast \
../oMLX-vlm/bin/python -m mlx_vlm.server \
  --host 0.0.0.0 \
  --port 18082 \
  --model <MODEL_VOLUME>/modeldown/models/gemma-4-26b-a4b-it-mxfp8 \
  --log-level INFO \
  --max-tokens 2048 \
  --max-kv-size 65536 \
  --prefill-step-size 2048 \
  --vision-cache-size 32
```

Health checks:

```text
curl http://<NODE_IP>:18082/health
curl http://<NODE_IP>:18082/v1/cache/stats | jq
```

##### 10.2 Starting 31B MXFP8 ((quality priority)

```text
cd /srv/llm/Desktop/llm-workspace/oMLX-vlm/mlx-vlm

APC_ENABLED=1 \
APC_NUM_BLOCKS=8192 \
APC_BLOCK_SIZE=16 \
APC_DISK_PATH=<MODEL_VOLUME>/mlx-vlm-apc-cache/gemma-4-31b-it-mxfp8 \
APC_DISK_MAX_GB=100 \
APC_DISK_SHARD_MAX_BLOCKS=256 \
APC_LAYER_MAJOR_MEMORY_MIN_TOKENS=50000 \
APC_HASH=fast \
../oMLX-vlm/bin/python -m mlx_vlm.server \
  --host 0.0.0.0 \
  --port 18083 \
  --model <MODEL_VOLUME>/modeldown/models/gemma-4-31b-it-mxfp8 \
  --log-level INFO \
  --max-tokens 2048 \
  --max-kv-size 65536 \
  --prefill-step-size 2048 \
  --vision-cache-size 32
```

Health checks:

```text
curl http://<NODE_IP>:18083/health
curl http://<NODE_IP>:18083/v1/cache/stats | jq
```

##### 10.3 Remote image request:26B-A4B, with Prefix cache

Calling the device to execute. Instead of following the local path of the server, the image is inserted into the base64 JSON file and uploaded.

```text
IMG="/srv/llm/图片/1.jpg"
REQ="/tmp/gemma26_apc_image_request.json"
TENANT="lab"

IMG_B64=$(base64 -w 0 "$IMG")

cat > "$REQ" <<EOF
{
  "model": "<MODEL_VOLUME>/modeldown/models/gemma-4-26b-a4b-it-mxfp8",
  "messages": [
    {
      "role": "system",
      "content": "你是一个擅长图像理解的中文助手。请准确描述图片内容，必要时指出不确定之处。回答必须使用中文，结构清晰，先给结论，再描述细节。"
    },
    {
      "role": "user",
      "content": [
        {
          "type": "text",
          "text": "请详细描述这张图片，包括主体、场景、文字、颜色、可能的用途。请用中文回答。"
        },
        {
          "type": "input_image",
          "image_url": "data:image/jpeg;base64,$IMG_B64"
        }
      ]
    }
  ],
  "max_tokens": 768,
  "temperature": 0.2,
  "top_p": 0.9,
  "stream": true
}
EOF

curl -N http://<NODE_IP>:18082/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "X-APC-Tenant: $TENANT" \
  --data-binary @"$REQ"
```

Repeat with the same image, system prompt, and `X-APC-Tenant` When requesting, it should be easier to hit the prefix/prompt cache.

##### 10.4 Remote image request:31B, with Prefix cache

```text
IMG="/srv/llm/图片/1.jpg"
REQ="/tmp/gemma31_apc_image_request.json"
TENANT="lab"

IMG_B64=$(base64 -w 0 "$IMG")

cat > "$REQ" <<EOF
{
  "model": "<MODEL_VOLUME>/modeldown/models/gemma-4-31b-it-mxfp8",
  "messages": [
    {
      "role": "system",
      "content": "你是一个擅长图像理解的中文助手。请准确描述图片内容，必要时指出不确定之处。回答必须使用中文，结构清晰，先给结论，再描述细节。"
    },
    {
      "role": "user",
      "content": [
        {
          "type": "text",
          "text": "请详细描述这张图片，包括主体、场景、文字、颜色、可能的用途。请用中文回答。"
        },
        {
          "type": "input_image",
          "image_url": "data:image/jpeg;base64,$IMG_B64"
        }
      ]
    }
  ],
  "max_tokens": 768,
  "temperature": 0.2,
  "top_p": 0.9,
  "stream": true
}
EOF

curl -N http://<NODE_IP>:18083/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "X-APC-Tenant: $TENANT" \
  --data-binary @"$REQ"
```

##### 10.5 Text Prefix cache for life testing

The first request is to write a cache:

```text
TENANT="lab"

curl -N http://<NODE_IP>:18082/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "X-APC-Tenant: $TENANT" \
  -d '{
    "model": "<MODEL_VOLUME>/modeldown/models/gemma-4-26b-a4b-it-mxfp8",
    "messages": [
      {
        "role": "system",
        "content": "你是一个中文技术助手。下面所有回答都要简洁、准确、按步骤说明。这个系统提示词会在多次请求中保持不变，用于测试 prefix cache。"
      },
      {
        "role": "user",
        "content": "固定前缀：Apple Silicon、MLX、统一内存、Metal 后端、本地 VLM 推理。问题 A：请说明统一内存对本地大模型推理的帮助。"
      }
    ],
    "max_tokens": 256,
    "temperature": 0.2,
    "stream": true
  }'
```

The second request repeats the same prefix, changing only the last question:

```text
TENANT="lab"

curl -N http://<NODE_IP>:18082/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "X-APC-Tenant: $TENANT" \
  -d '{
    "model": "<MODEL_VOLUME>/modeldown/models/gemma-4-26b-a4b-it-mxfp8",
    "messages": [
      {
        "role": "system",
        "content": "你是一个中文技术助手。下面所有回答都要简洁、准确、按步骤说明。这个系统提示词会在多次请求中保持不变，用于测试 prefix cache。"
      },
      {
        "role": "user",
        "content": "固定前缀：Apple Silicon、MLX、统一内存、Metal 后端、本地 VLM 推理。问题 B：请说明 Metal 后端对本地推理速度的帮助。"
      }
    ],
    "max_tokens": 256,
    "temperature": 0.2,
    "stream": true
  }'
```

See the cache statistics:

```text
curl http://<NODE_IP>:18082/v1/cache/stats | jq
```

Clear the cache:

```text
curl -X POST http://<NODE_IP>:18082/v1/cache/reset | jq
```

## R43 · oMLX inference framework performance test reports and load testing processes

#### 1. Test subjects

- inference framework : `oMLX`

- model : `DeepSeek-V4-Flash-4bit`

- Endpoint: `http://127.0.0.1:8000/v1/chat/completions`

- Authentication: `Bearer <API_TOKEN>

- Load testing tools: `evalscope 1.7.0`

- The data collection: `random`

- Input length: `128 tokens`

- Exit limits: `256 tokens`

- The resulting directory:

```text
/srv/llm/Desktop/llm-workspace/perf-bench/outputs/20260513_180339/omlx-dsv4-sweep
```

#### 2. Overall results

- Generated tokens: `9,693`

- Average output rate: `34.84 tok/s`

- The total duration of the test: `278.22 s`

- Success rates: `100%`

#### 3. Core performance data

|concurrency|Number of requests| Avg Latency | P99 Latency | TTFT | TPOT | Gen. tok/s | Decode tok/s |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 5 | 7.544 s | 9.480 s | 17.1 ms | 34.8 ms | 28.73 | 28.74 |
| 1 | 20 | 7.582 s | 8.580 s | 25.0 ms | 34.2 ms | 29.38 | 29.21 |
| 2 | 10 | 10.257 s | 12.800 s | 3.2 ms | 47.5 ms | 41.11 | 21.04 |
| 4 | 10 | 13.459 s | 19.340 s | 3.7 ms | 69.8 ms | 55.15 | 14.32 |

#### 4. Conclusions

- The single-stream baseline is stable: `并发 1 ` Production rate is about `29 tok/s ` TPOT is about.`34 ms`.

- After improving concurrency, total throughput increased:

  - `并发 2 `: `41.11 tok/s`

  - `并发 4 `: `55.15 tok/s`

- After improving concurrency, the single request latency significantly changed:

  - `并发 1 `: `7.58 s`

  - `并发 2 `: `10.26 s`

  - `并发 4 `: `13.46 s`

- If the goal is interactive experience, prioritize it.`并发 1`.

- If the goal is overall throughput, in the current test `并发 4` Highest throughput.

#### 5. load testing Operational processes

##### 5.1 Activation Environment

```text
cd /srv/llm/Desktop/llm-workspace
source /srv/llm/Desktop/llm-workspace/model-eval/bin/activate
evalscope --version
```

##### 5.2 Confirm the availability of the oMLX service

```text
[认证配置已脱敏；按当前实例配置]
  http://127.0.0.1:8000/v1/models | jq
```

Confirmation returns include:

```text
DeepSeek-V4-Flash-4bit
```

##### 5.3 Formal load testing

```text
cd /srv/llm/Desktop/llm-workspace/perf-bench

evalscope perf \
  --url http://127.0.0.1:8000/v1/chat/completions \
  --model DeepSeek-V4-Flash-4bit \
  --api openai \
[认证配置已脱敏；按当前实例配置]
  --dataset random \
  --tokenizer-path <MODEL_VOLUME>/models/mlx-community/DeepSeek-V4-Flash-4bit \
  --parallel 1 1 2 4 \
  --number 5 20 10 10 \
  --min-prompt-length 128 \
  --max-prompt-length 128 \
  --max-tokens 256 \
  --stream \
  --temperature 0 \
  --no-test-connection \
  --name omlx-dsv4-sweep \
  --outputs-dir ./outputs
```

##### 5.4 See the results

```text
ls -la /srv/llm/Desktop/llm-workspace/perf-bench/outputs/20260513_180339/omlx-dsv4-sweep
```

The key documents:

- `performance_summary.txt`

- `perf_report.html`

- `parallel_*/benchmark_summary.json`

- `parallel_*/benchmark_data.db`

#### 6. Recommendations

- Interactive use: adoption `并发 1` This is the main reference.

- Batch throughput testing: continue up testing `并发 6 `, `并发 8`.

- When load testing, synchronously observe resources:

```text
sudo asitop
```

## R44 · Mac device inference framework classification summary

> This document is used to organize the current `llm-workspace ` The local inference framework for Mac's that are already in use or ready to be used, explaining how they work with Apple's MLX, GGUF, DeepSeek-V4-Flash, image VLM, concurrency batching services, `vllm-mlx `, ` vllm-metal `and the original ` vLLM`The relationship between them.

The current core conclusions: **oMLX and vllm-mlx are not new underlying inference cores, they are all service layers built on the Apple MLX ecosystem.`vllm-metal` The advantages are that the original version of vLLM has an Apple Silicon/Metal hardware plug-in route that is closer to the CLI, OpenAI API, scheduler, paged KV and prefix cache meanings of vLLM. The limitation is that it is currently text-only, the multi-modal image encoder is not connected yet, model coverage and stability are not equivalent to CUDA vLLM. The original vLLM was still primarily aimed at GPU service environments such as NVIDIA/CUDA, and could not be directly matched to the oMLX/vllm-mlx/vllm-metal graphics on the Mac.**

#### 1. General conclusions

The current project inference framework can be divided into seven categories:

|Categories|The Framework|Core positioning|Recommended use|
| --- | --- | --- | --- |
|MLX service layout layer| oMLX |Local inference servers based on MLX ecology|Multi-model services, concurrency requests, cache, and long-term running of APIs|
|MLX vLLM-style service layer| vllm-mlx |The vLLM-style service framework for Apple Silicon|Continuous batching / paged KV / prefix cache|
|VLLM Metal Plug-ins layer| vllm-metal |Apple Silicon/MLX/Metal plugins for the original vLLM|Text model vLLM API, Qwen/Gemma text concurrency, vLLM eco-compatibility verification|
|MLX single class model inference layer| mlx-lm,mlx-vlm,mlx-embeddings,dflash-mlx |Specific model load and inference capabilities|Text, images, embedding, and accelerated generation|
|GGUF inference layer| llama.cpp |GGUF model General inference engine|GGUF model, quantization, testing, general local service|
|Specialized inference layer| ds4 |DeepSeek-V4-Flash is a dedicated inference service.|DeepSeek-V4-Flash text-length context service|
|Production level reference| vLLM |High throughput inference servers in GPU ecosystems such as CUDA/HIP|NVIDIA GPU/Multi-GPU/High QPS production service|

The most important selection principles:

|Task|Framework for recommendations|
| --- | --- |
|MLX format text model Long term API services| oMLX |
|MLX format text model vLLM API / concurrency verification|Vllm-metal or vllm-mlx|
|MLX format images / VLM single model testing|mlx-vlm.server or oMLX|
|It requires continuous batching, concurrency scheduling, cache and multi-model management.|oMLX and load testing with vllm-mlx|
|Qwen 3.6 / Gemma4 text model vLLM-style service| vllm-metal |
|GGUF model| llama.cpp |
|DeepSeek-V4-Flash exclusive model| ds4 |
|Embedding / rerank services| oMLX + mlx-embeddings |
|True large-scale high concurrency production services| vLLM + NVIDIA GPU |

#### 2. Framework directories for current projects

Current work directory:

```text
/srv/llm/Desktop/llm-workspace
```

The main frameworks and directories that have emerged are:

|Names|Local routes|The real nature|
| --- | --- | --- |
| omlx | /srv/llm/Desktop/llm-workspace/omlx |Real oMLX source code directory|
| vllm-mlx |Not yet installed, recommended independent directory /srv/llm/Desktop/llm-workspace/vllm-mlx or independent virtual environment|The vLLM-style MLX service framework on Apple Silicon|
| vllm-metal | /srv/llm/Desktop/llm-workspace/vllm-metal |vLLM Apple Silicon / Metal plugins source code directory|
| oMLX-vlm/mlx-vlm | /srv/llm/Desktop/llm-workspace/oMLX-vlm/mlx-vlm |MLX-VLM source code directory, not oMLX|
| oMLX-vlm/oMLX-vlm | /srv/llm/Desktop/llm-workspace/oMLX-vlm/oMLX-vlm |Python virtual environment used by MLX-VLM|
| llama.cpp | /srv/llm/Desktop/llm-workspace/llama.cpp |llama.cpp source code and building directories|
| llamacpp-test | /srv/llm/Desktop/llm-workspace/llamacpp-test |llama.cpp testing directories|
| ds4 | /srv/llm/Desktop/llm-workspace/ds4 |DeepSeek-V4-Flash is a dedicated inference framework.|
| mlx-vlm-perf-bench | /srv/llm/Desktop/llm-workspace/mlx-vlm-perf-bench |MLX-VLM / OpenAI API performance evaluation directory|
| model-eval | /srv/llm/Desktop/llm-workspace/model-eval |model Assessment of virtual environments or a directory of assessment tools|
| perf-bench | /srv/llm/Desktop/llm-workspace/perf-bench |Performance testing related directories|

This is a particular point that needs to be corrected:

```Markdown
oMLX-vlm 这个目录名容易误导。
之前使用 python -m mlx_vlm.server 启动的是 MLX-VLM server，不是 oMLX server。
真正的 oMLX 源码目录是 /srv/llm/Desktop/llm-workspace/omlx。
vllm-mlx 目前还不是当前项目已安装的主服务框架，建议后续作为 oMLX 的对照压测框架单独安装。
vllm-metal 当前主要用于文本模型 OpenAI API / vLLM 兼容服务验证，不作为 VLM 图片服务主线。
```

#### 3. o Relationship between MLX and MLX ecology

The key packages you have installed in your current source code environment are as follows:

```Markdown
mlx              0.31.2
mlx-lm           0.31.3
mlx-vlm          0.5.0
mlx-embeddings   0.1.0
dflash-mlx       0.1.5.1
omlx             0.3.9.dev2
```

They're not on the same level.

The precision levels are as follows:

```Markdown
最底层：
  mlx / mlx-metal
    Apple Silicon 上的张量计算、Metal 加速、数组和算子执行。

模型运行层：
  mlx-lm
    文本 LLM 的加载、tokenizer、generate、stream_generate、BatchGenerator。

  mlx-vlm
    视觉语言模型的加载、图片预处理、vision encoder、VLM prompt 处理、图文推理。

  mlx-embeddings
    embedding / rerank 类模型加载和推理。

  dflash-mlx
    特定模型和场景下的加速生成后端。

服务调度层：
  oMLX
    OpenAI / Anthropic API 服务、多模型管理、连续批处理、KV cache、prefix cache、
    SSD cache、热缓存、模型生命周期、管理界面、MCP 工具调用等。
```

So the relationship between oMLX and these libraries can be understood as follows:

```Markdown
oMLX
  ├── 调用 mlx-lm 跑文本 LLM
  ├── 调用 mlx-vlm 跑视觉语言模型
  ├── 调用 mlx-embeddings 跑 embedding / rerank
  ├── 可调用 dflash-mlx 做部分加速路径
  └── 底层统一依赖 mlx / mlx-metal 在 Apple Silicon 上执行计算
```

#### 4. oMLX and Ollama / llama.cpp analogy

This analogy is basically true:

```Markdown
Ollama
  └── llama.cpp / GGML / GGUF
        └── CPU / Metal / CUDA 等底层推理
```

In the MLX ecosystem:

```Markdown
oMLX
  ├── mlx-lm
  │     └── mlx / mlx-metal
  ├── mlx-vlm
  │     └── mlx / mlx-metal
  ├── mlx-embeddings
  │     └── mlx / mlx-metal
  └── dflash-mlx
        └── mlx / mlx-metal
```

So this is how we can judge:

```Markdown
oMLX 不是新的底层推理框架。
oMLX 更像是 MLX 生态里的本地推理服务器和模型管理系统。
```

But it's not just a layer of HTTP interface. OMLX offers a number of additional service capabilities:

|Capacity|oMLX is available|
| --- | --- |
|OpenAI API compatible interface|Support|
|Anthropic API compatible interface|Support|
|Multi-model directory automatically detected|Support|
|Multi-model loading and unloading|Support|
|LRU model eliminated|Support|
|model TTL|Support|
|Other names|Support|
| Admin Web UI |Support|
| continuous batching |Supported by mainly passed mlx-lm BatchGenerator|
|KV cache management|Support|
| prefix / prompt cache |Support|
|SSD layered KV cache|Support|
| hot cache |Support|
|VLM image input serviced|Support|
|Embedding / rerank services|Support|
|MCP tool calls|Support|

More precisely:

```Markdown
oMLX = MLX 模型推理库 + 服务封装 + 并发调度 + 缓存系统 + 多模型管理 + API/UI。
```

#### 5. oMLX,vllm-mlx,vllm-metal and the relationship between vLLM

These names are easily confused and need to be distinguished separately.

##### 5.1 Definition of the three

|The Framework|Definition of a phrase|
| --- | --- |
| oMLX |MLX local inference server and model management platform for Mac/Apple Silicon|
| vllm-mlx |A framework for MLX inference services in the vLLM style for Apple Silicon|
| vllm-metal |Apple Silicon/Metal hardware plug-in for the original vLLM, underlying passed MLX/Metal execution|
| vLLM |A high throughput LLM serving framework for GPU ecosystems such as CUDA/HIP|

##### 5.2 Levels of relations

`oMLX ` and `vllm-mlx` All of them are in the MLX service layer:

```Markdown
oMLX / vllm-mlx
  ├── mlx-lm
  ├── mlx-vlm
  ├── mlx-embeddings
  └── mlx / mlx-metal
```

`vllm-metal ` The location is different. It's not another one.`mlx-lm.server ` Packaging layers, instead of the original `vLLM` The platform plug-in mechanism is available on Apple Silicon/MLX/Metal:

```Markdown
vLLM core
  ├── vLLM scheduler / OpenAI API / v1 engine
  ├── vllm-metal platform plugin
  │     ├── mlx-lm / mlx-vlm model loading
  │     ├── Metal paged attention / paged KV
  │     ├── Qwen3.5 / Qwen3.6 hybrid SDPA + GDN path
  │     └── MLX / Metal kernels
  └── Apple Silicon unified memory
```

Originally published `vLLM` This is another technical route:

```Markdown
vLLM
  ├── CUDA / HIP / XPU / CPU 等后端
  ├── PagedAttention / KV cache 管理
  ├── continuous batching
  ├── tensor parallel / pipeline parallel
  └── OpenAI-compatible serving
```

So we can't `vllm-mlx` It is important to understand:

```Markdown
原版 vLLM 在 Mac 上的完整等价实现。
```

It's more accurate to understand:

```Markdown
vllm-mlx 是在 Apple Silicon / MLX / Metal 生态中实现 vLLM-style 服务思想。
vllm-metal 是原版 vLLM 的 Apple Silicon 插件路线，但当前能力仍受 Metal/MLX 后端实现进度限制。
```

##### 5.3 Functionality Contrast

|Comparisons| oMLX | vllm-mlx | vllm-metal |The original vLLM|
| --- | --- | --- | --- | --- |
|Main hardware| Apple Silicon Mac | Apple Silicon Mac | Apple Silicon Mac |NVIDIA GPU / AMD GPU / other backend|
|The main baseline| MLX / Metal | MLX / Metal | vLLM core + MLX / Metal plugin |CUDA / HIP / XPU / CPU, etc.|
|Model operating library| mlx-lm,mlx-vlm,mlx-embeddings,dflash-mlx | mlx-lm,mlx-vlm,mlx-embeddings |Mlx-lm / Mlx-vlm plus vLLM v1 engine|vLLM's own model executes the plug and the backend of the hardware|
|Location|Mac local inference server + management platform|VLLM-style Mac inference services|vLLM implemented the Metal plug-in on Apple Silicon|High throughput output-level inference server|
|Current location|Framework for mainstream services|Installing the control frame|Text vLLM Plugin Routing Control Framework|NVIDIA Production Services references|
| OpenAI API |Support|Support|support, go vllm serve|Support|
| Anthropic API |Support|Support|Not as the main position|View versions and deployments|
| continuous batching |Support, main dependency mlx-lm BatchGenerator and self-scheduling|Support, focus on location|Support for vLLM scheduler / batched tokens / max seqs, by model measured|Core capabilities|
| Paged KV / KV cache |Support for KV cache, prefix cache, SSD layered cache|Support for paged KV, prefix cache, SSD tiering|Support for Metal paged attention / paged KV, Qwen 3.6 text available|PageedAttention is the ability to sign|
| Prefix cache |Support|Support|Supported, but hybrid/GDN models need to be explicitly activated and measured|Support|
| SSD cache |Support|Support|It's not a mainstream capability.|Not the main production dependency, more dependency GPU VRAM|
|Multimodal management|Powerful, including EnginePool, LRU, TTL, Admin UI|We have a service level capability, specific maturity needs load testing|Single vllm service is more suitable for single model services|Multi-model deployments are supported, but common production deployments are broken down by model/example|
|Manage the interface| Admin Dashboard / macOS app |README refers to capabilities such as metrics / benchmarks, specifically in version.|No dedicated Mac management interface|Mainly service APIs and metrics|
|VLM / Input of images|support, dependency mlx-vlm|Theoretical dependency mlx-vlm, to be measured|Currently unavailable: multimodal encoder execution unconnected Metal runner|Support for some multi-modal models|
| embedding / rerank |Support|Support|Not the current main position|Support for embedding, rerank view of model/service implementation|
|Multi-GPU/Distributed|Not the main position|Not the main position|Apple Silicon single-machine is not the main position.|Strong force|
|Production maturity|Mac's local service direction is more complete and still needs to be model measured|Alpha/vLLM-style, suitable for controlled verification|Alpha/plugin route, text measurable, multi-mode not completed|The most mature, especially in the NVIDIA ecosystem|
|Is it possible to replace vLLM?|No substitute for equality|No substitute for equality|Closer to vLLM API/engine, but not equivalent to CUDA vLLM|The body|

##### 5.4 Applied contrasting scenarios

|The scene|Framework for recommendations|Why?|
| --- | --- | --- |
|Mac single-machine MLX model unified service| oMLX |Currently installed, model management, admin UI, cache and service governance are more complete|
|Verify the vLLM-style concurrency capabilities on Mac| vllm-metal / vllm-mlx |vllm-metal running the original vLLM plugin route; vllm-mlx is another MLX service layer control.|
|Mac text model continuous batching load testing|OMLX + vllm-metal + vllm-mlx comparison|Obtain measured results with the same model, concurrency, and data|
|Mac VLM image service|oMLX priority, mlx-vlm.server comparison|vllm-metal The current image encoder is not connected and cannot be used for VLM image request|
|Local inference within small teams| oMLX |Multi-model management and API services are more convenient|
|Multi-agent / Repeat system prompts / prefixes Repeat|OMLX,vllm-metal or vllm-mlx|All have prefix cache/KV cache related capabilities, but need to be model-measured.|
|GGUF model services| llama.cpp |oMLX / vllm-mlx / vllm-metal is primarily aimed at MLX/HF models, not GGUF's main route|
|Large-scale high QPS commercial API|The original vLLM + NVIDIA GPU|Mac single-machine unsuitable for collaboration is the main force behind this scenario|
|multi-GPU / multi-node / tensor parallel|The original vLLM|Apple Silicon single-machine MLX services are not as productive|

##### 5.5 Recommended judgments on current projects

The current project has been completed `oMLX` The source code is installed, so short-term recommendations:

```Markdown
先用 oMLX 做主线验证；
vllm-metal 用于 Qwen3.6 / Gemma4 等文本模型的 vLLM API 和并发能力验证；
后续再安装 vllm-mlx，作为另一条 MLX 服务层对照压测。
```

The following is the list of recommended test sequences:

```Markdown
1. oMLX 启动 /v1/models，确认模型发现和加载正常。
2. 用纯文本模型测试并发 1 / 2 / 4 / 8 / 16。
3. 用 VLM 图片模型测试并发 1 / 2 / 4。
4. 用 vllm-metal 对 Qwen3.6 / Gemma4 等文本模型做 vLLM API、max-num-seqs / max-num-batched-tokens / prefix cache 验证。
5. 安装 vllm-mlx，用同样模型和 EvalScope 参数重复测试。
6. 对比 RPS、TTFT、TPOT、P99 latency、success rate、内存占用。
```

The conclusions of the document should be amended as follows:

```Markdown
在 Mac / MLX 生态中，oMLX 和 vllm-mlx 都是可选的并发服务框架。
oMLX 当前更适合作为主力服务框架；
vllm-metal 当前已经可作为 vLLM 插件路线的文本对照框架；
vllm-mlx 更适合作为另一个 vLLM-style MLX 服务层对照验证框架；
原版 vLLM 仍然是 NVIDIA GPU 高吞吐生产服务的参照系，不能被 Mac 单机方案完全替代。
```

#### 6. The positioning of frameworks

##### 6.1 oMLX

Order the entrance:

```text
omlx serve
```

The source code for the directory is:

```text
/srv/llm/Desktop/llm-workspace/omlx
```

Current source code environment:

```text
/srv/llm/Desktop/llm-workspace/omlx/omlx-build
```

Suitable scenarios:

- MLX format text model services

- Multi-model API servers

- Long-running local inference services

- OpenAI / Anthropic API compatibility services

- Multi-user or multi-client concurrency access

- Prefix cache / KV cache / SSD cache scene

- Embedding / rerank Unified Services

- Local model platforms for managing interfaces

It is not appropriate or should be noted:

- Not suitable for direct operation of GGUF models

- It's not the same as llama.cpp.

- If you want to support a model architecture, it depends on the base.`mlx-lm ` / ` mlx-vlm ` / ` mlx-embeddings`

- VLM large language model can still be affected by prefill and vision encoder in a 64K image scene, and cannot simply be equated to vLLM-level throughput.

Recommended use:

```Markdown
Mac Studio / Apple Silicon 上的主力 MLX 模型服务框架。
```

##### 6.2 vllm-mlx

Project address:

```Markdown
https://github.com/waybarrios/vllm-mlx
```

Location:

```Markdown
Apple Silicon 上的 vLLM-style 推理服务框架。
```

Its core goal is not to replace MLX, but to pack MLX's eco-model operating libraries into a service form closer to vLLM:

```Markdown
vllm-mlx
  ├── OpenAI API
  ├── Anthropic API
  ├── continuous batching
  ├── paged KV cache
  ├── prefix cache
  ├── SSD-tiered cache
  ├── mlx-lm
  ├── mlx-vlm
  ├── mlx-embeddings
  └── MLX / Metal
```

Suitable scenarios:

- VLLM-style continuous batching on Mac

- Compare concurrency throughput with oMLX

- MLX text model API services

- MLX VLM service experiment

- Prefix cache / paged KV cache / SSD cache related tests

- OpenAI / Anthropic API compatibility service verification

It is not appropriate or should be noted:

- Not the original vLLM.

- VLLM on NVIDIA GPUs can't be directly replaced by VLLM.

- MLX/Metal/Apple Silicon single-machine capabilities are still underdependent

- Support for specific models depends on `mlx-lm ` / ` mlx-vlm`

- More overlap with the oMLX functionality must be passed measured to determine which model is better suited to the current model.

It is recommended to install in a standalone environment without contaminating existing oMLX:

```text
cd /srv/llm/Desktop/llm-workspace

uv venv --python 3.12 vllm-mlx-env

source /srv/llm/Desktop/llm-workspace/vllm-mlx-env/bin/activate

uv pip install -U pip setuptools wheel

uv pip install vllm-mlx \
  --index-url https://pypi.tuna.tsinghua.edu.cn/simple
```

Example start:

```text
vllm-mlx serve <MODEL_VOLUME>/modeldown/models/Qwen3.6-35B-A3B-bf16 \
  --host 0.0.0.0 \
  --port 18084 \
  --continuous-batching
```

Recommended use:

```Markdown
作为 oMLX 的对照框架，用同一模型和同一 EvalScope 参数测试并发能力。
```

##### 6.3 vllm-metal

Location:

```Markdown
vllm-metal 是原版 vLLM 的 Apple Silicon / Metal 硬件插件路线。
它复用 vLLM 的 CLI、OpenAI API、scheduler、v1 engine 等服务层能力，
并通过 MLX / Metal 在 Apple Silicon 上执行模型。
```

It's not `vllm-mlx` as a synonym for:

```Markdown
vllm-mlx   = 独立的 vLLM-style MLX 服务框架。
vllm-metal = 原版 vLLM 平台插件，将 vLLM 的服务层接到 Apple Silicon / Metal。
```

It's `vllm-mlx` The difference between:

|Comparisons| vllm-metal | vllm-mlx |
| --- | --- | --- |
|Technical routes|Plugins for the original vLLM platform|A separate vLLM-style MLX service framework|
|Orders to enter| vllm serve | vllm-mlx serve |
|Framework Levels| vLLM core + Metal plugin |MLX service layer|
|Implementation at the bottom| vLLM v1 engine + vllm-metal worker + MLX / Metal |MLX service layer implementation|
|Suitable for use|Verify the vLLM API on the Mac, Paged KV, prefix cache, text concurrency|Contrasting the vLLM-style service layer with oMLX|
|Multimodal|Current image encoder not connected|Theoretical dependency mlx-vlm, to be measured|

Advantages:

- Input is compatible with the original vLLM, used `vllm serve` It is also available as an OpenAI-compatible API.

- It is more user-friendly to deploy familiar vLLMs, with parameters, model services and client calls closer to the original vLLMs.

- It can replicate service concepts such as vLLM scheduler, paged KV, prefix cache, batched tokens.

- The vLLM API compatibility of MLX/HF directory text models such as Qwen 3.6 and Gemma 4 is validated on Apple Silicon.

- Supported by Pass `max-num-seqs `, ` max-num-batched-tokens`and related scheduling parameters for text serving load tests.

- The same OpenAI API load testing tool can be used with oMLX, vllm-mlx, as opposed to TTFT, TPOT, RPS, P99 latency and success rate.

Limitations:

- Currently, Alpha/plug-in routes, model coverage and stability are not equivalent to CUDA vLLM.

- It is not a complete Mac version of vLLM, nor can it replace the original vLLM production deployment on the NVIDIA GPU.

- Currently, it is more suitable for text-only service verification, where multimodal image input is not available on the mainline.

- VLM requests can even be resolved by the front end `mm_features` Metal runner may still be unable to execute image encoder and embedding splice.

- Not supporting GGUF, GGUF should still go `llama.cpp ` or the DeepSeek-V4-Flash `ds4` The route.

- Multi-model management, model lifecycle, management interface, cache management capabilities are not as complete as oMLX.

- The model's chat template, thinking switches, and special tokenizer behaviour require additional attention, otherwise unexpected outputs may occur.

Suitable scenarios:

- Verify the availability of the vLLM API and vLLM Scheduler on Apple Silicon on Mac.

- OpenAI API services for MLX/HF directory text models such as Qwen 3.6 / Gemma 4.

- Text model prefix cache, pageed KV, batched tokens, concurrency request load testing.

- The same model, the same pronoun, and the same horizontal contrast under the concurrency parameter are compared with oMLX, vllm-mlx.

- Single-model text inference service experiments in small teams on the Internet.

Unsuitable scenarios:

- VLM image identification of the main service.

- GGUF model service.

- DeepSeek-V4-Flash is dedicated model service.

- Multi-model unified management platform.

- CUDA vLLM multi-GPU / multi-node production throughput is expected to reach service.

Recommended use:

```Markdown
vllm-metal 适合作为 Mac 上的 vLLM 插件路线对照框架，
重点用于文本模型 API 兼容性、paged KV、prefix cache 和并发调度验证。
它可以补充 oMLX 的主线压测，但不替代 oMLX 的多模型管理和 VLM 服务能力。
```

##### 6.4 vLLM

Project location:

```Markdown
面向 GPU 生产服务的高吞吐 LLM inference / serving 框架。
```

Suitable scenarios:

- NVIDIA GPU

- Multi-GPU/multi-node

- High QPS online services

- tensor parallel

- pipeline parallel

- OpenAI-compatible APIs on a large scale

- High throughput text generation

The difference between the Mac and the local framework:

```Markdown
vLLM 的强项建立在 CUDA/HIP 等 GPU 后端和成熟的 PagedAttention / batching / 分布式服务能力之上。
Mac 上的 oMLX / vllm-mlx 是 MLX / Metal 生态里的本地服务框架，不能等价替代原版 vLLM。
```

Location of current projects:

```Markdown
vLLM 是生产级高并发服务的参照系，不是当前 Mac 本地已部署主框架。
```

##### 6.5 MLX-LM

Common entries:

```text
python -m mlx_lm.server
```

It's a code word.

```text
from mlx_lm import load, generate, stream_generate
```

Suitable scenarios:

- MLX model in pure text

- Scripted inference

- Small and medium-sized models for rapid verification

- Single model services that do not require complex model management

Relation with oMLX:

```Markdown
mlx-lm 是 oMLX 的文本模型底层之一。
oMLX 的文本 LLM 能力主要建立在 mlx-lm 之上。
```

Limitations:

- It's more of a model operating library than a complete local model platform.

- Multi-model management, cache management, strategy management, interface management, and service governance are less than oMLX.

##### 6.6 MLX-VLM

How to get started in current projects:

```text
cd /srv/llm/Desktop/llm-workspace/oMLX-vlm/mlx-vlm

../oMLX-vlm/bin/python -m mlx_vlm.server \
  --host 0.0.0.0 \
  --port 18082 \
  --model <MODEL_VOLUME>/modeldown/models/gemma-4-26b-a4b-it-mxfp8
```

Suitable scenarios:

- Picture understanding

- OCR

- Questions and Answers

- Multimodal model verification

- Gemma/MiniCPM/Qwen VLM class model testing

- Single model image API services

Relation with oMLX:

```Markdown
mlx-vlm 是 oMLX 的 VLM 底层之一。
oMLX 可以调用 mlx-vlm 的模型加载、图片处理和 VLM 推理能力。
```

Interpretation requiring correction:

```Markdown
MLX-VLM 代码中存在 BatchGenerator / VLM batch 相关能力，
但你之前使用 python -m mlx_vlm.server 对 26B/31B + 图片 + 64K 的实测结果显示：
并发 2 时 TTFT、TPOT 和总延迟明显变差，更接近低并发队列式服务。
```

As a result, in current projects, MLX-VLM is more suitable for:

```Markdown
图片模型功能验证、单模型低并发 API、图文性能基准测试。
```

It is not recommended to start directly `mlx_vlm.server` It was:

```Markdown
类似 vLLM 的高效 continuous batching 生产服务。
```

If you want to verify the true capability of an oMLX VLM service, you should use:

```text
omlx serve
```

It's not:

```text
python -m mlx_vlm.server
```

##### 6.7 MLX-Embeddings

Suitable scenarios:

- embedding

- rerank

- Local RAG to quantization

- Document retrieval

- Multimodal Support Models in Unified API Services

Relation with oMLX:

```Markdown
mlx-embeddings 是 oMLX embedding / rerank 能力的底层依赖之一。
```

How to recommend:

```Markdown
如果只是单独测试 embedding，可以直接使用 mlx-embeddings。
如果要长期服务化，建议通过 oMLX 管理。
```

##### 6.8 dflash-mlx

Suitable scenarios:

- Accelerated generation of specific models

- Speculative / diffusion decoding class optimization path

- Improved response speeds for partially short context or adapted models

Relation with oMLX:

```Markdown
dflash-mlx 是 oMLX 可调用的加速后端，不是通用替代 mlx-lm / mlx-vlm 的框架。
```

Please note:

- We need to see if the model is compatible.

- It's important to look at the context and see if the length is appropriate

- Long context scenarios may fall back to oMLX's usual LLM/VLM engine

##### 6.9 llama.cpp

Order the entrance:

```text
./build/bin/llama-server
```

Local directories:

```text
/srv/llm/Desktop/llm-workspace/llama.cpp
```

Suitable scenarios:

- GGUF model

- Common quantization model

- CPU / Metal Locally inference

- Model verification after conversion

- Quantization version comparison

- OpenAI compatible with HTTP servers

The difference between oMLX and OMLX:

```Markdown
llama.cpp 是 GGUF 推理引擎。
oMLX 是 MLX 模型服务框架。
```

The model format selection:

```Markdown
GGUF 模型 -> llama.cpp
MLX 模型目录 -> oMLX / mlx-lm / mlx-vlm
```

Concurrency notes:

```Markdown
llama.cpp 的 llama-server 支持 slots、--parallel 和 --cont-batching。
但在当前项目中，还没有对大模型、长上下文、Mac Studio M3 Ultra 场景下的高效批次并发做完整验证。
```

The current recommendation is therefore:

```Markdown
llama.cpp 作为 GGUF 主力框架；
是否作为高并发服务，需要按具体模型、上下文、parallel 参数单独压测。
```

##### 6.10 ds4

Local directories:

```text
/srv/llm/Desktop/llm-workspace/ds4
```

Suitable scenarios:

- DeepSeek-V4-Flash

- DeepSeek-V4-Flash is a specially optimized model

- Long-term context of text inference

- Single model residency services

- Stabilizing the text API

The differences between the two frameworks:

```Markdown
ds4 是更专用的 DeepSeek-V4-Flash 推理路线。
它不是通用 MLX 模型服务框架，也不是 GGUF 通用框架。
```

Concurrency notes:

```Markdown
根据之前分析，ds4 的 HTTP 层可以接收多个请求，
但推理层更接近单一 Metal worker 队列式处理，
不是 vLLM 那种 continuous batching 多请求合批 decode 服务。
```

Recommended location:

```Markdown
DeepSeek-V4-Flash 专用服务优先选 ds4。
通用 MLX 多模型服务优先选 oMLX。
GGUF 模型优先选 llama.cpp。
```

#### 7. Current model directory matching with framework

Current model examples of directories:

```Markdown
<MODEL_VOLUME>/modeldown/models
```

There are models:

```Markdown
DeepSeek-V4-Flash
DeepSeek-V4-Flash-FP4-FP8-native.gguf
DeepSeek-V4-Flash-Q4KExperts-F16HC-F16Compressor-F16Indexer-Q8Attn-Q8Shared-Q8Out-chat-v2.gguf
gemma-4-26b-a4b-it-bf16
gemma-4-26b-a4b-it-mxfp8
gemma-4-31B-it-assistant-bf16
gemma-4-31b-it-bf16
gemma-4-31b-it-mxfp8
MiniCPM-V-4.6-bf16
Qwen3.6-35B-A3B-bf16
```

Recommended matching:

|Model|Format/Type|Framework for recommendations|Notes|
| --- | --- | --- | --- |
| DeepSeek-V4-Flash |Specialized directory model| ds4 |DeepSeek-V4-Flash exclusive routes|
| DeepSeek-V4-Flash-*.gguf | GGUF | llama.cpp |GGUF prioritizes llama.cpp|
| gemma-4-26b-a4b-it-bf16 |MLX VLM / Gemma4 text skeleton| oMLX / mlx-vlm / vllm-metal |VLM routes prioritize image capability; Testing of text capabilities with vllm-metal|
| gemma-4-26b-a4b-it-mxfp8 | MLX VLM | oMLX / mlx-vlm |The current 64K image test is the main candidate|
| gemma-4-31B-it-assistant-bf16 |MLX model| oMLX / mlx-lm |For pure text, follow the text route.|
| gemma-4-31b-it-bf16 |MLX model / Gemma4 text skeleton| oMLX / mlx-lm / mlx-vlm / vllm-metal |VLM depending on the specific configuration; Testing of text capabilities with vllm-metal|
| gemma-4-31b-it-mxfp8 | MLX VLM | oMLX / mlx-vlm |Quality priority, speed significantly slower than 26B|
| MiniCPM-V-4.6-bf16 | MLX VLM | oMLX / mlx-vlm |Image / Multimodal routes|
| Qwen3.6-35B-A3B-bf16 | MLX Qwen3.6 / MoE / VLM wrapper | vllm-metal / oMLX / mlx-lm |Text services are available with vllm-metal for vLLM API control; The image capacity does not run vllm-metal, it needs to run mlx-vlm / oMLX|

#### 8. concurrency and batching capacity analysis

There are three concepts to distinguish:

```Markdown
1. HTTP 并发接入：
   server 可以同时接收多个请求。

2. 队列式并发：
   多个请求排队等待，同一时刻主要还是一个请求在推理。

3. continuous batching：
   服务端把多个请求的 prefill / decode 动态合批，提升整体吞吐。
```

A lot of frameworks can do the first point, but not necessarily the third.

##### 8.1 Concurrence judgments in current projects

|The Framework|HTTP concurrency access|Whether Batch concurrency services are suitable|Current judgments|
| --- | --- | --- | --- |
| oMLX |Support|It is appropriate.|Currently installed MLX main service framework, suitable for continuous batching/multi-request scheduling|
| vllm-mlx |Support|Suitable, measured after installation|vLLM-style MLX service framework, compatible with oMLX control load testing|
| vllm-metal |Support|Model concurrency validation for text is based on model measured|It is compatible with vLLM API verification, max-num-seqs / max-num-batched-tokens, paged KV, prefix cache; Image request is not currently available on the main line|
| mlx-vlm.server |Support|Not recommended as a high concurrency main service|26B/31B + images + 64K measured closer to low concurrency queue service|
| mlx-lm.server |Support|There is a certain capacity, but service governance is weaker than oMLX|More suitable for light text services|
| ds4 |Support|Unsuitable for batch concurrency services|Inference layer closer to the single metal worker queue|
| llama.cpp |Support|Theoretically supported slots / cont-batching, measured|GGUF's core framework, but the current project has not completed high concurrency verification|
|The original vLLM|Support|Suitable for large-scale high concurrency|NVIDIA GPU/multi-GPU production service reference system, not the current Mac native MLX mainline|

##### 8.2 Why oMLX is better suited for current mainline batch concurrency services

OMLX's advantages include not only the ability to launch the API service bar, but the fact that it is designed entirely around the service:

- `EnginePool` Manage multiple models

- `BatchedEngine` Processing of text LLM continuous batching

- `VLMEngine` Processing of visual language model services

- `Scheduler` Responsible for request scheduling

- `mlx-lm BatchGenerator` Responsible for batch production mechanisms

- `prefix cache` Reducing repetition of prefixes

- `paged SSD cache` Support for KV cache layer management

- `max-concurrent-requests` Limit the number of concurrency requests

- `hot cache` Control the size of the hot cache

Therefore, among the currently installed MLX model services, oMLX is best suited for pre-verification.

##### 8.3 Why test vllm-metal / vllm-mlx

`vllm-metal ` and `vllm-mlx` All of them work together as control frameworks for oMLX, but they counter different issues:

```Markdown
vllm-metal：验证原版 vLLM 插件路线在 Apple Silicon 上的文本服务能力。
vllm-mlx：验证独立 vLLM-style MLX 服务层的调度和缓存能力。
```

It is recommended to test them for the following reasons:

- They are all running in the Apple Silicon/MLX/Metal ecosystem.

- It's compatible with oMLX to do text model concurrency load testing.

- All emphasize the capabilities of KV cache, prefix cache or paged KV.

- You can compare the same model, the same concurrency, the same EvalScope parameter.

- It can help determine whether the current model is more suitable for the oMLX main service, the vLLM Metal plug-in route, or the vLLM-style MLX service layer.

Misconception to avoid:

```Markdown
vllm-metal 不是 CUDA vLLM 在 Mac 上的完整等价替代。
vllm-mlx 不是原版 vLLM 的完整 Mac 版。
两者都需要按具体模型、上下文长度和并发参数实测，不能只按名称判断吞吐。
```

Recommendations for the current project:

```Markdown
oMLX 做主线；
vllm-metal 做文本模型 vLLM 插件路线对照；
vllm-mlx 做另一条 vLLM-style MLX 服务层对照；
原版 vLLM 作为 NVIDIA 高吞吐服务参照系。
```

##### 8.4 Why does direct use of MLX-VLM not equal oMLX / vllm-mlx

This is how we started before:

```text
python -m mlx_vlm.server
```

This service can receive image requests and can provide an OpenAI-style interface, but it is not the same as full oMLX.

You are `gemma-4-26b-a4b-it-mxfp8 ` and `gemma-4-31b-it-mxfp8` The performance test of the 64K image above shows:

|Model|concurrency|Average latency|P99 latency| Avg TTFT | Avg TPOT |Success rates|
| --- | --- | --- | --- | --- | --- | --- |
| gemma-4-26b-a4b-it-mxfp8 | 1 | 20.993 s | 42.260 s | 19159.8 ms | 19.4 ms | 100.0% |
| gemma-4-26b-a4b-it-mxfp8 | 2 | 35.176 s | 52.610 s | 23180.3 ms | 153.1 ms | 91.7% |
| gemma-4-31b-it-mxfp8 | 1 | 80.549 s | 211.390 s | 76642.7 ms | 63.6 ms | 100.0% |
| gemma-4-31b-it-mxfp8 | 2 | 238.291 s | 436.570 s | 138114.4 ms | 904.7 ms | 100.0% |

The results are as follows:

```Markdown
在 26B/31B + 图片 + 64K 场景下，直接使用 mlx_vlm.server 并发 2 时并没有体现出高效合批收益。
尤其是 31B 模型，并发 2 后平均延迟从 80.549 s 上升到 238.291 s，TPOT 从 63.6 ms 上升到 904.7 ms。
```

The document should therefore be amended as follows:

```Markdown
MLX-VLM 能跑图片模型，也具备部分 batch 相关机制；
但当前项目实测下，它不应被定位为高并发批处理服务主框架。
真正要验证 batch/concurrent serving，应优先使用 oMLX 源码版服务；
文本模型可进一步用 vllm-metal / vllm-mlx 做对照压测；
图片模型仍应优先走 oMLX / mlx-vlm 路线，不应把 vllm-metal 当作 VLM 主服务。
```

##### 8.5 Concurrency positioning of ds4

DS4 is better suited for:

```Markdown
DeepSeek-V4-Flash 单模型长上下文文本服务。
```

It should not be understood as:

```Markdown
vLLM 类 continuous batching 服务。
```

The current judgement:

```Markdown
ds4 可以接收多个 HTTP 请求，但推理层更接近队列等待。
适合稳定服务，不适合追求多请求合批吞吐。
```

##### 8.6 The concurrency positioning of llama.cpp

It's called llama.cpp `llama-server` Support for:

```Markdown
--parallel
--cont-batching
slots
```

But in the Mac Studio large language model long context scenario, it is necessary to test separately:

- Model size

- How to quantize GGUF

- `--ctx-size`

- `--parallel`

- `--batch-size`

- `--ubatch-size`

- Metal memory occupied

- TTFT / TPOT / RPS

Current suggestions:

```Markdown
llama.cpp 是 GGUF 主力框架；
是否能作为高效批次并发服务，要以具体压测结果为准。
```

#### 9. device rating recommendations

##### 9.1 32GB level

It is suitable for:

- Small GGUF

- Small MLX text model

- `llama.cpp` Lightweight testing

- `mlx-lm` Small model script test

It is not suitable for:

- 26B / 31B VLM

- DeepSeek-V4-Flash

- 64K long context image testing

- Multi-modal residency services

Recommended framework:

```Markdown
llama.cpp
mlx-lm
```

##### 9.2 64GB level

It is suitable for:

- Small and medium sized GGUF

- Small and medium sized MLX text models

- Low concurrency image model testing

- Small-scale local API services

Control is needed:

- Length of context

- number of concurrency

- model quantization precision

- How to open image input

Recommended framework:

```Markdown
llama.cpp
mlx-lm
oMLX
轻量 mlx-vlm
```

##### 9.3 128GB level

It is suitable for:

- Larger text model

- Medium-sized VLM

- Local OpenAI API services

- single-machine RAG / embedding / rerank

- Medium low concurrency in-team web services

Recommended framework:

```Markdown
oMLX
llama.cpp
mlx-vlm
mlx-embeddings
```

##### 9.4 256GB level

It is suitable for:

- large language model

- Long term context

- Multi-model switching

- More stable local services

- DeepSeek-V4-Flash exclusive routes

Recommended framework:

```Markdown
oMLX
ds4
llama.cpp
mlx-vlm
```

##### 9.5 512 GB level

It is suitable for:

- The current Mac Studio M3 Ultra / 512GB

- 26B / 31B VLM 64K image test

- DeepSeek-V4-Flash

- large language model long context

- Multi-model directory services

- Prefix cache / KV cache / SSD cache verification

- concurrency scheduling and batching capability testing

Recommended framework:

```Markdown
oMLX 作为 MLX 主服务
vllm-metal 作为 vLLM Metal 文本对照验证框架
vllm-mlx 作为 vLLM-style 对照压测框架
ds4 作为 DeepSeek-V4-Flash 专用服务
llama.cpp 作为 GGUF 主服务
mlx-vlm 作为 VLM 单模型验证和对照测试
```

#### 10. Recommended architecture for the current Mac Studio M3 Ultra/512GB

It is recommended to break down the inference services on the current device into several main lines:

##### 10.1 MLX model Main service: oMLX

The purpose:

- MLX text model

- MLX VLM model

- embedding

- rerank

- Multi-model unified API

- Continuous batching testing

- Prefix cache / SSD cache test

Recommended ways to start:

```text
cd /srv/llm/Desktop/llm-workspace/omlx

source /srv/llm/Desktop/llm-workspace/omlx/omlx-build/bin/activate

omlx serve \
  --model-dir <MODEL_VOLUME>/modeldown/models \
  --host 0.0.0.0 \
  --port 18080 \
  --max-model-memory disabled \
  --max-process-memory disabled \
  --paged-ssd-cache-dir <MODEL_VOLUME>/omlx-cache \
  --paged-ssd-cache-max-size 100GB \
  --hot-cache-max-size 8GB \
  --max-concurrent-requests 8 \
  --log-level info
```

Testing:

```text
curl http://127.0.0.1:18080/v1/models | jq
```

##### 10.2 vLLM-style control service: vllm-mlx

The purpose:

- Continuous batching versus oMLX

- Prefix cache / paged KV cache as opposed to oMLX

- Verify the concurrency throughput of the MLX text model

- Verify that the VLM image model is comparable to the VLM image model `mlx_vlm.server` More suitable for servicing

It is recommended to install in an independent environment:

```text
cd /srv/llm/Desktop/llm-workspace

uv venv --python 3.12 vllm-mlx-env

source /srv/llm/Desktop/llm-workspace/vllm-mlx-env/bin/activate

uv pip install -U pip setuptools wheel

uv pip install vllm-mlx \
  --index-url https://pypi.tuna.tsinghua.edu.cn/simple
```

Example start:

```text
vllm-mlx serve <MODEL_VOLUME>/modeldown/models/Qwen3.6-35B-A3B-bf16 \
  --host 0.0.0.0 \
  --port 18084 \
  --continuous-batching
```

Location:

```Markdown
对照压测框架，不建议在没有实测前直接替代 oMLX。
```

##### 10.3 vLLM Metal text control service: vllm-metal

The purpose:

- Verify the route of the original vLLM API/scheduler plugins on Apple Silicon

- OpenAI API service controls for text models such as Qwen 3.6/Gemma4

- Text model paged KV, prefix cache, batched tokens, concurrency parameter verification

- TTFT, TPOT, RPS and P99 latency are compared to the same load testing tools used by oMLX/vllm-mlx.

Location:

```Markdown
文本模型 vLLM 插件路线对照框架。
它适合验证 vLLM 兼容服务和文本并发调度，
但当前不作为图片 VLM 主服务，也不替代 oMLX 的多模型管理能力。
```

##### 10.4 DeepSeek-V4-Flash dedicated service: DS4

The purpose:

- DeepSeek-V4-Flash

- Long-term context of text inference

- Single model Stability of services

Location:

```Markdown
专用文本服务，不作为通用批次并发服务。
```

##### 10.5 GGUF Main service: llama.cpp

The purpose:

- DeepSeek-V4-Flash GGUF release

- Other GGUF models

- Quantization model testing

- llama.cpp server load testing

Location:

```Markdown
GGUF 模型优先走 llama.cpp，不建议强行放到 oMLX。
```

##### 10.6 VLM control testing: MLX-VLM server

The purpose:

- Single model image testing

- Compared to the oMLX VLM service

- 64K context, model quality

Location:

```Markdown
适合测试和低并发服务；
不建议作为主要高并发批处理服务。
```

#### 11. Scene selection table

|The scene|Framework of preference|Selective framework|Why?|
| --- | --- | --- | --- |
|MLX text model API| oMLX | mlx-lm.server |oMLX service governance and cache more complete|
|MLX text model concurrency load testing| oMLX | vllm-metal / vllm-mlx |oMLX is the main line; vllm-metal verifies the route of the original vLLM plugin; VLLM-mlx is a vLLM-style service layer control.|
|MLX image model API| oMLX | mlx-vlm.server |oMLX is more suitable for servicing, while MLX-VLM is suitable for functionality testing; vllm-metal is not currently used as an image VLM route|
|Image model functionality verified| mlx-vlm.server | oMLX |It's straightforward, simple, and easy to adjust.|
|Image model batch concurrency testing| oMLX | mlx-vlm.server / vllm-mlx |Image tasks should not assume high concurrency gains; vllm-metal is not used for image encoder routing|
| DeepSeek-V4-Flash | ds4 | llama.cpp GGUF |DS4 is a dedicated route.|
| DeepSeek-V4-Flash GGUF | llama.cpp |It's not.|GGUF should go llama.cpp|
|General GGUF| llama.cpp | Ollama / LM Studio |Llama.cpp is more controllable|
| embedding | oMLX | mlx-embeddings |Long-term service with oMLX, single measurement with mlx-embeddings|
| rerank | oMLX | mlx-embeddings |Same as above|
|Unified Multi-Model Service| oMLX |Multi-service manual management|oMLX has EnginePool and admin interface|
|Mac MLX High concurrency batching services| oMLX | vllm-metal / vllm-mlx |The text model can be contrasted by all three parties under the same conditions; Image model does not run vllm-metal|
|Real high-production QPS service|The original vLLM| SGLang / TensorRT-LLM |It is better suited for NVIDIA GPU/multi-GPU/multi-node|

#### 12. Amendments to previous documents

This rewrite addresses the following issues:

##### 12.1 Modified oMLX positioning

The old judgement:

```Markdown
oMLX 主要是 Apple Silicon 上的文本推理服务。
```

It was amended as follows:

```Markdown
oMLX 是 MLX 生态的本地推理服务层，支持 LLM、VLM、embedding、rerank 等模型类型。
它不是底层推理内核，而是服务封装、调度、缓存和管理系统。
```

##### 12.2 Correction of the relationship between oMLX and MLX-VLM

The old judgments are easy to make.`oMLX-vlm` The directory is mistaken for oMLX.

It was amended as follows:

```Markdown
/srv/llm/Desktop/llm-workspace/oMLX-vlm/mlx-vlm 是 MLX-VLM 源码目录。
/srv/llm/Desktop/llm-workspace/omlx 才是真正的 oMLX 源码目录。
```

##### 12.3 Modified MLX-VLM concurrency capability description

The old judgement:

```Markdown
MLX-VLM 具备 continuous batching 机制。
```

It was amended as follows:

```Markdown
MLX-VLM 代码中有 batch 相关能力，但当前项目在 26B/31B + 图片 + 64K 场景下实测，
直接使用 mlx_vlm.server 并没有体现出高效 batch serving；
并发增加后更像队列等待，尤其 31B 延迟急剧上升。
```

##### 12.4 Modified ds4 concurrency positioning

The old judgment may have mixed HTTP concurrency with inference-level concurrency.

It was amended as follows:

```Markdown
ds4 可以接收多个 HTTP 请求，但推理层更接近单 Metal worker 队列式处理，
不是 vLLM 式 continuous batching 服务。
```

##### 12.5 Modified llama.cpp concurrency positioning

Old judgments may have underestimated llama.cpp's support for slots/continuous batching.

It was amended as follows:

```Markdown
llama.cpp 支持 slots、--parallel、--cont-batching；
但在当前项目中的大模型、长上下文、Mac Studio 场景下还需要单独压测验证。
```

##### 12.6 Added vllm-mlx correction to vLLM

Additional checks required:

```Markdown
vllm-mlx 是 Apple Silicon / MLX 生态中的 vLLM-style 服务框架。
它不是原版 vLLM，也不能等价替代 NVIDIA GPU 上的 vLLM。
```

The current project has been identified as follows:

```Markdown
oMLX 是当前已安装的 MLX 主服务框架；
vllm-mlx 是后续建议安装的对照压测框架；
原版 vLLM 是高吞吐生产服务参照系。
```

##### 12.7 Added vllm-metal positioning correction

Additional checks required:

```Markdown
vllm-metal 是原版 vLLM 的 Apple Silicon / Metal 插件路线，
不是 vllm-mlx 的同义词，也不是完整 CUDA vLLM 的 Mac 等价替代。
```

The current project has been identified as follows:

```Markdown
vllm-metal 适合做 Qwen3.6 / Gemma4 等文本模型的 vLLM API、paged KV、
prefix cache 和并发调度验证；
图片 VLM 输入当前不作为可用主线；
多模型管理和长期服务治理仍优先使用 oMLX。
```

#### 13. Final recommendation

For the current Mac Studio M3 Ultra/512GB, it is recommended to use the following final workflows:

|Task|Framework for recommendations|Notes|
| --- | --- | --- |
|MLX Multi-Model Unified Service| oMLX |Framework for mainstream services|
|MLX text model concurrency services| oMLX |Priority verification of continuous batching|
|MLX image model services| oMLX |Prioritization of servicing and MLX-VLM as a counterpoint|
|MLX image model single measurement| mlx-vlm.server |Easy and quick verification|
|VLLM Metal text contrast| vllm-metal |Verify the vLLM API, Scheduler, Paged KV, prefix cache and text concurrency|
|VLLM-style service layer control| vllm-mlx |Comparison with oMLX using the same model and parameter|
|High concurrency in mass production|The original vLLM + NVIDIA GPU|The Mac single-machine solution is not an equal replacement|
| DeepSeek-V4-Flash | ds4 |Special routes|
|GGUF model| llama.cpp |GGUF standard route|
| embedding / rerank | oMLX |Unified API management|
|Mac locally high concurrency batching verification| oMLX + vllm-metal + vllm-mlx |The text model is third-party control. Image model based on oMLX/MLX-VLM|

In one sentence, he concludes:

```Markdown
oMLX 不是替代 mlx-lm / mlx-vlm 的底层推理框架，
而是把 MLX 生态模型能力封装成可管理、可并发、可缓存、可长期运行的本地推理服务。

在当前项目中：
MLX 模型服务优先 oMLX；
文本模型 vLLM 插件路线对照使用 vllm-metal；
vLLM-style MLX 服务层对照测试使用 vllm-mlx；
图片模型单测可用 MLX-VLM；
GGUF 模型优先 llama.cpp；
DeepSeek-V4-Flash 专用模型优先 ds4；
真正大规模高并发生产服务仍然应参考原版 vLLM + NVIDIA GPU。
```
