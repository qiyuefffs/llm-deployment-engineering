# 12 打包、启停、监控与交付

[总目录](README.md) · [上一章](11-parallel-and-scaling.md) · [下一章：术语与资料](13-glossary-and-references.md)

**本章目标：** 让接手的人在目标设备上找到正确文件，启动正确模型，判断是否可用，遇到问题能够停止和回退。

## 1. 一份完整交付至少包含七项

| 材料 | 至少包含什么 | 接手人怎样检查 |
| --- | --- | --- |
| 环境记录 | 系统、设备、驱动、工具链、运行时、精确依赖 | 与现场环境比较 |
| 模型清单 | 来源、revision/哈希、模板、精度、许可证 | 文件和分片校验 |
| 引擎制品 | 源码 commit、构建参数、运行库或镜像 digest | 版本检查，最小设备运行 |
| 参数配置 | 模型路径、别名、端口、上下文、并发、缓存 | 对照实际启动日志 |
| 启停说明 | 启动、就绪、停止、重启、日志位置 | 从停止状态重建服务 |
| 验收材料 | 输入、质量规则、功能、性能、异常、稳定性 | 独立复查并重新执行 |
| 限制与恢复 | 不支持的功能、已知故障、上一版本 | 失败时有明确处理路径 |

主线是“制品 → 配置 → 运行 → 证据”。一条启动命令不能代替这些材料。

## 2. 把运行包与实验数据分开管理

```text
release/
├── README.md
├── environment/          环境和依赖记录
├── manifest/             引擎、模型、模板身份
├── bin/                  可分发的程序与必要运行库
├── config/               不含凭据的参数
├── inputs/               公开验收输入
├── operations/           启停、恢复、监控说明
└── validation/           验收规则与结果索引
```

大权重通过合规模型托管或其他受控存储分发，清单里记录来源和校验值。不要用“我机器上的目录存在”当作外部可访问下载。

代码、配置模板、公开输入与脱敏报告可以放 GitHub。原始私有日志、完整环境变量、私人 FlowUs 目录和签名附件地址不放进仓库。

## 3. 固定版本后，还要做一次干净复建

Python 项目先保存可公开的依赖记录；源码项目保存 commit、子模块、编译器与 CMake 参数；容器保存镜像 digest。

```bash
python --version
python -m pip check
python -m pip freeze > environment/requirements.lock.txt
git rev-parse HEAD > environment/source-commit.txt
git submodule status > environment/submodules.txt
```

上面假定当前目录是对应源码仓库，且 `environment/` 已存在。`pip freeze` 中可能包含本地路径或私有下载 URL，分享前审查；它也不保证能跨系统、跨设备安装。

干净复建至少执行：准备环境 → 获取固定模型 → 构建或安装 → 功能检查 → 小负载 → 目标负载 → 停止与恢复。重建成功日志要单独保存，不能沿用旧失败日志。

A10 Case 当前缺少第二个全新实例的完整重建记录，所以仍保留这一限制，不因已有健康截图就改写成完全可复现已验收。

## 4. FlowUs 的“Conda 打包”其实包含两种工作

原笔记以 Conda 建环境，然后用 PyInstaller 生成 `LLM-Tool`。需要区分：

| 方式 | 主要交付什么 | 不自动解决什么 |
| --- | --- | --- |
| Conda 环境导出/迁移 | Python 及依赖环境描述或包 | 宿主驱动、系统 ABI、GPU 支持 |
| PyInstaller | Python 应用可执行文件或目录 | 模型权重、外部引擎、驱动和所有原生依赖 |
| 容器 | 用户态文件系统与运行环境 | 宿主设备、内核和所需驱动 |
| 原生引擎包 | llama-server 等二进制与库 | 所有芯片和系统都通用 |

已有 Python 客户端工程的打包结构示例：

```bash
python -m PyInstaller --onedir --name local-llm-client app.py
```

前提是自己的工程存在 `app.py`，已安装匹配版本 PyInstaller。仓库没有假装提供这个客户端。若使用 `.spec`，把名称、数据文件、动态库和 hidden imports 写进 spec，再执行该 spec；不要混用互相覆盖的命令行设置。

打包后要在另一台目标环境检查：程序能启动、引擎路径正确、模型可找到、API 可连、取消和退出可用。GUI 不显示控制台时，仍需可查的日志文件。

