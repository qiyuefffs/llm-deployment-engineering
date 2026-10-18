# Part VI: troubleshooting reference

[简体中文](../01-deployment-foundations/06-troubleshooting.md) | **English**

[Contents](README.md) · [Previous: List of knowledge libraries](05-knowledge-base.md) · [Appendix A: Commands](appendices/commands.md)

## 6.1 Identify the failing stage first

```text
Install → Build → Device Initialization → Read model → Allocate memory
 → Execute the operator → template / sampling → API → concurrency and running continuously
```

Find the location of the first failure and then go up and down. Save the first error and the logs before and after, and the process after the exit and disconnection is often just the result.

## 6.2 Quick reference

|The phenomenon|Common inspection directions|What do you do first?|Passed Standards|
| --- | --- | --- | --- |
|Wheels can't be installed|CPU architecture, Python ABI, and platform|See unname/Python/package tags|Packaging and Environmental Matching|
|Installed successfully but no device|Driver, rear wheel, device permissions|The system lists and then frame the small operator|It's really about doing the calculations and synchronizing.|
|CUDA/HIP building failure|Compiler, target architecture, headers, libraries|Save the first compilation Error with CMake configuration|Target Binary Build and Run|
|GPU is recognized but kernel failure|Model precision, operator, architecture goals|Small model / Simple precision control|Target model completed generation|
|Container can't see device|Host driver, container runtime, mapping|Host priorities, container re-evaluation|container inside small operator passed|
|model load failure|File loss, shard, architecture, and version|Test manifest and load errors|Full load and generate|
|loaded afterwarm-up OOM|Graphs, workspace, KV pre-allocated|Peak control and capture phases|Goal configuration ready and surplus|
|Long input / concurrency OOM|KV, prefill budget, sequence of activities|Fixed variables gradually increase|Target workloads without OOM|
|device total memory error is small|Backend budget, drivers, shared memory|Compare physical memory, Runtime, GTT, and TTM|Runtime availability based|
|Generate a code/character tag|Templates, tokenizers, artifact conversions|Minimum official format request|Officially and Stop Right|
|It's just reasoning, not legitimacy.|Exit limits, reasoning configuration, analytics|Check the finish_reason with the original response|Complete answers to the task|
|HTTP 404/ wrong model|Port, path, other names|Health and Models, then request|API paths and names match|
|Non-flowing available, flowing cardboard|SSE, agent buffer, client|Curl-N direct connection|Sections arrived and ended correctly|
|throughput increases but experience is poor|Queueing, lengths, ITL, and caching|Analysis of TTFT and tail latency|Effective throughput under target SLO|
|Multi-GPU hanging up/slow|Topology, communication libraries, P2P, and partitioning|All-reduce, smaller model|Communication with the target model|
|NPUs can list but cannot generate|Graph compilation, operators, shapes, and precision|See compilation and generated boundaries|Create a real token, not just a compilation|
|Mac text for visual failure|Plug-in visual capabilities and preprocessing|See specific versions and encoder errors|The image assignment passed separately|
|Continuous running slows|Temperature controls, page changes, leaks, resources, competition|Simultaneous recording of frequency/temperature/memory|Steady state performance maintained|

Each amendment addresses only one proven direction. Don't see GPUs that don't work, reinstall drivers, frameworks, and models at the same time, making it impossible to know which changes are effective.

## 6.3 GB10: why can a build fail with the correct architecture?

E01 saves a specific vLLM submission error with the CUDA13 combination:

```text
Instruction 'cvt with .e2m1x2' not supported on .target 'sm_121'
```

It refers to the compatibility of compilation instructions with the target architecture. Source notes used `TORCH_CUDA_ARCH_LIST=12.0` Bypassing a specific path, but this is only an attempt to submit, and cannot be promoted to all GB10 programs with 12.0.

Verification sequence: Confirm device computing capability → See if the framework supports the architecture → Find the specific failure kernel with precision → Verify CUDA and source code Repair → Only reconstruct the relevant environment → Complete the model run. It's called llama.cpp.`CMAKE_CUDA_ARCHITECTURES` The PyTorch variable cannot be confused with the same switch.

## 6.4 Missing build dependencies: CURL errors

The GB10 llama.cpp record of the E10 is missing from the CURL development header. The distinction between curl systems is that curl compilers and curl compilers can find the libcurl header and the curl: the former does not represent the latter.

