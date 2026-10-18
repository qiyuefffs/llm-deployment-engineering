# 推测解码：验证速度，也验证答案与归因

**完整工程记录：** [GB10关闭/开启MTP、DFlash完整构建与测试原文](../../engineering/nvidia-gb10.md)

[总目录](../../SUMMARY.md) · [性能总章](../../02-capability-layers/04-memory-performance.md) · [实验记录模板](../../templates/experiment-record.md)

## 本章概览

推测解码尝试用较低代价提出多个候选，再由目标模型验证，减少逐步生成的串行成本。能否获益取决于候选质量、接受率、验证开销、设备资源与负载。它不是在所有模型上打开一个开关就会加速。

本章结合FlowUs中MTP开/关和DFlash记录。已有历史吞吐可用于学习怎样分析，但原始请求和质量证据不全，不能补写为本轮已复现的优化成果。

## 1. 先理解一轮中发生什么

普通decode通常每步增加一个目标模型token。推测路线先提出若干候选，再由目标模型验证，接受一段候选，必要时修正并继续。草稿可以来自另一个模型、模型自身的预测头或其他机制。

有效接受的token越多，可能减少目标模型串行轮数；但草稿生成和验证也要计算、存储和调度。如果接受率低、batch较大或额外模型占掉重要资源，整体收益可能很小甚至为负。

不同算法对分布保持、采样和模型结构有具体条件。框架声称支持某机制，不等于当前量化、TP和attention组合都适用；应查固定版本，再运行质量与统计检查。

## 2. MTP 历史结果

作者记录使用同一系列模型、输入512、输出上限256，比较关闭与开启MTP，候选数3。汇总如下：

| 并发 / 请求数 | 关闭吞吐 | 开启吞吐 | 观察变化 |
| --- | --- | --- | --- |
| 1 / 20 | 20.82token/s | 30.14token/s | +44.76% |
| 2 / 40 | 36.87token/s | 48.92token/s | +32.68% |
| 4 / 80 | 49.33token/s | 75.57token/s | +53.19% |

各并发开关之间有配对，但不能只看这张表。c1的平均ITL从46.12ms变为78.27ms，c2的TTFT从352.24ms变为608.22ms。总产出增加并不保证首token和流式间隔改善。

应结合原工具ITL定义、批量接受产生的输出形态、实际token与逐请求时间分析。原记录缺原始逐请求文件、模型revision和质量等价证据，因此这些现象不能被包装成“所有用户都更快”。

## 3. DFlash 的 2.03 倍该怎样写？

历史汇总中吞吐21.52变为43.74token/s，观察比值约2.03。但配置同时改变：上下文32768→8192，活动序列1→8，内存预算0.70→0.85，基线显式eager而另一边未显式设置。

这些变化都可能影响资源、调度与执行，因此适合写“两个部署组合的观察差异”，不能写“DFlash单项带来2.03倍”。承认归因条件不足，能够帮助下一轮设计更清楚的实验。

## 4. 怎样重新做一组可解释的实验？

先固定目标模型和制品、环境、上下文、序列预算、图模式、缓存、请求集和采样。记录不启用推测的A组，启用推测的B组，除了机制所必需的额外参数外保持一致。若框架必须联动调整配置，就明确实验比较的是组合方案。

每组先预热，再多轮运行，并交替顺序以减少温度、缓存和时间漂移。记录候选数、接受率或接受长度、草稿开销、目标模型执行、实际输出与资源。单独增加候选长度时，也要观察额外显存与验证成本。

质量检查使用固定任务集与原始答案。对于理论上应保持分布的实现，仍需验证框架、采样和量化组合；对于不保证相同输出的方案，应按照任务正确率和评分规则比较。不能只因输出更短而把完成时间缩短当作加速。

## 5. 怎样决定保留？

如果目标是本地交互，重点看TTFT、输出流畅度、完整答案与功耗；如果目标是服务容量，重点看满足延迟和质量约束的总产出。接受率、吞吐和尾延迟一起看，才能判断收益是否值得额外模型与维护成本。

保留开关前后的可启动配置和制品身份。出现质量退化、错误率增加或资源不稳定时，能够回到普通decode基线。没有完整对照时，先记为候选方案，避免将历史漂亮数字当作交付标准。

## 六、Gemma MTP：先把服务条件恢复出来

原两篇记录使用GB10和镜像`vllm/vllm-openai:gemma4-0505-cu130`。目标模型为`gemma-4-26B-A4B-it`，MTP路线另加载`gemma-4-26B-A4B-it-assistant`。这属于带辅助制品的实现，不能把“模型内置预测头”和“加载assistant模型”的开销混为一谈。