## 5. 就绪检查要有超时

进程存在、端口开放、模型就绪、业务正确，是四个检查点。下面针对已经启动的 llama-server，最多等待约 60 秒；实际大型模型的时限按冷启动记录设置。

```python
import json
import time
from urllib.error import HTTPError, URLError
from urllib.request import urlopen

ready = False
deadline = time.monotonic() + 60
while time.monotonic() < deadline:
    try:
        remaining = max(0.1, deadline - time.monotonic())
        with urlopen('http://127.0.0.1:8000/health', timeout=min(3, remaining)) as r:
            ready = r.status == 200 and json.load(r).get('status') == 'ok'
    except (HTTPError, URLError, TimeoutError, OSError, ValueError):
        ready = False
    if ready:
        break
    time.sleep(min(1, max(0, deadline - time.monotonic())))
if not ready:
    raise SystemExit('就绪超时：检查服务进程、模型加载和日志')
print('模型就绪；下一步执行功能样例')
```

就绪后仍要验证实际模型与功能。服务端模型别名正确，不能代替模型文件身份检查。

## 6. 常驻 Linux 服务的管理模板

Notebook 未必有 systemd。下面用于管理员已经准备好用户、目录、权限、二进制和运行库的 Linux 主机；不是要求在当前电脑执行系统改动。

```ini
[Unit]
Description=Local LLM service
After=network.target

[Service]
Type=simple
User=llm
WorkingDirectory=/opt/local-llm
ExecStart=/opt/local-llm/bin/llama-server -m /srv/models/model.gguf --alias local-model --host 127.0.0.1 --port 8000 -c 4096 -np 1 -ngl 99
Restart=on-failure
RestartSec=5
TimeoutStopSec=30
KillSignal=SIGINT

[Install]
WantedBy=multi-user.target
```

先以同一账号前台运行，功能通过后再注册服务。启动器中的环境变量不会自动继承交互式终端配置，需要明确给出运行库和可写缓存路径。

停止与切换时，先停止接收新任务，再等待或取消已有请求，确认设备资源释放。只针对当前服务操作，不用全局杀进程命令处理所有模型。

## 7. 监控要能回答用户为什么变慢

| 观察层 | 记录项 | 能解释什么 |
| --- | --- | --- |
| 用户任务 | 首个可见答案、任务完成、失败 | 真实使用体验 |
| 服务请求 | 排队、TTFT、完成耗时、实际 token、错误 | 长等待和容量问题 |
| 引擎 | 活跃序列、KV、抢占、缓存、实际后端 | 调度与内存问题 |
| 设备 | 主机/设备内存、交换、频率、温度、功率 | 资源压力和端侧降频 |

同一个 run ID 将配置、请求和设备采样关联起来。查看指标端点时保存具体版本的指标名称，不把别的版本教程中的名称直接当成当前事实。

告警与目标绑定：错误率上升、队列持续积压、尾延迟过线、内存增长或热稳定速度下降。空闲时 GPU 利用率低，不需要当作性能故障。

## 8. 发布与回滚怎样验收

把“模型 + tokenizer/模板 + 引擎 + 配置”作为同一发布版本。模板更改也会影响 token 数、输出和缓存，应做回归。

发布前先在候选配置完成固定样例和目标负载，再切换入口。保留上一个可用版本的清单与文件，不把可变 `master/latest` 下载地址当成回滚备份。

回滚后重新检查：正确模型、功能、异常处理、目标负载和资源释放。端侧应用还要测断网、磁盘不足、模型损坏、升级中断、休眠恢复和用户取消。

## 9. 知识库按工程记录维护

每次项目只需持续补齐这条记录：

```text
设备与限制 → 选型理由 → 最小运行 → 基线
 → 失败或瓶颈 → 对照实验 → 验收 → 剩余限制
```

有完整记录的内容写“已测试”；只有命令或原理整理的写“参考步骤/待验证”。一篇笔记后续出现反例，要更新结论并保留版本条件。

**本章交付：** 七项材料、启停与恢复说明、监控口径、一次干净复建记录。可直接从[适配记录](templates/adaptation-record.md)、[实验记录](templates/experiment-record.md)和[部署复盘模板](../../templates/deployment-review.md)开始。
