# 完整操作实例：第一个本地推理服务

[知识体系目录](../../SUMMARY.md) · [llama.cpp原理与构建](../../chapters/frameworks/llama-cpp.md) · [性能分析](../../chapters/performance/benchmarking.md)

## 这次练习完成什么？

从空运行目录开始，下载固定版本的llama.cpp与公开GGUF，校验制品，启动本机服务，发送功能与流式请求，采集指标，再停止服务运行引擎基准。每一步都有完整程序和可打开的真实结果。

练习使用小模型，目的是在普通Windows电脑上走完整条工程链路。它不能代表大模型容量，也不要求GPU。2026-10-18已经实际执行，**链路完成，但总验收未通过**：三道功能题通过两道，畸形JSON返回500。下文保留原始失败，不把预期答案写成实际结果。

## 1. 认识目录与环境

```text
practice/first-service/
├── README.md                 本教程
├── manifest.json             固定模型、引擎与服务参数
├── prepare.py                下载、校验与解压
├── run_exercise.py           管理服务、请求、记录与基准
└── results/
    └── 2026-10-18-windows-cpu/  已公开的真实运行记录
```

本次环境为Windows10.0.26200、AMD64、i5-12600KF、16逻辑线程、Python3.13.12；程序限定4线程、`-ngl 0`纯CPU。Python代码仅使用标准库，无需安装PyTorch或CUDA。建议至少8GiB内存、约2GiB空闲磁盘，并确认18080端口空闲；具体CPU指令要求以官方二进制为准。

| 制品 | 固定身份 |
| --- | --- |
| llama.cpp | 官方release b9557，实测提交0f7fada56 |
| Windows压缩包 | llama-b9557-bin-win-cpu-x64.zip |
| 模型 | Qwen/Qwen3-0.6B-GGUF，Q8_0 |
| 模型revision | 23749fefcc72300e3a2ad315e1317431b06b590a |
| 文件 | Qwen3-0.6B-Q8_0.gguf，639446688字节 |
| 服务 | 127.0.0.1:18080，别名book-qwen3-06b |
| 资源参数 | ctx2048、parallel2、线程4、CPU |

固定下载地址与摘要都在[manifest.json](manifest.json)。模型许可证Apache-2.0，引擎项目许可证MIT；权重不存入仓库，按原模型页条款获取。

## 2. 获取仓库，进入正确目录

在PowerShell执行。若已经克隆仓库，从已有目录进入即可：

```powershell
git clone https://github.com/qiyuefffs/llm-serving-diagnosis.git
cd llm-serving-diagnosis
cd docs/01-deployment-foundations/practice/first-service
python --version
```

以下所有命令都在`first-service`目录执行。不要从另一个位置运行后再猜模型在哪里；运行目录、代码目录和模型缓存目录是不同概念。

## 3. 下载并验证模型和引擎

```powershell
python prepare.py --runtime-dir .runtime
```

程序下载固定官方压缩包与GGUF，检查压缩包摘要、模型字节数与SHA256，解压到`.runtime`，保存`download-hashes.json`。重复执行会复用校验通过的文件。网络失败或摘要不一致时停止，不继续启动模型。

本次模型SHA256为：

```text
9465e63a22add5354d9bb4b99e90117043c7124007664907259bd16d043bb031
```

看到`Prepared`后，检查`.runtime/llama-server.exe`、`llama-bench.exe`和模型文件存在。依赖DLL与可执行程序保持在解压目录中；不要只复制一个exe到其他位置。

