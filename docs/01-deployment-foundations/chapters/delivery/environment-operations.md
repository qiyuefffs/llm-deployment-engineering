# 环境封装、启停与回滚

[总目录](../../SUMMARY.md) · [工程交付总章](../../02-capability-layers/05-engineering-delivery.md) · [接口与监控](api-monitoring.md)

## 本章概览

一套部署只有作者当前终端能运行，还不能方便地交给别人。交付要把环境、制品、配置、启动入口和恢复步骤固定下来。下一次重启、换设备或升级后，仍能判断运行的是哪套组合。

本章依据FlowUs中的Docker Runtime、双卡容器、昇腾镜像和Intel服务记录整理。示例统一采用本机回环地址与公开占位路径；容器和systemd配置是说明模板，不代表本轮执行了系统安装或服务注册。

## 1. 固定五类身份

硬件身份包括型号、CPU架构、内存和设备拓扑；系统身份包括系统、内核、驱动和运行时；框架身份包括源码提交、构建选项、依赖与镜像；模型身份包括仓库、revision、文件摘要、模板和转换；运行身份包括最终命令、参数、输入和结果目录。

只写“CUDA13、最新版vLLM、Qwen量化版”不足以复现。镜像tag也可能移动，正式交付应记录digest。模型别名用于API路由，不能代替模型制品身份。

## 2. 虚拟环境与容器各管什么？

Python虚拟环境隔离Python依赖，适合实验与轻量部署；它不隔离宿主驱动、内核和GPU设备。容器可以封装用户态依赖、文件系统和入口，但仍依赖宿主设备、驱动与容器Runtime配套。

NVIDIA容器使用`--gpus`选择可见设备，不代表对该设备设置硬性显存配额。容器的`--memory`主要约束主机内存，也不能代替框架内存预算。统一内存和专用显存平台的限制要按实际机制确认。

作者昇腾记录中的`vllm-ascend:v0.10.0rc1-310p`是芯片与插件配套组合，不应替换成任意`latest`后仍沿用原测试结论。

## 3. 一个最小容器启动模板

先准备自己的、已经验证的镜像digest，并确认模型目录可读。下面不提供虚构digest，`<verified-digest>`需要替换成实际保存的值：

```bash
docker run --name llm-text-service --rm \
  --gpus '"device=0"' \
  -p 127.0.0.1:8001:8001 \
  -v /srv/models/example-model:/models/example-model:ro \
  <verified-image>@sha256:<verified-digest> \
  --model /models/example-model \
  --served-model-name example-model \
  --host 0.0.0.0 --port 8001 \
  --max-model-len 4096 --max-num-seqs 1 \
  --gpu-memory-utilization 0.80
```

该模板假定镜像入口为vLLM API服务；其他镜像要核对ENTRYPOINT和CMD。容器内绑定所有接口，宿主映射到回环，客户端通过宿主8001访问。模型只读挂载，结果目录需要时另设可写挂载。

先前台运行以查看加载和首次错误，再考虑守护运行与重启策略。保存`docker inspect`中必要的镜像身份、挂载、设备与命令字段；公开副本不包含环境凭据和私人地址。

停止指定实例用`docker stop llm-text-service`。不要使用会影响所有容器或删除整个模型目录的快捷命令。恢复时仍用已验证镜像、模型和配置。

## 4. Linux 前台服务怎样交给 systemd？

先让前台命令和API通过，再写服务配置。以下例子使用已有`llm`用户，二进制与模型已经安装；创建用户和文件权限由目标机器运维流程完成。

```ini
[Unit]
Description=Local llama.cpp text service
After=network.target

[Service]
Type=simple
User=llm
WorkingDirectory=/srv/llm
ExecStart=/srv/llm/bin/llama-server -m /srv/models/model.gguf --alias local-model --host 127.0.0.1 --port 18080 -ngl 0 -c 2048 -np 2 -t 4 --metrics
Restart=on-failure
RestartSec=5
TimeoutStopSec=30

[Install]
WantedBy=multi-user.target
```

把实际配置保存为`/etc/systemd/system/local-llm.service`后，按目标机器权限运行：

```bash
sudo systemctl daemon-reload
sudo systemctl start local-llm.service
systemctl status local-llm.service --no-pager
journalctl -u local-llm.service -n 100 --no-pager
curl --fail-with-body http://127.0.0.1:18080/health
```

进程active不等于模型ready，仍需健康和短请求检查。确认资源与恢复行为后，再决定是否执行`systemctl enable`开机启动。停止用`sudo systemctl stop local-llm.service`，维护时确认没有自动启动造成资源竞争。

作者Intel记录中服务曾按任务需要停止以释放共享内存，但保留enabled状态。这提醒我们同时记录“当前是否运行”和“重启后是否自启”，两者不能混写。

## 5. 升级与回滚按一次变更记录

升级前保存已验证配置、模型清单、环境、功能与性能基线；新版本在独立环境或独立实例验证。不要直接覆盖唯一可用的二进制和依赖。需要相同端口时先安排切换与停止，避免请求误连。

回滚条件提前写清，例如功能错误、异常率上升、尾延迟超标或资源持续增长。回滚步骤应能够恢复旧环境与制品，随后重新做健康、功能和小负载检查。只把配置文件改回去但继续使用新模型或新kernel，不算恢复旧组合。

## 6. 一份启停手册应写到什么程度？

读者应能找到启动入口、环境激活、工作目录、端口与别名、ready标准、日志、停止方法、超时和恢复配置。每一步写预期现象与失败后的检查入口。

首次下载与模型加载不计入稳态推理速度，但要计入部署耗时和冷启动。端侧应用还要说明离线条件、缓存大小、剩余磁盘和共享内存需求；交付包不要夹带多GB权重缓存或私人运行日志。

最后做一次从干净终端开始的演练：激活环境、校验模型、启动、发请求、保存产物、停止，再恢复。能完成这条链，下一位工程师才有可靠起点。
