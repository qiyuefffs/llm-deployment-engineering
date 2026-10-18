# KV、缓存与调度：分别解决什么问题

**完整工程记录：** [MLX-VLM APC完整配置与调用原文](../../engineering/apple-mlx.md)

[总目录](../../SUMMARY.md) · [显存与性能总章](../../02-capability-layers/04-memory-performance.md) · [压测](benchmarking.md)

## 本章概览

KV Cache保存历史状态；PagedAttention组织状态；Continuous Batching安排请求；Chunked Prefill划分长输入计算；Prefix Cache复用相同前缀。把这五件事分清，才知道一个开关为什么可能有用、为什么也可能没有收益。

本章参考FlowUs的KV、Prefill与Prefix笔记及GB10服务配置。原笔记将vLLM前缀缓存与RadixAttention混称，本体系按各项目实现区分：RadixAttention是SGLang相关机制的名称，不能直接当作vLLM Prefix Cache的实现说明。

## 1. KV 保存的是什么？

自回归生成每次增加一个token，需要利用历史信息。缓存历史token的Key与Value，可以避免重复计算对应投影；后续attention仍要读取相关状态。因而KV减少重复计算，同时消耗内存和带宽，并不会让长上下文完全免费。

常规全注意力估算可用`2 × 层数 × KV头数 × 头维度 × token数 × 每元素字节`。GQA减少KV头数；滑动窗口、MLA与混合架构需要各自计算。总章[4.3节](../../02-capability-layers/04-memory-performance.md#43-粗略显存估算)给出算例，实际预算还要核对引擎日志。

## 2. PagedAttention 改善内存组织

请求长度不同，生成也会动态增长。按最大长度为每个请求预留连续大块KV，容易浪费容量。块管理将逻辑序列映射到物理块，在请求增长和结束时进行分配与回收，也可支持一定形式的共享。

它改善的是缓存管理，不等于降低每个元素位宽。块粒度、元数据、引用计数和共享仍有成本。观察时看实际KV容量、活动序列、空闲块、抢占与重算，不能只看服务启动用了多少显存。

Flash Attention主要改善attention计算的数据访问与中间存储，两者作用不同。一个服务可以同时采用分页KV与合适的attention kernel。

## 3. Continuous Batching 怎样影响并发？

假设三个请求输出长度分别20、200、50。如果整批等待所有请求完成，短请求结束后部分资源可能空闲。持续批处理在迭代之间让新请求加入、已完成请求退出，通常能改善多请求利用。

但活动序列越多，每轮资源和KV压力也会变化，单请求可能更慢。`max-num-seqs`是活动序列预算，`max-num-batched-tokens`是每轮token预算，客户端并发和到达率属于输入负载。三者一起决定排队与批处理，不能把任何一个数字叫作“真实GPU并发”。

本体系CPU实跑c2相对c1提高HTTP总吞吐，但TTFT和E2E上升。这种结果应按目标延迟判断，而不是只选吞吐最大的一档。

## 4. Chunked Prefill 给长输入分段

长输入的prefill可能占用较多计算与工作区，并干扰已经开始decode的请求。Chunked Prefill按调度预算处理输入块，使prefill与decode有更多交错机会。

它不减少需要读入的全部输入，也不能保证每个请求TTFT下降。块预算小可能改善其他请求的流式间隔，却增加长输入自身的调度轮数；预算大可能更偏向prefill效率。实验应同时看长请求TTFT和短请求ITL/E2E。

设计测试时准备两类公开任务：固定长输入、短输出，以及短输入、较长输出。先分别测试，再按固定比例混合；关闭/开启或调整预算时只改一项，保留请求级记录。

## 5. Prefix Cache 复用相同 token 前缀

多个请求反复包含相同长系统提示或文档时，前缀缓存可以复用已经计算的状态。匹配对象是token序列及实现要求的缓存身份，不是肉眼看起来相似的句子。模板、空白、时间戳或采样前置处理变化，都可能影响可复用部分。

不要在公共前缀前面加入每次变化的编号；这会破坏后续长段的前缀匹配。需要区分请求时，把变化放到稳定长前缀之后，并检查tokenizer得到的序列。

### 一次缓存实验的执行顺序

1. 保存当前模板、tokenizer、缓存开关和资源预算，重启受控测试实例，形成已知初始状态。
2. 发送公共长前缀加问题A，保存首轮时间与命中指标。
3. 发送完全相同公共前缀加问题B、C，观察可复用token、TTFT与资源。
4. 换成不同前缀但长度接近的D、E，作为未命中对照。
5. 调整缓存容量或加入干扰请求，观察挤出后是否需要重算。

首轮与热命中分开报告。若只是同一短句重复一百次，它可以验证机制，但不能代表新文档首次输入的性能。命中率高而总体吞吐不变，也可能因为瓶颈在decode或其他阶段。

## 6. KV 量化与卸载是容量方案

KV量化降低每元素存储，有机会容纳更长历史或更多序列；也可能增加误差和转换开销。K与V类型、后端、attention实现之间有组合限制。应先查固定版本支持，再单独实验长上下文质量。

KV卸载将部分状态放到其他存储层，减少设备常驻压力，但带来搬运与访问延迟。CPU内存、统一内存和磁盘的代价不同，不应都称为“增加显存”。发生频繁swap时，先核对系统实际可用内存与并发预算。

## 7. 优化顺序与复查

先把模型和质量基线固定，再按实际问题选择一项：容量不足看KV预算，长输入干扰看分块调度，重复文档看前缀复用，多请求利用低看批处理。每次保存开关、请求、缓存状态、资源和质量。

作者GB10服务同时启用多个机制并完成200请求，这说明配置整体可运行；没有单变量对照，不能宣称其中某一个机制带来了确定收益。机制解释与实验归因需要分别成立。

## 八、MLX-VLM APC：从配置到冷暖缓存实验

FlowUs中还有一套完整的APC配置。它运行在带相关实现的`mlx_vlm.server`，不是`omlx serve`，模型为Gemma4 26B-A4B/31B MXFP8。原笔记未保存该源码补丁的精确commit，所以读者应先确认当前安装确实支持这些环境变量和cache端点；它们不能自动套到任意上游版本。

### 8.1 按实际作用理解配置

| 参数 | 原值 | 作用与检查 |
| --- | --- | --- |
| APC_ENABLED | 1 | 是否真正启用，以启动日志核对 |
| APC_NUM_BLOCKS | 8192 | 缓存块数量预算 |
| APC_BLOCK_SIZE | 16 | 每块token粒度 |
| APC_DISK_MAX_GB | 26B为80、31B为100 | 磁盘缓存上限，需检查剩余空间 |
| APC_DISK_SHARD_MAX_BLOCKS | 256 | 单磁盘分片块预算 |
| APC_LAYER_MAJOR_MEMORY_MIN_TOKENS | 50000 | 该实现布局策略阈值 |
| APC_HASH | fast | 实现提供的哈希模式，需核对版本和隔离要求 |
| max-kv-size | 65536 | 服务KV相关上限，含义按该版本检查 |
| prefill-step-size | 2048 | 分段处理输入的预算 |
| vision-cache-size | 32 | 视觉缓存项预算，与文本APC分开看 |

8192×16=131072只是按块计算的token槽位预算，不能据此宣称每条请求支持131072上下文。模型窗口、单请求KV设置、活动请求数、块共享和实际内存还会分别限制容量。

以下保留26B路线，路径统一为公开示例。运行前创建专用缓存目录，不与其他服务混用：

```bash
mkdir -p ./cache/gemma26-apc
APC_ENABLED=1 \
APC_NUM_BLOCKS=8192 \
APC_BLOCK_SIZE=16 \
APC_DISK_PATH="$PWD/cache/gemma26-apc" \
APC_DISK_MAX_GB=80 \
APC_DISK_SHARD_MAX_BLOCKS=256 \
APC_LAYER_MAJOR_MEMORY_MIN_TOKENS=50000 \
APC_HASH=fast \
python -m mlx_vlm.server \
  --model /srv/models/gemma-4-26b-a4b-it-mxfp8 \
  --host 127.0.0.1 --port 18082 \
  --max-tokens 2048 --max-kv-size 65536 \
  --prefill-step-size 2048 --vision-cache-size 32 --log-level INFO
```

31B路线使用另一缓存目录、端口18083和100GB磁盘预算。缓存必须与模型和配置对应；共用一个空泛目录不能保证模型身份隔离。

### 8.2 准备真正可复用的长前缀

原笔记使用稳定system提示和两个问题验证接口。为了观察较明显的prefill差异，可以生成公开长文，保持system与长文前缀逐字一致，只在尾部换问题。下面是新的可复查实验输入，不把它标成历史已测结果：

```python
import json
from pathlib import Path

out = Path('requests/apc')
out.mkdir(parents=True, exist_ok=True)
prefix = '\n'.join(
    f'条目{i:03d}：设备部署需要核对模型、版本、内存、接口与验收结果。'
    for i in range(128)
)
questions = {'a': '概括这份材料的主题。', 'b': '提取五项部署检查。'}
for name, question in questions.items():
    body = {
        'model': '/srv/models/gemma-4-26b-a4b-it-mxfp8',
        'messages': [
            {'role': 'system', 'content': '依据所给材料回答，使用简洁中文。'},
            {'role': 'user', 'content': prefix + '\n问题：' + question},
        ],
        'temperature': 0, 'max_tokens': 256, 'stream': True,
    }
    (out / f'{name}.json').write_text(
        json.dumps(body, ensure_ascii=False), encoding='utf-8')
```

模型字段仍以server实际接受的ID为准。128条是输入生成规则，不等于128token；正式报告使用模型tokenizer或服务统计保存实际输入数。把时间戳和run-id插到长文最前面，会让稳定前缀丢失，运行编号应存元数据而非污染输入。

### 8.3 按顺序验证冷、热与隔离

先在自己专用的测试实例检查健康和初始统计；需要空缓存时仅重置这个实例，不影响他人的服务：

```bash
curl --fail-with-body http://127.0.0.1:18082/health
curl --fail-with-body http://127.0.0.1:18082/v1/cache/stats -o cache-before.json
curl --fail-with-body -X POST http://127.0.0.1:18082/v1/cache/reset

curl -N --fail-with-body http://127.0.0.1:18082/v1/chat/completions \
  -H 'Content-Type: application/json' -H 'X-APC-Tenant: book-demo' \
  --data-binary @requests/apc/a.json -o cold-a.sse
curl --fail-with-body http://127.0.0.1:18082/v1/cache/stats -o cache-after-a.json

curl -N --fail-with-body http://127.0.0.1:18082/v1/chat/completions \
  -H 'Content-Type: application/json' -H 'X-APC-Tenant: book-demo' \
  --data-binary @requests/apc/b.json -o warm-b.sse
curl --fail-with-body http://127.0.0.1:18082/v1/cache/stats -o cache-after-b.json
```

`X-APC-Tenant`在这套实现中参与缓存隔离。它是稳定测试标识，不是身份认证凭据。测试时保持同值，再单独换成`book-demo-2`观察隔离，不能为了提高命中率而让真实多用户任意共享状态。

仅保存curl墙钟不足以得到TTFT。完整性能测量应使用支持SSE计时的工具，并记录首正文、总时间、实际token和命中统计。上面的命令主要展示操作顺序与原始证据位置。

### 8.4 一张覆盖关键状态的实验表

| 组别 | 前缀/租户/进程状态 | 核对内容 |
| --- | --- | --- |
| 冷A | 空cache、前缀P、租户T | 初次prefill、写入、TTFT |
| 热B | 前缀P、租户T，只改尾部问题 | 可复用token、命中与TTFT |
| 未命中C | 等长不同前缀Q、租户T | 避免只靠进程预热解释收益 |
| 隔离D | 前缀P、租户U | 租户状态是否隔离 |
| 挤出E | 插入超过预算的其他前缀 | 回收、重算、错误和内存 |
| 磁盘F | 按实现保留cache后重启 | 磁盘恢复成本与首请求行为 |

每组先检查答案，再统计速度。不能为了获得热命中而在a/b之间不小心保持整个问题相同，最后把完整响应复用误当成前缀复用。框架可能缓存不同阶段，日志与统计字段应说明到底复用了什么。

### 8.5 为什么暂时不把APC与KV量化一起开

原MLX-VLM实现开启`--kv-bits`时会跳过APC。这个限制来自该实现，不是所有框架的普遍定律。先建立APC-only与KV-quant-only两条独立配置，检查启动日志，不要把两个开关写上后就宣称同时生效。

如果主要痛点是重复长文TTFT，可优先测APC；如果是长上下文容量，KV量化可能更相关。最终可以保留两套适用负载不同的配置，但要记录质量、缓存行为和资源边界。

## 九、多模态缓存：同一张图不等于全部计算可复用

视觉缓存可能复用图像encoder输出，文本前缀缓存可能复用后续KV，两者的身份和容量不同。图片字节相同但缩放、裁剪、processor版本变化，视觉特征也可能不同；图片相同但放在消息中的位置变化，语言模型状态不一定全部可复用。

原MLX-VLM的vision-cache-size32/64是不同服务配置中的项数预算，不能当成32/64张任意尺寸图片的固定内存。测试应该记录分辨率、切片、视觉token、processor与缓存统计；同图换问题、换图同问题、同图不同尺寸分别做对照。

不要通过高命中短测试掩盖首张新图成本。端侧相册与文档应用可能反复处理同一素材，也可能每次上传新图，二者值得保留各自结果。

## 十、调度参数怎样一步步调

以GB10历史配置为起点：ctx16184、seqs4、batched8192、FP8 KV、prefix和chunked prefill。它是一套完成过200请求突发的组合。要知道瓶颈，应先分别做单请求长输入与单请求长输出，再做混合负载。

第一轮固定所有条件，只改活动序列1/2/4，观察KV、输出吞吐与TTFT。第二轮固定合适的seqs，只改batched预算，观察长输入TTFT、短请求ITL和工作区。第三轮固定负载，单独比较冷/热缓存。所有运行都保存输入和结束原因，质量失败的运行不参与有效吞吐推荐。

如果降低batched预算后短请求更顺畅、长输入首token更慢，可以解释为调度取舍；如果全部都变慢，继续看额外轮次、利用率与软件开销。调参的目标是找到满足任务的工作点，不是让每个参数都达到最大值。
## 2026更新：缓存、调度和状态搬运的边界

当前vLLM V1在支持的配置下默认启用chunked prefill。调度通常先接纳decode，再用剩余`max-num-batched-tokens`放入prefill；预算较小时可能减少流式干扰，较大时可能改善长输入完成速度。先看最终生效配置，避免把默认已开的功能写成新的单项优化。

### 前缀复用不是答案复用

Prefix cache复用相同token前缀对应的模型状态，不跳过后续问题的生成。chat template、system文本、工具定义、图片处理、模型revision与adapter变化，都可能影响身份。将每次不同的时间戳放在最前面，通常会破坏后面的可复用前缀。

缓存命中率必须写分母：请求命中率、匹配token比例和块命中率不能互换。测量冷A、同前缀热B、不同前缀C和容量挤出D；保存实际prefill token、命中统计与TTFT，避免只凭第二次快判断APC成功。

### KV offload什么时候有用

当GPU状态容量限制可并发的长会话时，可以评估CPU内存等外部缓存。但省掉的重算是否值得搬运，要同时看热度、KV字节、主机内存、PCIe/网络和排队时间。只扩容量可能让更多请求排在低效搬运路径上。

持久化KV必须绑定模型、模板、位置编码、dtype、布局与引擎版本，不能把某个框架的状态文件当作通用格式。恢复后用固定输入验收答案与长度，失败应能够重算。

### 新模型的状态不全是普通KV

混合attention与GDN/SSM层可能同时维护窗口KV、压缩状态和循环状态。前缀分叉、推测拒绝、取消及PD传输，需要引擎保存和恢复对应状态；纯attention的缓存策略不能直接套用。

若长输入后性能变化，记录各类buffer与层实现；不是所有模型的状态都随总token等比例增长，也不是所有attention都能换成同一个FlashAttention backend。

**继续阅读：** [当前引擎与模型结构](../frameworks/serving-engines.md) · [PD/KV传输](disaggregated-serving.md) · [权重与KV分组实验](../models/quantization.md)。
