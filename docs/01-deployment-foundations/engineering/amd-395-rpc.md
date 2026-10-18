# AMD 395五机HIP RPC：GTT修复、构建、分发与Kimi加载

[工程实例索引](README.md) · [知识体系总目录](../SUMMARY.md)

技术标签：`ROCm / HIP / GTT / TTM / RPC / split`

## 环境、拓扑与约束

| 项目 | 配置 |
| --- | --- |
| 节点 | 5台Ryzen AI Max+395 / Radeon8060S，主节点＋4个RPC节点 |
| 软件 | ROCm7.2.1、HIP7.2.53211、Kernel6.17.0-35、llama.cpp b9557-0f7fada56 |
| 容量问题 | dmesg显示GTT120000MiB，但DKMS TTM实际约63215MiB；修复后设备可见约120000MiB |
| 模型 | Kimi-K2.5-Q2；模型revision与各分片需另行固定 |
| 首次预算 | ctx512、batch32、ubatch8、FA off；先验证容量与加载 |

## 完整适配与部署流程

```text
BIOS UMA预算 → /proc/cmdline → amdgpu模块来源 → GTT/TTM
 → 本机HIP枚举 → 同commit编译RPC → 同版本分发
 → 4个RPC进程 → 主机list-devices → 小模型 → Kimi小上下文
 → 内存/连接/进度观察 → llama-server与API → 正式负载
```

GTT/TTM修复涉及驱动模块与重启，先记录模块来源和恢复方式；它只解决可分配内存，不代表五机已获得速度提升。原文有完整排错、DKMS处理与加载过程，保留在下方。

为避免泄露节点，原私有地址替换成`<NODE_IP>`。新运行需明确设置`RPC_NODE_1`到`RPC_NODE_4`，四个值各对应一个节点；不要把所有占位符替换成同一机器。程序版本与依赖库在五机保持一致。

## 加速优化与验收

原tensor-split为`14,21.5,21.5,21.5,21.5`，主机少分配以保留映射、状态与系统空间。先用同模型调整split，检查各节点实际buffer和主机峰值；再增大ctx/batch/ubatch，每次只改变一个主变量。

容量验收与速度验收分开：五机能加载目标模型是容量结果；没有单机同口径基线就不报告多机加速比。记录RPC网络吞吐、加载时间、prefill/decode、API TTFT和失败恢复。下方包含完整部署记录、编译记录和原功能测试脚本；脚本是历史技术材料，不会由文档自动执行。

## 完整技术记录的使用约定

以下直接保留相关FlowUs文章的技术正文、命令、表格、日志、失败和后续实验，不以摘要替代原过程。私人路径、节点、认证与附件地址脱敏；`<NODE_IP>`等占位符需要按当前环境填写。原建议或预测仍是建议或预测。上方执行顺序与技术修订用于解释历史记录中的冲突，历史GPU/NPU实验未在本轮重跑。

## R23 · AMD Strix Halo 395 五机 HIP RPC 串联部署 Kimi-K2.5-Q2 实战文档

本文记录一次 AMD Ryzen AI Max+ 395 / Radeon 8060S 五机串联部署 Kimi-K2.5-Q2 GGUF 的完整适配过程。重点不是只给最终命令，而是把 BIOS、GRUB、ROCm、HIP 编译、RPC 串联、加载时间、内存占用、推理速度 以及真实踩坑全部写清楚，便于后续复现和排障。

> 本文面向内网实验环境。`rpc-server --host 0.0.0.0` 不安全，只能放在可信 局域网或直连网段中，不能暴露到公网。

#### 1. 最终结论

本次五机部署最终成功。Kimi-K2.5-Q2 可以在五台 AMD Strix Halo 395 机器上 通过 HIP 后端和 llama.cpp RPC 正常加载并推理。

最终关键状态：

```text
主机 ROCm0: 120000 MiB total
从机 RPC0: 120000 MiB total
从机 RPC1: 120000 MiB total
从机 RPC2: 120000 MiB total
从机 RPC3: 120000 MiB total
```

Kimi-K2.5-Q2 小上下文验证结果：

```text
Prompt: 19.3 t/s
Generation: 8.2 t/s
```

Qwen3.5-9B 小模型五机 RPC 冒烟测试结果：

```text
Prompt: 40.3 t/s
Generation: 21.3 t/s
```

本次最关键的坑：

```text
从机安装了 amdgpu-dkms 6.16.13 后，虽然 dmesg 显示 120000M GTT，
但 TTM 实际被钳到 66286690304 字节，llama.cpp / HIP 看到的 total
只有 63215 MiB。
```

错误状态示例：

```text
GTT size has been set as 125829120000 but TTM size has been set as 66286690304, this is unusual
ROCm0: AMD Radeon Graphics (63215 MiB, 124xxx MiB free)
```

正确状态示例：

```text
ROCm0: AMD Radeon Graphics (120000 MiB, 124xxx MiB free)
```

最终修复方式：

```text
sudo apt-get remove -y amdgpu-dkms
sudo reboot
```

注意：只移除 `amdgpu-dkms`，不要直接 `autoremove` 清理 `amdgpu-dkms-firmware`，避免把固件一起清掉。

#### 2. 实测硬件和网络拓扑

##### 2.1 机器角色

| 角色 | IP | 用途 |
| --- | --- | --- |
| 主机 | <NODE_IP> | 运行 llama-cli 或 llama-server，本地 GPU 也参与分配 |
| 从机 1 | <NODE_IP> | 运行 rpc-server |
| 从机 2 | <NODE_IP> | 运行 rpc-server |
| 从机 3 | <NODE_IP> | 运行 rpc-server |
| 从机 4 | <NODE_IP> | 运行 rpc-server |

##### 2.2 设备

每台机器：

```text
CPU/APU: AMD Ryzen AI Max+ 395
GPU: AMD Radeon 8060S
GPU target: gfx1151
内存: 128 GB 级别 LPDDR5
```

##### 2.3 网络

本次使用 USB4 / Thunderbolt 直连桥接网段，不是 WiFi。

主机检查：

```text
ip -br addr
```

实测可见：

```text
nm-bridge    <NODE_IP>/24
thunderbolt0 UP
wlp195s0     192.168.5.xxx/24
```

其中 `192.168.1.x` 是五机串联使用的直连网段，`192.168.5.x` 是 WiFi 或其它 上网网段。

验证四台从机连通性：

```text
ping -c 1 -W 2 <NODE_IP>
ping -c 1 -W 2 <NODE_IP>
ping -c 1 -W 2 <NODE_IP>
ping -c 1 -W 2 <NODE_IP>
```

#### 3. BIOS 设置

AMD 官方示例中提到的方向是降低 iGPU 预留显存，把更多系统内存交给 GTT/UMA 使用。实测这批设备 BIOS 中 `iGPU Memory Size` 最低只能设置为 `2GB`， 无法设置到 `512MB`。

本次最终成功配置：

```text
iGPU Memory Size = 2GB
```

重启后 dmesg 中可见：

```text
VRAM: 2048M
2048M of VRAM memory ready
120000M of GTT memory ready
```

结论：

- BIOS 最低只能 `2GB` 时可以使用，不是本次失败根因。

- 只要 Linux/ROCm/HIP 最终能看到 `120000 MiB total`，Kimi 五机加载可以成功。

- 如果 BIOS 可以调到 `512MB`，可以按官方示例设置，但不是这批机器的必要条件。

#### 4. 系统和 ROCm 基线

##### 4.1 操作系统和内核

本次成功环境：

```text
Ubuntu 24.04
Kernel: 6.17.0-35-generic
```

检查命令：

```text
uname -a
```

##### 4.2 ROCm 和 HIP 版本

本次成功环境：

```text
ROCm: 7.2.1
HIP: 7.2.53211-e1a6bc5663
```

检查命令：

```text
/opt/rocm/bin/hipcc --version | head -n 5
dpkg-query -W 'rocm-core' 'hip-runtime-amd' 'hsa-rocr' 2>/dev/null
```

实测输出：

```text
hip-runtime-amd  7.2.53211.70201-81~24.04
hsa-rocr         1.18.0.70201-81~24.04
rocm-core        7.2.1.70201-81~24.04
```