共用条件为TP1、BF16、ctx8192、seqs4、batched8192、memory0.90、async scheduling，禁用图像/音频输入。以下展示固定镜像内的服务参数，主模型和assistant都需要先准备完整制品：

```bash
vllm serve /srv/models/gemma-4-26B-A4B-it \
  --served-model-name gemma4-mtp --host 127.0.0.1 --port 8015 \
  --tensor-parallel-size 1 --dtype bfloat16 \
  --max-model-len 8192 --max-num-seqs 4 \
  --max-num-batched-tokens 8192 --gpu-memory-utilization 0.90 \
  --limit-mm-per-prompt '{"image":0,"audio":0}' \
  --async-scheduling \
  --speculative-config '{"model":"/srv/models/gemma-4-26B-A4B-it-assistant","num_speculative_tokens":3,"draft_tensor_parallel_size":1}'
```

对照服务使用相同主要参数，删除speculative-config，改为8016端口与`gemma4-base`别名。按顺序测试两个服务以减少资源竞争；若制品确需远程代码，先审阅并固定来源再启用相应选项。

### 6.1 原负载与运行顺序

输入目标512、输出256，c1/c2/c4分别20/40/80请求。每个并发档位的开/关组请求数相同，三档之间请求数不同。新复测建议同样本量、多轮并交替开关顺序，原表仍按当时条件保存。

```bash
vllm bench serve \
  --backend openai-chat --base-url http://127.0.0.1:8015 \
  --endpoint /v1/chat/completions --model gemma4-mtp \
  --tokenizer /srv/models/gemma-4-26B-A4B-it \
  --dataset-name random --random-input-len 512 --random-output-len 256 \
  --num-prompts 20 --max-concurrency 1 \
  --save-result --save-detailed --result-dir results/mtp/c1
```

c2改40请求/并发2，c4改80请求/并发4；baseline使用8016与对应模型名。还要保存随机seed、采样、思考、warmup和缓存状态，避免两组只有目标长度相同而实际输入不一致。

## 七、MTP的完整结果：吞吐、等待与流式一起看

| 指标 | c1关闭 | c1开启 | c2关闭 | c2开启 | c4关闭 | c4开启 |
| --- | --- | --- | --- | --- | --- | --- |
| 请求数 | 20 | 20 | 40 | 40 | 80 | 80 |
| 总输出token | 5120 | 5120 | 10240 | 10240 | 20480 | 20480 |
| 时间s | 245.92 | 169.88 | 277.70 | 209.31 | 415.19 | 271.00 |
| 输出token/s | 20.82 | 30.14 | 36.87 | 48.92 | 49.33 | 75.57 |
| 平均TTFT ms | 488.14 | 462.90 | 352.24 | 608.22 | 562.37 | 596.33 |
| 平均TPOT ms | 46.30 | 31.49 | 53.06 | 38.38 | 79.19 | 50.41 |
| 平均ITL ms | 46.12 | 78.27 | 52.85 | 99.52 | 78.88 | 131.48 |
| 接受率% | — | 38.07 | — | 40.77 | — | 41.16 |

吞吐在三档都提高，但TTFT没有统一改善，ITL报告值变大。推测路线可能一次验证并输出一段token，事件打包方式会影响客户端间隔。因此“平均每输出token所需总时间”与“连续流事件之间的等待”可能呈现不同趋势。

要判断用户是否更舒服，需要原始SSE时间、每事件token和页面显示策略。只从聚合表无法确认输出是否均匀，也不能把ITL变大解释成目标模型一定变慢。

### 7.1 接受率的计数要检查分母

c1记录为2032次draft、8128个draft token、3094个accepted token，接受率约38.07%；报告acceptance length2.52。配置候选数3，而工具分位置统计出现0—3共四个位置，说明工具内部计数可能包含额外位置/验证行为，不能自行用“配置3”改写报告。

接受率和平均接受长度不是同一个比例。需要同时保存drafts、draft tokens、accepted tokens、每位置接受率及工具定义。仅凭接受率40%，无法算出吞吐一定提升多少，因为提出候选、目标验证、回退和输出搬运也消耗时间。

原报告peak output throughput与配置并发有不一致字段，这些峰值未参与本体系推荐。对可核算的总输出/总时间保留比较，对无法解释的字段保留问题，避免选择看起来最好的一列。

## 八、DFlash：GB10源码与执行路径

