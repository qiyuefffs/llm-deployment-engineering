# AMD 395 five-machine HIP RPC: GTT repair, build, distribute and load with Kimi

[简体中文](../../01-deployment-foundations/engineering/amd-395-rpc.md) | **English**

[Index of engineering examples](README.md) · [General directory of knowledge systems](../SUMMARY.md)

Technical labels: `ROCm / HIP / GTT / TTM / RPC / split`

## Environment, topology and constraints

|Projects|Configuration|
| --- | --- |
|The nodes|5 Ryzen AI Max + 395 / Radeon 8060S, main node + 4 RPC nodes|
|Software| ROCm7.2.1,HIP7.2.53211,Kernel6.17.0-35,llama.cpp b9557-0f7fada56 |
|Capacity issues|dmesg displays GTT120000MiB, but DKMS TTM is actually about 63215MiB; After repair, the device is about 120,000 MiB.|
|Model|Kimi-K2.5-Q2; Model revision needs to be fixed with different shards|
|First Budget|ctx512,batch32,ubatch8,FA off; Pre-verification of capacity and load|

## Complete adaptation and deployment processes

```text
BIOS UMA budget → /proc/cmdline → amdgpu module source → GTT/TTM
 → HIP upload → Commit compilation RPC → Distributed in the same version
 → 4 RPC processes → Host list-devices → Small model → Kimi small context
 → memory / connection / progress observation → llama-server with API → official workload
```

GTT/TTM repairs involve driver modules and restarts, first recording the source and recovery mode of the module; It only addresses allowable memory, and does not mean that the five machines have been upgraded. In the original version, the complete layout, DKMS processing and loading process, is retained below.

In order to avoid the leakage of the nodes, the original private address was replaced with a new one.`<NODE_IP>`. New operations need to be set up clearly ` RPC_NODE_1 `to ` RPC_NODE_4`The four values correspond to one node; Don't replace all placeholders with the same machine. The program version is compatible with the dependency library on all five machines.

## Accelerated optimization and acceptance testing

The original tensor-split is `14,21.5,21.5,21.5,21.5` The host is less allocated to retain mapping, status and system space. Using the same model, adjust the split to check the actual buffer and host peak of each node. Add to the ctx/batch/ubatch, changing only one main variable each time.

Capacity acceptance testing is separated from speed acceptance testing: the five-machine loaded target model is the result of capacity; No single-machine with the same calibre as the baseline would report a multi-node acceleration ratio. Record RPC network throughput, loading time, prefill/decode, API TTFT and failure recovery. The following contains the full deployment records, compilation records, and original functionality test scripts; The script is historical technical material and is not automatically executed by the document.

## Agreement on the use of complete technical records

The following technical correctness, commands, tables, logs, failures and subsequent experiments of the relevant FlowUs articles are retained directly, without abbreviating the original process. private paths, nodes, authentication and sanitization of attached addresses; `<NODE_IP>` For example, the placeholder needs to be filled in the current environment. The original suggestion or prediction is still a suggestion or prediction. The above execution sequence and technical revisions are used to explain conflicts in historical records, and historical GPU/NPU experiments have not been repeated in this round.

## R23 · AMD Strix Halo 395 five-speed HIP RPC series deployment of the Kimi-K2.5-Q2 real-time warfare documentation

This article documents a complete adaptation process for the AMD Ryzen AI Max+ 395 / Radeon 8060S series deployment of the Kimi-K2.5-Q2 GGUF. The focus is not just on the final commands, but on the BIOS, GRUB, ROCm, HIP compilation, RPC sequencing, load time, memory occupancy, inference speed, and the actual crawler.

> This article focuses on the Internet experimental environment.`rpc-server --host 0.0.0.0` It is not secure, can only be placed on a trusted local area network or a direct connection to the network, and cannot be exposed to the public network.

#### 1. The final conclusion

The launch of the five aircraft was a success. The Kimi-K2.5-Q2 can be used on five AMD Strix Halo 395 machines with passed HIP backend and llama.cpp RPC regular loading and inference.

The final key state:

```text
主机 ROCm0: 120000 MiB total
从机 RPC0: 120000 MiB total
从机 RPC1: 120000 MiB total
从机 RPC2: 120000 MiB total
从机 RPC3: 120000 MiB total
```

The results of the Kimi-K2.5-Q2 small context verification:

```text
Prompt: 19.3 t/s
Generation: 8.2 t/s
```

Qwen 3.5-9B small model five-engine RPC smoke test results:

```text
Prompt: 40.3 t/s
Generation: 21.3 t/s
```

The most critical crater this time:

```text
从机安装了 amdgpu-dkms 6.16.13 后，虽然 dmesg 显示 120000M GTT，
但 TTM 实际被钳到 66286690304 字节，llama.cpp / HIP 看到的 total
只有 63215 MiB。
```

Example of wrong state:

```text
GTT size has been set as 125829120000 but TTM size has been set as 66286690304, this is unusual
ROCm0: AMD Radeon Graphics (63215 MiB, 124xxx MiB free)
```

A good example of this is:

```text
ROCm0: AMD Radeon Graphics (120000 MiB, 124xxx MiB free)
```

The final solution:

```text
sudo apt-get remove -y amdgpu-dkms
sudo reboot
```