检查 ROCm 设备节点：

```text
ls -l /dev/kfd /dev/dri/renderD*
```

期望：

```text
/dev/kfd 存在
/dev/dri/renderD128 存在
当前用户属于 render/video 相关权限组
```

#### 5. GRUB 和 GTT/TTM 配置

五台机器都需要写入相同的内核参数。

编辑：

```text
sudo nano /etc/default/grub
```

推荐配置：

```text
GRUB_CMDLINE_LINUX_DEFAULT="quiet splash ttm.pages_limit=30720000 ttm.page_pool_size=30720000 amdgpu.gttsize=120000 amdgpu.cwsr_enable=0"
```

更新并重启：

```text
sudo update-grub
sudo reboot
```

重启后检查当前运行参数：

```text
cat /proc/cmdline
```

期望包含：

```text
ttm.pages_limit=30720000
ttm.page_pool_size=30720000
amdgpu.gttsize=120000
amdgpu.cwsr_enable=0
```

检查 dmesg：

```text
sudo dmesg -T | grep -Ei 'VRAM:|GTT memory ready|VRAM memory ready|Detected VRAM|RAM width' | tail -n 20
```

期望：

```text
VRAM: 2048M
2048M of VRAM memory ready
120000M of GTT memory ready
```

##### 5.1 只看 dmesg 不够

这是本次最容易误判的地方。

从机曾经已经显示：

```text
120000M of GTT memory ready
```

但 `llama-cli --list-devices` 仍然是：

```text
ROCm0: AMD Radeon Graphics (63215 MiB, 124xxx MiB free)
```

因此最终判断标准必须是：

```text
cd /srv/llm/xiangmu/llama.cpp/build-hip-rpc-official/bin
env LD_LIBRARY_PATH=. ./llama-cli --list-devices
```

正确输出必须类似：

```text
Available devices:
  ROCm0: AMD Radeon Graphics (120000 MiB, 124xxx MiB free)
```

如果 total 仍然是 `63215 MiB`，Kimi 大模型还是会失败。

#### 6. 关键坑：amdgpu-dkms 导致 TTM 只有 63GB

##### 6.1 故障现象

Kimi 加载失败时出现过：

```text
alloc_tensor_range: failed to allocate RPC0[<NODE_IP>:50053] buffer of size 87013675008
unable to allocate RPC0[<NODE_IP>:50053] buffer
```

`87013675008` 字节约为 `81 GiB`。当从机 HIP total 只有 `63215 MiB` 时， 这个分配必然失败。

当时从机设备显示：

```text
ROCm0: AMD Radeon Graphics (63215 MiB, 124xxx MiB free)
```

##### 6.2 真实原因

从机安装了 `amdgpu-dkms`：

```text
dpkg-query -W 'amdgpu-dkms' 2>/dev/null
```

问题机器输出：

```text
amdgpu-dkms  1:6.16.13.30300100-2303411.24.04
```

从机实际加载的模块路径：

```text
modinfo amdgpu | grep -E 'filename:|version:|srcversion:|vermagic:'
```

错误状态：

```text
filename: /lib/modules/6.17.0-35-generic/updates/dkms/amdgpu.ko.zst
version: 6.16.13
```

dmesg 中还有关键告警：

```text
GTT size has been set as 125829120000 but TTM size has been set as 66286690304, this is unusual
```

`66286690304` 字节约为 `63215 MiB`，正好对应 llama.cpp 看到的错误 total。

##### 6.3 正确状态

主机没有 `amdgpu-dkms`，使用内核自带 amdgpu：

```text
filename: /lib/modules/6.17.0-35-generic/kernel/drivers/gpu/drm/amd/amdgpu/amdgpu.ko.zst
```

主机重启后：

```text
ROCm0: AMD Radeon Graphics (120000 MiB, 119988 MiB free)
```

##### 6.4 修复命令

先模拟确认不会误删 ROCm runtime：

```text
sudo apt-get -s remove amdgpu-dkms
```

期望只显示：

```text
The following packages will be REMOVED:
  amdgpu-dkms
```

实际移除：

```text
sudo apt-get remove -y amdgpu-dkms
sudo reboot
```

重启后确认：

```text
modinfo amdgpu | grep -E 'filename:|version:|srcversion:|vermagic:'
```

正确路径：

```text
filename: /lib/modules/6.17.0-35-generic/kernel/drivers/gpu/drm/amd/amdgpu/amdgpu.ko.zst
```

再次确认：

```text
cd /srv/llm/xiangmu/llama.cpp/build-hip-rpc-official/bin
env LD_LIBRARY_PATH=. ./llama-cli --list-devices
```

正确输出：

```text
ROCm0: AMD Radeon Graphics (120000 MiB, 124xxx MiB free)
```

##### 6.5 不要做的事

不要为了省事直接执行：

```text
sudo apt autoremove
```

因为它可能把 `amdgpu-dkms-firmware` 一起清理掉。实际操作中只移除 `amdgpu-dkms` 就足够。

不要再次通过 `amdgpu-install` 把内核 DKMS 驱动装回去，否则可能回到 `63215 MiB total`。

#### 7. 编译 llama.cpp HIP RPC

##### 7.1 推荐构建目录

本次最终使用：

```text
/srv/llm/xiangmu/llama.cpp/build-hip-rpc-official
```

##### 7.2 CMake 配置

在主机执行：

```text
cd /srv/llm/xiangmu/llama.cpp

cmake -S . -B build-hip-rpc-official \
  -DCMAKE_BUILD_TYPE=Release \
  -DGGML_HIP=ON \
  -DGGML_RPC=ON \
  -DGGML_HIP_ROCWMMA_FATTN=ON \
  -DAMDGPU_TARGETS=gfx1151
```

编译：

```text
cmake --build build-hip-rpc-official --config Release -j"$(nproc)"
```

##### 7.3 编译参数检查

```text
rg -n "GGML_HIP|GGML_RPC|HIP_ROCWMMA|HIP_GRAPHS|HIP_NO_VMM|RPC_RDMA|AMDGPU_TARGETS|GPU_TARGETS" \
  build-hip-rpc-official/CMakeCache.txt
```

本次实测关键项：

```text
AMDGPU_TARGETS:UNINITIALIZED=gfx1151
GGML_HIP:BOOL=ON
GGML_HIP_ROCWMMA_FATTN:BOOL=ON
GGML_RPC:BOOL=ON
GGML_RPC_RDMA:BOOL=ON
```

`GGML_RPC_RDMA=ON` 是因为构建环境发现了 `libibverbs`。本次 USB4 直连走的是 TCP/RPC 路径，RDMA 开关不是 Kimi 能否加载成功的关键。

##### 7.4 验证本机设备

```text
cd /srv/llm/xiangmu/llama.cpp/build-hip-rpc-official/bin
env LD_LIBRARY_PATH=. ./llama-cli --list-devices
```

期望：

```text
Available devices:
  ROCm0: AMD Radeon Graphics (120000 MiB, xxxxxx MiB free)
```

如果提示：

```text
failed to initialize ROCm: no ROCm-capable device is detected
```

优先检查：

```text
ls -l /dev/kfd /dev/dri/renderD*
groups
cat /proc/cmdline
/opt/rocm/bin/rocminfo | grep -i gfx -m 5
```

#### 8. 分发二进制到从机

在主机打包：

```text
cd /srv/llm/xiangmu/llama.cpp
tar -C build-hip-rpc-official -czf /tmp/llama-hip-rpc-official-bin.tgz bin
```

复制到四台从机：

```text
for ip in <NODE_IP> <NODE_IP> <NODE_IP> <NODE_IP>; do
  scp /tmp/llama-hip-rpc-official-bin.tgz "link@${ip}:/tmp/"
done
```

从机解压：

```text
for ip in <NODE_IP> <NODE_IP> <NODE_IP> <NODE_IP>; do
  ssh "link@${ip}" \
    'mkdir -p /srv/llm/xiangmu/llama.cpp/build-hip-rpc-official &&
     cd /srv/llm/xiangmu/llama.cpp/build-hip-rpc-official &&
     tar -xzf /tmp/llama-hip-rpc-official-bin.tgz'
done
```

