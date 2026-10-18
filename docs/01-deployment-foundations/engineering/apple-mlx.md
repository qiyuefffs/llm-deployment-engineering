# Apple M3 Ultra：vllm-metal、MLX-VLM、APC与oMLX优化

[工程实例索引](README.md) · [知识体系总目录](../SUMMARY.md)

技术标签：`MLX / Metal / chat template / APC / batching`

## 环境与执行分支

| 分支 | 适配重点 | 已记录结果 |
| --- | --- | --- |
| vllm-metal | Python3.12.13、MLX0.31.2、vLLM0.21.0+cpu、插件0.2.0 | 文本与模板修复；视觉encoder失败 |
| MLX-VLM | 模型、processor、单图CLI、server协议 | 多视觉模型与完整调用代码 |
| APC | 块预算、磁盘缓存、tenant、冷暖缓存、KV量化互斥 | 自定义分支操作，无完整patch commit |
| oMLX | 父目录发现、模型加载、统一内存、连续批处理 | c1/c2/c4完整延迟与吞吐 |

## 完整部署适配过程

1. 记录macOS、芯片、物理/可用统一内存、Python/MLX与框架版本，各分支独立环境。
2. 检查原生扩展实际导入路径，避免当前源码目录遮蔽已安装`_rs`模块。
3. 文本先检查模板、reasoning/content与finish_reason，再进入图片。没有视觉encoder的服务应转支持路径，不能靠增大max_tokens修复HTTP500。
4. MLX-VLM使用其版本要求的图片schema；测试卡、base64和SSE客户端见[完整输入链路](../chapters/frameworks/vllm-service.md#七从图片文件到流式答案的完整链路)。
5. oMLX检查模型父目录与模型ID，显式加载后再测试。APC按原变量设置并检查stats，先冷、再暖、再变前缀，再测挤出和租户隔离。

## 实际并发优化

| 并发 | 请求数 | 总生成token/s | 单请求TPOT | 平均延迟 |
| --- | --- | --- | --- | --- |
| 1 | 20 | 29.38 | 34.2ms | 7.582s |
| 2 | 10 | 41.11 | 47.5ms | 10.257s |
| 4 | 10 | 55.15 | 69.8ms | 13.459s |

输入目标128、输出上限256；缓存和环境缺项照原记录标注。并发4总吞吐最高，但单请求更慢；工作点按交互或批处理目标选择。原首组c1/5请求也保留在全文，不从小样本推导稳定p99。

下方完整保留构建、文本/视觉排错、MLX-VLM/APC、oMLX操作、测试报告和框架定位文章。各框架的能力声明以固定版本功能验证为准，调研建议不自动记作实测。

## 完整技术记录的使用约定

以下直接保留相关FlowUs文章的技术正文、命令、表格、日志、失败和后续实验，不以摘要替代原过程。私人路径、节点、认证与附件地址脱敏；`<NODE_IP>`等占位符需要按当前环境填写。原建议或预测仍是建议或预测。上方执行顺序与技术修订用于解释历史记录中的冲突，历史GPU/NPU实验未在本轮重跑。

## R40 · vllm-metal 编译与推理记录

> 记录时间：2026-05-18
> 设备：Mac Studio / Apple M3 Ultra / 512GB 统一内存
> 工作目录：`/srv/llm/Desktop/llm-workspace/vllm-metal`
> 模型目录：`/Volumes/990pro/modeldown/models`

本文记录在 Mac Apple Silicon 上编译安装 `vllm-metal`、启动 Qwen3.6 文本推理服务、OpenAI API 调用，以及本次踩到的网络、模板、多模态等问题。

#### 1. 当前结论

本次 `vllm-metal` 已经编译安装成功：

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

验证结果：

```Markdown
vllm CLI 可用
vllm_metal 可 import
vllm_metal._rs 原生扩展可 import
Qwen3.6-35B-A3B-bf16 文本推理可用
Qwen3.6-35B-A3B-bf16 图片识别在 vllm-metal 中不可用
```

重要限制：

```Markdown
vllm-metal 当前主要用于 text-only LLM 推理。
Qwen3.6-35B-A3B-bf16 虽然是 VLM / ConditionalGeneration 包装，但 vllm-metal 的多模态 encoder 链路尚未接通。
图片识别请走 mlx-vlm / oMLX，不要走 vllm-metal。
```

#### 2. 源码拉取后安装流程

##### 2.1 进入源码目录

```text
cd /srv/llm/Desktop/llm-workspace/vllm-metal
```

##### 2.2 创建并激活虚拟环境

安装脚本会自动创建 `.venv-vllm-metal`，如果已经存在可直接激活：

```text
source /srv/llm/Desktop/llm-workspace/vllm-metal/.venv-vllm-metal/bin/activate
```

确认 Python：

```text
which python
python -V
```

期望：

```Markdown
/srv/llm/Desktop/llm-workspace/vllm-metal/.venv-vllm-metal/bin/python
Python 3.12.13
```

##### 2.3 按官方文档运行本地安装脚本

官方文档推荐：

```text
curl -fsSL https://raw.githubusercontent.com/vllm-project/vllm-metal/main/install.sh | bash
```

本次因为已经拉取了源码，直接在本地源码目录运行：

```text
cd /srv/llm/Desktop/llm-workspace/vllm-metal
./install.sh
```

本地运行脚本的效果：

```Markdown
创建 / 使用 .venv-vllm-metal
下载 vllm-0.21.0.tar.gz
安装 vllm 0.21.0+cpu
编译并安装 vllm-metal 0.2.0
生成 vllm_metal/_rs.cpython-312-darwin.so
```

安装脚本中的核心流程：

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

#### 3. 网络下载踩坑

##### 3.1 curl HTTP/2 framing layer 报错

最初安装时遇到：

```Markdown
curl: (16) Error in the HTTP2 framing layer
```

现象：

```Markdown
下载 vllm-0.21.0.tar.gz 时长时间 0 字节
约 90 秒后失败
```

原因判断：

```Markdown
GitHub release asset 下载链路不稳定。
系统 curl 默认走 HTTP/2，遇到代理/网络链路异常。
```

处理思路：

```text
curl --http1.1 --retry 8 --retry-delay 3 --retry-all-errors ...
```

##### 3.2 curl connection reset by peer

后续下载能开始，但中途断流：

```Markdown
36 32.8M   36 11.9M
curl: (56) Recv failure: Connection reset by peer
```

说明：

```Markdown
HTTP/1.1 后已经能下载，但链路仍然会被对端重置。
```

建议使用断点续传：

```text
curl --http1.1 \
  --retry 20 \
  --retry-delay 5 \
  --retry-all-errors \
  -fL \
  -C - \
  -O https://github.com/vllm-project/vllm/releases/download/v0.21.0/vllm-0.21.0.tar.gz
```

如果仍然太慢，开启代理：

```text
export HTTPS_PROXY=http://127.0.0.1:7890
export HTTP_PROXY=http://127.0.0.1:7890
export ALL_PROXY=socks5://127.0.0.1:7890

./install.sh
```

端口按本机代理实际端口调整。

#### 4. 安装成功验证

##### 4.1 查看包版本

```text
cd /srv/llm/Desktop/llm-workspace/vllm-metal
source .venv-vllm-metal/bin/activate

python -m pip list | grep -E '^(vllm|vllm-metal|mlx|mlx-lm|mlx-vlm|mlx-metal|torch|transformers|nanobind)\b'
```

本次结果：

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

##### 4.2 检查 vllm CLI

```text
source /srv/llm/Desktop/llm-workspace/vllm-metal/.venv-vllm-metal/bin/activate
which vllm
vllm --version
```

期望：

```Markdown
/srv/llm/Desktop/llm-workspace/vllm-metal/.venv-vllm-metal/bin/vllm
0.21.0+cpu
```

##### 4.3 检查原生扩展

不要在源码根目录检查 `_rs`，否则当前目录的 `./vllm_metal/` 会遮蔽 venv 里的已安装包。

正确做法：

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

本次验证：

```Markdown
vllm_metal: import OK
vllm_metal._rs: import OK
```

如果在源码根目录执行，可能看到：

```Markdown
ModuleNotFoundError: No module named 'vllm_metal._rs'
```

这不是编译失败，而是 Python import 优先级导致源码目录遮蔽了 site-packages。

#### 5. 本地模型目录与支持情况

当前模型目录：

```text
cd /Volumes/990pro/modeldown/models
ls
```

模型列表：

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

按 vllm-metal 当前能力判断：

| 模型 | vllm-metal 适配判断 | 说明 |
| --- | --- | --- |
| Qwen3.6-35B-A3B-bf16 | 文本可用，视觉不可用 | 架构属于 Qwen3.5/Qwen3.6 MoE / ConditionalGeneration 包装；文本可跑，图片 encoder 未接通 |
| gemma-4-26b-a4b-it-bf16 | 可测试，实验性 | Gemma4 在 vllm-metal 中为 experimental 支持 |
| gemma-4-31b-it-bf16 | 可测试，实验性 | 同上 |
| gemma-4-26b-a4b-it-mxfp8 | 需实测 | Gemma4 架构支持，但 mxfp8 量化形态未作为明确验证主线 |
| gemma-4-31b-it-mxfp8 | 需实测 | 同上 |
| MiniCPM-V-4.6-bf16 | 不建议 | VLM，多模态不是 vllm-metal 当前稳定主线 |
| DeepSeek-V4-Flash | 不建议 | deepseek_v4 不在当前支持矩阵 |
| *.gguf | 不支持 | vllm-metal 不跑 GGUF，应用 ds4 / llama.cpp |

#### 6. Qwen3.6 文本服务启动命令

重要：不要在源码根目录启动服务，避免 import 遮蔽；建议在 `/private/tmp` 启动。

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

vllm serve /Volumes/990pro/modeldown/models/Qwen3.6-35B-A3B-bf16 \
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
  --chat-template /Volumes/990pro/modeldown/models/Qwen3.6-35B-A3B-bf16/chat_template.jinja \
  --default-chat-template-kwargs '{"enable_thinking": false}' \
  --generation-config vllm \
  --override-generation-config '{"do_sample": false, "temperature": 0, "top_p": 1}' \
  --scheduler-reserve-full-isl \
  --disable-uvicorn-access-log \
  --disable-fastapi-docs \
  --uvicorn-log-level warning
```

参数说明：

| 参数 | 作用 |
| --- | --- |
| VLLM_METAL_USE_PAGED_ATTENTION=1 | 启用 paged KV cache，提高并发能力 |
| VLLM_METAL_MEMORY_FRACTION=0.90 | 给 paged KV 留较大内存预算 |
| VLLM_METAL_GDN_LAZY_DECODE=1 | Qwen3.6 hybrid/GDN decode 优化 |
| --max-num-seqs 16 | 单轮最多调度 16 条序列 |
| --max-num-batched-tokens 32768 | 单轮最多处理 32768 token |
| --chat-template .../chat_template.jinja | 显式加载模型目录中的 Qwen chat template |
| --default-chat-template-kwargs '{"enable_thinking": false}' | 关闭默认 thinking 模式 |
| --generation-config vllm | 不读取模型自带高温采样配置 |
| --override-generation-config ... | 默认关闭采样，提升稳定性 |

#### 7. 文本调用示例

##### 7.1 本机调用

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

##### 7.2 其他设备调用

Mac 设备 IP：

```Markdown
<NODE_IP>
```

其他设备调用：

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

#### 8. 推理踩坑与解决

##### 8.1 输出 `Here's a thinking process`

现象：

```text
"content": "Here's a thinking process:\n\n1. **Analyze User Input:** ..."
```

同时：

```Markdown
finish_reason: "length"
```

原因：

```Markdown
模型目录的 tokenizer_config.json 中 chat_template 为 None。
真实模板文件是 chat_template.jinja。
该模板默认会在 assistant 开头插入 <think>。
如果没有显式传 enable_thinking=false，模型容易进入思考输出模式。
```

模板关键片段：

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

解决：

服务启动时加：

```text
--chat-template /Volumes/990pro/modeldown/models/Qwen3.6-35B-A3B-bf16/chat_template.jinja \
--default-chat-template-kwargs '{"enable_thinking": false}'
```

请求时也可加：

```text
"chat_template_kwargs": {
  "enable_thinking": false
}
```

##### 8.2 服务端默认 generation_config 偏发散

模型目录中 `generation_config.json`：

```text
{
  "do_sample": true,
  "temperature": 1.0,
  "top_p": 0.95
}
```

这会导致输出更发散。

解决：

启动时使用：

```text
--generation-config vllm \
--override-generation-config '{"do_sample": false, "temperature": 0, "top_p": 1}'
```

请求中也建议：

```text
"temperature": 0
```

##### 8.3 图片识别请求触发 500

请求图片识别时，服务端返回：

```text
{
  "error": {
    "message": "EngineCore encountered an issue. See stack trace (above) for the root cause.",
    "type": "InternalServerError",
    "code": 500
  }
}
```

Mac 端日志关键报错：

```Markdown
NotImplementedError: Multimodal encoder execution is not wired on Metal yet.
Metal currently registers multimodal runtime state, but image encoding and embedding splice are not connected to the runner.
```

说明：

```Markdown
图片已经被 vLLM 前端解析并预处理。
日志中能看到 mm_features、pixel_values、image_grid_thw。
但 vllm-metal runner 没有接通 image encoder 和 embedding splice。
```

结论：

```Markdown
vllm-metal 当前不能用于该 Qwen3.6 模型的图片识别。
这不是编译错误。
这是框架当前能力边界。
```

处理：

```Markdown
Qwen3.6 文本推理继续用 vllm-metal。
Qwen3.6 图片识别请走 mlx-vlm / oMLX。
```

注意：图片请求触发 fatal error 后，日志会出现：

```Markdown
EngineCore encountered a fatal error
EngineDeadError
```

此时需要 `Ctrl+C` 停掉当前服务并重启。

##### 8.4 here-doc JSON 拼接错误

错误命令最后出现：

```Markdown
EOFstream": false
```

原因：

```Markdown
here-doc 结束符 EOF 必须单独一行。
EOF 后不能粘任何 JSON 字段。
```

正确格式：

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

推荐先用 `python3 -m json.tool` 检查请求文件：

```text
python3 -m json.tool /tmp/request.json >/dev/null && echo "JSON OK"
```

##### 8.5 Codex 沙盒中 `No Metal device available`

在 Codex / 沙盒环境中运行部分命令时可能看到：

```Markdown
RuntimeError: [metal::load_device] No Metal device available.
This typically occurs in headless, sandboxed, or virtualized macOS sessions where the GPU is not accessible.
```

说明：

```Markdown
这是沙盒环境拿不到 Metal GPU。
不是本机 Terminal 中的编译失败。
```

真实终端中以 `vllm serve` 启动后能正常文本推理，说明 Metal 链路可用。

#### 9. 图片识别替代路线：mlx-vlm

由于 vllm-metal 当前无法执行多模态 encoder，图片识别建议用 `mlx-vlm`。

如果图片在 Linux 设备：

```text
scp "/srv/llm/图片/1.jpg" goflash@<NODE_IP>:/tmp/1.jpg
```

Mac 上测试：

```text
cd /private/tmp
source /srv/llm/Desktop/llm-workspace/vllm-metal/.venv-vllm-metal/bin/activate

python -m mlx_vlm.generate \
  --model /Volumes/990pro/modeldown/models/Qwen3.6-35B-A3B-bf16 \
  --image /tmp/1.jpg \
  --prompt "请识别这张图片，描述图片中的主要内容、场景、物体和可能的文字。" \
  --max-tokens 512 \
  --temperature 0.0
```

#### 10. 后续建议

1. `vllm-metal` 继续用于 Qwen3.6 文本并发、prefix cache、吞吐测试。

2. 图片识别走 `mlx-vlm` 或 `oMLX`，不要在当前 vllm-metal 服务上发送图片请求。

3. Gemma4 bf16 可作为第二组 vllm-metal 文本模型测试对象。

4. DeepSeek-V4 GGUF 继续走 `ds4` / `llama.cpp` 路线。

5. 如果后续 vllm-metal 官方接通 multimodal encoder，再重新测试 Qwen3.6 VLM。

## R41 · mlx-vlm 多视觉模型推理与 API 调用指南

本文档记录当前 Mac Studio 上基于 `mlx-vlm` 源码环境进行多模态模型加载、命令行推理、API 服务启动、远程调用、OCR/识图请求的操作流程。

适用模型：

- `MiniCPM-V-4.6-bf16`

- `Qwen3.6-35B-A3B-bf16`

- `gemma-4-26b-a4b-it-bf16`

- `gemma-4-31b-it-bf16`

当前源码环境：

```text
/srv/llm/Desktop/llm-workspace/oMLX-vlm/mlx-vlm
```

虚拟环境：

```text
/srv/llm/Desktop/llm-workspace/oMLX-vlm/oMLX-vlm
```

#### 1. 环境准备

进入源码目录并激活虚拟环境：

```text
cd /srv/llm/Desktop/llm-workspace/oMLX-vlm/mlx-vlm
source ../oMLX-vlm/bin/activate
```

确认当前安装的 `mlx-vlm` 来自源码目录：

```text
uv pip list | grep mlx-vlm
python -c "import mlx_vlm; print(mlx_vlm.__file__)"
```

确认 MLX/Metal 可用：

```text
python -c "import mlx.core as mx; print(mx.default_device()); print(mx.device_info())"
```

如果 `python` 命令不可用，可以直接使用虚拟环境解释器：

```text
/srv/llm/Desktop/llm-workspace/oMLX-vlm/oMLX-vlm/bin/python
```

#### 2. 模型路径

当前模型默认位于：

```text
/Volumes/990pro/modeldown/models
```

四个模型路径：

```text
/Volumes/990pro/modeldown/models/MiniCPM-V-4.6-bf16
/Volumes/990pro/modeldown/models/Qwen3.6-35B-A3B-bf16
/Volumes/990pro/modeldown/models/gemma-4-26b-a4b-it-bf16
/Volumes/990pro/modeldown/models/gemma-4-31b-it-bf16
```

可用下面命令确认模型文件完整性：

```text
ls /Volumes/990pro/modeldown/models/MiniCPM-V-4.6-bf16
ls /Volumes/990pro/modeldown/models/Qwen3.6-35B-A3B-bf16
ls /Volumes/990pro/modeldown/models/gemma-4-26b-a4b-it-bf16
ls /Volumes/990pro/modeldown/models/gemma-4-31b-it-bf16
```

关键配置：

- `MiniCPM-V-4.6-bf16`: `model_type=minicpmv4_6`，适合轻量 OCR/识图。

- `Qwen3.6-35B-A3B-bf16`: `model_type=qwen3_5_moe`，适合复杂图文理解，但更重。

- `gemma-4-26b-a4b-it-bf16`: `model_type=gemma4`，适合通用多模态推理。

- `gemma-4-31b-it-bf16`: `model_type=gemma4`，适合通用多模态推理，比 26B 更重。

#### 3. 命令行直接推理

##### 3.1 MiniCPM-V-4.6-bf16

文本推理：

```text
python -m mlx_vlm.generate \
  --model /Volumes/990pro/modeldown/models/MiniCPM-V-4.6-bf16 \
  --prompt "你好，请做一个简短自我介绍。" \
  --max-tokens 512 \
  --temperature 0.0
```

图片识图：

```text
python -m mlx_vlm.generate \
  --model /Volumes/990pro/modeldown/models/MiniCPM-V-4.6-bf16 \
  --image /path/to/image.jpg \
  --prompt "请详细描述这张图片。" \
  --max-tokens 1024 \
  --temperature 0.0
```

OCR：

```text
python -m mlx_vlm.generate \
  --model /Volumes/990pro/modeldown/models/MiniCPM-V-4.6-bf16 \
  --image /path/to/image.jpg \
  --prompt "请对图片进行OCR识别，逐行输出所有可见文字，保留原始顺序和表格结构，不要编造。" \
  --max-tokens 4096 \
  --temperature 0.0
```

OCR 细节优先模式：

```text
python -m mlx_vlm.generate \
  --model /Volumes/990pro/modeldown/models/MiniCPM-V-4.6-bf16 \
  --image /path/to/image.jpg \
  --prompt "请对图片进行OCR识别，逐行输出所有可见文字，保留原始顺序和表格结构，不要编造。" \
  --max-tokens 4096 \
  --temperature 0.0 \
  --processor-kwargs '{"downsample_mode": "4x", "max_slice_nums": 36}'
```

##### 3.2 Qwen3.6-35B-A3B-bf16

文本推理：

```text
python -m mlx_vlm.generate \
  --model /Volumes/990pro/modeldown/models/Qwen3.6-35B-A3B-bf16 \
  --prompt "你好，请做一个简短自我介绍。" \
  --max-tokens 512 \
  --temperature 0.0
```

图片识图：

```text
python -m mlx_vlm.generate \
  --model /Volumes/990pro/modeldown/models/Qwen3.6-35B-A3B-bf16 \
  --image /path/to/image.jpg \
  --prompt "请详细描述这张图片。" \
  --max-tokens 1024 \
  --temperature 0.0
```

OCR：

```text
python -m mlx_vlm.generate \
  --model /Volumes/990pro/modeldown/models/Qwen3.6-35B-A3B-bf16 \
  --image /path/to/image.jpg \
  --prompt "请对图片进行OCR识别，逐行输出所有可见文字，保留原始顺序和表格结构，不要编造。" \
  --max-tokens 4096 \
  --temperature 0.0
```

高分辨率输入尝试：

```text
python -m mlx_vlm.generate \
  --model /Volumes/990pro/modeldown/models/Qwen3.6-35B-A3B-bf16 \
  --image /path/to/image.jpg \
  --prompt "请对图片进行OCR识别，逐行输出所有可见文字，保留原始顺序和表格结构，不要编造。" \
  --max-tokens 4096 \
  --temperature 0.0 \
  --processor-kwargs '{"max_pixels": 3211264}'
```

##### 3.3 gemma-4-26b-a4b-it-bf16

文本推理：

```text
python -m mlx_vlm.generate \
  --model /Volumes/990pro/modeldown/models/gemma-4-26b-a4b-it-bf16 \
  --prompt "你好，请做一个简短自我介绍。" \
  --max-tokens 512 \
  --temperature 0.0
```

##### 3.4 gemma-4-31b-it-bf16

文本推理：

```text
python -m mlx_vlm.generate \
  --model /Volumes/990pro/modeldown/models/gemma-4-31b-it-bf16 \
  --prompt "你好，请做一个简短自我介绍。" \
  --max-tokens 512 \
  --temperature 0.0
```

图片识图：

```text
python -m mlx_vlm.generate \
  --model /Volumes/990pro/modeldown/models/gemma-4-31b-it-bf16 \
  --image /path/to/image.jpg \
  --prompt "请详细描述这张图片。" \
  --max-tokens 1024 \
  --temperature 0.0
```

OCR：

```text
python -m mlx_vlm.generate \
  --model /Volumes/990pro/modeldown/models/gemma-4-31b-it-bf16 \
  --image /path/to/image.jpg \
  --prompt "请对图片进行OCR识别，逐行输出所有可见文字，保留原始顺序和表格结构，不要编造。" \
  --max-tokens 4096 \
  --temperature 0.0
```

图片识图：

```text
python -m mlx_vlm.generate \
  --model /Volumes/990pro/modeldown/models/gemma-4-26b-a4b-it-bf16 \
  --image /path/to/image.jpg \
  --prompt "请详细描述这张图片。" \
  --max-tokens 1024 \
  --temperature 0.0
```

OCR：

```text
python -m mlx_vlm.generate \
  --model /Volumes/990pro/modeldown/models/gemma-4-26b-a4b-it-bf16 \
  --image /path/to/image.jpg \
  --prompt "请对图片进行OCR识别，逐行输出所有可见文字，保留原始顺序和表格结构，不要编造。" \
  --max-tokens 4096 \
  --temperature 0.0
```

#### 4. API 服务启动

API 服务由 `mlx_vlm.server` 提供，接口兼容 OpenAI 风格：

```text
/v1/chat/completions
```

服务启动时通过 `--model` 预加载模型。`mlx_vlm.server` 没有 `/v1/models/{id}/load` 这种运行时加载接口。

##### 4.1 监听地址说明

仅本机调用：

```text
--host 127.0.0.1
```

局域网其他设备调用：

```text
--host 0.0.0.0
```

或绑定指定局域网 IP：

```text
--host <NODE_IP>
```

查看 Mac Studio 局域网 IP：

```text
ipconfig getifaddr en0
ipconfig getifaddr en1
```

##### 4.2 MiniCPM-V-4.6-bf16 API 服务

OCR/识图稳定版：

```text
python -m mlx_vlm.server \
  --host <NODE_IP> \
  --port 8080 \
  --model /Volumes/990pro/modeldown/models/MiniCPM-V-4.6-bf16 \
  --max-tokens 4096 \
  --max-kv-size 32768 \
  --prefill-step-size 2048 \
  --vision-cache-size 64 \
  --log-level INFO
```

长上下文/省内存版：

```text
python -m mlx_vlm.server \
  --host <NODE_IP> \
  --port 8080 \
  --model /Volumes/990pro/modeldown/models/MiniCPM-V-4.6-bf16 \
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

##### 4.3 Qwen3.6-35B-A3B-bf16 API 服务

建议先使用 8081，避免和 MiniCPM 服务冲突。

稳定版：

```text
python -m mlx_vlm.server \
  --host <NODE_IP> \
  --port 8081 \
  --model /Volumes/990pro/modeldown/models/Qwen3.6-35B-A3B-bf16 \
  --max-tokens 4096 \
  --max-kv-size 32768 \
  --prefill-step-size 2048 \
  --vision-cache-size 32 \
  --log-level INFO
```

省内存版：

```text
python -m mlx_vlm.server \
  --host <NODE_IP> \
  --port 8081 \
  --model /Volumes/990pro/modeldown/models/Qwen3.6-35B-A3B-bf16 \
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

##### 4.4 gemma-4-26b-a4b-it-bf16 API 服务

建议使用 8082，避免和其他服务冲突。

稳定版：

```text
python -m mlx_vlm.server \
  --host <NODE_IP> \
  --port 8082 \
  --model /Volumes/990pro/modeldown/models/gemma-4-26b-a4b-it-bf16 \
  --max-tokens 4096 \
  --max-kv-size 32768 \
  --prefill-step-size 2048 \
  --vision-cache-size 32 \
  --log-level INFO
```

##### 4.5 gemma-4-31b-it-bf16 API 服务

建议使用 8083，避免和其他服务冲突。

稳定版：

```text
python -m mlx_vlm.server \
  --host <NODE_IP> \
  --port 8083 \
  --model /Volumes/990pro/modeldown/models/gemma-4-31b-it-bf16 \
  --max-tokens 4096 \
  --max-kv-size 32768 \
  --prefill-step-size 2048 \
  --vision-cache-size 32 \
  --log-level INFO
```

省内存版：

```text
python -m mlx_vlm.server \
  --host <NODE_IP> \
  --port 8083 \
  --model /Volumes/990pro/modeldown/models/gemma-4-31b-it-bf16 \
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

省内存版：

```text
python -m mlx_vlm.server \
  --host <NODE_IP> \
  --port 8082 \
  --model /Volumes/990pro/modeldown/models/gemma-4-26b-a4b-it-bf16 \
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

#### 5. API 健康检查

以 MiniCPM 服务为例：

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

#### 6. API 文本调用

MiniCPM 示例：

```text
curl http://<NODE_IP>:8080/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "/Volumes/990pro/modeldown/models/MiniCPM-V-4.6-bf16",
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

Qwen 示例：

```text
curl http://<NODE_IP>:8081/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "/Volumes/990pro/modeldown/models/Qwen3.6-35B-A3B-bf16",
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

Gemma 示例：

```text
curl http://<NODE_IP>:8082/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "/Volumes/990pro/modeldown/models/gemma-4-26b-a4b-it-bf16",
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

Gemma 31B 示例：

```text
curl http://<NODE_IP>:8083/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "/Volumes/990pro/modeldown/models/gemma-4-31b-it-bf16",
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

#### 7. API 图片识图调用

从其他 Linux 设备调用时，不要把大图片 base64 直接放进命令行参数，否则可能出现：

```Markdown
bash: /usr/bin/curl: 参数列表过长
```

推荐写入临时 JSON 文件，再用 `curl -d @file` 调用。

以 MiniCPM 为例：

```text
IMG_B64=$(base64 -w 0 "/srv/llm/图片/1.jpg")

cat > /tmp/vlm_image_request.json <<EOF
{
  "model": "/Volumes/990pro/modeldown/models/MiniCPM-V-4.6-bf16",
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

调用 Qwen 时替换端口和模型路径：

```Markdown
端口: 8081
模型: /Volumes/990pro/modeldown/models/Qwen3.6-35B-A3B-bf16
```

调用 Gemma 时替换端口和模型路径：

```Markdown
端口: 8082
模型: /Volumes/990pro/modeldown/models/gemma-4-26b-a4b-it-bf16
```

调用 Gemma 31B 时替换端口和模型路径：

```Markdown
端口: 8083
模型: /Volumes/990pro/modeldown/models/gemma-4-31b-it-bf16
```

#### 8. API OCR 调用

普通 OCR：

```text
IMG_B64=$(base64 -w 0 "/srv/llm/图片/1.jpg")

cat > /tmp/vlm_ocr_request.json <<EOF
{
  "model": "/Volumes/990pro/modeldown/models/MiniCPM-V-4.6-bf16",
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

OCR JSON 输出：

```text
IMG_B64=$(base64 -w 0 "/srv/llm/图片/1.jpg")

cat > /tmp/vlm_ocr_json_request.json <<EOF
{
  "model": "/Volumes/990pro/modeldown/models/MiniCPM-V-4.6-bf16",
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

期望模型返回的内容结构：

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

#### 9. Python 调用示例

```text
import base64
import requests

server = "http://<NODE_IP>:8080/v1/chat/completions"
model = "/Volumes/990pro/modeldown/models/MiniCPM-V-4.6-bf16"
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

#### 10. OCR 图片预处理建议

OCR 图片不要过度压缩。文档、截图、表格、小字图片建议先转正、保持较高分辨率、轻微增强对比度。

Linux 调用设备上可用：

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

然后用 `/tmp/ocr_ready.jpg` 生成 base64：

```text
IMG_B64=$(base64 -w 0 "/tmp/ocr_ready.jpg")
```

#### 11. processor-kwargs 注意事项

`mlx_vlm.generate` 的 CLI 支持：

```text
--processor-kwargs '{"downsample_mode": "4x", "max_slice_nums": 36}'
```

这对 MiniCPM-V 4.6 的 OCR 小字、表格、文档类任务通常有帮助，但会更慢、更占内存。

当前 `mlx_vlm.server` 的 `/v1/chat/completions` API 只显式处理了 `resize_shape`，没有把请求中的 `processor_kwargs` 整体转发给底层 `generate/prepare_inputs`。因此直接在 API JSON 中加入：

```text
{
  "processor_kwargs": {
    "downsample_mode": "4x",
    "max_slice_nums": 36
  }
}
```

一般不会生效，除非修改 `mlx_vlm/server.py` 增加转发逻辑。

当前 API 可用的图像相关参数主要是：

```text
{
  "resize_shape": [2000, 2000]
}
```

示例：

```text
{
  "model": "/Volumes/990pro/modeldown/models/MiniCPM-V-4.6-bf16",
  "messages": [],
  "max_tokens": 4096,
  "temperature": 0.0,
  "resize_shape": [2000, 2000]
}
```

#### 12. 参数建议

OCR 稳定优先：

```text
--max-tokens 4096
--max-kv-size 32768
--prefill-step-size 2048
--vision-cache-size 64
```

长上下文/省内存：

```text
--max-kv-size 262144
--prefill-step-size 4096
--kv-bits 4
--kv-quant-scheme uniform
--kv-group-size 64
--quantized-kv-start 4096
```

注意：

- `max_tokens` 是最大输出 token 数，不是上下文长度。

- `max_kv_size` 才是服务端配置的 KV cache/token 上下文上限。

- 三个模型配置里的文本上下文上限约为 `262144` tokens。

- 35B/26B bf16 模型建议先从 `32768` 或 `65536` 上下文开始，不要一上来使用 256K。

- OCR 推荐 `temperature=0.0`，减少编造。

#### 13. 常见问题

##### 13.1 其他设备访问不到服务

检查服务是否绑定局域网 IP：

```text
--host <NODE_IP>
```

或：

```text
--host 0.0.0.0
```

检查健康接口：

```text
curl http://<NODE_IP>:8080/health
```

如果 Mac 防火墙拦截 Python，需要允许入站连接。

##### 13.2 curl 报参数列表过长

不要把 base64 直接放入命令行参数。应写入 JSON 文件：

```text
curl http://<NODE_IP>:8080/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d @/tmp/request.json
```

##### 13.3 模型路径怎么写

API 请求中的 `model` 字段建议和服务启动参数 `--model` 完全一致，例如：

```text
"/Volumes/990pro/modeldown/models/MiniCPM-V-4.6-bf16"
```

##### 13.4 API 的 `/v1/models` 不显示本地模型

`mlx_vlm.server` 的 `/v1/models` 主要扫描 Hugging Face cache，不一定列出通过本地路径 `--model` 预加载的模型。只要启动日志显示 `Model and processor loaded successfully`，并且 `/v1/chat/completions` 能返回内容，就说明服务可用。

##### 13.5 oMLX 和 mlx-vlm 的区别

`oMLX serve` 是另一个多模型服务入口。之前 `oMLX 0.3.9.dev1` 内置的 `mlx_vlm-0.4.5` 不支持 `MiniCPM-V-4.6`，会报：

```Markdown
Model type minicpmv4_6 not supported.
```

当前独立源码环境安装的是：

```Markdown
mlx-vlm 0.5.0
```

因此可以直接加载 `MiniCPM-V-4.6-bf16`。

## R42 · oMLX Mac 推理操作流程

当前环境与内存基线

记录时间：

```text
2026-05-13 17:52:35 CST
```

硬件环境：

```text
Apple M3 Ultra (8E + 24P + 80GPU)
统一内存：512GB
```

模型加载后监控数据：

```text
RAM Usage: 183.5 / 512.0GB
swap inactive
GPU Usage: 3% @ 683 MHz
E-CPU Usage: 17%~21% @ 1237 MHz
P-CPU Usage: 0% @ 0 MHz
CPU+GPU+ANE Power: 0.37W
```

说明：以上数据来自 `sudo asitop`，用于说明本文流程的验证环境和加载后内存占用情况。

#### 1. 模型目录

模型父目录：

```text
/Volumes/990pro/models/mlx-community
```

目标模型目录：

```text
/Volumes/990pro/models/mlx-community/DeepSeek-V4-Flash-4bit
```

说明：`omlx serve --model-dir` 填父目录，不是模型子目录。

#### 2. 启动 oMLX

```text
omlx serve \
  --model-dir /Volumes/990pro/models/mlx-community \
  --host 127.0.0.1 \
  --port 8000 \
  --max-model-memory disabled \
  --max-process-memory disabled \
  --paged-ssd-cache-dir /Volumes/990pro/omlx-cache \
  --paged-ssd-cache-max-size 100GB \
  --hot-cache-max-size 8GB \
  --log-level info
```

启动成功标志：

```text
Uvicorn running on http://127.0.0.1:8000
```

#### 3. API Key

当前实际 API Key：

```text
8888
```

来源：

```text
~/.omlx/settings.json
```

后续所有请求都要带：

```text
[认证配置已脱敏；按当前实例配置]
```

#### 4. 查看模型

```text
[认证配置已脱敏；按当前实例配置]
  http://127.0.0.1:8000/v1/models | jq
```

确认返回中包含：

```text
DeepSeek-V4-Flash-4bit
```

#### 5. 加载模型

```text
curl -X POST \
[认证配置已脱敏；按当前实例配置]
  http://127.0.0.1:8000/v1/models/DeepSeek-V4-Flash-4bit/load | jq
```

#### 6. 非流式推理

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

#### 7. 流式推理

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

#### 8. 常见问题

`Invalid API key`

原因：请求头里的 key 不对。当前应使用 `8888`。

`address already in use`

原因：端口被占用。处理方式：

```text
lsof -nP -iTCP:8000 -sTCP:LISTEN
```

或直接换端口，例如：

```text
--port 8001
```

`首次加载较慢`

原因：模型体积大，属于正常现象。

#### 9. 修改 API Key

如果要改成自己的 key，重启服务时显式指定：

```text
omlx serve \
  --model-dir /Volumes/990pro/models/mlx-community \
  --host 127.0.0.1 \
  --port 8000 \
[认证配置已脱敏；按当前实例配置]
  --max-model-memory disabled \
  --max-process-memory disabled \
  --paged-ssd-cache-dir /Volumes/990pro/omlx-cache \
  --paged-ssd-cache-max-size 100GB \
  --hot-cache-max-size 8GB \
  --log-level info
```

之后请求头改为：

```text
[认证配置已脱敏；按当前实例配置]
```

#### 10. MLX-VLM Gemma MXFP8：Prefix / Prompt 缓存推理

> 本节用于 `mlx_vlm.server`，不是 `omlx serve`。适用模型：

  - `/Volumes/990pro/modeldown/models/gemma-4-26b-a4b-it-mxfp8`

  - `/Volumes/990pro/modeldown/models/gemma-4-31b-it-mxfp8`

缓存使用 MLX-VLM 的 APC（Automatic Prefix Caching）。它会缓存重复的提示词前缀、长系统提示词、长文档上下文、多轮历史前缀。请求侧必须复用同一个 `X-APC-Tenant` 才方便隔离和命中同一组缓存。

注意：开启 APC 时不要同时加 `--kv-bits`，服务端在 KV cache quantization 开启时会跳过 APC。

##### 10.1 启动 26B-A4B MXFP8（推荐日常使用）

```text
cd /srv/llm/Desktop/llm-workspace/oMLX-vlm/mlx-vlm

APC_ENABLED=1 \
APC_NUM_BLOCKS=8192 \
APC_BLOCK_SIZE=16 \
APC_DISK_PATH=/Volumes/990pro/mlx-vlm-apc-cache/gemma-4-26b-a4b-it-mxfp8 \
APC_DISK_MAX_GB=80 \
APC_DISK_SHARD_MAX_BLOCKS=256 \
APC_LAYER_MAJOR_MEMORY_MIN_TOKENS=50000 \
APC_HASH=fast \
../oMLX-vlm/bin/python -m mlx_vlm.server \
  --host 0.0.0.0 \
  --port 18082 \
  --model /Volumes/990pro/modeldown/models/gemma-4-26b-a4b-it-mxfp8 \
  --log-level INFO \
  --max-tokens 2048 \
  --max-kv-size 65536 \
  --prefill-step-size 2048 \
  --vision-cache-size 32
```

健康检查：

```text
curl http://<NODE_IP>:18082/health
curl http://<NODE_IP>:18082/v1/cache/stats | jq
```

##### 10.2 启动 31B MXFP8（质量优先）

```text
cd /srv/llm/Desktop/llm-workspace/oMLX-vlm/mlx-vlm

APC_ENABLED=1 \
APC_NUM_BLOCKS=8192 \
APC_BLOCK_SIZE=16 \
APC_DISK_PATH=/Volumes/990pro/mlx-vlm-apc-cache/gemma-4-31b-it-mxfp8 \
APC_DISK_MAX_GB=100 \
APC_DISK_SHARD_MAX_BLOCKS=256 \
APC_LAYER_MAJOR_MEMORY_MIN_TOKENS=50000 \
APC_HASH=fast \
../oMLX-vlm/bin/python -m mlx_vlm.server \
  --host 0.0.0.0 \
  --port 18083 \
  --model /Volumes/990pro/modeldown/models/gemma-4-31b-it-mxfp8 \
  --log-level INFO \
  --max-tokens 2048 \
  --max-kv-size 65536 \
  --prefill-step-size 2048 \
  --vision-cache-size 32
```

健康检查：

```text
curl http://<NODE_IP>:18083/health
curl http://<NODE_IP>:18083/v1/cache/stats | jq
```

##### 10.3 远程图片请求：26B-A4B，带 Prefix 缓存

在调用设备执行。图片不走服务端本地路径，而是 base64 放入 JSON 文件再上传。

```text
IMG="/srv/llm/图片/1.jpg"
REQ="/tmp/gemma26_apc_image_request.json"
TENANT="lab"

IMG_B64=$(base64 -w 0 "$IMG")

cat > "$REQ" <<EOF
{
  "model": "/Volumes/990pro/modeldown/models/gemma-4-26b-a4b-it-mxfp8",
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

再次用相同图片、相同系统提示词、相同 `X-APC-Tenant` 请求时，应更容易命中 prefix/prompt 缓存。

##### 10.4 远程图片请求：31B，带 Prefix 缓存

```text
IMG="/srv/llm/图片/1.jpg"
REQ="/tmp/gemma31_apc_image_request.json"
TENANT="lab"

IMG_B64=$(base64 -w 0 "$IMG")

cat > "$REQ" <<EOF
{
  "model": "/Volumes/990pro/modeldown/models/gemma-4-31b-it-mxfp8",
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

##### 10.5 文本 Prefix 缓存命中测试

第一次请求用于写入缓存：

```text
TENANT="lab"

curl -N http://<NODE_IP>:18082/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "X-APC-Tenant: $TENANT" \
  -d '{
    "model": "/Volumes/990pro/modeldown/models/gemma-4-26b-a4b-it-mxfp8",
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

第二次请求复用相同前缀，只改最后的问题：

```text
TENANT="lab"

curl -N http://<NODE_IP>:18082/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "X-APC-Tenant: $TENANT" \
  -d '{
    "model": "/Volumes/990pro/modeldown/models/gemma-4-26b-a4b-it-mxfp8",
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

查看缓存统计：

```text
curl http://<NODE_IP>:18082/v1/cache/stats | jq
```

清空缓存：

```text
curl -X POST http://<NODE_IP>:18082/v1/cache/reset | jq
```

## R43 · oMLX 推理框架性能测试报告与压测流程

#### 1. 测试对象

- 推理框架：`oMLX`

- 模型：`DeepSeek-V4-Flash-4bit`

- 接口：`http://127.0.0.1:8000/v1/chat/completions`

- 认证：`Bearer <API_TOKEN>

- 压测工具：`evalscope 1.7.0`

- 数据集：`random`

- 输入长度：`128 tokens`

- 输出上限：`256 tokens`

- 结果目录：

```text
/srv/llm/Desktop/llm-workspace/perf-bench/outputs/20260513_180339/omlx-dsv4-sweep
```

#### 2. 总体结果

- 总生成 tokens：`9,693`

- 平均输出速率：`34.84 tok/s`

- 总测试时长：`278.22 s`

- 成功率：`100%`

#### 3. 核心性能数据

| 并发 | 请求数 | Avg Latency | P99 Latency | TTFT | TPOT | Gen. tok/s | Decode tok/s |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 5 | 7.544 s | 9.480 s | 17.1 ms | 34.8 ms | 28.73 | 28.74 |
| 1 | 20 | 7.582 s | 8.580 s | 25.0 ms | 34.2 ms | 29.38 | 29.21 |
| 2 | 10 | 10.257 s | 12.800 s | 3.2 ms | 47.5 ms | 41.11 | 21.04 |
| 4 | 10 | 13.459 s | 19.340 s | 3.7 ms | 69.8 ms | 55.15 | 14.32 |

#### 4. 结论

- 单流基线稳定：`并发 1` 下生成速度约 `29 tok/s`，TPOT 约 `34 ms`。

- 提高并发后，总吞吐上升：

  - `并发 2`：`41.11 tok/s`

  - `并发 4`：`55.15 tok/s`

- 提高并发后，单请求延迟明显变差：

  - `并发 1`：`7.58 s`

  - `并发 2`：`10.26 s`

  - `并发 4`：`13.46 s`

- 如果目标是交互体验，优先看 `并发 1`。

- 如果目标是总体吞吐，当前测试里 `并发 4` 吞吐最高。

#### 5. 压测操作流程

##### 5.1 激活环境

```text
cd /srv/llm/Desktop/llm-workspace
source /srv/llm/Desktop/llm-workspace/model-eval/bin/activate
evalscope --version
```

##### 5.2 确认 oMLX 服务可用

```text
[认证配置已脱敏；按当前实例配置]
  http://127.0.0.1:8000/v1/models | jq
```

确认返回中包含：

```text
DeepSeek-V4-Flash-4bit
```

##### 5.3 执行正式压测

```text
cd /srv/llm/Desktop/llm-workspace/perf-bench

evalscope perf \
  --url http://127.0.0.1:8000/v1/chat/completions \
  --model DeepSeek-V4-Flash-4bit \
  --api openai \
[认证配置已脱敏；按当前实例配置]
  --dataset random \
  --tokenizer-path /Volumes/990pro/models/mlx-community/DeepSeek-V4-Flash-4bit \
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

##### 5.4 查看结果

```text
ls -la /srv/llm/Desktop/llm-workspace/perf-bench/outputs/20260513_180339/omlx-dsv4-sweep
```

重点文件：

- `performance_summary.txt`

- `perf_report.html`

- `parallel_*/benchmark_summary.json`

- `parallel_*/benchmark_data.db`

#### 6. 建议

- 交互式使用：采用 `并发 1` 作为主要参考。

- 批量吞吐测试：继续向上试 `并发 6`、`并发 8`。

- 压测时同步观察资源：

```text
sudo asitop
```

## R44 · Mac 设备推理框架分类总结

> 本文档用于整理当前 `llm-workspace` 中已使用或已准备使用的 Mac 本地推理框架，并说明它们与 Apple MLX、GGUF、DeepSeek-V4-Flash、图片 VLM、并发批处理服务、`vllm-mlx`、`vllm-metal` 以及原版 `vLLM` 之间的关系。

当前核心结论：**oMLX 和 vllm-mlx 都不是新的底层推理内核，它们都是基于 Apple MLX 生态构建的服务层。`vllm-metal` 则是原版 vLLM 的 Apple Silicon / Metal 硬件插件路线，优势是更贴近 vLLM 的 CLI、OpenAI API、scheduler、paged KV 与 prefix cache 语义；局限是当前仍以 text-only 为主，多模态图片 encoder 尚未接通，模型覆盖和稳定性不能等同于 CUDA vLLM。原版 vLLM 仍主要面向 NVIDIA/CUDA 等 GPU 服务环境，不能直接与 Mac 上的 oMLX / vllm-mlx / vllm-metal 画等号。**

#### 1. 总体结论

当前项目中的推理框架可以分成七类：

| 类别 | 框架 | 核心定位 | 推荐用途 |
| --- | --- | --- | --- |
| MLX 服务编排层 | oMLX | 基于 MLX 生态的本地推理服务器 | 多模型服务、并发请求、缓存、长期运行 API |
| MLX vLLM-style 服务层 | vllm-mlx | 面向 Apple Silicon 的 vLLM 风格服务框架 | 对照测试 continuous batching / paged KV / prefix cache |
| vLLM Metal 插件层 | vllm-metal | 原版 vLLM 的 Apple Silicon / MLX / Metal 插件 | 文本模型 vLLM API、Qwen/Gemma 文本并发、vLLM 生态兼容性验证 |
| MLX 单类模型推理层 | mlx-lm、mlx-vlm、mlx-embeddings、dflash-mlx | 具体模型加载与推理能力 | 文本、图片、embedding、加速生成 |
| GGUF 推理层 | llama.cpp | GGUF 模型通用推理引擎 | GGUF 模型、量化测试、通用本地服务 |
| 专用推理层 | ds4 | DeepSeek-V4-Flash 专用推理服务 | DeepSeek-V4-Flash 文本长上下文服务 |
| 生产级参照系 | vLLM | CUDA/HIP 等 GPU 生态的高吞吐推理服务器 | NVIDIA GPU / 多卡 / 高 QPS 生产服务 |

最重要的选型原则：

| 任务 | 推荐框架 |
| --- | --- |
| MLX 格式文本模型长期 API 服务 | oMLX |
| MLX 格式文本模型 vLLM API / 并发验证 | vllm-metal 或 vllm-mlx |
| MLX 格式图片 / VLM 单模型测试 | mlx-vlm.server 或 oMLX |
| 需要连续批处理、并发调度、缓存和多模型管理 | oMLX，并用 vllm-mlx 做对照压测 |
| Qwen3.6 / Gemma4 文本模型 vLLM-style 服务 | vllm-metal |
| GGUF 模型 | llama.cpp |
| DeepSeek-V4-Flash 专用模型 | ds4 |
| embedding / rerank 服务 | oMLX + mlx-embeddings |
| 真正大规模高并发生产服务 | vLLM + NVIDIA GPU |

#### 2. 当前项目中的框架目录

当前工作目录：

```text
/srv/llm/Desktop/llm-workspace
```

当前已出现的主要框架和目录：

| 名称 | 本地路径 | 实际性质 |
| --- | --- | --- |
| omlx | /srv/llm/Desktop/llm-workspace/omlx | 真正的 oMLX 源码目录 |
| vllm-mlx | 尚未安装，建议独立目录 /srv/llm/Desktop/llm-workspace/vllm-mlx 或独立虚拟环境 | Apple Silicon 上的 vLLM-style MLX 服务框架 |
| vllm-metal | /srv/llm/Desktop/llm-workspace/vllm-metal | vLLM Apple Silicon / Metal 插件源码目录 |
| oMLX-vlm/mlx-vlm | /srv/llm/Desktop/llm-workspace/oMLX-vlm/mlx-vlm | MLX-VLM 源码目录，不是 oMLX |
| oMLX-vlm/oMLX-vlm | /srv/llm/Desktop/llm-workspace/oMLX-vlm/oMLX-vlm | MLX-VLM 使用的 Python 虚拟环境 |
| llama.cpp | /srv/llm/Desktop/llm-workspace/llama.cpp | llama.cpp 源码和构建目录 |
| llamacpp-test | /srv/llm/Desktop/llm-workspace/llamacpp-test | llama.cpp 测试相关目录 |
| ds4 | /srv/llm/Desktop/llm-workspace/ds4 | DeepSeek-V4-Flash 专用推理框架 |
| mlx-vlm-perf-bench | /srv/llm/Desktop/llm-workspace/mlx-vlm-perf-bench | MLX-VLM / OpenAI API 性能评估目录 |
| model-eval | /srv/llm/Desktop/llm-workspace/model-eval | 模型评估虚拟环境或评估工具目录 |
| perf-bench | /srv/llm/Desktop/llm-workspace/perf-bench | 性能测试相关目录 |

需要特别纠正的一点：

```Markdown
oMLX-vlm 这个目录名容易误导。
之前使用 python -m mlx_vlm.server 启动的是 MLX-VLM server，不是 oMLX server。
真正的 oMLX 源码目录是 /srv/llm/Desktop/llm-workspace/omlx。
vllm-mlx 目前还不是当前项目已安装的主服务框架，建议后续作为 oMLX 的对照压测框架单独安装。
vllm-metal 当前主要用于文本模型 OpenAI API / vLLM 兼容服务验证，不作为 VLM 图片服务主线。
```

#### 3. oMLX 与 MLX 生态的关系

你当前源码环境中安装的关键包如下：

```Markdown
mlx              0.31.2
mlx-lm           0.31.3
mlx-vlm          0.5.0
mlx-embeddings   0.1.0
dflash-mlx       0.1.5.1
omlx             0.3.9.dev2
```

它们不是同一层级的东西。

准确层级如下：

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

所以，oMLX 与这些库的关系可以这样理解：

```Markdown
oMLX
  ├── 调用 mlx-lm 跑文本 LLM
  ├── 调用 mlx-vlm 跑视觉语言模型
  ├── 调用 mlx-embeddings 跑 embedding / rerank
  ├── 可调用 dflash-mlx 做部分加速路径
  └── 底层统一依赖 mlx / mlx-metal 在 Apple Silicon 上执行计算
```

#### 4. oMLX 和 Ollama / llama.cpp 的类比

这个类比基本成立：

```Markdown
Ollama
  └── llama.cpp / GGML / GGUF
        └── CPU / Metal / CUDA 等底层推理
```

对应到 MLX 生态：

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

因此可以这样判断：

```Markdown
oMLX 不是新的底层推理框架。
oMLX 更像是 MLX 生态里的本地推理服务器和模型管理系统。
```

但它也不是“只套了一层 HTTP 接口”。oMLX 额外提供了很多服务能力：

| 能力 | oMLX 是否提供 |
| --- | --- |
| OpenAI API 兼容接口 | 支持 |
| Anthropic API 兼容接口 | 支持 |
| 多模型目录自动发现 | 支持 |
| 多模型加载 / 卸载 | 支持 |
| LRU 模型淘汰 | 支持 |
| 模型 TTL | 支持 |
| 模型别名 | 支持 |
| Admin Web UI | 支持 |
| continuous batching | 支持，主要通过 mlx-lm BatchGenerator |
| KV cache 管理 | 支持 |
| prefix / prompt cache | 支持 |
| SSD 分层 KV cache | 支持 |
| hot cache | 支持 |
| VLM 图片输入服务化 | 支持 |
| embedding / rerank 服务 | 支持 |
| MCP 工具调用 | 支持 |

更准确的一句话：

```Markdown
oMLX = MLX 模型推理库 + 服务封装 + 并发调度 + 缓存系统 + 多模型管理 + API/UI。
```

#### 5. oMLX、vllm-mlx、vllm-metal 与 vLLM 的关系

这几个名字很容易混淆，需要单独区分。

##### 5.1 三者一句话定义

| 框架 | 一句话定义 |
| --- | --- |
| oMLX | 面向 Mac / Apple Silicon 的 MLX 本地推理服务器和模型管理平台 |
| vllm-mlx | 面向 Apple Silicon 的 vLLM-style MLX 推理服务框架 |
| vllm-metal | 原版 vLLM 的 Apple Silicon / Metal 硬件插件，底层通过 MLX / Metal 执行 |
| vLLM | 面向 CUDA/HIP 等 GPU 生态的高吞吐 LLM serving 框架 |

##### 5.2 层级关系

`oMLX` 和 `vllm-mlx` 都位于 MLX 服务层：

```Markdown
oMLX / vllm-mlx
  ├── mlx-lm
  ├── mlx-vlm
  ├── mlx-embeddings
  └── mlx / mlx-metal
```

`vllm-metal` 的位置不同。它不是另一个 `mlx-lm.server` 包装层，而是把原版 `vLLM` 的平台插件机制接到 Apple Silicon / MLX / Metal 上：

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

原版 `vLLM` 则是另一条技术路线：

```Markdown
vLLM
  ├── CUDA / HIP / XPU / CPU 等后端
  ├── PagedAttention / KV cache 管理
  ├── continuous batching
  ├── tensor parallel / pipeline parallel
  └── OpenAI-compatible serving
```

因此不能把 `vllm-mlx` 理解成：

```Markdown
原版 vLLM 在 Mac 上的完整等价实现。
```

更准确的理解是：

```Markdown
vllm-mlx 是在 Apple Silicon / MLX / Metal 生态中实现 vLLM-style 服务思想。
vllm-metal 是原版 vLLM 的 Apple Silicon 插件路线，但当前能力仍受 Metal/MLX 后端实现进度限制。
```

##### 5.3 功能对比

| 对比项 | oMLX | vllm-mlx | vllm-metal | 原版 vLLM |
| --- | --- | --- | --- | --- |
| 主要硬件 | Apple Silicon Mac | Apple Silicon Mac | Apple Silicon Mac | NVIDIA GPU / AMD GPU / 其他后端 |
| 主要底层 | MLX / Metal | MLX / Metal | vLLM core + MLX / Metal plugin | CUDA / HIP / XPU / CPU 等 |
| 模型运行库 | mlx-lm、mlx-vlm、mlx-embeddings、dflash-mlx | mlx-lm、mlx-vlm、mlx-embeddings | mlx-lm / mlx-vlm 加 vLLM v1 engine | vLLM 自身模型执行栈和各硬件后端 |
| 定位 | Mac 本地推理服务器 + 管理平台 | vLLM-style Mac 推理服务 | vLLM 在 Apple Silicon 上的 Metal 插件实现 | 高吞吐生产级推理服务器 |
| 当前定位 | 主力服务框架 | 待安装对照框架 | 文本 vLLM 插件路线对照框架 | NVIDIA 生产服务参照系 |
| OpenAI API | 支持 | 支持 | 支持，走 vllm serve | 支持 |
| Anthropic API | 支持 | 支持 | 不作为主定位 | 视版本和部署方式 |
| continuous batching | 支持，主要依赖 mlx-lm BatchGenerator 和自身调度 | 支持，定位上重点强调 | 支持 vLLM scheduler / batched tokens / max seqs，需按模型实测 | 核心能力 |
| Paged KV / KV cache | 支持 KV cache、prefix cache、SSD 分层缓存 | 支持 paged KV、prefix cache、SSD tiering | 支持 Metal paged attention / paged KV，Qwen3.6 文本可用 | 核心能力，PagedAttention 是标志能力 |
| Prefix cache | 支持 | 支持 | 支持，但 hybrid/GDN 模型需显式开启和实测 | 支持 |
| SSD cache | 支持 | 支持 | 当前不是主线能力 | 不是主要生产依赖，更多依赖 GPU 显存 |
| 多模型管理 | 强，包含 EnginePool、LRU、TTL、Admin UI | 有服务层能力，具体成熟度需压测 | 单 vllm serve 进程更适合单模型服务 | 支持多模型部署，但常见生产部署会按模型/实例拆分 |
| 管理界面 | Admin Dashboard / macOS app | README 提到 metrics / benchmark 等能力，具体以版本为准 | 无专门 Mac 管理界面 | 主要是服务 API 和 metrics |
| VLM / 图片输入 | 支持，依赖 mlx-vlm | 理论依赖 mlx-vlm，需实测 | 当前不可用：multimodal encoder execution 未接通 Metal runner | 支持部分多模态模型 |
| embedding / rerank | 支持 | 支持 | 不是当前主定位 | 支持 embedding，rerank 视模型/服务实现 |
| 多 GPU / 分布式 | 不是主定位 | 不是主定位 | 不是主定位，Apple Silicon 单机 | 强项 |
| 生产成熟度 | Mac 本地服务方向较完整，仍需按模型实测 | Alpha / vLLM-style，适合对照验证 | Alpha / 插件路线，文本可测，多模态未完成 | 最成熟，尤其 NVIDIA 生态 |
| 是否可替代 vLLM | 不可等价替代 | 不可等价替代 | 更接近 vLLM API/engine，但不能等价替代 CUDA vLLM | 本体 |

##### 5.4 适用场景对比

| 场景 | 推荐框架 | 原因 |
| --- | --- | --- |
| Mac 单机 MLX 模型统一服务 | oMLX | 当前已安装，模型管理、Admin UI、缓存和服务治理更完整 |
| Mac 上验证 vLLM-style 并发能力 | vllm-metal / vllm-mlx | vllm-metal 走原版 vLLM 插件路线；vllm-mlx 是另一条 MLX 服务层对照 |
| Mac 文本模型 continuous batching 压测 | oMLX + vllm-metal + vllm-mlx 对比 | 用同一模型、同一并发、同一数据得到真实结果 |
| Mac VLM 图片服务 | oMLX 优先，mlx-vlm.server 对照 | vllm-metal 当前图片 encoder 未接通，不应用于 VLM 图片请求 |
| 小团队内网本地推理 | oMLX | 多模型管理和 API 服务更方便 |
| 多 agent / 重复系统提示词 / prefix 复用 | oMLX、vllm-metal 或 vllm-mlx | 都有 prefix cache / KV cache 相关能力，但需要按模型实测命中率 |
| GGUF 模型服务 | llama.cpp | oMLX / vllm-mlx / vllm-metal 主要面向 MLX/HF 模型，不是 GGUF 主路线 |
| 大规模高 QPS 商业 API | 原版 vLLM + NVIDIA GPU | Mac 单机不适合作为这种场景的主力 |
| 多卡 / 多机 / tensor parallel | 原版 vLLM | Apple Silicon 单机 MLX 服务不具备同等生产能力 |

##### 5.5 对当前项目的推荐判断

当前项目已经完成了 `oMLX` 源码安装，所以短期建议：

```Markdown
先用 oMLX 做主线验证；
vllm-metal 用于 Qwen3.6 / Gemma4 等文本模型的 vLLM API 和并发能力验证；
后续再安装 vllm-mlx，作为另一条 MLX 服务层对照压测。
```

推荐测试顺序：

```Markdown
1. oMLX 启动 /v1/models，确认模型发现和加载正常。
2. 用纯文本模型测试并发 1 / 2 / 4 / 8 / 16。
3. 用 VLM 图片模型测试并发 1 / 2 / 4。
4. 用 vllm-metal 对 Qwen3.6 / Gemma4 等文本模型做 vLLM API、max-num-seqs / max-num-batched-tokens / prefix cache 验证。
5. 安装 vllm-mlx，用同样模型和 EvalScope 参数重复测试。
6. 对比 RPS、TTFT、TPOT、P99 latency、success rate、内存占用。
```

文档结论应修正为：

```Markdown
在 Mac / MLX 生态中，oMLX 和 vllm-mlx 都是可选的并发服务框架。
oMLX 当前更适合作为主力服务框架；
vllm-metal 当前已经可作为 vLLM 插件路线的文本对照框架；
vllm-mlx 更适合作为另一个 vLLM-style MLX 服务层对照验证框架；
原版 vLLM 仍然是 NVIDIA GPU 高吞吐生产服务的参照系，不能被 Mac 单机方案完全替代。
```

#### 6. 各框架定位

##### 6.1 oMLX

命令入口：

```text
omlx serve
```

本地源码目录：

```text
/srv/llm/Desktop/llm-workspace/omlx
```

当前源码环境：

```text
/srv/llm/Desktop/llm-workspace/omlx/omlx-build
```

适合场景：

- MLX 格式文本模型服务

- 多模型 API server

- 长期运行的本地推理服务

- OpenAI / Anthropic API 兼容服务

- 多用户或多客户端并发访问

- prefix cache / KV cache / SSD cache 场景

- embedding / rerank 统一服务

- 需要管理界面的本地模型平台

不适合或需要注意：

- 不适合直接运行 GGUF 模型

- 不等同于 llama.cpp

- 能否支持某个模型架构，取决于底层 `mlx-lm` / `mlx-vlm` / `mlx-embeddings`

- VLM 大模型在 64K 图片场景下仍然可能受 prefill 和 vision encoder 影响，不能简单等同于 vLLM 级别吞吐

推荐用途：

```Markdown
Mac Studio / Apple Silicon 上的主力 MLX 模型服务框架。
```

##### 6.2 vllm-mlx

项目地址：

```Markdown
https://github.com/waybarrios/vllm-mlx
```

定位：

```Markdown
Apple Silicon 上的 vLLM-style 推理服务框架。
```

它的核心目标不是替代 MLX，而是把 MLX 生态的模型运行库封装成更接近 vLLM 的服务形态：

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

适合场景：

- Mac 上验证 vLLM-style continuous batching

- 与 oMLX 做并发吞吐对照

- MLX 文本模型 API 服务

- MLX VLM 服务实验

- prefix cache / paged KV cache / SSD cache 相关测试

- OpenAI / Anthropic API 兼容服务验证

不适合或需要注意：

- 不是原版 vLLM

- 不能直接等价替代 NVIDIA GPU 上的 vLLM

- 底层仍然依赖 MLX / Metal / Apple Silicon 单机能力

- 具体模型支持取决于 `mlx-lm` / `mlx-vlm`

- 与 oMLX 功能重叠较多，必须通过实测决定哪个更适合当前模型

建议安装到独立环境，不要污染现有 oMLX：

```text
cd /srv/llm/Desktop/llm-workspace

uv venv --python 3.12 vllm-mlx-env

source /srv/llm/Desktop/llm-workspace/vllm-mlx-env/bin/activate

uv pip install -U pip setuptools wheel

uv pip install vllm-mlx \
  --index-url https://pypi.tuna.tsinghua.edu.cn/simple
```

示例启动：

```text
vllm-mlx serve /Volumes/990pro/modeldown/models/Qwen3.6-35B-A3B-bf16 \
  --host 0.0.0.0 \
  --port 18084 \
  --continuous-batching
```

推荐用途：

```Markdown
作为 oMLX 的对照框架，用同一模型和同一 EvalScope 参数测试并发能力。
```

##### 6.3 vllm-metal

定位：

```Markdown
vllm-metal 是原版 vLLM 的 Apple Silicon / Metal 硬件插件路线。
它复用 vLLM 的 CLI、OpenAI API、scheduler、v1 engine 等服务层能力，
并通过 MLX / Metal 在 Apple Silicon 上执行模型。
```

它不是 `vllm-mlx` 的同义词：

```Markdown
vllm-mlx   = 独立的 vLLM-style MLX 服务框架。
vllm-metal = 原版 vLLM 平台插件，将 vLLM 的服务层接到 Apple Silicon / Metal。
```

它和 `vllm-mlx` 的区别：

| 对比项 | vllm-metal | vllm-mlx |
| --- | --- | --- |
| 技术路线 | 原版 vLLM 平台插件 | 独立的 vLLM-style MLX 服务框架 |
| 命令入口 | vllm serve | vllm-mlx serve |
| 框架层级 | vLLM core + Metal plugin | MLX 服务层 |
| 底层执行 | vLLM v1 engine + vllm-metal worker + MLX / Metal | MLX 服务层实现 |
| 适合用途 | 验证 Mac 上的 vLLM API、paged KV、prefix cache、文本并发 | 与 oMLX 做 vLLM-style 服务层对照 |
| 多模态 | 当前图片 encoder 未接通 | 理论依赖 mlx-vlm，需实测 |

优势：

- 入口和原版 vLLM 一致，使用 `vllm serve` 和 OpenAI-compatible API。

- 对熟悉 vLLM 的部署方式更友好，参数、模型服务和客户端调用方式更接近原版 vLLM。

- 可以复用 vLLM scheduler、paged KV、prefix cache、batched tokens 等服务概念。

- 适合在 Apple Silicon 上验证 Qwen3.6、Gemma4 等 MLX/HF 目录文本模型的 vLLM API 兼容性。

- 支持通过 `max-num-seqs`、`max-num-batched-tokens` 等调度参数做文本并发压测。

- 可与 oMLX、vllm-mlx 使用同一 OpenAI API 压测工具对比 TTFT、TPOT、RPS、P99 latency 和 success rate。

局限性：

- 当前仍是 Alpha / 插件路线，模型覆盖面和稳定性不能等同于 CUDA vLLM。

- 它不是完整的 Mac 版 vLLM，也不能替代 NVIDIA GPU 上的原版 vLLM 生产部署。

- 当前更适合 text-only 服务验证，多模态图片输入不是可用主线。

- VLM 请求即使能被前端解析成 `mm_features`，Metal runner 仍可能无法执行 image encoder 和 embedding splice。

- 不支持 GGUF，GGUF 仍应走 `llama.cpp` 或 DeepSeek-V4-Flash 的 `ds4` 路线。

- 多模型管理、模型生命周期、管理界面、缓存治理能力不如 oMLX 完整。

- 模型的 chat template、thinking 开关、特殊 tokenizer 行为需要额外关注，否则可能出现非预期输出。

适合场景：

- Mac 上验证 vLLM API 与 vLLM scheduler 在 Apple Silicon 上的可用性。

- Qwen3.6 / Gemma4 等 MLX/HF 目录文本模型的 OpenAI API 服务。

- 文本模型 prefix cache、paged KV、batched tokens、并发请求压测。

- 与 oMLX、vllm-mlx 做同模型、同提示词、同并发参数下的横向对照。

- 小团队内网中的单模型文本推理服务实验。

不适合场景：

- VLM 图片识别主服务。

- GGUF 模型服务。

- DeepSeek-V4-Flash 专用模型服务。

- 多模型统一管理平台。

- 期望达到 CUDA vLLM 多卡 / 多机生产吞吐的服务。

推荐用途：

```Markdown
vllm-metal 适合作为 Mac 上的 vLLM 插件路线对照框架，
重点用于文本模型 API 兼容性、paged KV、prefix cache 和并发调度验证。
它可以补充 oMLX 的主线压测，但不替代 oMLX 的多模型管理和 VLM 服务能力。
```

##### 6.4 vLLM

项目定位：

```Markdown
面向 GPU 生产服务的高吞吐 LLM inference / serving 框架。
```

适合场景：

- NVIDIA GPU

- 多 GPU / 多机

- 高 QPS 在线服务

- tensor parallel

- pipeline parallel

- 大规模 OpenAI-compatible API

- 高吞吐文本生成

与 Mac 本地框架的区别：

```Markdown
vLLM 的强项建立在 CUDA/HIP 等 GPU 后端和成熟的 PagedAttention / batching / 分布式服务能力之上。
Mac 上的 oMLX / vllm-mlx 是 MLX / Metal 生态里的本地服务框架，不能等价替代原版 vLLM。
```

当前项目中的定位：

```Markdown
vLLM 是生产级高并发服务的参照系，不是当前 Mac 本地已部署主框架。
```

##### 6.5 MLX-LM

常见入口：

```text
python -m mlx_lm.server
```

或在代码中使用：

```text
from mlx_lm import load, generate, stream_generate
```

适合场景：

- 纯文本 MLX 模型

- 脚本化推理

- 小中型模型快速验证

- 不需要复杂模型管理的单模型服务

与 oMLX 的关系：

```Markdown
mlx-lm 是 oMLX 的文本模型底层之一。
oMLX 的文本 LLM 能力主要建立在 mlx-lm 之上。
```

局限：

- 自身更偏模型运行库，不是完整本地模型平台

- 多模型管理、缓存策略、管理界面、服务治理能力不如 oMLX

##### 6.6 MLX-VLM

当前项目中的启动方式：

```text
cd /srv/llm/Desktop/llm-workspace/oMLX-vlm/mlx-vlm

../oMLX-vlm/bin/python -m mlx_vlm.server \
  --host 0.0.0.0 \
  --port 18082 \
  --model /Volumes/990pro/modeldown/models/gemma-4-26b-a4b-it-mxfp8
```

适合场景：

- 图片理解

- OCR

- 图文问答

- 多模态模型验证

- Gemma / MiniCPM / Qwen VLM 类模型测试

- 单模型图片 API 服务

与 oMLX 的关系：

```Markdown
mlx-vlm 是 oMLX 的 VLM 底层之一。
oMLX 可以调用 mlx-vlm 的模型加载、图片处理和 VLM 推理能力。
```

需要修正的判断：

```Markdown
MLX-VLM 代码中存在 BatchGenerator / VLM batch 相关能力，
但你之前使用 python -m mlx_vlm.server 对 26B/31B + 图片 + 64K 的实测结果显示：
并发 2 时 TTFT、TPOT 和总延迟明显变差，更接近低并发队列式服务。
```

因此在当前项目中，MLX-VLM 更适合：

```Markdown
图片模型功能验证、单模型低并发 API、图文性能基准测试。
```

不建议把直接启动的 `mlx_vlm.server` 当成：

```Markdown
类似 vLLM 的高效 continuous batching 生产服务。
```

如果要验证真正的 oMLX VLM 服务能力，应该使用：

```text
omlx serve
```

而不是：

```text
python -m mlx_vlm.server
```

##### 6.7 MLX-Embeddings

适合场景：

- embedding

- rerank

- 本地 RAG 向量化

- 文档检索

- 多模型统一 API 服务中的辅助模型

与 oMLX 的关系：

```Markdown
mlx-embeddings 是 oMLX embedding / rerank 能力的底层依赖之一。
```

推荐方式：

```Markdown
如果只是单独测试 embedding，可以直接使用 mlx-embeddings。
如果要长期服务化，建议通过 oMLX 管理。
```

##### 6.8 dflash-mlx

适合场景：

- 特定模型的加速生成

- speculative / diffusion decoding 类优化路径

- 部分短上下文或适配模型的响应速度提升

与 oMLX 的关系：

```Markdown
dflash-mlx 是 oMLX 可调用的加速后端，不是通用替代 mlx-lm / mlx-vlm 的框架。
```

注意事项：

- 需要看模型是否兼容

- 需要看上下文长度是否适合

- 长上下文场景可能回退到 oMLX 的常规 LLM/VLM engine

##### 6.9 llama.cpp

命令入口：

```text
./build/bin/llama-server
```

本地目录：

```text
/srv/llm/Desktop/llm-workspace/llama.cpp
```

适合场景：

- GGUF 模型

- 通用量化模型

- CPU / Metal 本地推理

- 模型转换后验证

- 量化版本对比

- 通用 OpenAI 兼容 HTTP server

与 oMLX 的区别：

```Markdown
llama.cpp 是 GGUF 推理引擎。
oMLX 是 MLX 模型服务框架。
```

模型格式选择：

```Markdown
GGUF 模型 -> llama.cpp
MLX 模型目录 -> oMLX / mlx-lm / mlx-vlm
```

并发说明：

```Markdown
llama.cpp 的 llama-server 支持 slots、--parallel 和 --cont-batching。
但在当前项目中，还没有对大模型、长上下文、Mac Studio M3 Ultra 场景下的高效批次并发做完整验证。
```

因此当前建议：

```Markdown
llama.cpp 作为 GGUF 主力框架；
是否作为高并发服务，需要按具体模型、上下文、parallel 参数单独压测。
```

##### 6.10 ds4

本地目录：

```text
/srv/llm/Desktop/llm-workspace/ds4
```

适合场景：

- DeepSeek-V4-Flash

- DeepSeek-V4-Flash 专用优化模型

- 长上下文文本推理

- 单模型常驻服务

- 稳定文本 API

与其他框架的区别：

```Markdown
ds4 是更专用的 DeepSeek-V4-Flash 推理路线。
它不是通用 MLX 模型服务框架，也不是 GGUF 通用框架。
```

并发说明：

```Markdown
根据之前分析，ds4 的 HTTP 层可以接收多个请求，
但推理层更接近单一 Metal worker 队列式处理，
不是 vLLM 那种 continuous batching 多请求合批 decode 服务。
```

推荐定位：

```Markdown
DeepSeek-V4-Flash 专用服务优先选 ds4。
通用 MLX 多模型服务优先选 oMLX。
GGUF 模型优先选 llama.cpp。
```

#### 7. 当前模型目录与框架匹配

当前模型目录示例：

```Markdown
/Volumes/990pro/modeldown/models
```

已有模型：

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

推荐匹配：

| 模型 | 格式 / 类型 | 推荐框架 | 说明 |
| --- | --- | --- | --- |
| DeepSeek-V4-Flash | 专用目录模型 | ds4 | DeepSeek-V4-Flash 专用路线 |
| DeepSeek-V4-Flash-*.gguf | GGUF | llama.cpp | GGUF 优先走 llama.cpp |
| gemma-4-26b-a4b-it-bf16 | MLX VLM / Gemma4 文本骨干 | oMLX / mlx-vlm / vllm-metal | 图片能力优先 VLM 路线；文本能力可用 vllm-metal 实验性验证 |
| gemma-4-26b-a4b-it-mxfp8 | MLX VLM | oMLX / mlx-vlm | 当前 64K 图片测试主力候选 |
| gemma-4-31B-it-assistant-bf16 | MLX 模型 | oMLX / mlx-lm | 若为纯文本，走文本路线 |
| gemma-4-31b-it-bf16 | MLX 模型 / Gemma4 文本骨干 | oMLX / mlx-lm / mlx-vlm / vllm-metal | 取决于具体 config 是否 VLM；文本能力可用 vllm-metal 实验性验证 |
| gemma-4-31b-it-mxfp8 | MLX VLM | oMLX / mlx-vlm | 质量优先，速度明显慢于 26B |
| MiniCPM-V-4.6-bf16 | MLX VLM | oMLX / mlx-vlm | 图片 / 多模态路线 |
| Qwen3.6-35B-A3B-bf16 | MLX Qwen3.6 / MoE / VLM wrapper | vllm-metal / oMLX / mlx-lm | 文本服务可用 vllm-metal 做 vLLM API 对照；图片能力不走 vllm-metal，需走 mlx-vlm / oMLX |

#### 8. 并发与批处理能力分析

这里需要区分三个概念：

```Markdown
1. HTTP 并发接入：
   server 可以同时接收多个请求。

2. 队列式并发：
   多个请求排队等待，同一时刻主要还是一个请求在推理。

3. continuous batching：
   服务端把多个请求的 prefill / decode 动态合批，提升整体吞吐。
```

很多框架都能做到第 1 点，但不一定能做到第 3 点。

##### 8.1 当前项目中的并发判断

| 框架 | HTTP 并发接入 | 是否适合批次并发服务 | 当前判断 |
| --- | --- | --- | --- |
| oMLX | 支持 | 适合 | 当前已安装的 MLX 主服务框架，适合先做 continuous batching / 多请求调度验证 |
| vllm-mlx | 支持 | 适合，需安装后实测 | vLLM-style MLX 服务框架，适合作为 oMLX 对照压测 |
| vllm-metal | 支持 | 适合文本模型并发验证，需按模型实测 | 适合验证 vLLM API、max-num-seqs / max-num-batched-tokens、paged KV、prefix cache；图片请求不是当前可用主线 |
| mlx-vlm.server | 支持 | 不建议作为高并发主服务 | 26B/31B + 图片 + 64K 实测更接近低并发队列服务 |
| mlx-lm.server | 支持 | 有一定能力，但服务治理弱于 oMLX | 更适合轻量文本服务 |
| ds4 | 支持 | 不适合作为批次并发服务 | 推理层更接近单 Metal worker 队列 |
| llama.cpp | 支持 | 理论支持 slots / cont-batching，需实测 | GGUF 主力框架，但当前项目尚未完成高并发验证 |
| 原版 vLLM | 支持 | 适合大规模高并发 | NVIDIA GPU / 多卡生产服务参照系，不是当前 Mac 本地 MLX 主线 |

##### 8.2 为什么 oMLX 更适合当前主线批次并发服务

oMLX 的优势不只是“能启动 API 服务”，而是它围绕服务做了完整设计：

- `EnginePool` 管理多个模型

- `BatchedEngine` 处理文本 LLM continuous batching

- `VLMEngine` 处理视觉语言模型服务

- `Scheduler` 负责请求调度

- `mlx-lm BatchGenerator` 负责批次生成机制

- `prefix cache` 减少重复前缀计算

- `paged SSD cache` 支持 KV cache 分层管理

- `max-concurrent-requests` 可限制并发请求数

- `hot cache` 控制内存热缓存规模

所以在当前已安装的 MLX 模型服务里，oMLX 是最适合先验证的方案。

##### 8.3 为什么还要测试 vllm-metal / vllm-mlx

`vllm-metal` 和 `vllm-mlx` 都适合作为 oMLX 的对照框架，但它们对照的是不同问题：

```Markdown
vllm-metal：验证原版 vLLM 插件路线在 Apple Silicon 上的文本服务能力。
vllm-mlx：验证独立 vLLM-style MLX 服务层的调度和缓存能力。
```

建议测试它们的原因：

- 都运行在 Apple Silicon / MLX / Metal 生态中

- 都适合与 oMLX 做文本模型并发压测对照

- 都强调 KV cache、prefix cache 或 paged KV 相关能力

- 可以用同一模型、同一并发、同一 EvalScope 参数对比

- 能帮助判断当前模型更适合 oMLX 主服务、vLLM Metal 插件路线，还是 vLLM-style MLX 服务层

需要避免的误解：

```Markdown
vllm-metal 不是 CUDA vLLM 在 Mac 上的完整等价替代。
vllm-mlx 不是原版 vLLM 的完整 Mac 版。
两者都需要按具体模型、上下文长度和并发参数实测，不能只按名称判断吞吐。
```

对当前项目的推荐：

```Markdown
oMLX 做主线；
vllm-metal 做文本模型 vLLM 插件路线对照；
vllm-mlx 做另一条 vLLM-style MLX 服务层对照；
原版 vLLM 作为 NVIDIA 高吞吐服务参照系。
```

##### 8.4 为什么直接用 MLX-VLM 不等同于 oMLX / vllm-mlx

之前启动方式是：

```text
python -m mlx_vlm.server
```

这个服务可以接收图片请求，也可以提供 OpenAI 风格接口，但它不等同于完整 oMLX。

你在 `gemma-4-26b-a4b-it-mxfp8` 和 `gemma-4-31b-it-mxfp8` 上的 64K 图片性能测试显示：

| 模型 | 并发 | 平均延迟 | P99 延迟 | Avg TTFT | Avg TPOT | 成功率 |
| --- | --- | --- | --- | --- | --- | --- |
| gemma-4-26b-a4b-it-mxfp8 | 1 | 20.993 s | 42.260 s | 19159.8 ms | 19.4 ms | 100.0% |
| gemma-4-26b-a4b-it-mxfp8 | 2 | 35.176 s | 52.610 s | 23180.3 ms | 153.1 ms | 91.7% |
| gemma-4-31b-it-mxfp8 | 1 | 80.549 s | 211.390 s | 76642.7 ms | 63.6 ms | 100.0% |
| gemma-4-31b-it-mxfp8 | 2 | 238.291 s | 436.570 s | 138114.4 ms | 904.7 ms | 100.0% |

这个结果说明：

```Markdown
在 26B/31B + 图片 + 64K 场景下，直接使用 mlx_vlm.server 并发 2 时并没有体现出高效合批收益。
尤其是 31B 模型，并发 2 后平均延迟从 80.549 s 上升到 238.291 s，TPOT 从 63.6 ms 上升到 904.7 ms。
```

因此文档中需要修正为：

```Markdown
MLX-VLM 能跑图片模型，也具备部分 batch 相关机制；
但当前项目实测下，它不应被定位为高并发批处理服务主框架。
真正要验证 batch/concurrent serving，应优先使用 oMLX 源码版服务；
文本模型可进一步用 vllm-metal / vllm-mlx 做对照压测；
图片模型仍应优先走 oMLX / mlx-vlm 路线，不应把 vllm-metal 当作 VLM 主服务。
```

##### 8.5 ds4 的并发定位

ds4 更适合：

```Markdown
DeepSeek-V4-Flash 单模型长上下文文本服务。
```

不应把它理解成：

```Markdown
vLLM 类 continuous batching 服务。
```

当前判断：

```Markdown
ds4 可以接收多个 HTTP 请求，但推理层更接近队列等待。
适合稳定服务，不适合追求多请求合批吞吐。
```

##### 8.6 llama.cpp 的并发定位

llama.cpp 的 `llama-server` 支持：

```Markdown
--parallel
--cont-batching
slots
```

但在 Mac Studio 大模型长上下文场景下，需要单独测试：

- 模型大小

- GGUF 量化方式

- `--ctx-size`

- `--parallel`

- `--batch-size`

- `--ubatch-size`

- Metal 内存占用

- 多请求 TTFT / TPOT / RPS

当前建议：

```Markdown
llama.cpp 是 GGUF 主力框架；
是否能作为高效批次并发服务，要以具体压测结果为准。
```

#### 9. 设备档位建议

##### 9.1 32GB 级别

适合：

- 小型 GGUF

- 小型 MLX 文本模型

- `llama.cpp` 轻量测试

- `mlx-lm` 小模型脚本测试

不适合：

- 26B / 31B VLM

- DeepSeek-V4-Flash

- 64K 长上下文图片测试

- 多模型常驻服务

推荐框架：

```Markdown
llama.cpp
mlx-lm
```

##### 9.2 64GB 级别

适合：

- 中小型 GGUF

- 中小型 MLX 文本模型

- 低并发图片模型测试

- 小规模本地 API 服务

需要控制：

- 上下文长度

- 并发数

- 模型量化精度

- 是否开启图片输入

推荐框架：

```Markdown
llama.cpp
mlx-lm
oMLX
轻量 mlx-vlm
```

##### 9.3 128GB 级别

适合：

- 较大文本模型

- 中等规模 VLM

- 本地 OpenAI API 服务

- 单机 RAG / embedding / rerank

- 中低并发团队内网服务

推荐框架：

```Markdown
oMLX
llama.cpp
mlx-vlm
mlx-embeddings
```

##### 9.4 256GB 级别

适合：

- 大模型

- 长上下文

- 多模型切换

- 更稳定的本地服务

- DeepSeek-V4-Flash 专用路线

推荐框架：

```Markdown
oMLX
ds4
llama.cpp
mlx-vlm
```

##### 9.5 512GB 级别

适合：

- 当前 Mac Studio M3 Ultra / 512GB

- 26B / 31B VLM 64K 图片测试

- DeepSeek-V4-Flash

- 大模型长上下文

- 多模型目录服务

- prefix cache / KV cache / SSD cache 验证

- 并发调度和批处理能力测试

推荐框架：

```Markdown
oMLX 作为 MLX 主服务
vllm-metal 作为 vLLM Metal 文本对照验证框架
vllm-mlx 作为 vLLM-style 对照压测框架
ds4 作为 DeepSeek-V4-Flash 专用服务
llama.cpp 作为 GGUF 主服务
mlx-vlm 作为 VLM 单模型验证和对照测试
```

#### 10. 当前 Mac Studio M3 Ultra / 512GB 的推荐架构

建议把当前设备上的推理服务拆成几条主线：

##### 10.1 MLX 模型主服务：oMLX

用途：

- MLX 文本模型

- MLX VLM 模型

- embedding

- rerank

- 多模型统一 API

- continuous batching 测试

- prefix cache / SSD cache 测试

推荐启动方式：

```text
cd /srv/llm/Desktop/llm-workspace/omlx

source /srv/llm/Desktop/llm-workspace/omlx/omlx-build/bin/activate

omlx serve \
  --model-dir /Volumes/990pro/modeldown/models \
  --host 0.0.0.0 \
  --port 18080 \
  --max-model-memory disabled \
  --max-process-memory disabled \
  --paged-ssd-cache-dir /Volumes/990pro/omlx-cache \
  --paged-ssd-cache-max-size 100GB \
  --hot-cache-max-size 8GB \
  --max-concurrent-requests 8 \
  --log-level info
```

测试：

```text
curl http://127.0.0.1:18080/v1/models | jq
```

##### 10.2 vLLM-style 对照服务：vllm-mlx

用途：

- 与 oMLX 对比 continuous batching

- 与 oMLX 对比 prefix cache / paged KV cache

- 验证 MLX 文本模型并发吞吐

- 验证 VLM 图片模型是否比 `mlx_vlm.server` 更适合服务化

建议独立环境安装：

```text
cd /srv/llm/Desktop/llm-workspace

uv venv --python 3.12 vllm-mlx-env

source /srv/llm/Desktop/llm-workspace/vllm-mlx-env/bin/activate

uv pip install -U pip setuptools wheel

uv pip install vllm-mlx \
  --index-url https://pypi.tuna.tsinghua.edu.cn/simple
```

示例启动：

```text
vllm-mlx serve /Volumes/990pro/modeldown/models/Qwen3.6-35B-A3B-bf16 \
  --host 0.0.0.0 \
  --port 18084 \
  --continuous-batching
```

定位：

```Markdown
对照压测框架，不建议在没有实测前直接替代 oMLX。
```

##### 10.3 vLLM Metal 文本对照服务：vllm-metal

用途：

- 验证原版 vLLM API / scheduler 在 Apple Silicon 上的插件路线

- Qwen3.6 / Gemma4 等文本模型的 OpenAI API 服务对照

- 文本模型 paged KV、prefix cache、batched tokens、并发参数验证

- 与 oMLX / vllm-mlx 使用同一压测工具对比 TTFT、TPOT、RPS 和 P99 latency

定位：

```Markdown
文本模型 vLLM 插件路线对照框架。
它适合验证 vLLM 兼容服务和文本并发调度，
但当前不作为图片 VLM 主服务，也不替代 oMLX 的多模型管理能力。
```

##### 10.4 DeepSeek-V4-Flash 专用服务：ds4

用途：

- DeepSeek-V4-Flash

- 长上下文文本推理

- 单模型稳定服务

定位：

```Markdown
专用文本服务，不作为通用批次并发服务。
```

##### 10.5 GGUF 主服务：llama.cpp

用途：

- DeepSeek-V4-Flash GGUF 版本

- 其他 GGUF 模型

- 量化模型测试

- llama.cpp server 压测

定位：

```Markdown
GGUF 模型优先走 llama.cpp，不建议强行放到 oMLX。
```

##### 10.6 VLM 对照测试：MLX-VLM server

用途：

- 单模型图片测试

- 与 oMLX VLM 服务做对照

- 验证图片缓存、64K 上下文、模型质量

定位：

```Markdown
适合测试和低并发服务；
不建议作为主要高并发批处理服务。
```

#### 11. 场景选型表

| 场景 | 首选框架 | 备选框架 | 原因 |
| --- | --- | --- | --- |
| MLX 文本模型 API | oMLX | mlx-lm.server | oMLX 服务治理和缓存更完整 |
| MLX 文本模型并发压测 | oMLX | vllm-metal / vllm-mlx | oMLX 是主线；vllm-metal 验证原版 vLLM 插件路线；vllm-mlx 做 vLLM-style 服务层对照 |
| MLX 图片模型 API | oMLX | mlx-vlm.server | oMLX 更适合服务化，MLX-VLM 适合功能测试；vllm-metal 当前不作为图片 VLM 路线 |
| 图片模型功能验证 | mlx-vlm.server | oMLX | 直接、简单、调试方便 |
| 图片模型批次并发测试 | oMLX | mlx-vlm.server / vllm-mlx | 图片任务不宜假设高并发收益；vllm-metal 不用于图片 encoder 路线 |
| DeepSeek-V4-Flash | ds4 | llama.cpp GGUF | ds4 是专用路线 |
| DeepSeek-V4-Flash GGUF | llama.cpp | 无 | GGUF 应走 llama.cpp |
| 通用 GGUF | llama.cpp | Ollama / LM Studio | llama.cpp 可控性更强 |
| embedding | oMLX | mlx-embeddings | 长期服务用 oMLX，单测用 mlx-embeddings |
| rerank | oMLX | mlx-embeddings | 同上 |
| 多模型统一服务 | oMLX | 多服务手动管理 | oMLX 有 EnginePool 和管理界面 |
| Mac MLX 高并发批处理服务 | oMLX | vllm-metal / vllm-mlx | 文本模型可三者同条件对照；图片模型不走 vllm-metal |
| 真正生产级高 QPS 服务 | 原版 vLLM | SGLang / TensorRT-LLM | 更适合 NVIDIA GPU / 多卡 / 多机 |

#### 12. 对之前文档的修正

本次重写主要修正以下问题：

##### 12.1 修正 oMLX 定位

旧判断：

```Markdown
oMLX 主要是 Apple Silicon 上的文本推理服务。
```

修正为：

```Markdown
oMLX 是 MLX 生态的本地推理服务层，支持 LLM、VLM、embedding、rerank 等模型类型。
它不是底层推理内核，而是服务封装、调度、缓存和管理系统。
```

##### 12.2 修正 oMLX 与 MLX-VLM 的关系

旧判断容易把 `oMLX-vlm` 目录误认为 oMLX。

修正为：

```Markdown
/srv/llm/Desktop/llm-workspace/oMLX-vlm/mlx-vlm 是 MLX-VLM 源码目录。
/srv/llm/Desktop/llm-workspace/omlx 才是真正的 oMLX 源码目录。
```

##### 12.3 修正 MLX-VLM 并发能力描述

旧判断：

```Markdown
MLX-VLM 具备 continuous batching 机制。
```

修正为：

```Markdown
MLX-VLM 代码中有 batch 相关能力，但当前项目在 26B/31B + 图片 + 64K 场景下实测，
直接使用 mlx_vlm.server 并没有体现出高效 batch serving；
并发增加后更像队列等待，尤其 31B 延迟急剧上升。
```

##### 12.4 修正 ds4 并发定位

旧判断可能把 HTTP 并发接入和推理层并发混在一起。

修正为：

```Markdown
ds4 可以接收多个 HTTP 请求，但推理层更接近单 Metal worker 队列式处理，
不是 vLLM 式 continuous batching 服务。
```

##### 12.5 修正 llama.cpp 并发定位

旧判断可能低估了 llama.cpp 的 slots / continuous batching 支持。

修正为：

```Markdown
llama.cpp 支持 slots、--parallel、--cont-batching；
但在当前项目中的大模型、长上下文、Mac Studio 场景下还需要单独压测验证。
```

##### 12.6 新增 vllm-mlx 与 vLLM 的关系修正

需要新增的判断：

```Markdown
vllm-mlx 是 Apple Silicon / MLX 生态中的 vLLM-style 服务框架。
它不是原版 vLLM，也不能等价替代 NVIDIA GPU 上的 vLLM。
```

对当前项目的正确定位：

```Markdown
oMLX 是当前已安装的 MLX 主服务框架；
vllm-mlx 是后续建议安装的对照压测框架；
原版 vLLM 是高吞吐生产服务参照系。
```

##### 12.7 新增 vllm-metal 定位修正

需要新增的判断：

```Markdown
vllm-metal 是原版 vLLM 的 Apple Silicon / Metal 插件路线，
不是 vllm-mlx 的同义词，也不是完整 CUDA vLLM 的 Mac 等价替代。
```

对当前项目的正确定位：

```Markdown
vllm-metal 适合做 Qwen3.6 / Gemma4 等文本模型的 vLLM API、paged KV、
prefix cache 和并发调度验证；
图片 VLM 输入当前不作为可用主线；
多模型管理和长期服务治理仍优先使用 oMLX。
```

#### 13. 最终推荐

对于当前 Mac Studio M3 Ultra / 512GB，建议采用以下最终分工：

| 任务 | 推荐框架 | 说明 |
| --- | --- | --- |
| MLX 多模型统一服务 | oMLX | 主力服务框架 |
| MLX 文本模型并发服务 | oMLX | 优先验证 continuous batching |
| MLX 图片模型服务 | oMLX | 服务化优先，MLX-VLM 做对照 |
| MLX 图片模型单测 | mlx-vlm.server | 方便快速验证 |
| vLLM Metal 文本对照 | vllm-metal | 验证 vLLM API、scheduler、paged KV、prefix cache 和文本并发 |
| vLLM-style 服务层对照 | vllm-mlx | 与 oMLX 使用同模型同参数对比 |
| 大规模生产级高并发 | 原版 vLLM + NVIDIA GPU | Mac 单机方案不能等价替代 |
| DeepSeek-V4-Flash | ds4 | 专用路线 |
| GGUF 模型 | llama.cpp | GGUF 标准路线 |
| embedding / rerank | oMLX | 统一 API 管理 |
| Mac 本地高并发批处理验证 | oMLX + vllm-metal + vllm-mlx | 文本模型三者对照；图片模型以 oMLX / MLX-VLM 为主 |

一句话结论：

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