Note: Remove only `amdgpu-dkms ` Don't be direct.`autoremove ` Cleaning `amdgpu-dkms-firmware`; avoid removing the firmware along with it.

#### 2. measured hardware and network topology

##### 2.1 Role of the machine

|The Role| IP |Useful|
| --- | --- | --- |
|The host| <NODE_IP> |It runs llama-cli or llama-server, and the local GPU is also involved in the distribution.|
|From Table 1| <NODE_IP> |Running rpc-server|
|From Mechanic 2| <NODE_IP> |Running rpc-server|
|From 3| <NODE_IP> |Running rpc-server|
|From the 4th| <NODE_IP> |Running rpc-server|

##### 2.2 device

Each machine:

```text
CPU/APU: AMD Ryzen AI Max+ 395
GPU: AMD Radeon 8060S
GPU target: gfx1151
内存: 128 GB 级别 LPDDR5
```

##### 2.3 network

This time using USB4/Thunderbolt to connect directly to the bridge network, not WiFi.

The host checks:

```text
ip -br addr
```

measured See:

```text
nm-bridge    <NODE_IP>/24
thunderbolt0 UP
wlp195s0     192.168.5.xxx/24
```

including `192.168.1.x ` It is a vertical network of five machines used for serial connections.`192.168.5.x` It's WiFi or some other internet connection.

Verify the connectivity of four machines from the machine:

```text
ping -c 1 -W 2 <NODE_IP>
ping -c 1 -W 2 <NODE_IP>
ping -c 1 -W 2 <NODE_IP>
ping -c 1 -W 2 <NODE_IP>
```

#### 3. BIOS settings

The direction mentioned in AMD's official example is to reduce the VRAM reservation of the iGPU and give more system RAM to GTT/UMA use. In the BIOS of the tested devices, `iGPU Memory Size ` At least it can be set to `2GB ` Can't set it to `512MB`.

This is the most successful configuration:

```text
iGPU Memory Size = 2GB
```

After rebooting, see dmesg:

```text
VRAM: 2048M
2048M of VRAM memory ready
120000M of GTT memory ready
```

In conclusion:

- The BIOS at least can.`2GB` It's not the root cause of this failure.

- As long as Linux/ROCm/HIP can finally be seen `120000 MiB total` In the meantime, Kimi's five loads will be successful.

- If the BIOS can be switched to `512MB` It can be set up as an official example, but not as a requirement for these machines.

#### 4. System and ROCm baseline

##### 4.1 Operating system and core

This is a successful environment:

```text
Ubuntu 24.04
Kernel: 6.17.0-35-generic
```

Check commands:

```text
uname -a
```

##### 4.2 ROCm and HIP versions

This is a successful environment:

```text
ROCm: 7.2.1
HIP: 7.2.53211-e1a6bc5663
```

Check commands:

```text
/opt/rocm/bin/hipcc --version | head -n 5
dpkg-query -W 'rocm-core' 'hip-runtime-amd' 'hsa-rocr' 2>/dev/null
```

Measured output:

```text
hip-runtime-amd  7.2.53211.70201-81~24.04
hsa-rocr         1.18.0.70201-81~24.04
rocm-core        7.2.1.70201-81~24.04
```

Check the ROCm device nodes:

```text
ls -l /dev/kfd /dev/dri/renderD*
```

Expectations are:

```text
/dev/kfd 存在
/dev/dri/renderD128 存在
当前用户属于 render/video 相关权限组
```

#### 5. GRUB and GTT/TTM configuration

All five machines need to write the same core parameters.

Edit:

```text
sudo nano /etc/default/grub
```

Recommended configuration:

```text
GRUB_CMDLINE_LINUX_DEFAULT="quiet splash ttm.pages_limit=30720000 ttm.page_pool_size=30720000 amdgpu.gttsize=120000 amdgpu.cwsr_enable=0"
```

Updated and restarted:

```text
sudo update-grub
sudo reboot
```

Check the current running parameter after rebooting:

```text
cat /proc/cmdline
```

Expect to include:

```text
ttm.pages_limit=30720000
ttm.page_pool_size=30720000
amdgpu.gttsize=120000
amdgpu.cwsr_enable=0
```

Check the dmesg:

```text
sudo dmesg -T | grep -Ei 'VRAM:|GTT memory ready|VRAM memory ready|Detected VRAM|RAM width' | tail -n 20
```

Expectations are:

```text
VRAM: 2048M
2048M of VRAM memory ready
120000M of GTT memory ready
```

##### 5.1 Just looking at dmesg is not enough

This is the easiest place to make mistakes.

It has been shown that:

```text
120000M of GTT memory ready
```

But `llama-cli --list-devices` It's still:

```text
ROCm0: AMD Radeon Graphics (63215 MiB, 124xxx MiB free)
```

Therefore, the final criterion must be:

```text
cd /srv/llm/xiangmu/llama.cpp/build-hip-rpc-official/bin
env LD_LIBRARY_PATH=. ./llama-cli --list-devices
```

The correct output must be similar to:

```text
Available devices:
  ROCm0: AMD Radeon Graphics (120000 MiB, 124xxx MiB free)
```

If the total is still `63215 MiB` This is not the case with the Kimi large language model, which will fail.

