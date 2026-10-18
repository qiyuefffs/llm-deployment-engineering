# 第2层：模型格式与量化层

[总目录](../SUMMARY.md) · [GGUF完整流程](../chapters/models/gguf-conversion.md) · [量化与AWQ四组](../chapters/models/quantization.md)

## 2.1 这一层解决什么问题？

| 问题 | 检查对象 | 输出 |
| --- | --- | --- |
| 放不下 | 权重大小、KV/状态、工作区、卸载位置 | 精度/量化/并行与内存预算 |
| 不能加载 | 架构、张量名称与类型、分片、转换器 | 支持该引擎的完整制品 |
| 量化后慢 | 实际kernel、group/layout、反量化、batch | 后端性能与质量对照 |
| 答案变化 | 权重误差、模板、tokenizer、采样、输出预算 | 固定题集的差异与采用结论 |
| VLM缺功能 | processor、视觉encoder、投影与输入协议 | 单独功能范围和完整材料 |

模型身份至少是`仓库＋revision＋文件清单＋量化配置＋模板＋工具版本`。磁盘目录名和“4bit”标签不足以确定制品。

## 2.2 模型格式体系

```text
模型制品
├── Hugging Face目录：safetensors/bin＋config＋tokenizer＋template
├── GGUF：张量与模型元数据容器，可包含F16/BF16或量化张量
├── ONNX：计算图及内嵌/外部权重
├── OpenVINO IR：XML/BIN及GenAI、tokenizer/processor配置
├── TensorRT / TensorRT-LLM：对应版本的检查点/执行制品
└── 平台专用图、运行包与编译缓存
```

| 文件 | 工程职责 | 失败表现 |
| --- | --- | --- |
| config.json | 架构、层数、维度、RoPE/MoE等 | unknown model、shape错误 |
| *.safetensors＋索引 | 张量内容及张量到分片文件映射 | missing tensor/shard、大小不符 |
| tokenizer* | 文本编码、特殊token、解码 | token数异常、乱码或停止不正确 |
| chat_template.jinja | 角色、历史、工具、思考与生成起点 | 角色标记、只思考、工具解析失败 |
| generation_config.json | 默认采样与停止策略 | 与显式参数叠加导致实验不一致 |
| processor/preprocessor | 图像/音频预处理 | 文本成功但多模态失败 |
| quantization_config | 方法、位宽、分组、模块排除 | kernel/布局不支持或误加载 |

分片索引不决定GPU切分；多分片也可加载到一张GPU。转换和量化生成新制品，须保存源身份、工具commit、命令、日志和输出摘要。

```python
import json
from pathlib import Path
p = Path('/srv/models/example-model')
cfg = json.loads((p/'config.json').read_text(encoding='utf-8'))
print(cfg.get('model_type'), cfg.get('architectures'))
idx = p/'model.safetensors.index.json'
if idx.exists():
    shards = set(json.loads(idx.read_text(encoding='utf-8'))['weight_map'].values())
    assert all((p/s).is_file() for s in shards)
```

该代码只检查分片存在，不验证内容正确；下载摘要仍需独立核验。

## 2.3 量化体系

```text
数值表示：FP16/BF16、FP8、INT8/INT4、MXFP4/NVFP4等
量化对象：权重W、激活A、KV/循环状态分别记录
量化方法：AWQ、GPTQ、工具支持的动态/静态/在线方案
存储布局：分组、scale/zero-point、pack、混合精度、排除模块
执行实现：设备原生低精度kernel或反量化/转换路径
```

| 术语 | 具体含义 | 不能据此推断 |
| --- | --- | --- |
| W4A16 | 主要权重4bit、激活16bit的路线 | KV也4bit、所有层都4bit |
| AWQ/GPTQ | 权重量化方法与相应制品 | 所有设备使用同一kernel |
| Q4_K_M | GGUF K-quant混合方案 | K代表k-means、恰好4BPW |
| FP8 | 需区分具体格式与scale | 任何GPU均有原生FP8矩阵指令 |
| KV量化 | 历史状态低精度存储 | 权重变小、长上下文无质量损失 |
| 在线量化 | 加载/运行过程中转换的路线 | 无校准成本、与离线文件等价 |

128个4bit权重的数据区为64字节；若额外有2字节scale就是至少66字节，还不含zero、对齐与敏感层。容量估算不能只乘0.5字节。低精度源转存F16不会恢复已经丢失的信息。

## 2.4 常见格式解释

| 候选 | 适用检查 | 性能与质量风险 |
| --- | --- | --- |
| FP16/BF16 | 原生支持、权重容量、基线 | 权重带宽与内存较高 |
| FP8 | 硬件代际、format/scale、模型kernel | 软件转换、回退、校准与长文本质量 |
| INT8/INT4 | 方法、group、布局和校准集 | 小文件未必更快，任务可能退化 |
| AWQ/GPTQ | 引擎、模型与设备kernel组合 | 不同制品不能只按位宽归因 |
| GGUF | 转换器/后端认识架构和tensor type | unknown type、缺tensor、辅助模型不配套 |
| IR | 对应设备可编译、tokenizer/GenAI完整 | GPU成功不表示NPU可编译 |
| KV低精度 | 长度/并发下资源和质量对照 | 长程检索、稳定性与后端限制 |

## 2.5 vLLM 与 llama.cpp 的格式选择

| 执行路线 | 制品选择 | 必验项 |
| --- | --- | --- |
| vLLM | 受支持HF架构与FP16/BF16/FP8/AWQ/GPTQ等 | 量化kernel、模板、活动序列、KV与API |
| llama.cpp | 受支持GGUF与必要mmproj/辅助权重 | 张量类型、后端卸载、ctx、完整输出 |
| OpenVINO GenAI | 完整IR和管线配置 | 编译设备、shape、实际生成与输出质量 |
| MLX-LM/VLM | 对应实现支持的MLX制品 | tokenizer、模板、processor、统一内存 |

vLLM部分版本的GGUF支持按实际功能测试，不假设与llama.cpp相同。选择顺序是引擎支持→容量→质量→负载性能，不能先选最小文件再解决所有兼容问题。

## 2.6 格式选择

```text
目标任务与设备 → 引擎支持矩阵 → 原精度基线/候选量化
 → 完整下载与摘要 → 加载/模板 → 固定质量题集
 → 同负载性能/峰值 → 制品采用或回退
```

| 实例 | 具体选择与结果 |
| --- | --- |
| [RTX2060](../engineering/nvidia-rtx2060.md) | GGUF＋CPU/GPU混合，重点总内存和卸载 |
| [8060S](../engineering/amd-8060s.md) | Q4约58token/s与BF16约10token/s，质量与计时缺项明确保留 |
| [GB10 AWQ](../engineering/nvidia-gb10.md) | 26B-A4B/31B四组4/8bit，保留完整延迟；不单凭位宽归因 |
| [Intel IR](../engineering/intel-arc-npu.md) | 固定revision的INT4/INT8；GPU与NPU分别验收 |
| [Mac](../engineering/apple-mlx.md) | GGUF/Metal与MLX制品分路线，视觉不沿用文本结论 |

原操作全文：[HF→GGUF→量化→Ollama](../engineering/gguf-ollama.md)。制品交付包含身份清单、完整文件、转换/量化记录、摘要、功能与质量结果。