Check the dependency indicated by the CMake error when processing, the corresponding development packet installed on the current OS, or the fact that the source code document is fixed to close the functionality that is not really needed. Keep the modified CMake output and reconstruct it. Don't copy one from another system.`.so` Fill in the running directory.

## 6.5 AMD shared memory: identify the allocation limit

The physical capacity of the E03 is large enough, but the device detects about 63GB and assigns about 87GB of failure at a time; The actual TTM limit is lower than the GTT request value. The correct path is compared in three layers: system physical memory → driver / core budget → HIP allowable amount seen.

```bash
free -h
rocminfo > rocminfo.txt
```

Read the available GTT/TTM and device logs according to the driver version. Before modifying the kernel, DKMS, or driver, the root cause and recovery methods are first confirmed, and the knowledge system does not provide a set of GRUB rewriting scripts for all machines.

After repair, first check the device to see the total, then the small model, then the target model short input; Finally, add context and API workload. Capacity issue not automatically proven multi-node performance.

## 6.6 Intel: separate enumeration, compilation, and generation

In E02, OpenVINO can list NPUs, but INT4 compilation failure; INT8's run of 420 seconds was stopped overtime, exit 124. Exit124 indicates the outer layer overtime, not the speed of the output token.

Check to record: plugin version, model IR, precision, input shape, compilation error, whether a token has been generated. Passed GPU routes running the same task can help differentiate between model materials and NPU execution problems, but cannot prove that NPU must support it.

Another version of the GGUF + OpenVINO version is trying to get to the bottom of this.`CPY/cache_r` This is the same path failure, while supporting the IR + GenAI GPU is successful. The two routes are different artifact and executor, so don't just change the device.

## 6.7 Mac: the build succeeds but the model fails

Special branches of E05 can be compiled, but specific FP4/FP8 models are triggered.`Asserting on type 42`. First, determine the GGUF tensor type and Metal kernel implementation, and then determine whether the model file is incomplete or the current backend is not supported.

Vllm-metal has a clear error in the group data:

```text
NotImplementedError: Multimodal encoder execution is not wired on Metal yet.
```

This refers to the visual capability gap in this version. Changing the image URL, adding context, or improving memory can't fix the missing encoder. Record the available text, see fail, and choose the path to support the task.

## 6.8 Successful API response, unusable result

Check the status of HTTP → JSON structure →`finish_reason`→ Reasoning / English → Task Answering. The inference model may only be reasoned when the token limit is reached; Structured output may be legitimate JSON but it is semantically incorrect.

If the original response is correct and the application is not, check the client resolution; If the original response is not correct, check the model pattern, template and output budget. Save the original response, and don't use the UI blank to judge if the model is bad.

Intel's short generated record stops at the reasoning stage, which is the quality boundary to be maintained: the speed field has a value, and does not mean that the business answer has been completed.

## 6.9 Why is the first token slow with multiple requests?

First, break down the rows, prefill and transmit. In E01's 200 requests, the service activity sequence budget is 4, with an average TTFT of about 148 seconds. The waiting queue and the arrival pattern should be looked at first and the processing time of each input analysed.

This can be done as follows: single request of the same length → fixed concurrency scan → control of the arrival rate → sudden recovery. Only concurrency increases slower, prioritizing capacity checks and scheduling; The single request is also slow, then check the backend, input length and kernel.

## 6.10 Communication failures across devices

Ensure that each device is calculated correctly and then run. [Communication Check the script](../01-deployment-foundations/examples/all_reduce_check.py). Check the device number, rank, network, interface, communication library and topology, and don't run all the processes to determine communication correctly.

llama.cpp RPC also checks the worker port, if the host can connect, if the backend is initialized, if each node model is allocated to the network path. compilation contains RDMA that is not equivalent to runtime using RDMA; In the absence of a single-machine baseline, the acceleration ratio is not calculated.

## 6.11 What to save after troubleshooting

Retain the minimal triggering input, versions and final command, first error, resource state, diagnostic evidence, fix, retest results, and rollback procedure. The public only retains the necessary sanitization content.

At least run the minimal request with the original trigger input after the bug is fixed; When modifying the underlying components, add the corresponding functionality and return the target workload. Repeatable conclusions are replenished to the knowledge layer, and the whole process is preserved. [Project retrospective](04-project-review.md).