建议使用 SSH key。不要把真实密码写进脚本或文档。

#### 9. 启动从机 RPC 服务

四台从机都执行：

```text
cd /srv/llm/xiangmu/llama.cpp/build-hip-rpc-official/bin
env LD_LIBRARY_PATH=/srv/llm/xiangmu/llama.cpp/build-hip-rpc-official/bin \
  ./rpc-server -p 50053 -c --host 0.0.0.0
```

后台启动模板：

```text
for ip in <NODE_IP> <NODE_IP> <NODE_IP> <NODE_IP>; do
  ssh "link@${ip}" \
    'pkill -x rpc-server 2>/dev/null || true
     cd /srv/llm/xiangmu/llama.cpp/build-hip-rpc-official/bin
     nohup env LD_LIBRARY_PATH=/srv/llm/xiangmu/llama.cpp/build-hip-rpc-official/bin \
       ./rpc-server -p 50053 -c --host 0.0.0.0 \
       > /tmp/rpc-server-hip.log 2>&1 < /dev/null &
     sleep 2
     pgrep -ax rpc-server
     tail -n 20 /tmp/rpc-server-hip.log'
done
```

正确日志：

```text
ggml_cuda_init: found 1 ROCm devices (Total VRAM: 120000 MiB):
  Device 0: AMD Radeon Graphics, gfx1151 (0x1151), VMM: no, Wave Size: 32, VRAM: 120000 MiB
```

注意：

- `-c` 开启 RPC 本地 cache，有助于大 tensor 后续复用。

- `--host 0.0.0.0` 只允许在可信内网使用。

- 如果 RPC server 日志仍显示 `Total VRAM: 63215 MiB`，不要继续加载 Kimi，先回到 第 6 节修复 `amdgpu-dkms` / TTM。

#### 10. 主机验证五机设备列表

主机执行：

```text
cd /srv/llm/xiangmu/llama.cpp/build-hip-rpc-official/bin

env LD_LIBRARY_PATH=. ./llama-cli \
  --rpc <NODE_IP>:50053,<NODE_IP>:50053,<NODE_IP>:50053,<NODE_IP>:50053 \
  --list-devices
```

本次最终正确输出：

```text
Available devices:
  ROCm0: AMD Radeon Graphics (120000 MiB, 117696 MiB free)
  RPC0: <NODE_IP>:50053 (120000 MiB, 124415 MiB free)
  RPC1: <NODE_IP>:50053 (120000 MiB, 124345 MiB free)
  RPC2: <NODE_IP>:50053 (120000 MiB, 124392 MiB free)
  RPC3: <NODE_IP>:50053 (120000 MiB, 124381 MiB free)
```

必须看到五个设备都是 `120000 MiB` 后，再加载 Kimi。

#### 11. 先用小模型冒烟测试

不要直接上 Kimi。先用小模型确认 HIP/RPC 计算路径正常。

示例模型：

```text
/srv/llm/xiangmu/models/Qwen3.5-9B/Qwen3.5-9B-Q4_K_M.gguf
```

测试命令：

```text
cd /srv/llm/xiangmu/llama.cpp/build-hip-rpc-official/bin

env LD_LIBRARY_PATH=. ./llama-cli \
  -m /srv/llm/xiangmu/models/Qwen3.5-9B/Qwen3.5-9B-Q4_K_M.gguf \
  -ngl 999 \
  --rpc <NODE_IP>:50053,<NODE_IP>:50053,<NODE_IP>:50053,<NODE_IP>:50053 \
  -c 512 -b 64 -ub 16 -fa off \
  --single-turn --simple-io --no-display-prompt \
  -p '你好，请用一句话介绍你自己。' \
  -n 8
```

本次结果：

```text
Prompt: 40.3 t/s
Generation: 21.3 t/s
```

小模型通过后再上 Kimi。

#### 12. Kimi-K2.5-Q2 五机加载命令

模型路径：

```text
/srv/llm/xiangmu/models/Kimi-K2.5-GGUF/Kimi-K2.5-GGUF/UD-Q2_K_XL/Kimi-K2.5-UD-Q2_K_XL-00001-of-00008.gguf
```

模型目录大小约 `350G`，只需要指定第一个分片，llama.cpp 会自动加载其它分片。

##### 12.1 小上下文加载验证

本次成功命令：

```text
cd /srv/llm/xiangmu/llama.cpp/build-hip-rpc-official/bin

env LD_LIBRARY_PATH=. ./llama-cli \
  -m /srv/llm/xiangmu/models/Kimi-K2.5-GGUF/Kimi-K2.5-GGUF/UD-Q2_K_XL/Kimi-K2.5-UD-Q2_K_XL-00001-of-00008.gguf \
  -ngl 999 \
  --split-mode layer \
  --tensor-split 0.143,0.21425,0.21425,0.21425,0.21425 \
  --rpc <NODE_IP>:50053,<NODE_IP>:50053,<NODE_IP>:50053,<NODE_IP>:50053 \
  --no-mmap \
  -c 512 -b 32 -ub 8 -fa off \
  --single-turn --simple-io --no-display-prompt \
  -p '你好，请用一句话介绍你自己。' \
  -n 8
```

参数说明：

| 参数 | 说明 |
| --- | --- |
| -ngl 999 | 尽量把层卸载到 GPU/远端 RPC 设备 |
| --split-mode layer | MoE 大模型使用 layer split，更稳 |
| --tensor-split 0.143,0.21425,0.21425,0.21425,0.21425 | 主机少分配，四台从机多分配 |
| --no-mmap | 大模型建议启用，避免 mmap 引入额外内存压力 |
| -c 512 | 小上下文验证，降低风险 |
| -fa off | 首次加载验证先关闭 FA，确认基础路径可用 |
| -b 32 -ub 8 | 小 batch，降低首次验证内存压力 |

本次结果：

```text
Prompt: 19.3 t/s
Generation: 8.2 t/s
```

##### 12.2 为什么主机 split 少一些

用户诉求是避免主机系统卡死崩溃。主机除了本地 GPU 分配，还负责：

- 读取 350G GGUF 分片。

- 管理 RPC 连接。

- 调度计算图。

- 承担本地系统、桌面、其它任务内存。

因此本次选择：

```text
主机: 0.143
从机 1: 0.21425
从机 2: 0.21425
从机 3: 0.21425
从机 4: 0.21425
```

比例总和：

```text
0.143 + 0.21425 x 4 = 1.0
```

如果主机还有其它任务，可以继续降低主机比例，例如：

```text
0.10,0.225,0.225,0.225,0.225
```

但需要验证每台从机不会超过 `120000 MiB` total。

##### 12.3 后续性能测试命令

小上下文验证通过后，再逐步提高：

```text
cd /srv/llm/xiangmu/llama.cpp/build-hip-rpc-official/bin

env LD_LIBRARY_PATH=. ./llama-cli \
  -m /srv/llm/xiangmu/models/Kimi-K2.5-GGUF/Kimi-K2.5-GGUF/UD-Q2_K_XL/Kimi-K2.5-UD-Q2_K_XL-00001-of-00008.gguf \
  -ngl 999 \
  --split-mode layer \
  --tensor-split 0.143,0.21425,0.21425,0.21425,0.21425 \
  --rpc <NODE_IP>:50053,<NODE_IP>:50053,<NODE_IP>:50053,<NODE_IP>:50053 \
  --no-mmap \
  -c 32768 -b 64 -ub 16 -fa on \
  --single-turn --simple-io --no-display-prompt \
  -p '你好，请用一句话介绍你自己。' \
  -n 64
```

如果出现不稳定，按这个顺序回退：

```text
1. -fa on 改为 -fa off
2. -ub 16 改为 -ub 8
3. -b 64 改为 -b 32
4. -c 32768 改为 -c 4096 或 -c 512
```

#### 13. 加载时间和内存占用实测

Kimi-K2.5-Q2 GGUF 目录约 `350G`。首次加载主要时间消耗在：

```text
1. 主机顺序读取 GGUF 分片。
2. 按 layer split 将权重通过 RPC 发送到从机。
3. 从机在 UMA/GTT 中分配大 tensor。
```

