# DSpark：从块草稿到自适应验证

[总目录](../../SUMMARY.md) · [MTP与推测解码](speculative-decoding.md) · [压测方法](benchmarking.md) · [本次资料核查](../../evidence/2026-10-refresh.md)

**资料核查：2026-10-18。** 本章是依据官方实现整理的工程流程，尚未在本仓库的GPU环境执行。下面的命令、教学计算和上游实验各自标明来源，不提供虚构的本机加速数字。

## 1. DSpark解决什么问题

普通decode每轮运行目标模型，通常推进一个token。推测解码让较便宜的草稿模块先提出候选，再用目标模型批量验证。工程目标是减少生成同一段答案所需的昂贵串行轮数。

草稿也有成本。传统自回归草稿要逐个预测，DFlash采用块草稿，一次前向提出一段候选。DSpark在块草稿中增加半自回归的Markov head，让当前位置利用前一个token的信息；配套confidence head可估计各位置被接受的可能性，用于选择值得验证的候选。

这涉及两个独立问题：**怎样生成更合适的草稿，以及花多少算力验证草稿。** vLLM的adaptive verification处理后一个问题，当前开发文档也将它用于其他受支持的模型草稿方法。不能将所有自适应推测都统称为DSpark。

| 名称 | 工程职责 | 需要的材料 |
| --- | --- | --- |
| MTP | 使用模型支持的多token预测结构提出候选 | 原生MTP权重，或引擎规定的assistant制品 |
| EAGLE-3 | 用目标模型隐藏状态辅助草稿预测 | 与目标匹配的专用草稿模型 |
| DFlash | 用块扩散草稿一次提出多个候选 | 配套DFlash制品与特征接口 |
| DSpark | 块草稿加入半自回归依赖，可带置信度预测 | 与目标匹配的DSpark制品 |
| Dynamic SD | 根据当前batch区间调整草稿长度K | 引擎支持及事先测出的区间配置 |
| Adaptive verification | 按置信度和执行成本分配验证预算 | 对应runner、attention、图执行与估计器支持 |

**DSpark算法与DGX Spark设备名称不同。** 设备的ARM64、统一内存和CUDA部署见[DGX Spark专题](../hardware/dgx-spark.md)。

## 2. 为什么高并发时固定K可能变慢

并发很低时，decode经常受权重读取限制，GPU可能还有计算余量。一次多验证几个位置，有机会用较少的额外时间换来更多已接受token。

并发升高后，目标模型原本就能批量处理很多请求。额外候选开始争用矩阵计算、attention、KV和图执行预算。后几个位置接受率低，验证后又被丢弃，就可能比普通decode更慢。

可以用下面的量判断方向，但不能把它当成无需测量的速度公式：

```text
实际推进效率 = 目标模型确认并推进的token
             / (草稿耗时 + 验证耗时 + 调度/采样/搬运耗时)
```

如果每轮接受长度增加20%，但每轮耗时增加40%，最终生成仍会变慢。只看acceptance rate会漏掉这个问题。

### 2.1 验证预算怎样分给不同请求

假设某请求前面各位置的条件接受概率为0.9、0.8、0.5，则依次保留下来的概率约为0.9、0.72、0.36。越靠后的位置，通常越不值得付出同样的验证成本。

vLLM会把不同请求的候选位置放在一起比较。在总验证预算内，某条高置信请求的第5个位置，可能比另一条低置信请求的第1个位置更值得验证。预算还要结合启动时测出的step成本，而非只设一个概率阈值。

这是机制说明和教学数字，不是本仓库训练出的confidence，也不是一组性能测量。

## 3. 先核对支持条件，再选部署路线

本章对应的源码锚点：

- llama.cpp：`5aeac37a35b44fde4bdffaec9159f2fcb253b622`。
- vLLM：`2365177ddda7714502e4df7a1669cc79c0a4dfd0`。
- DeepSpec：`005e03b81cec38b7da6399833d609ee89a2587f2`。

这些是资料快照，不是声称所有已发布二进制均包含相同功能。复现时保存自己实际构建的commit、模型revision和二进制版本。

