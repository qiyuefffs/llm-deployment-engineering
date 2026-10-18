# 03 准备模型：文件、格式、量化与校验

[总目录](README.md) · [上一章](02-hardware-compatibility.md) · [下一章：估算内存](04-memory-and-kv-cache.md)

**本章目标：** 拿到框架能使用的完整模型制品，确认文件身份，理解量化改了什么，并保留质量检查所需输入。

## 1. 模型名之外，还要记录哪些内容

“部署一个 27B Q4 模型”不足以复现。模型可能有多个转换版本、不同聊天模板和不同量化布局。

| 内容 | 为什么需要 |
| --- | --- |
| 模型仓库、revision 或文件 SHA256 | 同名文件可能更新，哈希用来核对身份 |
| 架构与配置 | 框架要认识这个模型，不能只看参数规模 |
| 权重文件与分片清单 | 少一个分片，也可能到加载阶段才报错 |
| Tokenizer、聊天模板、特殊 token | 决定输入怎样排列、结束条件是什么 |
| 数值精度、量化方法与布局 | 决定内存、可用 kernel 和质量 |
| 来源与许可证 | 决定怎样使用、公开和分发 |

FlowUs 双卡记录使用 GPTQ INT4 路线，A10 Case 使用 GGUF Q4_K_M。它们都压缩权重，但文件、加载方式和算子不同，不能互相替换名字后直接运行。

## 2. 分清格式、精度和量化方法

| 名称 | 它是什么 | 部署时检查什么 |
| --- | --- | --- |
| safetensors | 张量存储格式 | config、分片索引、tokenizer 是否齐全 |
| GGUF | 张量和元数据容器 | 架构、张量类型、框架版本是否支持 |
| BF16、FP16、FP8、INT8、INT4 | 数值表示或位宽描述 | 设备和 kernel 是否真正支持该路径 |
| GPTQ、AWQ | 量化方法 | 量化配置、分组、布局、执行后端 |
| Q4_K_M | GGUF 中常用的一种量化方案标记 | 实际混合张量类型、质量和速度 |
| ONNX / OpenVINO IR / engine | 图或部署制品 | 算子集、动态形状、运行时和目标设备 |

**W4A16** 通常描述权重 4bit、激活 16bit。它没有说明所有计算都会以 4bit 执行，也没有说明 KV Cache 是什么精度。

权重量化、KV 量化和激活精度应分开记录。DGX Spark 笔记同时使用 FP8 权重模型与 `--kv-cache-dtype fp8`，不能把两者合称一个“FP8 开关”。

## 3. 已有实例：用 aria2 下载固定 GGUF

在一个有足够空间的 Linux 实验目录执行。此处只下载与校验，不启动 GPU 推理。

```bash
mkdir -p models
MODEL_URL='https://www.modelscope.cn/models/Abiray/Qwen3.8-27B-Q4_K_M-GGUF/resolve/master/Qwen3.8-27B-Q4_K_M.gguf'
aria2c -x 8 -s 8 -k 1M -c --file-allocation=none \
  -d models -o Qwen3.8-27B-Q4_K_M.gguf "$MODEL_URL"
```

| 参数 | 作用 |
| --- | --- |
| `-x 8` | 每个服务器最多 8 条连接 |
| `-s 8` | 下载分成 8 段 |
| `-c` | 在服务端支持时继续未完成下载 |
| `--file-allocation=none` | 不提前分配完整文件空间 |

连接数更高不一定更快。限速、限流、磁盘速度和网络链路都可能成为限制。下载失败时先看 HTTP 状态与剩余空间。

下载结束后核验：

```bash
stat -c '%n %s bytes' models/Qwen3.8-27B-Q4_K_M.gguf
printf '%s  %s\n' \
  '6a96cc760fc65cc6b9ea7f1922e3ff8b2a48c09f209456f23bbae9ef7032c867' \
  'models/Qwen3.8-27B-Q4_K_M.gguf' | sha256sum -c -
```

**已有记录：** 文件大小 `16,810,714,400` 字节，SHA256 如上。大小约为 16.81GB，换算约 15.66GiB。下载地址中的 `master` 可变，因此必须核对哈希。哈希一致说明文件身份一致，不单独证明来源可信或许可证允许分发。

