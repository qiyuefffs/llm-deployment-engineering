# Environmental packaging, switching off and rollback

[简体中文](../../../01-deployment-foundations/chapters/delivery/environment-operations.md) | **English**

[Contents](../../SUMMARY.md) · [General Chapter of Engineering Delivery](../../02-capability-layers/05-engineering-delivery.md) · [Interfaces and monitoring](api-monitoring.md)

## Overview of this chapter

A set of deployments that can only be run by the author's current terminal and cannot be easily passed on to others. Delivery to fix the environment, artifact, configuration, start entry and restore steps. The next time you restart, change your device or upgrade, you can still decide which combination is running.

This chapter is based on Docker Runtime, dual-GPU container, Ascend image and Intel service records in FlowUs. The example consists of a unified local loop address and a public positioning path; Container and systemd configuration are template descriptions, and do not represent system installation or service registration in this round.

## 1. Fixed five-category identity

Hardware identity includes model, CPU architecture, memory and device topology; System identity includes system, kernel, driver and runtime; Framework identities include source code, submit, build options, dependency and image; Model identity includes repository, revision, file summary, template and conversion; Running identities include final commands, parameters, input and result directories.

Just write CUDA13, the latest version of vLLM, Qwen quantization, the version of CUDA is not enough to reproduce. Image tags can also be moved, and official delivery should record digest. Model names are used for API routing and cannot replace model artifact identities.

## 2. What is the relationship between the virtual environment and the container?

Python virtual environment isolates Python dependency for experimentation and light deployment; It does not separate the host driver, kernel and GPU device. Containers can encapsulate user mode dependency, file system and input, but still dependency host device, driver and container runtime support.

NVIDIA containers used `--gpus ` Select a visible device, which does not represent a hard VRAM quota for the device. the container `--memory` The main constraint is host memory and cannot replace frame memory budget. The limitations of unified memory and dedicated VRAM platforms should be confirmed by the actual mechanism.

Ascend records by author `vllm-ascend:v0.10.0rc1-310p ` is a combination of chip and plug-in support and should not be substituted for any `latest` The results of the tests were later based on the original results.

## 3. Start a minimal container template

Prepare your own, verified image digest and confirm that the model directory is readable. The following is not a fictional digest.`<verified-digest>` The value that needs to be replaced with the actual saved value:

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

The template assumes that image input is a vLLM API service; Other images must be verified by ENTRYPOINT and CMD. The container binds all the interfaces, the host maps back to the loop, the client passes the host8001 access. The model only reads uploads, and the resulting directory can be uploaded when needed.

The front-end runs to check for loads and first errors, and then takes into account security and restart strategies. Keeping `docker inspect` the necessary image identity, attachment, device and command fields; Public copies do not include environmental credentials and private addresses.

Stop using specified instances `docker stop llm-text-service`. Do not use shortcuts that affect all containers or delete the entire model directory. The restored image, model and configuration are still validated.

## 4. How is the Linux front-end service delivered to systemd?

First, let the command and API pass, and then write the service configuration. The following examples are available: `llm` User, binary and model have been installed; The creation of user and file permissions is done by the target machine operation and maintenance process.

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

Save the actual configuration as `/etc/systemd/system/local-llm.service` After that, run according to the permissions of the target machine:

```bash
sudo systemctl daemon-reload
sudo systemctl start local-llm.service
systemctl status local-llm.service --no-pager
journalctl -u local-llm.service -n 100 --no-pager
curl --fail-with-body http://127.0.0.1:18080/health
```

Process active is not the same as model ready, but requires a healthy and short request check. Confirming resources and deciding whether to execute recovery actions `systemctl enable ` It's open. Stop using `sudo systemctl stop local-llm.service` When maintaining, verify that no automatic start-up causes resources to compete.

The service in the author's Intel records had to be stopped by the task to release shared memory, but remained enabled. This reminds us to record simultaneously whether the pump is currently running and whether the pump is self-igniting after restarting, both of which cannot be rewritten.

## 5. Upgrades and rollbacks recorded by change

Before upgrading, save verified configuration, model, list, environment, functionality and performance baseline; New versions have been verified in independent environments or independent instances. Do not directly cover the only available binary and dependency. When the same port is needed, arrange switching and stopping to avoid request misconnection.

Rollback conditions are pre-written, such as functionality errors, increased error rates, tail latency, overhead or continuous increase in resources. The rollback steps should be able to restore the old environment and artifact and then re-examine the health, functionality and small workload. Only change the configuration file back, but continue to use the new model or new kernel, not including restoring the old combination.

## 6. To what extent should an activation manual be written?

Readers should be able to find the boot entry, environment activation, work directory, port with aliases, ready standards, logs, stop methods, overtime and restore configuration. Each step describes the expected phenomenon and check-in after failure.

First downloads and model uploads do not include steady state inference speeds, but deployment time and cold start. On-device applications should also specify offline conditions, cache size, residual disk and shared memory requirements. Delivery packages should not be accompanied by more than one GB weights cache or private running log.

One last exercise from a clean terminal: activation, environment, test model, start, request, save product, stop, and restore. The next engineer has a reliable starting point to complete this chain.

## How to set up a maintainable deployment directory

A common problem in FlowUs multi-platform engineering is the stacking of source code, virtual environments, models and temporary logs: branches that cover the product, imported from the wrong directory at launch, and don't know where a GGUF was converted weeks later. The delivery directory should identify the life cycle of these objects.