#### 6. Key issue: amdgpu-dkms limited TTM to 63GB

##### 6.1 Failure phenomena

This is what happened when Kimi Loaded Fail:

```text
alloc_tensor_range: failed to allocate RPC0[<NODE_IP>:50053] buffer of size 87013675008
unable to allocate RPC0[<NODE_IP>:50053] buffer
```

`87013675008 ` Byte savings are: `81 GiB `. When the HIP total is only `63215 MiB` This distribution will inevitably fail.

The worker device reported:

```text
ROCm0: AMD Radeon Graphics (63215 MiB, 124xxx MiB free)
```

##### 6.2 The real reason

Installed from the machine `amdgpu-dkms`:

```text
dpkg-query -W 'amdgpu-dkms' 2>/dev/null
```

The problem is machine output:

```text
amdgpu-dkms  1:6.16.13.30300100-2303411.24.04
```

Module paths from the actual loading of the machine:

```text
modinfo amdgpu | grep -E 'filename:|version:|srcversion:|vermagic:'
```

The wrong state:

```text
filename: /lib/modules/6.17.0-35-generic/updates/dkms/amdgpu.ko.zst
version: 6.16.13
```

The Dmesg also issued a key alert to police:

```text
GTT size has been set as 125829120000 but TTM size has been set as 66286690304, this is unusual
```

`66286690304 ` Byte savings are: `63215 MiB` It's the perfect match for the error total of llama.cpp.

##### 6.3 The correct state

The host doesn't `amdgpu-dkms`, using the kernel's in-tree amdgpu:

```text
filename: /lib/modules/6.17.0-35-generic/kernel/drivers/gpu/drm/amd/amdgpu/amdgpu.ko.zst
```

After the host is restarted:

```text
ROCm0: AMD Radeon Graphics (120000 MiB, 119988 MiB free)
```

##### 6.4 Repair commands

Pre-simulated confirmation that the ROCm runtime will not be erased:

```text
sudo apt-get -s remove amdgpu-dkms
```

It's only expected that:

```text
The following packages will be REMOVED:
  amdgpu-dkms
```

The actual removal:

```text
sudo apt-get remove -y amdgpu-dkms
sudo reboot
```

After rebooting confirmed:

```text
modinfo amdgpu | grep -E 'filename:|version:|srcversion:|vermagic:'
```

The right path:

```text
filename: /lib/modules/6.17.0-35-generic/kernel/drivers/gpu/drm/amd/amdgpu/amdgpu.ko.zst
```

Confirm again:

```text
cd /srv/llm/xiangmu/llama.cpp/build-hip-rpc-official/bin
env LD_LIBRARY_PATH=. ./llama-cli --list-devices
```

The correct output:

```text
ROCm0: AMD Radeon Graphics (120000 MiB, 124xxx MiB free)
```

##### 6.5 What Not to Do

Do not execute directly for the sake of the province:

```text
sudo apt autoremove
```

Because it could take `amdgpu-dkms-firmware ` Let's get this cleaned up. Only removed from actual operations `amdgpu-dkms` That's enough.

Don't pass again `amdgpu-install ` If the kernel of the DKMS driver is reinstalled, it may return to the kernel.`63215 MiB total`.

#### 7. compilation llama.cpp HIP RPC

##### 7.1 Recommended to build directories

This is the final use:

```text
/srv/llm/xiangmu/llama.cpp/build-hip-rpc-official
```

##### 7.2 CMake configuration

In the host, execute:

```text
cd /srv/llm/xiangmu/llama.cpp

cmake -S . -B build-hip-rpc-official \
  -DCMAKE_BUILD_TYPE=Release \
  -DGGML_HIP=ON \
  -DGGML_RPC=ON \
  -DGGML_HIP_ROCWMMA_FATTN=ON \
  -DAMDGPU_TARGETS=gfx1151
```

compilation :

```text
cmake --build build-hip-rpc-official --config Release -j"$(nproc)"
```

##### 7.3 Compilation parameters checked

```text
rg -n "GGML_HIP|GGML_RPC|HIP_ROCWMMA|HIP_GRAPHS|HIP_NO_VMM|RPC_RDMA|AMDGPU_TARGETS|GPU_TARGETS" \
  build-hip-rpc-official/CMakeCache.txt
```

The key items measured this time are:

```text
AMDGPU_TARGETS:UNINITIALIZED=gfx1151
GGML_HIP:BOOL=ON
GGML_HIP_ROCWMMA_FATTN:BOOL=ON
GGML_RPC:BOOL=ON
GGML_RPC_RDMA:BOOL=ON
```

`GGML_RPC_RDMA=ON ` This is because the built environment has been discovered.`libibverbs`. This USB4 line is the TCP/RPC path, and the RDMA switch is not the key to successfully loading Kimi.

##### 7.4 Verify the native device

```text
cd /srv/llm/xiangmu/llama.cpp/build-hip-rpc-official/bin
env LD_LIBRARY_PATH=. ./llama-cli --list-devices
```

Expectations are:

```text
Available devices:
  ROCm0: AMD Radeon Graphics (120000 MiB, xxxxxx MiB free)
```

If you ask:

```text
failed to initialize ROCm: no ROCm-capable device is detected
```

Priority checks:

```text
ls -l /dev/kfd /dev/dri/renderD*
groups
cat /proc/cmdline
/opt/rocm/bin/rocminfo | grep -i gfx -m 5
```

#### 8. Distribute binary to machine

Package on the host:

```text
cd /srv/llm/xiangmu/llama.cpp
tar -C build-hip-rpc-official -czf /tmp/llama-hip-rpc-official-bin.tgz bin
```

It was copied to four machines:

```text
for ip in <NODE_IP> <NODE_IP> <NODE_IP> <NODE_IP>; do
  scp /tmp/llama-hip-rpc-official-bin.tgz "link@${ip}:/tmp/"
done
```

From the pressurizer:

```text
for ip in <NODE_IP> <NODE_IP> <NODE_IP> <NODE_IP>; do
  ssh "link@${ip}" \
    'mkdir -p /srv/llm/xiangmu/llama.cpp/build-hip-rpc-official &&
     cd /srv/llm/xiangmu/llama.cpp/build-hip-rpc-official &&
     tar -xzf /tmp/llama-hip-rpc-official-bin.tgz'
done
```

It is recommended to use the SSH key. Don't put real passwords in scripts or documents.

#### 9. Start RPC services from the machine

Four of them were executed from the plane:

```text
cd /srv/llm/xiangmu/llama.cpp/build-hip-rpc-official/bin
env LD_LIBRARY_PATH=/srv/llm/xiangmu/llama.cpp/build-hip-rpc-official/bin \
  ./rpc-server -p 50053 -c --host 0.0.0.0
```

In the background, start the template:

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

Right log:

```text
ggml_cuda_init: found 1 ROCm devices (Total VRAM: 120000 MiB):
  Device 0: AMD Radeon Graphics, gfx1151 (0x1151), VMM: no, Wave Size: 32, VRAM: 120000 MiB
```

Please note:

- `-c` Activate RPC local cache, which helps to reuse large tensors later.

- `--host 0.0.0.0` It is only allowed to be used on a trusted internet connection.

- If the RPC server log is still displayed `Total VRAM: 63215 MiB ` Don't keep loading Kimi, go back to Section 6 and fix it.`amdgpu-dkms` / TTM.

#### 10. Host verified five machine device list

Hosted by:

```text
cd /srv/llm/xiangmu/llama.cpp/build-hip-rpc-official/bin

env LD_LIBRARY_PATH=. ./llama-cli \
  --rpc <NODE_IP>:50053,<NODE_IP>:50053,<NODE_IP>:50053,<NODE_IP>:50053 \
  --list-devices
```

In the end, the output was correct:

```text
Available devices:
  ROCm0: AMD Radeon Graphics (120000 MiB, 117696 MiB free)
  RPC0: <NODE_IP>:50053 (120000 MiB, 124415 MiB free)
  RPC1: <NODE_IP>:50053 (120000 MiB, 124345 MiB free)
  RPC2: <NODE_IP>:50053 (120000 MiB, 124392 MiB free)
  RPC3: <NODE_IP>:50053 (120000 MiB, 124381 MiB free)
```

We have to look at all five devices.`120000 MiB` After that, we load up Kimi again.

#### 11. smoke test with small model

Don't go directly to Kimi. A small model confirms that the HIP/RPC computation path is normal.

Example model:

```text
/srv/llm/xiangmu/models/Qwen3.5-9B/Qwen3.5-9B-Q4_K_M.gguf
```

The test command:

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

The result is:

```text
Prompt: 40.3 t/s
Generation: 21.3 t/s
```

The younger model passed and then came Kimi.

#### 12. Kimi-K2.5-Q2 five-plane loading command

The model path:

```text
/srv/llm/xiangmu/models/Kimi-K2.5-GGUF/Kimi-K2.5-GGUF/UD-Q2_K_XL/Kimi-K2.5-UD-Q2_K_XL-00001-of-00008.gguf
```

Model directory size `350G` The first shard is specified, and llama.cpp automatically loads the other shards.

##### 12.1 Small context loaded verification

This is a successful order:

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

Parameter explains:

|Parameters|Notes|
| --- | --- |
| -ngl 999 |Try to get layers offloaded to GPU/remote RPC devices as much as possible.|
| --split-mode layer |MoE large language model with layer split, more stable|
| --tensor-split 0.143,0.21425,0.21425,0.21425,0.21425 |Host less distributed, four more distributed from machines|
| --no-mmap |large language model recommended enabling to avoid introducing additional memory stress to mmap|
| -c 512 |Small context verification and risk reduction|
| -fa off |First load verification shut down the FA to confirm the base path is available|
| -b 32 -ub 8 |Small batch, lowering first verification memory pressure|

The result is:

```text
Prompt: 19.3 t/s
Generation: 8.2 t/s
```

##### 12.2 Why is the host split a little bit

The user's appeal is to avoid the crash of the host system's card. In addition to the local GPU allocation, the host is responsible for:

- Read the 350G GGUF shard.

- Manage the RPC connection.

- Scheduling Calculation Chart.

- To take on local system, desktop, and other task memory.

So this is the choice:

```text
主机: 0.143
从机 1: 0.21425
从机 2: 0.21425
从机 3: 0.21425
从机 4: 0.21425
```