本次小上下文加载大约经历了十几分钟级别。加载期间通过：

```text
cat /proc/<llama-cli-pid>/io
```

观察读盘进度：

| 读盘量 | 粗略进度 | 状态 |
| --- | --- | --- |
| 101GB | 约 29% | 已连接四台 RPC，开始分配 |
| 147GB | 约 42% | .12 基本完成，开始 .13 |
| 174GB | 约 50% | .13 接收中 |
| 236GB | 约 67% | 开始 .14 |
| 306GB | 约 87% | 开始 .64 |
| 358GB | 约 100% | 进入最后初始化和生成 |

加载期间主机内存示例：

```text
Mem: 123Gi total, 81Gi used, 41Gi available
Swap: 0B used
```

加载期间从机内存会先后上升，不是四台同时上升，因为 layer split 会按段依次传输：

```text
.12 先接收
.13 后接收
.14 后接收
.64 最后接收
```

加载完成并退出后，主机内存恢复：

```text
Mem: 123Gi total, 8.6Gi used, 114Gi available
Swap: 0B used
```

四台从机 RPC 服务仍在，内存也恢复到健康状态：

```text
rpc-server running
Mem available: 120Gi 左右
```

#### 14. 常用监控命令

##### 14.1 查主机 Kimi 进程

```text
pgrep -af 'llama-cli|Kimi-K2.5|kimi'
ps -p <pid> -o pid,stat,etime,%cpu,%mem,rss,vsz,nlwp,cmd
cat /proc/<pid>/io
```

##### 14.2 查 RPC 连接

```text
ss -tinp | grep -A1 -E '192\.168\.1\.(12|13|14|64):50053|llama-cli'
```

重点看：

```text
bytes_sent
bytes_acked
rtt
retrans
rwnd_limited
```

加载阶段如果只有一台从机 `bytes_sent` 快速增长，通常是正常的 layer 分段传输。

##### 14.3 查从机内存和服务

```text
for ip in <NODE_IP> <NODE_IP> <NODE_IP> <NODE_IP>; do
  ssh "link@${ip}" \
    'hostname
     free -h
     pgrep -ax rpc-server
     tail -n 20 /tmp/rpc-server-hip.log'
done
```

##### 14.4 查 ROCm/HIP 设备

```text
cd /srv/llm/xiangmu/llama.cpp/build-hip-rpc-official/bin
env LD_LIBRARY_PATH=. ./llama-cli --list-devices
```

带 RPC：

```text
env LD_LIBRARY_PATH=. ./llama-cli \
  --rpc <NODE_IP>:50053,<NODE_IP>:50053,<NODE_IP>:50053,<NODE_IP>:50053 \
  --list-devices
```

#### 15. Vulkan 后端为什么不适合这次 Kimi 五机部署

本次早期使用 Vulkan 后端可以加载模型，但推理时出现极慢或近似卡死，表现为：

```text
Prompt: 0.0 t/s
Generation: 0.0 t/s
```

对比：

- AMD 官方示例使用 HIP 后端和 ROCm。

- 以前八机串联 DeepSeek-V3.1-Q4 在 Vulkan 下可以跑到约 `5 tokens/s`，但这不代表 Kimi-K2.5-Q2 五机 Vulkan 也能稳定。

- Kimi-K2.5-Q2 模型尺寸和 MoE 访问模式不同，五机下对 RPC、UMA/GTT、后端实现更敏感。

本次最终选择 HIP 的原因：

```text
1. HIP 是 AMD 官方教程路径。
2. HIP 下可以直接暴露 ROCm UMA/GTT 设备总量。
3. 修复 amdgpu-dkms 后，HIP total 能达到 120000 MiB。
4. Kimi 已实测成功加载并达到 8.2 t/s generation。
```

结论：当前环境建议使用 HIP 后端，不建议继续用 Vulkan 承担 Kimi-K2.5-Q2 五机主路径。

#### 16. 常见问题和处理

##### 16.1 dmesg 是 120000M，但 llama.cpp 只有 63215 MiB

检查：

```text
sudo dmesg -T | grep -Ei 'GTT size has been set|TTM size'
modinfo amdgpu | grep -E 'filename:|version:'
dpkg-query -W 'amdgpu-dkms' 2>/dev/null
```

如果看到：

```text
/updates/dkms/amdgpu.ko.zst
GTT size has been set as 125829120000 but TTM size has been set as 66286690304
```

处理：

```text
sudo apt-get remove -y amdgpu-dkms
sudo reboot
```

##### 16.2 rpc-server 日志仍然是 Total VRAM 63215 MiB

不要继续跑 Kimi。先修从机：

```text
cat /proc/cmdline
sudo dmesg -T | grep -Ei 'GTT memory ready|TTM size'
modinfo amdgpu | grep -E 'filename:|version:'
cd /srv/llm/xiangmu/llama.cpp/build-hip-rpc-official/bin
env LD_LIBRARY_PATH=. ./llama-cli --list-devices
```

目标是从机本地 `llama-cli --list-devices` 先变成：

```text
ROCm0: AMD Radeon Graphics (120000 MiB, xxxxxx MiB free)
```

##### 16.3 主机崩溃或内存占满

不要盲目开启：

```text
GGML_CUDA_ENABLE_UNIFIED_MEMORY=1
```

之前在 Kimi 大模型上使用这个环境变量导致主机严重内存压力和崩溃风险。

建议：

```text
1. 修复每台机器的 120000 MiB total，不要靠强行 unified memory 绕过。
2. 主机 tensor split 少分配。
3. 首次验证使用 -c 512、-b 32、-ub 8、-fa off。
4. 确认小上下文成功后，再扩大 context 和开启 FA。
```

##### 16.4 加载很慢是不是卡死

不一定。Kimi 目录约 `350G`，首次加载需要把大权重按 layer 发送到远端 RPC。

判断是否在动：

```text
cat /proc/<pid>/io
ss -tinp | grep -A1 -E '192\.168\.1\.(12|13|14|64):50053|llama-cli'
```

如果 `read_bytes` 增长，或者某个 RPC 连接 `bytes_sent` 增长，说明仍在加载。

##### 16.5 SSH 刚重启后 No route to host

从机重启后 USB4/Thunderbolt bridge 重新建链需要时间，短时间出现：

```text
No route to host
```

不一定是失败。先等 10 到 30 秒，再 ping：

```text
ping -c 1 -W 2 <NODE_IP>
```

##### 16.6 `.64` 的 GRUB 参数重复

曾经出现过 `/proc/cmdline` 中参数重复：

```text
ttm.pages_limit=30720000 ... quiet splash ttm.pages_limit=30720000 ...
```

建议清理 `/etc/default/grub`，只在 `GRUB_CMDLINE_LINUX_DEFAULT` 中保留一次， 并保持：

```text
GRUB_CMDLINE_LINUX=""
```

然后：

```text
sudo update-grub
sudo reboot
```

##### 16.7 ROCm 能识别 GPU，但无法加载到 GPU

优先检查：

```text
ls -l /dev/kfd /dev/dri/renderD*
groups
rocminfo | grep -i gfx -m 5
modinfo amdgpu | grep -E 'filename:|version:'
cd /srv/llm/xiangmu/llama.cpp/build-hip-rpc-official/bin
env LD_LIBRARY_PATH=. ./llama-cli --list-devices
```

本次经验：ROCm runtime 版本一致不代表一定可加载大模型，内核 amdgpu 模块路径和 TTM 实际上限也必须正确。

#### 17. 一键检查清单

在每台机器本地执行：

```text
echo '== cmdline =='
cat /proc/cmdline

echo '== amdgpu module =='
modinfo amdgpu | grep -E 'filename:|version:|srcversion:|vermagic:'

echo '== dmesg memory =='
sudo dmesg -T | grep -Ei 'GTT size has been set|VRAM:|GTT memory ready|VRAM memory ready|Detected VRAM|RAM width' | tail -n 30

echo '== rocm packages =='
dpkg-query -W 'rocm-core' 'hip-runtime-amd' 'hsa-rocr' 'amdgpu-dkms' 2>/dev/null || true

echo '== devices =='
cd /srv/llm/xiangmu/llama.cpp/build-hip-rpc-official/bin
env LD_LIBRARY_PATH=. ./llama-cli --list-devices
```