这一份记录的环境不同于前面的Qwen FP8服务：vLLM commit`2cc008e7b`，CUDA13.0.88，PyTorch2.11.0+cu130，Python3.12.13，20核ARM CPU，约119GiB统一内存。目标为Qwen3.6-35B-A3B BF16与配套DFlash drafter。

### 8.1 构建前保存哪些条件

先记录CPU架构、device capability、PyTorch构建、CUDA_HOME、nvcc/ptxas、源码commit与改动。原环境采用`TORCH_CUDA_ARCH_LIST=12.1a`和指定ptxas；该值与此前17d87168d中的12.0绕过不属于同一构建，不能合并成一套固定建议。

原流程使用仓库`use_existing_torch.py`保持已有torch构建，随后`--no-build-isolation`编译。这样做要求主动准备和记录全部构建依赖；它不会自动保证ABI正确。修改requirements以适应ARM64/FlashInfer时，保存diff，并核对最终实际安装。

```bash
git rev-parse HEAD
python -m pip freeze > build-packages.txt
python - <<'PY'
import torch
print(torch.__version__, torch.version.cuda)
print(torch.cuda.get_device_name(0), torch.cuda.get_device_capability(0))
import vllm
from vllm.v1.spec_decode.dflash import DFlashProposer
print(vllm.__version__, DFlashProposer.__name__)
PY
```

模块可导入是第一道检查，首次服务生成还可能触发JIT、attention或CUDA Graph路径。原遇到过`linear_attention not supported by flash_attn`，处理方向是确认混合层的后端选择，不能为所有层强制一个不支持的实现。

### 8.2 启动与确认机制生效

原高吞吐配置如下，路径、监听与日志整理为公开形式：

```bash
vllm serve /srv/models/Qwen3.6-35B-A3B \
  --host 127.0.0.1 --port 18000 \
  --served-model-name qwen36-dflash --dtype bfloat16 \
  --max-model-len 8192 --max-num-seqs 8 \
  --gpu-memory-utilization 0.85 \
  --speculative-config '{"method":"dflash","model":"/srv/models/Qwen3.6-35B-A3B-DFlash","num_speculative_tokens":5}'
```

drafter如果通过auto_map加载代码，应按固定仓库审阅后启用相应远程代码选项。启动先完成短题，确认日志/指标中DFlash、draft与acceptance实际出现，再压测。命令写了speculative-config不等于运行中一定命中期望机制。

## 九、DFlash完整对照与下一轮实验

原负载为spec_bench、50请求、并发1、seed42、输出256，实际输入13655、输出12800。两个部署组合的结果如下：

| 指标 | 普通decode组合 | DFlash组合 |
| --- | --- | --- |
| ctx / seqs | 32768 / 1 | 8192 / 8 |
| 内存预算 | 0.70 | 0.85 |
| eager | 显式开启 | 未显式设置 |
| 时间s | 594.69 | 292.62 |
| 输出token/s | 21.52 | 43.74 |
| TTFT mean / median ms | 893.20 / 213.45 | 294.13 / 261.00 |
| TTFT P99 ms | 16024.24 | 571.91 |
| TPOT mean / P99 ms | 43.14 / 43.34 | 21.80 / 29.03 |
| ITL mean / P99 ms | 42.97 / 53.15 | 72.82 / 87.71 |
| 接受率 / 接受长度 | — | 48.15% / 3.41 |

基线TTFT均值比中位数大很多，P99达16秒，提示存在慢请求。缺原始时序无法判断是编译、缓存、排队还是其他原因。不能把全部TTFT变化直接归因于DFlash。

下一轮可以拆成四组：A普通decode＋固定预算；B仅增加DFlash；C普通decode＋调整后预算；D DFlash＋调整后预算。A/B看机制变化，A/C看服务配置变化，C/D再看新预算下机制收益。若某组合不被该版本支持，就明确说明无法形成完整单变量对照。

候选数也应从小到大单独扫。后面位置接受率下降时，增加草稿长度会产生更多无效计算；观察接受长度、内存、目标验证时间和最终Goodput，再决定是否增加。原文中的预期倍数不作为实测结果填入表中。

## 十、怎样写一份能复查的推测解码结论

结论先说明设备、目标/drafter身份、版本、任务和负载；再列实际输出数、总时间、TTFT、TPOT、流式间隔、接受统计与资源；最后说明质量集、异常和回退。

对于这两份历史记录，可以保留MTP的三组配对观察和DFlash的组合方案差异。要进一步称为可交付优化，需要补原始请求与质量回归。它们已经足够用于学习完整实验方法，不需要通过省略配置差异来增强结论。