| 检查项 | 必须确认的内容 | 不满足时 |
| --- | --- | --- |
| 目标与草稿配对 | 模型系列、隐藏状态接口、tokenizer、训练目标 | 换配套草稿，不能只按参数量选 |
| 模型模式 | 草稿训练时thinking/non-thinking及任务分布 | 分模式测接受率和答案质量 |
| 量化 | 目标、草稿、KV各自dtype与kernel | 先恢复可工作的精度基线 |
| 内存 | 两份权重/共享张量、两侧状态、验证workspace | 降低预算或先用较小模型 |
| 执行后端 | attention、CUDA graph、采样和并行方式 | 按固定版本支持范围调整 |

DeepSpec公开了Qwen3-4B/8B/14B等配套制品。官方说明其发布实验使用对应目标模型生成的non-thinking训练数据；直接改为长思考负载，接受率不应沿用原实验数字。自行训练还涉及目标特征缓存，默认Qwen3-4B设置的缓存可达约38TB，不能把“草稿很小”理解为训练链路也很轻。

## 4. llama.cpp路线：Qwen3-4B与DSpark完整操作

此路线优先用于理解本地部署。示例为Linux Bash、NVIDIA CUDA；其他后端应按各自实例构建，并单独确认该组合支持。4B目标的BF16权重约8GB只是数量级，设备还需容纳草稿、KV与工作区。

### 4.1 准备目录与固定源码

在新实验目录执行：

```bash
mkdir -p dspark-lab/models dspark-lab/artifacts dspark-lab/records
cd dspark-lab
git clone https://github.com/ggml-org/llama.cpp.git
git -C llama.cpp checkout 5aeac37a35b44fde4bdffaec9159f2fcb253b622
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r llama.cpp/requirements.txt huggingface_hub
git -C llama.cpp rev-parse HEAD > records/llama-commit.txt
python -m pip freeze > records/conversion-packages.txt
```

依赖由该提交的requirements约束，安装后保存解析结果。CUDA编译依赖见[CUDA平台章节](../hardware/nvidia.md)。

### 4.2 下载配套模型并保存revision

用公开仓库API解析一次revision，再按该revision下载，避免后续重跑追到变化的main：

```bash
python - <<'PY'
import json
from pathlib import Path
from huggingface_hub import HfApi, snapshot_download

items = {
    "target": ("Qwen/Qwen3-4B", "models/Qwen3-4B"),
    "draft": ("deepseek-ai/dspark_qwen3_4b_block7", "models/DSpark-Qwen3-4B"),
}
revisions = {}
api = HfApi()
for role, (repo, directory) in items.items():
    revision = api.model_info(repo).sha
    snapshot_download(repo_id=repo, revision=revision, local_dir=directory)
    revisions[role] = {"repo": repo, "revision": revision, "directory": directory}
Path("records/model-revisions.json").write_text(
    json.dumps(revisions, indent=2), encoding="utf-8")
PY
```

重新复现时使用已保存的revision，不再重新解析。核对模型卡与许可；本例不需要把认证信息写入脚本或日志。

### 4.3 转换目标与草稿

```bash
python llama.cpp/convert_hf_to_gguf.py models/Qwen3-4B \
  --outtype bf16 --outfile artifacts/Qwen3-4B-BF16.gguf
python llama.cpp/convert_hf_to_gguf.py models/DSpark-Qwen3-4B \
  --target-model-dir models/Qwen3-4B \
  --outtype bf16 --outfile artifacts/Qwen3-4B-DSpark-BF16.gguf
sha256sum artifacts/*.gguf > records/gguf-sha256.txt
```

`--target-model-dir`让转换器获取目标的tokenizer和相应共享张量信息。草稿不能作为独立聊天模型随意替换。先保持BF16减少变量，跑通后再单独引入目标量化；不要默认普通权重的每一种量化都适合草稿的Markov/confidence模块。

### 4.4 构建并确认参数存在

```bash
cmake -S llama.cpp -B llama.cpp/build-cuda \
  -DGGML_CUDA=ON -DCMAKE_BUILD_TYPE=Release
cmake --build llama.cpp/build-cuda \
  --target llama-server llama-bench -j 4
llama.cpp/build-cuda/bin/llama-server --version > records/server-version.txt
llama.cpp/build-cuda/bin/llama-server --help > records/server-help.txt
rg 'draft-dspark|spec-draft-conf-min|gpu-layers-draft' records/server-help.txt
```