合格标准：

```text
1. cmdline 包含 ttm.pages_limit=30720000 和 amdgpu.gttsize=120000。
2. modinfo amdgpu 指向 kernel/drivers/gpu/drm/amd/amdgpu/amdgpu.ko.zst。
3. dmesg 没有 TTM size 66286690304 告警。
4. amdgpu-dkms 不应处于已安装并生效状态。
5. llama-cli --list-devices 显示 ROCm0 total = 120000 MiB。
```

主机检查 RPC：

```text
cd /srv/llm/xiangmu/llama.cpp/build-hip-rpc-official/bin

env LD_LIBRARY_PATH=. ./llama-cli \
  --rpc <NODE_IP>:50053,<NODE_IP>:50053,<NODE_IP>:50053,<NODE_IP>:50053 \
  --list-devices
```

合格标准：

```text
ROCm0 total = 120000 MiB
RPC0 total = 120000 MiB
RPC1 total = 120000 MiB
RPC2 total = 120000 MiB
RPC3 total = 120000 MiB
```

#### 18. 从零部署顺序

推荐严格按这个顺序执行：

```text
1. BIOS: iGPU Memory Size 设置为最低值，本批设备最低为 2GB。
2. 安装 Ubuntu 24.04 和可用内核，本次成功为 6.17.0-35-generic。
3. 安装 ROCm/HIP runtime，本次成功为 ROCm 7.2.1。
4. 写入 GRUB: ttm.pages_limit=30720000、ttm.page_pool_size=30720000、amdgpu.gttsize=120000、amdgpu.cwsr_enable=0。
5. 重启。
6. 检查 dmesg: 120000M of GTT memory ready。
7. 检查 amdgpu 模块路径，不能是 /updates/dkms/amdgpu.ko.zst。
8. 检查 llama-cli --list-devices，必须是 120000 MiB total。
9. 主机编译 build-hip-rpc-official。
10. 分发 bin 到四台从机。
11. 四台从机启动 rpc-server -p 50053 -c --host 0.0.0.0。
12. 主机 --rpc --list-devices，确认五个设备都是 120000 MiB。
13. 先跑 Qwen 小模型冒烟测试。
14. 再跑 Kimi 小上下文 -c 512、-fa off 验证。
15. 最后扩大 context，开启 -fa on，做正式服务部署。
```

#### 19. 正式服务部署建议

如果要用 `llama-server` 对外提供 OpenAI compatible API，建议先沿用已经验证的 split 和 RPC 参数：

```text
cd /srv/llm/xiangmu/llama.cpp/build-hip-rpc-official/bin

env LD_LIBRARY_PATH=. ./llama-server \
  -m /srv/llm/xiangmu/models/Kimi-K2.5-GGUF/Kimi-K2.5-GGUF/UD-Q2_K_XL/Kimi-K2.5-UD-Q2_K_XL-00001-of-00008.gguf \
  -ngl 999 \
  --split-mode layer \
  --tensor-split 0.143,0.21425,0.21425,0.21425,0.21425 \
  --rpc <NODE_IP>:50053,<NODE_IP>:50053,<NODE_IP>:50053,<NODE_IP>:50053 \
  --no-mmap \
  -c 32768 -b 64 -ub 16 -fa on \
  --host 0.0.0.0 --port 8081
```

如果正式服务不稳定，先回退为：

```text
-c 4096
-b 32
-ub 8
-fa off
```

稳定后再逐项增加。

#### 20. 参考资料

- AMD 官方技术文章：How to run a one trillion parameter LLM locally on AMD， `https://www.amd.com/en/developer/resources/technical-articles/2026/how-to-run-a-one-trillion-parameter-llm-locally-an-amd.html`。

- llama.cpp RPC 文档：`tools/rpc/README.md`。

- 本仓库已有 AMD 395 编译文档：`AMD395-BUILD-GUIDE.md`。

- 本仓库已有 RPC 部署文档：`DEPLOY-GUIDE.md`。

本文中的关键数值来自本次实测：

```text
ROCm/HIP: 7.2.1 / 7.2.53211-e1a6bc5663
Kernel: 6.17.0-35-generic
llama.cpp build: b9557-0f7fada56
Kimi test: Prompt 19.3 t/s, Generation 8.2 t/s
Qwen test: Prompt 40.3 t/s, Generation 21.3 t/s
```

未命名页面（私人页面链接不公开）

## R24 · AMD 395 llamcpp+rpc编译流程

### AMD Ryzen AI Max+ 395 编译部署指南

#### 1. 系统准备

##### 1.1 TTM 内存调优

在 BIOS 中将 iGPU Memory Size 设置为 512MB，然后修改内核参数：

```text
sudo nano /etc/default/grub
```

将 `GRUB_CMDLINE_LINUX_DEFAULT` 修改为：

```text
GRUB_CMDLINE_LINUX_DEFAULT="quiet splash ttm.pages_limit=30720000 amdgpu.gttsize=120000"
```

更新并重启：

```text
sudo update-grub
sudo reboot
```

重启后验证：

```text
sudo dmesg | grep "amdgpu.*memory"
# 期望输出：
# amdgpu: 98304M of VRAM memory ready
# amdgpu: 120000M of GTT memory ready.
```

##### 1.2 安装 ROCm 7.x

```text
wget https://repo.radeon.com/amdgpu-install/7.0.2/ubuntu/noble/amdgpu-install_7.0.2.70002-1_all.deb
sudo apt install ./amdgpu-install_7.0.2.70002-1_all.deb
sudo apt update
sudo usermod -a -G render,video $LOGNAME
sudo apt install rocm

export PATH=$PATH:/opt/rocm-7.0.2/bin
export LD_LIBRARY_PATH=/opt/rocm-7.0.2/lib
```

安装完成后重启。

##### 1.3 安装编译依赖

```text
sudo apt install cmake build-essential git ccache libibverbs-dev patchelf libssl-dev -y
```

| 依赖包 | 用途 |
| --- | --- |
| cmake | 构建系统 |
| build-essential | GCC 编译器 |
| git | 版本控制 |
| ccache | 编译缓存，加速重复编译 |
| libibverbs-dev | RDMA 网络传输支持 |
| patchelf | 修改二进制文件的库搜索路径 |
| libssl-dev | OpenSSL 开发库，为 llama-server 提供 HTTPS 支持 |

#### 2. 编译 llama.cpp

##### 2.1 获取源码

```text
git clone https://github.com/ggml-org/llama.cpp
cd llama.cpp
```

##### 2.2 配置 CMake

```text
cmake -B build \
  -DGGML_HIP=ON \
  -DGGML_RPC=ON \
  -DGGML_HIP_ROCWMMA_FATTN=ON \
  -DAMDGPU_TARGETS="gfx1151" \
  -DCMAKE_BUILD_TYPE=Release \
  -DGGML_LTO=ON \
  -DGGML_CCACHE=ON \
  -DGGML_BACKEND_DL=ON \
  -DGGML_NATIVE=OFF \
  -DLLAMA_OPENSSL=ON
```

参数说明：

| 参数 | 说明 |
| --- | --- |
| -DGGML_HIP=ON | 启用 ROCm HIP 后端，在 AMD GPU 上运行推理 |
| -DGGML_RPC=ON | 启用 RPC 通信后端，支持多机串联 |
| -DGGML_HIP_ROCWMMA_FATTN=ON | 启用 rocWMMA Flash Attention，加速注意力计算 |
| -DAMDGPU_TARGETS="gfx1151" | 指定目标 GPU 架构（Radeon 8060S / RDNA 3.5） |
| -DGGML_LTO=ON | 链接时优化，减小二进制体积 |
| -DGGML_CCACHE=ON | 编译缓存，重复编译加速 |
| -DGGML_BACKEND_DL=ON | 后端动态库加载 |
| -DGGML_NATIVE=OFF | 关闭本机优化（与 BACKEND_DL 不兼容，必须关闭） |
| -DLLAMA_OPENSSL=ON | 使用系统 OpenSSL 提供 HTTPS 支持（用于在线下载模型） |