```text
/srv/llm/
├── releases/
│ ── engine-r1/ Verified procedures and support libraries
│ ── engine-r2/ Verified version
├── configs/
│ ── baseline.env Environmental variables, public copies only technical fields
│ ── baseline-command.txt Full start entry
│ ── candidate-command.txt Changes to the candidate
├── manifests/
│   ├── hardware.json
│   ├── packages.txt
│   └── model-files.sha256
Requests / Fixed public functionality / error input
The results/run-id/follow logs, responses, resources and conclusions
Cache/Cache can be reconstructed and budgeted
/srv/models/model-release/ Model artifact independently managed
```

The path is publicly agreed, and the reader can change to their own disk, but the files, uploads, and verification commands must be changed together. The model may be large, and delivery repositories usually provide downloads, revisions and summaries. The cache can be reconstructed and cannot be used as the only proof of results.

The program version and model version are named after each other and combined by a run-id. The same model replaces the kernel, and the same engine replaces the template. Don't just change the name of the report file into a new version of the file to cover the original file.

## Eight, save the valid parameter to a running card.

A running card should allow the reader to start the current program without reading the entire historical error. It records the final configuration, and values that have been tried but abandoned remain in the experimental record and do not continue to be mixed into the default commands.

|Fields|Fill in the content|Why is it necessary?|
| --- | --- | --- |
|Artifact|Repository/revision, format/quantization, and file checksums|Determine which model is running|
|Engine|Commit/package version, image digest, backend|Confirmation of the implementation|
|functionality|Text/images/audio, templates, output settings|Preventing cross-capacity inference|
|resources|ctx, seqs, batch, KV, and memory budget|Determine the boundaries of the workload|
|Produced|temperature, top_p, reasoning mode, stop sequences, and output limit|Keep quality comparable to workload|
|Interface|Linking addresses, ports, aliases, routes|Avoid requests and wrong services|
|acceptance testing|Input, success, quality, latency and resources Thresholds|Determine when to delete the default|
|Rehabilitation|Previous version: Start/Stop and test|Make sure to fall back|

For example, the GB10 FP8 running card writes seqs4 with 200 request suddenly, and can't write only 200 bits of concurrency. Intel TTS writes Talker/Decoder=NPU, CP=CPU, not just device=NPU; Apple's text service clearly stated that the visual encoder failed. The operating card is capable of transmitting simultaneously with the border.

## How to confirm that resources have been released after the service is stopped

Process stopping, port release, model buffer recovery and subprocess termination are not exactly the same events. In the Intel NPUW original experiment, the compilation subprocess after disconnection was still ongoing, and subsequent CPU testing was thus disrupted.

Instances that the service administrator stops managing themselves are then checked for specified processes and their subprocesses, port and resource curves. The processor/container managed by systemd is usually easy to close, but still needs to verify the actual behavior. The front-end Ctrl+C should also see if the service has completed the exit, instead of starting the next round directly after the terminal is closed.

Do not use blur matching batches to kill all Python, all rpc-servers or all GPU processes. On multi-model machines, this would disrupt other running and contaminating experiments. Record the PID, container name or unit that has been created and verify them after stopping instead of guess the process name.

If resources are not backed up, first identify the device, statistical latency, file page cache, framework processes that are still alive and genuine leaks. The Linux page cache is part of the system's recyclable memory, which is not the same as the model but also contains the same amount of non-recyclable RAM. It's not necessary to have global drop_caches for every round of optimization.

## Write a rollback as an example of a failure TTS experiment

The entire NPU Code Predictor experiment was hot RTF0.723, but the audio only translated one word and could not be used. Rational rollback records include:

1. Keeping failure, environment, patches, fixed inputs, WAV summaries, logs and quality results easy to locate.
2. Restore the default pipeline to a validated CPU/NPU mixed path, restoring corresponding dependency and configuration.
3. To retrieve the identity of the file, run again an original quality input, and check the content with a natural ending.
4. Reviewed resources, ports and short workloads to confirm no remaining candidate processes.
5. To mark the candidate as a quality failure, the default start entry only refers to the baseline.

The original construction has restored the upstream pipeline. This rollback does not remove the optimization value: the fixed shape and failure output form the material for subsequent numerical checks, but the default service remains available in combination.

Mac vllm-metal images to EngineDead also need to restore the process: stop the instance, restart the text service, confirm the health of the shortcuts, and then route the image task to a past visual verification implementation. Simply returning healthy 200 can't replace the actual generated checks.

## 11. What content needs to be upgraded

driver, device, kernel, resources and continuous stability; Models, interfaces and performance are re-measured by engine changes; Model/Quantization Variable re-measurement of quality and resources; Template /processor changes to retest input and output; Scheduling Budget changes re-measure target length, mixed workload and tail latency.

It is not necessary to run the entire set of hardware benchmarks every time a document is corrected, but the actual execution of the portfolio changes should cover the affected links. Linking the change effects to corresponding acceptance testing can reduce meaningless over-measurements and avoid switching all services as soon as you're done.

## 12 - Give the shortest route to the next user

On the delivery front page, write the support range and input, then give the environment preparation, model, access, start, functionality, check, result location, stop, sort and restore. Detailed performance Analysis links to independent reports, and the default command retains an authoritative version.

To allow the recipient to execute in full from a new terminal in a step by step manner; If you have to ask for a private path, environmental variable, unsaved patch or input file, add this dependency to the public material. The sustainability of real engineering comes from these details, not just from a container image.