无`rg`时使用`grep -E`。如果没有DSpark参数，检查源码与实际二进制路径，先解决版本问题。

### 4.5 运行A组基线

```bash
llama.cpp/build-cuda/bin/llama-server \
  -m artifacts/Qwen3-4B-BF16.gguf \
  -ngl 99 -c 8192 -np 1 -b 512 -ub 128 -fa on --jinja \
  --alias qwen3-dspark-lab --host 127.0.0.1 --port 8080 \
  > records/baseline.log 2>&1
```

在另一个终端检查`/health`和`/v1/models`，完成短题与固定质量集，再压测。前台命令持续占用终端是正常现象。

### 4.6 停止A组，再运行B组

A组终端按Ctrl+C退出，确认它已释放设备和8080端口，再启动：

```bash
llama.cpp/build-cuda/bin/llama-server \
  -m artifacts/Qwen3-4B-BF16.gguf \
  -md artifacts/Qwen3-4B-DSpark-BF16.gguf -ngld 99 \
  --spec-type draft-dspark --spec-draft-n-max 7 \
  --spec-draft-p-min 0 \
  -ngl 99 -c 8192 -np 1 -b 512 -ub 128 -fa on --jinja \
  --alias qwen3-dspark-lab --host 127.0.0.1 --port 8080 \
  > records/dspark-k7.log 2>&1
```

`-ngld`为草稿的GPU卸载预算；必须从日志确认目标和草稿实际使用了哪个设备。`K=7`与该草稿训练block大小对应。超出训练block的请求会受实现限制，不能靠无限增加K获得收益。

本轮B组先关闭confidence截断，建立固定K对照。随后只修改`--spec-draft-p-min`，如0.3、0.5，形成C/D组。这个参数按请求截断低置信位置，**不等于vLLM跨请求的成本模型预算调度**。



该快照的说明页仍写`--spec-draft-conf-min`，而`common/arg.cpp`和`common/speculative.cpp`实际使用`--spec-draft-p-min`。本文命令按实现修订，执行前以本机二进制帮助再核对。

### 4.7 统一请求与计时

两组都使用下面的功能输入；`enable_thinking`固定为false，以配合本例草稿训练模式：

```bash
curl --fail-with-body http://127.0.0.1:8080/v1/chat/completions \
  -H 'Content-Type: application/json' \
  -d '{"model":"qwen3-dspark-lab","messages":[{"role":"user","content":"计算12乘13，只输出结果。"}],"chat_template_kwargs":{"enable_thinking":false},"temperature":0,"max_tokens":64}'
```

该题验收数字为156。正式质量集还要覆盖中文、代码、数字、JSON、长文和多轮；保存所有答案。随后从仓库根目录用[矩阵压测脚本](../../examples/run_optimization_matrix.py)分别测A/B/C，`--extra-body`统一传入同一模板设置。该脚本只记录HTTP性能，不能代替质量回归。

## 5. vLLM路线：固定K与自适应验证

官方示例使用`DeepSeek-V4-Flash-DSpark`。模型卡列出目标总参数284B、激活13B；总权重容量按284B及混合精度预算，不能按13B估算。其4×GB300示例属于服务器配置，不能照搬成单块GB10的可运行承诺。

下面给出在**已经按对应官方recipe完成容量、模型和并行配置**后需要加入的配置差异。它是参数片段，必须附加到同一套已能生成的`vllm serve`命令，不能单独执行：

```json
{
  "method": "dspark",
  "model": "/srv/models/DeepSeek-V4-Flash-DSpark",
  "num_speculative_tokens": 7,
  "draft_sample_method": "probabilistic",
  "enable_adaptive_verification": true
}
```

A组删除整个`--speculative-config`；B组保留同一份配置但设`enable_adaptive_verification=false`；C组改为true。目标revision、采样、并行、KV、图模式和输入保持一致。不要让B组用greedy而C组用probabilistic，之后把所有差异归因到自适应预算。

### 5.1 当前自适应验证的限制