A summary of the examples:

```text
0.143 + 0.21425 x 4 = 1.0
```

If the host has other tasks, it can continue to reduce the proportion of hosts, such as:

```text
0.10,0.225,0.225,0.225,0.225
```

But we need to verify that every one of them doesn't go over the plane.`120000 MiB` total.

##### 12.3 Follow-up performance test commands

After the small context verification is passed, it is gradually improved:

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

If there is instability, fallback in the following order:

```text
1. -fa on 改为 -fa off
2. -ub 16 改为 -ub 8
3. -b 64 改为 -b 32
4. -c 32768 改为 -c 4096 或 -c 512
```

#### 13. Loading time and memory occupancy measured

Kimi-K2.5-Q2 GGUF directory `350G`. The main time spent on the first load is:

```text
1. 主机顺序读取 GGUF 分片。
2. 按 layer split 将权重通过 RPC 发送到从机。
3. 从机在 UMA/GTT 中分配大 tensor。
```

In this small context, the loading took about ten minutes at the level. Passed during loading:

```text
cat /proc/<llama-cli-pid>/io
```

Watch the progress of the disc:

|Read the disc|Rough progress|Status|
| --- | --- | --- |
| 101GB |About 29%|Four RPCs have been connected and distributed|
| 147GB |About 42%|.12 Basically Finished, Started .13|
| 174GB |About 50 percent|.13 Received|
| 236GB |About 67%|Starting at 14.|
| 306GB |About 87 percent|Starting at .64|
| 358GB |It's about 100%.|Initializing and generating|

Example of host memory during loading:

```text
Mem: 123Gi total, 81Gi used, 41Gi available
Swap: 0B used
```

During loading, the machine's memory will be upgraded later, rather than the four simultaneously, as the layer split will be transmitted in sequence:

```text
.12 先接收
.13 后接收
.14 后接收
.64 最后接收
```

After loading and unloading, the host memory is restored:

```text
Mem: 123Gi total, 8.6Gi used, 114Gi available
Swap: 0B used
```

Four RPCs from the machine are still in service, and memory has been restored:

```text
rpc-server running
Mem available: 120Gi 左右
```

#### 14. Regular surveillance orders

##### 14.1 Check the host Kimi process

```text
pgrep -af 'llama-cli|Kimi-K2.5|kimi'
ps -p <pid> -o pid,stat,etime,%cpu,%mem,rss,vsz,nlwp,cmd
cat /proc/<pid>/io
```

##### 14.2 Check the RPC connection

```text
ss -tinp | grep -A1 -E '192\.168\.1\.(12|13|14|64):50053|llama-cli'
```

Focus on:

```text
bytes_sent
bytes_acked
rtt
retrans
rwnd_limited
```

Loading phase if there is only one from the machine `bytes_sent` Fast-growing, typically normal layer-by-layer transmission.

##### 14.3 View from machine memory and services

```text
for ip in <NODE_IP> <NODE_IP> <NODE_IP> <NODE_IP>; do
  ssh "link@${ip}" \
    'hostname
     free -h
     pgrep -ax rpc-server
     tail -n 20 /tmp/rpc-server-hip.log'
done
```

##### 14.4 Check the ROCm/HIP device

```text
cd /srv/llm/xiangmu/llama.cpp/build-hip-rpc-official/bin
env LD_LIBRARY_PATH=. ./llama-cli --list-devices
```

With RPC:

```text
env LD_LIBRARY_PATH=. ./llama-cli \
  --rpc <NODE_IP>:50053,<NODE_IP>:50053,<NODE_IP>:50053,<NODE_IP>:50053 \
  --list-devices
```

#### 15. Why Vulkan was unsuitable for this five-node Kimi deployment

This early use of the Vulkan backend was able to load the model, but the inference was extremely slow or near card-dead, showing:

```text
Prompt: 0.0 t/s
Generation: 0.0 t/s
```

It's the opposite.

- Official examples of AMD use HIP backend and ROCm.

- Previously, the eight DeepSeek-V3.1-Q4 series had been running under Vulkan for about a year.`5 tokens/s` However, this does not mean that the Kimi-K2.5 Q2 Vulkan is stable.

- The Kimi-K2.5-Q2 model is different in size from the MoE access mode and is more sensitive to the RPC, UMA/GTT, and backend.

The reason for HIP's final selection:

```text
1. HIP 是 AMD 官方教程路径。
2. HIP 下可以直接暴露 ROCm UMA/GTT 设备总量。
3. 修复 amdgpu-dkms 后，HIP total 能达到 120000 MiB。
4. Kimi 已实测成功加载并达到 8.2 t/s generation。
```

Conclusion: The current environment recommends using the backend of the HIP, and it is not recommended to continue using the Vulkan for the Kimi-K2.5-Q2 five-engine main path.

#### 16. Frequently Asked Questions and Treatments

##### 16.1 dmesg is 120000M, but llama.cpp is only 63215 MiB.

Check it out:

```text
sudo dmesg -T | grep -Ei 'GTT size has been set|TTM size'
modinfo amdgpu | grep -E 'filename:|version:'
dpkg-query -W 'amdgpu-dkms' 2>/dev/null
```

If you see:

```text
/updates/dkms/amdgpu.ko.zst
GTT size has been set as 125829120000 but TTM size has been set as 66286690304
```

How to deal with it:

```text
sudo apt-get remove -y amdgpu-dkms
sudo reboot
```

##### 16.2 rpc-server log is still Total VRAM 63215 MiB

Don't keep running Kimi. Repair the worker node first:

```text
cat /proc/cmdline
sudo dmesg -T | grep -Ei 'GTT memory ready|TTM size'
modinfo amdgpu | grep -E 'filename:|version:'
cd /srv/llm/xiangmu/llama.cpp/build-hip-rpc-official/bin
env LD_LIBRARY_PATH=. ./llama-cli --list-devices
```

The goal is to get from the plane's location.`llama-cli --list-devices` It's like:

```text
ROCm0: AMD Radeon Graphics (120000 MiB, xxxxxx MiB free)
```

##### 16.3 Domestic failure or memory occupancy

Do not blindly open:

```text
GGML_CUDA_ENABLE_UNIFIED_MEMORY=1
```

Previously, using this environment variable on the Kimi large language model led to the risk of severe memory stress and crashes on the host.

It suggests:

```text
1. 修复每台机器的 120000 MiB total，不要靠强行 unified memory 绕过。
2. 主机 tensor split 少分配。
3. 首次验证使用 -c 512、-b 32、-ub 8、-fa off。
4. 确认小上下文成功后，再扩大 context 和开启 FA。
```

##### 16.4 Loading slowly is not cardboard.

Not necessarily. Kimi's directory about `350G` The first load requires large weights to be layered and sent to the remote RPC.

It's not easy to see if it's moving.

```text
cat /proc/<pid>/io
ss -tinp | grep -A1 -E '192\.168\.1\.(12|13|14|64):50053|llama-cli'
```

If you `read_bytes ` Growth, or some RPC connection `bytes_sent` It's still burdened with growth, which means it's still burdening.

##### 16.5 No route to host immediately after restarting SSH

After rebooting the USB4/Thunderbolt bridge, it took time to rebuild the chain, and it was only a matter of time before:

```text
No route to host
```

It doesn't have to be failure. Wait 10 to 30 seconds and then ping:

```text
ping -c 1 -W 2 <NODE_IP>
```

##### 16.6 `.64` The GRUB parameter is repeated

There was a time.`/proc/cmdline` In the middle parameter repeat:

```text
ttm.pages_limit=30720000 ... quiet splash ttm.pages_limit=30720000 ...
```

Recommended cleaning `/etc/default/grub ` It's just `GRUB_CMDLINE_LINUX_DEFAULT` In this regard, I would like to emphasize the following:

```text
GRUB_CMDLINE_LINUX=""
```

And then:

```text
sudo update-grub
sudo reboot
```

##### 16.7 ROCm recognizes GPUs but cannot load to GPUs

Priority checks:

```text
ls -l /dev/kfd /dev/dri/renderD*
groups
rocminfo | grep -i gfx -m 5
modinfo amdgpu | grep -E 'filename:|version:'
cd /srv/llm/xiangmu/llama.cpp/build-hip-rpc-official/bin
env LD_LIBRARY_PATH=. ./llama-cli --list-devices
```

This experience: The ROCm runtime version does not necessarily mean that a large language model can be loaded, and the core amdgpu module path and TTM actual limits must be correct.

#### 17. One-click checklist

Run locally on each machine:

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

Qualifying criteria:

```text
1. cmdline 包含 ttm.pages_limit=30720000 和 amdgpu.gttsize=120000。
2. modinfo amdgpu 指向 kernel/drivers/gpu/drm/amd/amdgpu/amdgpu.ko.zst。
3. dmesg 没有 TTM size 66286690304 告警。
4. amdgpu-dkms 不应处于已安装并生效状态。
5. llama-cli --list-devices 显示 ROCm0 total = 120000 MiB。
```

Host checks the RPC:

```text
cd /srv/llm/xiangmu/llama.cpp/build-hip-rpc-official/bin

env LD_LIBRARY_PATH=. ./llama-cli \
  --rpc <NODE_IP>:50053,<NODE_IP>:50053,<NODE_IP>:50053,<NODE_IP>:50053 \
  --list-devices
```

Qualifying criteria:

```text
ROCm0 total = 120000 MiB
RPC0 total = 120000 MiB
RPC1 total = 120000 MiB
RPC2 total = 120000 MiB
RPC3 total = 120000 MiB
```

#### 18. In order of deployment

The recommendation is strictly executed in the following order:

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

#### 19. Recommendations for formal service deployment

If you want to `llama-server` An OpenAI compatible API is offered externally, and recommended that split and RPC parameters be used first:

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

If the official service is unstable, the first fallback is:

```text
-c 4096
-b 32
-ub 8
-fa off
```

Stabilisation and incremental increase.

#### 20. References

- How to run a one trillion parameter LLM locally on AMD `https://www.amd.com/en/developer/resources/technical-articles/2026/how-to-run-a-one-trillion-parameter-llm-locally-an-amd.html`.

- llama.cpp RPC documentation: `tools/rpc/README.md`.

- This repository already has AMD 395 compilation documentation: `AMD395-BUILD-GUIDE.md`.

- The repository already has RPC deployment documentation: `DEPLOY-GUIDE.md`.