> **注意：** 不要使用 `-DLLAMA_BUILD_BORINGSSL=ON`，该选项会从网络下载 BoringSSL，在国内网络环境下容易超时卡死。使用系统 OpenSSL 替代即可。

配置成功后确认以下输出：

```text
-- ccache found, compilation results will be cached.
-- HIP and hipBLAS found
-- Including HIP backend
-- Using RPC backend
--   RDMA transport enabled (auto-detected)
-- Found OpenSSL: ... (found version ...)
```

##### 2.3 编译

```text
cmake --build build --config Release -j$(nproc)
```

编译完成后，二进制文件位于 `build/bin/` 目录。

> **编译警告说明：** 编译过程中可能会出现 `UI: download bundle.css failed: Timeout was reached` 警告，这是 llama-server 内置 Web UI 的前端资源下载失败（国内网络无法访问 HuggingFace），**不影响编译和推理功能**。llama-server 的 OpenAI 兼容 API 接口完全正常，只是 Web UI 页面无法打开。如需 Web UI，可手动从 llama.cpp GitHub releases 下载 `tools/ui/dist` 资源包。

##### 2.4 验证编译结果

```text
./build/bin/llama-cli --list-devices
# 期望输出：
# ROCm0: AMD Radeon Graphics (xxxxx MiB, xxxxx MiB free)
```

#### 3. 修复二进制路径（分发到其他机器前必须执行）

##### 3.1 问题说明

编译产物的 RUNPATH 默认写死为编译机器的绝对路径：

```text
RUNPATH: /srv/llm/xiangmu/llama.cpp/build/bin
```

直接复制到其他机器会找不到动态库，无法运行。

##### 3.2 用 patchelf 修改为相对路径

```text
cd /srv/llm/xiangmu/llama.cpp/build/bin

for f in llama-cli llama-server rpc-server llama-bench llama-quantize llama-gguf-split *.so*; do
  [ -f "$f" ] && patchelf --set-rpath '$ORIGIN:/opt/rocm-7.2.0/lib' "$f" 2>/dev/null
done
```

##### 3.3 验证修改结果

```text
readelf -d llama-cli | grep -i "rpath\|runpath"
# 期望输出：
# Library runpath: [$ORIGIN:/opt/rocm-7.2.0/lib]
```

修改后，`build/bin/` 目录可复制到任意装了 ROCm 的机器的任意路径下直接运行。

#### 4. 多机 RPC 串联部署

##### 4.1 远程节点（第 2、3、4...N 台机器）

将 `build/bin/` 复制到每台远程节点后，启动 RPC 服务：

```text
./rpc-server -p 50053 -c --host 0.0.0.0
```

| 参数 | 说明 |
| --- | --- |
| -p 50053 | 监听端口 |
| -c | 启用本地缓存，加速模型加载 |
| --host 0.0.0.0 | 监听所有网络接口 |

##### 4.2 主节点（第 1 台机器）

```text
# 串联 2 台
./llama-server \
  -m /path/to/model.gguf \
  -c 32768 -fa on -ngl 999 --no-mmap \
  --host 0.0.0.0 --port 8081 \
  --rpc <节点2_IP>:50053

# 串联 4 台
./llama-server \
  -m /path/to/model.gguf \
  -c 32768 -fa on -ngl 999 --no-mmap \
  --host 0.0.0.0 --port 8081 \
  --rpc <节点2_IP>:50053,<节点3_IP>:50053,<节点4_IP>:50053

# 串联 8 台
./llama-server \
  -m /path/to/model.gguf \
  -c 32768 -fa on -ngl 999 --no-mmap \
  --host 0.0.0.0 --port 8081 \
  --rpc <N2>:50053,<N3>:50053,<N4>:50053,<N5>:50053,<N6>:50053,<N7>:50053,<N8>:50053
```

| 参数 | 说明 |
| --- | --- |
| -m | 模型文件路径 |
| -c 32768 | 上下文长度 |
| -fa on | 启用 Flash Attention |
| -ngl 999 | 全部层卸载到 GPU |
| --no-mmap | 禁用内存映射（模型大于系统内存时使用） |
| --rpc | 远程 RPC 节点地址列表 |

##### 4.3 注意事项

- DeepSeek-V3 和 Kimi-2.5 为 MoE 架构，不支持 `--split-mode tensor`，使用默认 `layer` 模式即可

- RPC 功能仍处于概念验证阶段，不要将 rpc-server 暴露在公网

- 如果网卡支持 RoCEv2 且安装了 libibverbs-dev，编译时会自动启用 RDMA 传输

#### 5. 测试脚本使用说明

项目根目录提供了 `test-llama-rpc.sh` 自动化测试脚本，支持多种运行模式。

##### 5.1 快速参考

```text
cd /srv/llm/xiangmu/llama.cpp

# 测试本地 GPU 推理
bash test-llama-rpc.sh gpu

# 启动 RPC 服务端（远程节点运行）
bash test-llama-rpc.sh rpc-server

# 测试 RPC 串联推理（主节点运行）
REMOTE_IP=<NODE_IP> bash test-llama-rpc.sh rpc-test

# 运行全部测试
bash test-llama-rpc.sh all
```

##### 5.2 模式详解

##### 模式 1：`gpu` — 本地 GPU 检查

```text
bash test-llama-rpc.sh gpu
```

执行以下测试：

1. **检查编译产物** — 验证 `llama-cli`、`rpc-server`、`libggml-hip.so` 等文件是否存在且可执行

2. **检查 RUNPATH** — 验证二进制文件是否已 patchelf 修复为 `$ORIGIN` 相对路径

3. **GPU 设备检测** — 运行 `--list-devices` 确认 ROCm 能识别 GPU

4. **本地推理测试** — 自动查找本地 `.gguf` 模型（>100MB）进行推理，未找到则跳过

> 脚本会自动跳过小于 100MB 的词表测试文件。如需测试推理，请将模型放到以下任一目录： `./models/`、`../models/`、`~/models/`、`/data/models/`

##### 模式 2：`rpc-server` — 启动 RPC 服务端

```text
bash test-llama-rpc.sh rpc-server
```

在远程节点上运行此模式，等效于：

```text
./rpc-server --host 0.0.0.0 -p 50053
```

启动后保持终端运行，等待主节点连接。

##### 模式 3：`rpc-test` — 测试 RPC 串联

```text
REMOTE_IP=<远程节点IP> bash test-llama-rpc.sh rpc-test
```

**必须设置 `REMOTE_IP` 环境变量**，指向已启动 rpc-server 的远程节点。

执行以下测试：

1. 检查远程节点 IP 是否已设置

2. ping 远程节点，确认网络互通

3. nc 检查远程端口（50053）是否可达

4. 使用本地模型通过 `--rpc` 参数进行串联推理

##### 模式 4：`all` — 全部测试（默认）

```text
bash test-llama-rpc.sh
# 或
bash test-llama-rpc.sh all
```

依次运行以上所有测试。

##### 5.3 双节点串联完整流程

**机器 A（主节点）：**

```text
# 1. 运行本地测试
bash test-llama-rpc.sh gpu
```

**机器 B（远程节点）：**

```text
# 2. 启动 RPC 服务
REMOTE_IP=<机器A的IP> bash test-llama-rpc.sh rpc-server
```

**机器 A（主节点）：**

```text
# 3. 测试串联
REMOTE_IP=<机器B的IP> bash test-llama-rpc.sh rpc-test
```

##### 5.4 配置说明

脚本开头的配置区可根据需要修改：

| 变量 | 默认值 | 说明 |
| --- | --- | --- |
| BIN_DIR | build/bin | 二进制文件路径 |
| RPC_PORT | 50053 | RPC 监听端口 |
| SERVER_HOST | 0.0.0.0 | RPC 监听地址 |
| REMOTE_IP | 空 | 远程节点 IP（通过环境变量设置） |
| PROMPT | Say hello in one sentence. | 推理测试提示词 |
| GEN_TOKENS | 16 | 最大生成 token 数 |

AMD 395 llamacpp rpc服务功能环境测试脚本（私人页面链接不公开）

