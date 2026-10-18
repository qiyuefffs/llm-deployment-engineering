# Layer 5: engineering delivery

[简体中文](../../01-deployment-foundations/02-capability-layers/05-engineering-delivery.md) | **English**

[Contents](../SUMMARY.md) · [Environment/off/rollback](../chapters/delivery/environment-operations.md) · [API/monitoring/acceptance testing](../chapters/delivery/api-monitoring.md)

## 5.1 What this layer addresses

Once generated, it is still necessary to decide how to provide and maintain this capability. Single-machine CLI, application built-in inference, local HTTP services and multi-copy online services use the same model calculations, but different lifecycle and maintenance requirements.

|Form of deployment|Applicable needs|The ability to adjust|
| --- | --- | --- |
|CLI/ batching|Offline verification, file processing, fixed tasks|Input, output, exit, log, run again|
|Embedded applications|Desktop or mobile offline functionality|Model distribution, memory, lifecycle, cancellation and UI response|
|Single-machine HTTP service|Multi-client sharing of a model example|request, calibration, queue, overtime, flow protocols, concurrency and limit flow|
|Multi-copy/multi-node|Expanded, high availability or large language model parallelism|Routing, health, capacity, communication, upgrades and failure recovery|

Multiple copies typically make multiple instances of service different requests; Model parallelism allows multiple devices to execute the same model together, and the two solve different problems. It can also be used in combination, but must calculate memory, communication and service capacity separately.

### Questions to answer after deployment

|Issue|Engineering requirements|Check it out|
| --- | --- | --- |
|Can it be rebuilt?|Fixed model, dependency, image/source code and input|Clean environment cold start|
|Can you serve?|Fixing model IDs, protocols, functionality and errors|Health, model list, normal/flow/error/cancel|
|Can you observe?|Use the same run-id/time axis as request and resources|Indicators, logs, request by request|
|Can you recover?|Only stop the target instance and keep the valid old version|Stop, port/device, release, rollback and return|
|Acceptance testing|Functionality, quality, performance, resources are all undervalued.|Passed / failed / not tested|

## 5.2 Delivery capability map

```text
Environmental packaging: Docker / uv or Conda / systemd / as needed Kubernetes
Service interface: OpenAI protocol / model routing / SSE / Certification and limited flow
Engine metrics / Prometheus / resources / sample / log
Pressure verification: Engine benchmark / HTTP workload / quality set / steady state and failure recovery
Running documentation: install / configuration / start / stop / acceptance testing / rollback
```

|Subheadings|It must be recorded|Common Faults|
| --- | --- | --- |
|container|Image tag+digest, device, model, upload, port, IPC/shared memory|Only the latest host has a GPU, but the container is not accessible.|
|Python environment|Expand and import paths for interpreters, locks, torch/runtime|pip to another environment, source code, directory coverage|
|Process management|Target PID or instance name, ready, exit code, log|Pkill broad compatibility, port and device remaining|
| SSE |Buffer agents, client flow read, end, cancel, overtime|role events when correct, snippet when token, buffer, false flow|
| metrics |KV, request latency/error, throughput|Mixed metric names, units and windows for different versions|
|resources|VRAM/RAM/RSS, swap, temperature/power consumption, each rank|UMA overlapping, just using it.|
|rollback|Old image / dependency / model / template / configuration|Only rollback Python does not rollback native extensions or templates|

### Four categories of acceptance testing

1. Functionality: input processing, full output, API, SSE, cancellation and error.
2. Quality: Fixed theme sets, structured fields, visual/audio content; This is a comparison to the original precision/old version.
3. Performance: actual tokens, SLO, concurrency/reach rate, resources, peak, steady state.
4. Running: cold start, stop, restart, log, upgrade/rollback and restore.

Intel's full NPU TTS performance is upgraded but the content is incorrect, hence rollback; Kokoro CPU real-time is passed and the RSS target is failure, so it is generally not possible to write only CPU passes. Response [Complete engineering records](../engineering/intel-arc-npu.md).

## 5.3 Seven deliverables for each project

|Delivery terms|Documents / Content|Audit issues|
| --- | --- | --- |
|1. Hardware environment|environment.json/txt, device/driver/Runtime/topology/capacity|Specifically on which device to execute|
|2. Model information|Manifest, revision, SHA256, template, and quantization/processor|What artifact is used, if the file is complete|
|3. Framework selection|Version/commit/digest, kernel, build and compatibility|Why execute, what is the alternative route?|
|4. Deployment program|Install, start, health, request, stop, restore|Whether there is a complete execution order|
|5. parameter configuration|Final-command, configuration, environment variables, and valid log|What was actually used at runtime|
|6. load testing results| inputs,requests,responses,metrics,resource,summary |Can the numbers be calculated from the original results?|
|7. Questions and Optimized Conclusions|Baseline, changes, failures, rollbacks, restrictions and pending testing|What is the solution and what are the conditions?|

The resulting directory is distinguished by run-id. Keep old combinations before upgrading and repeat the same input with SLO checks after upgrading; Unverified functionality not tested. template : [Adapted records](../templates/adaptation-record.md), [Experimental records](../templates/experiment-record.md), [Project retrospective](../04-project-review.md).