根据上述vLLM源码快照：

- attention后端必须支持设备端决定的query长度；不兼容的组合会在启动时报错。
- 需要FULL CUDA Graph；`--enforce-eager`与该机制不兼容。可以先用普通decode排错，但不能将eager配置保留在自适应组。
- 不支持与LoRA或pipeline parallelism组合。
- 无confidence head时使用在线接受率估计器，不能同时使用不生成完整草稿logits的`use_local_argmax_reduction`。

该快照的详细文档已列出对EAGLE、MTP、DFlash等草稿的支持，而部分概览仍写“DSpark only”。发生冲突时以固定版本的详细文档、配置校验和实现为准，保存启动验收；不要据一张概览表宣布任意模型都支持。

### 5.2 长上下文的成本画像

```bash
export VLLM_ADAPTIVE_VERIFICATION_PROFILE_CONTEXT_LEN=131072
```

该变量改变启动画像所用的合成KV长度，官方快照默认8192。它不修改模型的服务上下文上限，也不代表已经完成128K质量测试。只有目标业务确实是长上下文时才单独评估这项，否则可能用不匹配的画像做预算。

## 6. 一张可执行的实验表

| 组别 | 改动 | 负载 | 要证明什么 |
| --- | --- | --- | --- |
| A | 无推测 | c1/c2/c4/c8，短输入长输出、长输入短输出各一套 | 普通decode的资源和质量基线 |
| B | DSpark固定K | 与A同样本与采样 | 块草稿是否带来净收益 |
| C | 同K上限，自适应验证或confidence截断 | 与B一致 | 预算机制的增量价值 |
| D | 固定配置，逐步提高到达率 | 稳定流量与突发分别测 | 何时开始排队、何时低于基线 |

每组至少保存3轮，A/B顺序交替。记录输入/输出实际token、成功/失败、TTFT P50/P95/P99、TPOT、SSE事件间隔、墙钟吞吐、接受token/提出token、平均接受长度、草稿时间、验证时间和峰值内存。

**采用条件：** 在相同质量任务和目标负载下，有效吞吐或目标延迟改善，资源仍有余量；并发升高后若收益消失，提供普通decode配置或经过验证的动态策略。不要将质量未通过的高吞吐配置当成最终版本。

## 7. 常见故障与处理

| 现象 | 优先检查 | 下一步 |
| --- | --- | --- |
| 不认识`draft-dspark` | 二进制版本、PATH、源码commit | 使用明确路径运行新构建 |
| 草稿shape/token映射错误 | target/draft配对与转换参数 | 用固定目标目录重新转换 |
| 接受率低 | thinking模式、任务分布、模板、量化 | 先对齐训练目标，缩短K |
| 显存比预期大 | 草稿卸载、两侧KV、workspace、图 | 保存分项buffer，降低单项预算 |
| c1快、c8慢 | 有效batch和验证计算是否饱和 | 测短K或受支持的自适应策略 |
| 自适应启动拒绝eager/attention | FULL图及设备query长度支持 | 按支持矩阵换配置，不绕过校验 |
| TTFT不变、整段生成更快 | 优化主要作用于decode | 分阶段报告，不承诺首token加速 |

## 8. 官方资料

- [DeepSpec源码、训练与评测流程](https://github.com/deepseek-ai/DeepSpec/tree/005e03b81cec38b7da6399833d609ee89a2587f2)。
- [DSpark论文：Confidence-Scheduled Speculative Decoding with Semi-Autoregressive Generation](https://arxiv.org/abs/2607.05147)。
- [llama.cpp固定提交的推测解码文档](https://github.com/ggml-org/llama.cpp/blob/5aeac37a35b44fde4bdffaec9159f2fcb253b622/docs/speculative.md)。
- [vLLM固定提交的adaptive verification说明](https://github.com/vllm-project/vllm/blob/2365177ddda7714502e4df7a1669cc79c0a4dfd0/docs/features/speculative_decoding/adaptive_verification.md)。
- [DeepSeek-V4-Flash-DSpark模型卡](https://huggingface.co/deepseek-ai/DeepSeek-V4-Flash-DSpark)。模型卡的硬件、精度、模板与运行要求应一起阅读。