下载大约0.64GB模型，时间取决于网络。GitHub API限流与release资源失效是不同问题：必要时直接核对[固定release](https://github.com/ggml-org/llama.cpp/releases/tag/b9557)及清单中的资源地址。

## 4. 一条命令完成全流程

```powershell
python run_exercise.py --runtime-dir .runtime --output output/run-01
```

选择空的结果目录。程序拒绝覆盖已有记录，并在启动前检查端口。它只停止自己创建的server子进程；18080被占用时，应先确认并停止自己的旧实例。

程序依次做这些事：

1. 校验模型并记录引擎版本、系统、参数与启动命令。
2. 启动server，等待健康ready，检查模型列表。
3. 发送三道功能题，保存原始请求、答案、usage与判断。
4. 发送畸形JSON，记录状态，并检查服务随后是否健康。
5. c1/c2分别发送四条流式请求，保存正文、TTFT、E2E与汇总。
6. 采集metrics，停止自己的服务，保存脱敏日志。
7. 单独运行三轮pp64/tg32引擎基准，生成总验收文件。

默认退出0表示脚本流程完成，**是否达标请读`acceptance.json`**。希望自动化在验收失败时返回非零，可运行：

```powershell
python run_exercise.py --runtime-dir .runtime --output output/run-strict --strict
```

`--strict`在总验收失败时退出2。网络、加载或程序异常会中断并报错。保护原始结果的目录与端口检查是实跑后补充的操作保护，下面历史性能记录保持原样，没有为这些保护重复生成成绩。

## 5. 手工启动时怎样操作？

想观察启动日志，可以在同一PowerShell前台运行：

```powershell
$modelPath = (Resolve-Path .runtime/Qwen3-0.6B-Q8_0.gguf).Path
$templateArgs = '{"enable_thinking":false}'
& ./.runtime/llama-server.exe -m $modelPath `
  --host 127.0.0.1 --port 18080 --alias book-qwen3-06b `
  -c 2048 -np 2 -t 4 -tb 4 -ngl 0 --metrics `
  --chat-template-kwargs $templateArgs
```

PowerShell7与旧Windows PowerShell的原生命令引号传递可能不同；遇到JSON参数解析错误，优先用上面的Python入口，它按参数数组启动程序。前台服务按Ctrl+C停止后，再运行自动演练，避免端口和资源冲突。

启动日志应识别模型、CPU后端、2048总上下文与两槽位；本版本每槽位1024。实际请求长度要留出输出空间，不能把总2048当作每个槽位的独立预算。

第二个终端可用Python跨版本稳定发送请求：

```powershell
@'
import json, urllib.request
url = 'http://127.0.0.1:18080/v1/chat/completions'
body = {'model':'book-qwen3-06b',
        'messages':[{'role':'user','content':'中国首都是哪座城市？只输出城市名。'}],
        'max_tokens':64, 'temperature':0}
req = urllib.request.Request(url, data=json.dumps(body).encode('utf-8'),
                             headers={'Content-Type':'application/json'})
with urllib.request.urlopen(req, timeout=120) as response:
    print(json.dumps(json.load(response), ensure_ascii=False, indent=2))
'@ | python -X utf8 -
```

旧终端向Python管道传中文时还可能受终端编码影响。自动演练的提示词保存在UTF-8源码中，不依赖手动粘贴或管道编码。

## 6. 真实功能结果

原始输出见[functional.json](results/2026-10-18-windows-cpu/functional.json)：

| 输入 | 验收规则 | 实际正文 | 结果 |
| --- | --- | --- | --- |
| 计算2+2，只输出一个数字 | 严格等于4 | 2 | 失败 |
| 中国首都，只输出城市名 | 严格等于北京 | 北京 | 通过 |
| 只输出指定JSON对象 | 解析后等于对象 | {"ready":true} | 通过 |

算术题错误需要保留，不能换一道容易题让总验收变绿。这个小样本用于检查流程，不提供通用模型准确率。若要选业务模型，应增加代表任务，并与其他模型或原精度基线比较。

畸形输入是单个`{`。原始[invalid-request.json](results/2026-10-18-windows-cpu/invalid-request.json)记录HTTP500和JSON解析错误，之后健康为ok。我们的协议验收期望4xx，因此这项失败；健康恢复单独通过。

## 7. 真实 HTTP 与引擎结果

HTTP性能请求要求列举整数，但输出上限32token，可能截断。它们只用于时间与流式链路，不作为完整列举任务通过。两组各四条，实际总输出各128token：

| 并发 | 成功 | 测试窗口 | 输出吞吐 | 平均TTFT | 平均E2E |
| --- | --- | --- | --- | --- | --- |
| 1 | 4/4 | 2.406964s | 53.18token/s | 131.16ms | 601.56ms |
| 2 | 4/4 | 1.558745s | 82.12token/s | 217.49ms | 778.99ms |

并发2总吞吐增加，但请求平均等待增加。样本量只有4，不报告稳定P99。原始明细见[requests.jsonl](results/2026-10-18-windows-cpu/requests.jsonl)，计算结果见[http-summary.json](results/2026-10-18-windows-cpu/http-summary.json)。

停止server后，三轮引擎结果为pp64 `319.08±17.26token/s`，tg32 `69.88±0.22token/s`，见[engine-benchmark.json](results/2026-10-18-windows-cpu/engine-benchmark.json)。这些数字不包含HTTP排队，不能与HTTP总吞吐直接当成同一种指标。

## 8. 最终到哪里检查？

| 文件 | 检查内容 |
| --- | --- |
| [environment.json](results/2026-10-18-windows-cpu/environment.json) | 系统、版本与本次参数 |
| [server-command.json](results/2026-10-18-windows-cpu/server-command.json) | 实际启动参数，路径已改成公开占位符 |
| [models.json](results/2026-10-18-windows-cpu/models.json) | 实际模型别名 |
| [functional.json](results/2026-10-18-windows-cpu/functional.json) | 功能输入、响应和判断 |
| [invalid-request.json](results/2026-10-18-windows-cpu/invalid-request.json) | 异常状态和健康恢复 |
| [requests.jsonl](results/2026-10-18-windows-cpu/requests.jsonl) | 八条性能请求与计时 |
| [http-summary.json](results/2026-10-18-windows-cpu/http-summary.json) | 分组计数与吞吐 |
| [metrics.txt](results/2026-10-18-windows-cpu/metrics.txt) | 采样时的服务指标 |
| [server.log](results/2026-10-18-windows-cpu/server.log) | 加载、槽位与请求日志 |
| [engine-benchmark.json](results/2026-10-18-windows-cpu/engine-benchmark.json) | 独立引擎测量 |
| [acceptance.json](results/2026-10-18-windows-cpu/acceptance.json) | 最终通过项与失败项 |
| [download-hashes.json](results/2026-10-18-windows-cpu/download-hashes.json) | 下载文件摘要 |

本次结论为`exercise_passed=false`。运行链路、HTTP性能组和引擎基准完成；质量与异常协议有明确失败。不同CPU、指令集、系统负载和热状态会改变速度，复现目标是链路与可对照结果，不是要求小数完全相同。

下一步先查失败原因，再做更完整的质量集和性能实验。通过这次练习，应能独立说明“下载了什么、怎样启动、输入是什么、输出在哪里、为什么还不能交付”，再进入五层框架学习。