The key values in this article are derived from the measured:

```text
ROCm/HIP: 7.2.1 / 7.2.53211-e1a6bc5663
Kernel: 6.17.0-35-generic
llama.cpp build: b9557-0f7fada56
Kimi test: Prompt 19.3 t/s, Generation 8.2 t/s
Qwen test: Prompt 40.3 t/s, Generation 21.3 t/s
```

Unnamed page ((private page links are not public))

## R24 · AMD 395 llamcpp+rpc compilation process

### AMD Ryzen AI Max+ 395 compilation deployment guides

#### 1. Preparation of systems

##### 1.1 TTM memory optimization

In the BIOS, set the iGPU Memory Size to 512MB, and then modify the kernel parameter:

```text
sudo nano /etc/default/grub
```

It will be `GRUB_CMDLINE_LINUX_DEFAULT` Changed to:

```text
GRUB_CMDLINE_LINUX_DEFAULT="quiet splash ttm.pages_limit=30720000 amdgpu.gttsize=120000"
```

Updated and restarted:

```text
sudo update-grub
sudo reboot
```

After rebooting verification:

```text
sudo dmesg | grep "amdgpu.*memory"
# 期望输出：
# amdgpu: 98304M of VRAM memory ready
# amdgpu: 120000M of GTT memory ready.
```

##### 1.2 Install the ROCm 7.x

```text
wget https://repo.radeon.com/amdgpu-install/7.0.2/ubuntu/noble/amdgpu-install_7.0.2.70002-1_all.deb
sudo apt install ./amdgpu-install_7.0.2.70002-1_all.deb
sudo apt update
sudo usermod -a -G render,video $LOGNAME
sudo apt install rocm

export PATH=$PATH:/opt/rocm-7.0.2/bin
export LD_LIBRARY_PATH=/opt/rocm-7.0.2/lib
```

Reboot after installation is complete.

##### 1.3 Install compilation dependency

```text
sudo apt install cmake build-essential git ccache libibverbs-dev patchelf libssl-dev -y
```

|dependency package|Useful|
| --- | --- |
| cmake |Building systems|
| build-essential |GCC compiler|
| git |Version controls|
| ccache |Compilation cache to speed up repeat compilation|
| libibverbs-dev |RDMA network transmission support|
| patchelf |Modify the library search path for binary files|
| libssl-dev |OpenSSL development library, which provides HTTPS support for llama-servers|

#### 2. Build llama.cpp

##### 2.1 Access to the source code

```text
git clone https://github.com/ggml-org/llama.cpp
cd llama.cpp
```

##### 2.2 configuration CMake

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

Parameter explains:

|Parameters|Notes|
| --- | --- |
| -DGGML_HIP=ON |Enable the backend of the ROCm HIP and run inference on the AMD GPU|
| -DGGML_RPC=ON |Enable the backend of RPC communication and support multi-node sequencing|
| -DGGML_HIP_ROCWMMA_FATTN=ON |Enable the rocWMMA Flash Attention to speed up the attention calculation|
| -DAMDGPU_TARGETS="gfx1151" |Specify the target GPU architecture (Radeon 8060S / RDNA 3.5)|
| -DGGML_LTO=ON |Optimizing and reducing binary volume when linking|
| -DGGML_CCACHE=ON |Compilation cache, repeat compilation speed up|
| -DGGML_BACKEND_DL=ON |Load the backend dynamic library|
| -DGGML_NATIVE=OFF |Turn off Instant Optimization ((not compatible with BACKEND_DL, must be turned off)|
| -DLLAMA_OPENSSL=ON |The system uses OpenSSL to provide HTTPS support.|

> **Please note:** Do not use `-DLLAMA_BUILD_BORINGSSL=ON` This option allows you to download BoringSSL from the network, which is easy to overtime in a domestic network environment. OpenSSL is an alternative to OpenSSL.

Configuration Successfully Confirm the following output:

```text
-- ccache found, compilation results will be cached.
-- HIP and hipBLAS found
-- Including HIP backend
-- Using RPC backend
--   RDMA transport enabled (auto-detected)
-- Found OpenSSL: ... (found version ...)
```

##### 2.3 compilation

```text
cmake --build build --config Release -j$(nproc)
```

After the compilation is complete, the binary file is located at the bottom of the page.`build/bin/` The directory.

> **Compilation Warning:** It's possible that compilation will occur.`UI: download bundle.css failed: Timeout was reached ` Warning, this is a front-end resources download failure of the llama-server built-in Web UI (the domestic network cannot access HuggingFace), **It does not affect compilation and inference functionality.**. The OpenAI API interface on the llama-server is completely normal, but the Web UI page cannot be opened. If you want a Web UI, you can download it manually from llama.cpp GitHub releases `tools/ui/dist` resource bundle.

##### 2.4 Verified compilation results

```text
./build/bin/llama-cli --list-devices
# 期望输出：
# ROCm0: AMD Radeon Graphics (xxxxx MiB, xxxxx MiB free)
```

#### 3. Repair binary paths must be executed before they are distributed to other machines)

##### 3.1 Explanation of the problem

RUNPATH of the compilation product by default is written as the absolute path of the compilation machine:

```text
RUNPATH: /srv/llm/xiangmu/llama.cpp/build/bin
```

If you copy directly to other machines, you can't find a dynamic library and run it.

##### 3.2 Modify the relative path with patchelf

```text
cd /srv/llm/xiangmu/llama.cpp/build/bin

for f in llama-cli llama-server rpc-server llama-bench llama-quantize llama-gguf-split *.so*; do
  [ -f "$f" ] && patchelf --set-rpath '$ORIGIN:/opt/rocm-7.2.0/lib' "$f" 2>/dev/null
done
```

##### 3.3 Verify the results of the changes

```text
readelf -d llama-cli | grep -i "rpath\|runpath"
# 期望输出：
# Library runpath: [$ORIGIN:/opt/rocm-7.2.0/lib]
```

After the amendment, `build/bin/` The directory can be copied to run directly under any path of the machine with ROCm installed.

#### 4. Multi-node RPC series deployment

##### 4.1 Remote nodes: 2, 3, 4... N machine)

It will be `build/bin/` After copying to each remote node, start the RPC service:

```text
./rpc-server -p 50053 -c --host 0.0.0.0
```

|Parameters|Notes|
| --- | --- |
| -p 50053 |Watch the port|
| -c |Enable local cache, accelerate model loading|
| --host 0.0.0.0 |Listen to all network interfaces|

##### 4.2 Main node (Machine 1)

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

|Parameters|Notes|
| --- | --- |
| -m |model file path|
| -c 32768 |Length of context|
| -fa on |Enable Flash Attention|
| -ngl 999 |All layers offloading to the GPU|
| --no-mmap |The model is used when the system RAM is larger than the model used)|
| --rpc |List of remote RPC node addresses|