## R25 · AMD 395 llamacpp rpc服务功能环境测试脚本

测试脚本：

[test-llama-rpc.sh]([附件地址不公开]

```text
#!/bin/bash
#
# llama.cpp AMD 395 GPU + RPC 功能测试脚本
# 用法: bash test-llama-rpc.sh [模式]
#
# 模式:
#   gpu       - 仅测试本地 GPU 推理
#   rpc-server - 启动 RPC 服务端（远程节点运行）
#   rpc-test  - 测试 RPC 串联（主节点运行，需指定远程 IP）
#   all       - 运行所有测试（默认）
#
# 示例:
#   bash test-llama-rpc.sh gpu
#   bash test-llama-rpc.sh rpc-server
#   REMOTE_IP=<NODE_IP> bash test-llama-rpc.sh rpc-test
#

set -e

# ============================================================
# 配置区
# ============================================================

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
LLAMA_DIR="${SCRIPT_DIR}"
BIN_DIR="${LLAMA_DIR}/build/bin"
TEST_MODEL="ggml-org/gemma-3-1b-it-GGUF"
RPC_PORT=50053
SERVER_HOST="0.0.0.0"
REMOTE_IP="${REMOTE_IP:-}"
PROMPT="Say hello in one sentence."
GEN_TOKENS=16

# 颜色
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

pass() { echo -e "${GREEN}[PASS]${NC} $1"; }
fail() { echo -e "${RED}[FAIL]${NC} $1"; }
info() { echo -e "${YELLOW}[INFO]${NC} $1"; }

# ============================================================
# 测试 1: 检查二进制文件
# ============================================================
test_binaries() {
    echo ""
    echo "=========================================="
    echo " 测试 1: 检查编译产物"
    echo "=========================================="

    local ok=true
    for bin in llama-cli llama-server rpc-server llama-bench; do
        if [ -x "${BIN_DIR}/${bin}" ]; then
            pass "${bin} 存在且可执行"
        else
            fail "${bin} 不存在或不可执行: ${BIN_DIR}/${bin}"
            ok=false
        fi
    done

    for lib in libggml-hip.so libggml-rpc.so libggml.so libllama.so; do
        if [ -f "${BIN_DIR}/${lib}" ]; then
            pass "${lib} 存在"
        else
            fail "${lib} 不存在: ${BIN_DIR}/${lib}"
            ok=false
        fi
    done

    if $ok; then
        pass "所有二进制文件检查通过"
    else
        fail "部分文件缺失，请先完成编译"
        return 1
    fi
}

# ============================================================
# 测试 2: 检查 RUNPATH
# ============================================================
test_runpath() {
    echo ""
    echo "=========================================="
    echo " 测试 2: 检查 RUNPATH 可移植性"
    echo "=========================================="

    local rpath
    rpath=$(readelf -d "${BIN_DIR}/llama-cli" 2>/dev/null | grep -i "runpath" | head -1)

    if echo "$rpath" | grep -q '\$ORIGIN'; then
        pass "RUNPATH 已设置为相对路径: $rpath"
    elif echo "$rpath" | grep -q "rpath\|runpath"; then
        echo -e "${YELLOW}[WARN]${NC} RUNPATH 仍为绝对路径: $rpath"
        info "建议执行 patchelf 修复后再分发到其他机器"
    else
        fail "无法读取 RUNPATH"
    fi
}

# ============================================================
# 测试 3: GPU 检测
# ============================================================
test_gpu_detect() {
    echo ""
    echo "=========================================="
    echo " 测试 3: GPU 设备检测"
    echo "=========================================="

    local output
    output=$("${BIN_DIR}/llama-cli" --list-devices 2>&1) || true

    if echo "$output" | grep -qi "ROCm\|HIP\|gfx1151"; then
        pass "检测到 ROCm GPU 设备"
        echo "$output" | grep -i "ROCm\|Device\|AMD" | head -5
    else
        fail "未检测到 ROCm GPU"
        echo "$output" | head -10
        return 1
    fi
}

# ============================================================
# 测试 4: GPU 推理就绪检查（不下载模型）
# ============================================================
test_local_inference() {
    echo ""
    echo "=========================================="
    echo " 测试 4: GPU 推理就绪检查"
    echo "=========================================="

    # 检查是否有本地 GGUF 模型可用（跳过小于 100MB 的词表测试文件）
    local model_path=""
    for candidate in \
        ./models/*.gguf \
        ../models/*.gguf \
        ~/models/*.gguf \
        /data/models/*.gguf; do
        if [ -f "$candidate" ]; then
            local size_kb
            size_kb=$(du -k "$candidate" | cut -f1)
            if [ "$size_kb" -gt 102400 ]; then
                model_path="$candidate"
                break
            fi
        fi
    done

    if [ -n "$model_path" ]; then
        info "发现本地模型: $model_path"
        info "正在加载模型并测试推理..."

        local output
        output=$("${BIN_DIR}/llama-cli" \
            -m "$model_path" \
            -ngl 99 \
            -p "${PROMPT}" \
            -n "${GEN_TOKENS}" \
            --no-display-prompt \
            2>&1) || true

        if echo "$output" | grep -qi "error\|fail\|abort"; then
            fail "推理过程出错"
            echo "$output" | tail -10
            return 1
        fi

        local generated
        generated=$(echo "$output" | grep -v "^$\|llama_\|ggml\|system\|AMD\|ROCm\|device\|load\|mem\|time\|token\|generation\|sampling\|perf\|batch\|KV\|n_" | head -3)

        if [ -n "$generated" ]; then
            pass "GPU 推理成功，生成内容:"
            echo "    $generated"
        else
            pass "GPU 推理完成（模型已加载并执行）"
        fi

        echo ""
        info "性能统计:"
        echo "$output" | grep -i "eval time\|load time\|tokens per\|tk/s\|pp\|tg" | tail -5 | while read -r line; do
            echo "    $line"
        done
    else
        info "未找到本地 GGUF 模型，跳过推理测试"
        info "如需测试推理，请将模型文件放入 ./models/ 目录，或使用以下命令手动测试："
        echo ""
        echo "    # 示例：使用本地模型测试"
        echo "    ${BIN_DIR}/llama-cli -m /path/to/model.gguf -ngl 99 -p \"Hello\" -n 16"
        echo ""
        echo "    # 示例：使用 llama-server 启动服务"
        echo "    ${BIN_DIR}/llama-server -m /path/to/model.gguf -ngl 99 -fa on --host 0.0.0.0 --port 8081"
        echo ""
        pass "GPU 已就绪，可以加载模型进行推理"
    fi
}

# ============================================================
# 测试 5: RPC Server 启动
# ============================================================
test_rpc_server() {
    echo ""
    echo "=========================================="
    echo " 测试 5: RPC Server 启动"
    echo "=========================================="

    info "启动 RPC Server (端口 ${RPC_PORT})，5 秒后自动停止..."

    local output
    output=$(timeout 5 "${BIN_DIR}/rpc-server" \
        -p "${RPC_PORT}" \
        --host "${SERVER_HOST}" 2>&1) || true

    if echo "$output" | grep -qi "Starting RPC server"; then
        pass "RPC Server 启动成功"
        echo "$output" | grep -i "endpoint\|Device\|ROCm\|transport" | head -5 | while read -r line; do
            echo "    $line"
        done
    else
        fail "RPC Server 启动失败"
        echo "$output" | head -10
        return 1
    fi

    if echo "$output" | grep -qi "RDMA\|rdma"; then
        pass "RDMA 传输已启用"
    else
        info "RDMA 未启用（使用 TCP 传输）"
    fi
}

# ============================================================
# 测试 6: RPC 串联推理
# ============================================================
test_rpc_inference() {
    echo ""
    echo "=========================================="
    echo " 测试 6: RPC 串联推理"
    echo "=========================================="

    if [ -z "${REMOTE_IP}" ]; then
        info "未设置 REMOTE_IP，跳过 RPC 串联测试"
        info "用法: REMOTE_IP=<远程节点IP> bash test-llama-rpc.sh rpc-test"
        return 0
    fi

    info "远程节点: ${REMOTE_IP}:${RPC_PORT}"

    # 先检查远程节点是否可达
    info "检查远程 RPC 节点连通性..."
    if timeout 3 bash -c "echo > /dev/tcp/${REMOTE_IP}/${RPC_PORT}" 2>/dev/null; then
        pass "远程 RPC 节点可达"
    else
        fail "无法连接远程节点 ${REMOTE_IP}:${RPC_PORT}"
        info "请确认远程节点已运行: rpc-server -p ${RPC_PORT} --host 0.0.0.0"
        return 1
    fi

    info "通过 RPC 串联进行推理..."
    local output
    output=$("${BIN_DIR}/llama-cli" \
        -hf "${TEST_MODEL}" \
        -ngl 99 \
        -p "${PROMPT}" \
        -n "${GEN_TOKENS}" \
        --no-display-prompt \
        --rpc "${REMOTE_IP}:${RPC_PORT}" \
        2>&1) || true

    if echo "$output" | grep -qi "error\|fail\|abort"; then
        if echo "$output" | grep -qi "could not\|download\|network\|connect"; then
            fail "RPC 串联推理失败（网络或模型问题）"
        else
            fail "RPC 串联推理出错"
        fi
        echo "$output" | tail -20
        return 1
    fi

    local generated
    generated=$(echo "$output" | grep -v "^$\|llama_\|ggml\|system\|AMD\|ROCm\|device\|load\|mem\|time\|token\|generation\|sampling\|perf\|batch\|KV\|n_\|rpc\|RPC" | head -5)

    if [ -n "$generated" ]; then
        pass "RPC 串联推理成功，生成内容:"
        echo "    $generated"
    else
        pass "RPC 串联推理完成"
    fi

    echo ""
    info "性能统计:"
    echo "$output" | grep -i "eval time\|load time\|tokens per\|tk/s\|pp\|tg" | tail -5 | while read -r line; do
        echo "    $line"
    done
}

# ============================================================
# 主入口
# ============================================================
main() {
    local mode="${1:-all}"

    echo ""
    echo "##########################################"
    echo "# llama.cpp AMD 395 GPU + RPC 测试脚本  #"
    echo "##########################################"
    echo ""
    info "运行模式: ${mode}"
    info "llama.cpp 路径: ${LLAMA_DIR}"
    info "二进制目录: ${BIN_DIR}"

    case "${mode}" in
        gpu)
            test_binaries || exit 1
            test_runpath
            test_gpu_detect || exit 1
            test_local_inference
            ;;
        rpc-server)
            test_binaries || exit 1
            test_rpc_server
            ;;
        rpc-test)
            test_binaries || exit 1
            test_gpu_detect
            test_rpc_inference
            ;;
        all)
            test_binaries || exit 1
            test_runpath
            test_gpu_detect || exit 1
            test_local_inference
            test_rpc_server
            test_rpc_inference
            ;;
        *)
            echo "用法: bash $0 [gpu|rpc-server|rpc-test|all]"
            exit 1
            ;;
    esac

    echo ""
    echo "=========================================="
    echo " 测试完成"
    echo "=========================================="
    echo ""
}

main "$@"

```

说明文档

```text
test-llama-rpc.sh 使用说明
简介
自动化测试脚本，用于验证 AMD Ryzen AI Max+ 395 设备上的 llama.cpp 编译结果和 RPC 多机串联功能。

快速开始
cd /srv/llm/xiangmu/llama.cpp

# 1. 测试本地 GPU
bash test-llama-rpc.sh gpu

# 2. 在远程节点启动 RPC 服务
bash test-llama-rpc.sh rpc-server

# 3. 在主节点测试串联
REMOTE_IP=<NODE_IP> bash test-llama-rpc.sh rpc-test

# 4. 运行全部测试
bash test-llama-rpc.sh all
运行模式
gpu — 本地 GPU 检查
bash test-llama-rpc.sh gpu
依次执行 4 项测试：

测试项	内容	失败影响
测试 1: 编译产物	检查 llama-cli、rpc-server、libggml-hip.so、libggml-rpc.so 等是否存在且可执行	需重新编译
测试 2: RUNPATH	检查二进制是否已 patchelf 修复为 $ORIGIN 相对路径	需执行 patchelf
测试 3: GPU 检测	运行 --list-devices 确认 ROCm 识别 GPU，显示显存信息	需检查 ROCm/TTM 配置
测试 4: 本地推理	自动查找本地 .gguf 模型（>100MB）进行推理	无模型时跳过
关于测试 4：

脚本会自动在以下目录搜索 .gguf 文件：./models/、../models/、~/models/、/data/models/
小于 100MB 的文件（词表测试文件）会被自动跳过
未找到模型时，显示手动测试命令提示，不报错
rpc-server — 启动 RPC 服务端
bash test-llama-rpc.sh rpc-server
在远程节点（机器 B）上运行，启动 RPC 服务等待主节点连接：

等效命令: ./rpc-server --host 0.0.0.0 -p 50053
启动后终端会保持运行，不要关闭，直到测试完成。

rpc-test — 测试 RPC 串联推理
REMOTE_IP=<远程节点IP> bash test-llama-rpc.sh rpc-test
在主节点（机器 A）上运行，验证与远程节点的串联是否正常。

必须设置 REMOTE_IP 环境变量，否则会报错退出。

依次执行：

测试项	内容
检查 REMOTE_IP	确认环境变量已设置
ping 远程节点	确认网络互通
检查端口 50053	用 nc -zv 确认 rpc-server 已在监听
串联推理	用本地模型 + --rpc 参数执行推理
all — 全部测试（默认）
bash test-llama-rpc.sh all
# 或
bash test-llama-rpc.sh
依次运行 gpu + rpc-server + rpc-test 全部测试。

注意：all 模式下 rpc-test 需要 REMOTE_IP，如未设置会跳过串联测试。

双节点串联完整流程
准备
两台机器都已完成 TTM 内存调优、ROCm 安装、编译 + patchelf 修复
两台机器网络互通（同一局域网）
步骤
机器 A（主节点） — 验证本地 GPU：

bash test-llama-rpc.sh gpu
机器 B（远程节点） — 启动 RPC 服务：

bash test-llama-rpc.sh rpc-server
机器 A（主节点） — 测试串联：

REMOTE_IP=<机器B的IP> bash test-llama-rpc.sh rpc-test
预期输出
串联推理成功时，能看到类似：

llama_model_loader: - tensor xxx ... (ROCm0)    # 本机 GPU
llama_model_loader: - tensor yyy ... (RPC0)     # 远程 GPU
ROCm0 和 RPC0 同时出现，说明双节点串联生效。

配置说明
脚本开头（第 20-32 行）的可配置变量：

变量	默认值	说明
BIN_DIR	build/bin	llama.cpp 二进制文件路径
RPC_PORT	50053	RPC 服务监听端口
SERVER_HOST	0.0.0.0	RPC 服务监听地址
REMOTE_IP	空	远程节点 IP，通过 REMOTE_IP=x.x.x.x 设置
PROMPT	Say hello in one sentence.	推理测试的提示词
GEN_TOKENS	16	最大生成 token 数
输出格式
脚本使用颜色标记测试结果：

[PASS] 绿色 — 测试通过
[FAIL] 红色 — 测试失败
[INFO] 黄色 — 信息提示
常见问题
测试 4 显示"未找到本地 GGUF 模型"
将模型文件（.gguf）放到以下任一目录即可：

./models/
../models/
~/models/
/data/models/
或直接手动测试：

./build/bin/llama-cli -m /path/to/model.gguf -ngl 999 -fa on -p "Hello" -n 16
rpc-test 提示"REMOTE_IP 未设置"
运行时必须指定远程节点 IP：

REMOTE_IP=<NODE_IP> bash test-llama-rpc.sh rpc-test
端口检查失败（nc 不通）
确认远程节点已启动 rpc-server：bash test-llama-rpc.sh rpc-server
确认远程节点防火墙放行 50053 端口：
sudo ufw allow 50053
串联推理超时或断开
检查网络带宽（模型层分发需要较大带宽）
如果使用 RDMA，确认 rpc-server 输出中有 transport: RDMA
适当增大上下文长度 -c 4096 减少显存压力
```
