# On-device model to fit the records template

[简体中文](../../01-deployment-foundations/templates/adaptation-record.md) | **English**

[Return to the Knowledge System](../README.md)

Copy to your project and fill it out. Vacuum and aluminum pending testing The aluminum does not represent passed; The original log is stored as an alternative, not including credentials, device serial numbers or private entries in public records.

## 1. Objectives and constraints

- Projects/Dates/Managers:
- Real tasks and public input sources:
- Target terminal and usage methods (offline/resident/mobile):
- The first visible answer, the completion time, the threshold for success:
- Context / Output / concurrency Requirements:
- Memory, storage, power consumption/energy consumption and temperature requirements:
- In this case, the ability to adapt is not:

## 2. Accurate compatibility records

|Projects|Actual value|Evidence documents|
| --- | --- | --- |
| SoC/CPU/GPU/NPU,RAM/VRAM |To be completed| |
|OS/core, driver/firmware, SDK/runtime|To be completed| |
|Compiler/CMake, framework version/commit, backend|To be completed| |
|Model source/revision/architecture/quantization/hash|To be completed| |
|Template / Tokenizer / Generate Parameters / License|To be completed| |
|Power mode, heat dissipation, other workloads|To be completed| |

## 3. memory budget and effective configuration

- The device weights, KV/state, runtime, temporary space, surplus:
- Host RAM and System Reserves:
- ctx/slots/concurrency/logical batch/microbatch:
- KV type, Attention backend, threads and offloading:
- Start command with valid parameter log:
- The difference between estimated and measured:

## 4. Stage verification

|Verified|Status ((not tested / passed / failure / conditionally passed))|Input and evidence|Limitations|
| --- | --- | --- | --- |
|Build, assemble, initialize the backend.|Not tested| | |
|Models loaded with real devices|Not tested| | |
|Template, short/long input, multipurpose, stop|Not tested| | |
|Business quality and structured output|Not tested| | |
|API flow, cancellation and incorrect input|Not tested| | |
|Target workload performance and memory peak|Not tested| | |
|Long periods of sleep/recovery, temperature control|Not tested| | |
|Install, restart, upgrade and rollback offline|Not tested| | |

## 5. Questions and Deliveries

- Problem phenomena, minimal reproduction, root cause evidence and correction:
- Failure to support/fallback operators and quality risks:
- Context / concurrency and service thresholds for delivery:
- How to access and license the model/code/operating library:
- Install, start, stop, log, monitor and rollback inputs:
- Unfinished verification and the person responsible:

The final conclusion covers only the device, version and workload of this table; Don't push out the entire manufacturer platform has passed.