##### 4.3 Attention

- DeepSeek-V3 and Kimi-2.5 are MoE architectures that are not supported `--split-mode tensor ` Use the default `layer` It's a pattern.

- RPC functionality is still in the conceptual verification stage, do not expose rpc-servers to the public network

- If the network card supports RoCEv2 and has libibverbs-dev installed, the compilation automatically enables RDMA transmission.

#### 5. Test script use notes

Project root directory provided `test-llama-rpc.sh` Automated test scripts support multiple operating modes.

##### 5.1 Quick reference

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

##### 5.2 Detailed model

##### Module one: `gpu` A local GPU inspection

```text
bash test-llama-rpc.sh gpu
```

The following tests are performed:

1. **Check the compilation Products** Confirmed `llama-cli `, ` rpc-server `, ` libggml-hip.so`Whether files exist and can be executed

2. **Check the RUNPATH** The binary file has been patchelf repaired to `$ORIGIN` Relative path

3. **GPU device detection** It's running `--list-devices` Confirm that ROCm recognizes GPUs

4. **Local inference tests** See if you can find the site automatically `.gguf` model (>100MB) to inference and not find

> The script will automatically skip less than 100MB of wordpress test files. If you want to test inference, please place the model in any of the following directories: `./models/`, `../models/`, `~/models/`, `/data/models/`

##### Module two: `rpc-server` Starting the RPC service terminal

```text
bash test-llama-rpc.sh rpc-server
```

Running this model on remote nodes is equivalent to:

```text
./rpc-server --host 0.0.0.0 -p 50053
```

Keep the terminal running after launch, waiting for the main node to connect.

##### Module three: `rpc-test` RPC testing sequence

```text
REMOTE_IP=<远程节点IP> bash test-llama-rpc.sh rpc-test
```

**It must be set `REMOTE_IP` Environmental variables** A remote node that has been activated by the rpc-server.

The following tests are performed:

1. Check if the remote node IP is set

2. Ping remote nodes to confirm network connectivity

3. nc check whether the remote port (50053) is accessible

4. Using the local model passed `--rpc` Parameters for sequential inference

##### Module four: `all` All tests are defaulted.

```text
bash test-llama-rpc.sh
# 或
bash test-llama-rpc.sh all
```

All the above tests are run.

##### 5.3 Dual-node sequencing of the entire process

**The machine A (main node):**

```text
# 1. 运行本地测试
bash test-llama-rpc.sh gpu
```

**The machine B (remote node):**

```text
# 2. 启动 RPC 服务
REMOTE_IP=<机器A的IP> bash test-llama-rpc.sh rpc-server
```

**The machine A (main node):**

```text
# 3. 测试串联
REMOTE_IP=<机器B的IP> bash test-llama-rpc.sh rpc-test
```

##### 5.4 Configuration Explanation

The configuration area at the beginning of the script can be modified as needed:

|Variable|Default|Notes|
| --- | --- | --- |
| BIN_DIR | build/bin |binary file path|
| RPC_PORT | 50053 |RPC monitoring port|
| SERVER_HOST | 0.0.0.0 |Address of the RPC|
| REMOTE_IP |It's empty|IP of remote nodes (pass environment variable settings)|
| PROMPT | Say hello in one sentence. |Inference test suggestions|
| GEN_TOKENS | 16 |Maximum number of generated tokens|

AMD 395 llamacpp rpc service functionality Environmental test script ((private page link not public))

## R25 · AMD 395 llamacpp rpc service functionality Environmental testing script

The test script:

[test-llama-rpc.sh]

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

Explanation of the document

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