## 4. 使用 safetensors 模型时，先查 config

以下示例在模型已下载到 `/srv/models/example-model` 后执行。路径是公开占位路径，按本机实际位置修改。

```bash
python3 - <<'PY'
import json
from pathlib import Path
p = Path('/srv/models/example-model')
cfg = json.loads((p / 'config.json').read_text(encoding='utf-8'))
for key in ('model_type', 'architectures', 'torch_dtype', 'dtype',
            'hidden_size', 'num_hidden_layers', 'num_attention_heads',
            'num_key_value_heads', 'quantization_config'):
    print(key, ':', cfg.get(key, '未提供'))
index = p / 'model.safetensors.index.json'
if index.exists():
    meta = json.loads(index.read_text(encoding='utf-8'))
    shards = sorted(set(meta['weight_map'].values()))
    missing = [name for name in shards if not (p / name).is_file()]
    print('shards:', len(shards), 'missing:', missing)
    assert not missing, '模型分片不完整'
PY
```

部分模型的语言配置在 `text_config` 等子结构中，需要按实际架构读取。这里列出的字段不能代表所有模型。

**检查方法：** 确认模型架构在目标框架支持范围内；量化配置和下载制品一致；所有分片存在；tokenizer 和模板齐全。下一步再实际加载。

## 5. 什么时候需要自行转换与量化

优先使用来源明确、版本兼容的现成制品。自行转换适用于已有合法源权重、目标框架只接收另一种格式，或确实需要比较不同量化档位的情况。

以支持的 Hugging Face 文本模型转 GGUF 为例，流程是：

```text
完整源模型 → 固定版本转换工具 → 高精度 GGUF
 → 量化工具生成候选 → 加载验证 → 固定任务质量回归 → 性能测量
```

下面是 llama.cpp 的命令结构，**需要先安装该源码版本对应的转换依赖，并确认架构支持**。不是本轮新做的转换实验。

```bash
python3 convert_hf_to_gguf.py /srv/models/source-model \
  --outfile /srv/models/model-f16.gguf --outtype f16
./build/bin/llama-quantize \
  /srv/models/model-f16.gguf /srv/models/model-q4_k_m.gguf Q4_K_M
```

转换前检查源码版本的 `--help` 和依赖。不要把依赖环境不同的转换脚本、量化二进制和旧模型元数据随意拼接。需要重要性矩阵或校准数据的方案，还应保存数据来源与参数。

## 6. 量化后的质量怎么检查

建立一份固定输入，至少覆盖当前应用真正需要的能力。部署问答可包含中文解释、多轮指代、JSON 结构输出和超出知识范围时的处理。

| 检查 | 示例 | 如何判断 |
| --- | --- | --- |
| 基本输出 | 要求用三点解释“模型能加载但并发失败”的原因 | 内容非空，格式正确，没有循环输出 |
| 结构输出 | 要求输出包含 `status`、`checks` 的 JSON | 用 JSON 解析器和字段规则检查 |
| 多轮 | 第一轮定义设备，第二轮追问“它能放下吗” | 引用前文正确，没有丢失设备条件 |
| 任务质量 | 用公开说明书或自制标准题逐题验收 | 对照预先写好的评分规则 |
| 长输入 | 输入接近业务长度上界 | 没有模板截断和位置相关异常 |

同一输入应使用相同模板、采样参数和输出上限。输出被 `length` 截断时，先补足上限再评质量。不能把截断造成的不完整全部归因于量化。

## 7. 本章交付与常见失败

| 现象 | 先查什么 |
| --- | --- |
| `unknown model architecture` | 框架版本与模型架构支持 |
| 找不到 tensor / shape 不匹配 | 分片、转换来源、配置是否对应同一 revision |
| 文件大致正确但加载失败 | 下载完整性、哈希、格式版本 |
| 能回答但角色混乱 | tokenizer、聊天模板、特殊 token |
| Q4 比高精度慢 | 量化 kernel、回退路径、批量和硬件，不能只比较文件大小 |

**本章交付：** 模型来源、文件清单、校验值、模板与量化配置、固定质量样例。下一步计算[内存预算](04-memory-and-kv-cache.md)。
