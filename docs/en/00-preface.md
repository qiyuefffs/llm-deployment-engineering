# Environment and evidence conventions

[简体中文](../01-deployment-foundations/00-preface.md) | **English**

[Knowledge base home](README.md) · [Complete engineering examples](engineering/README.md)

## Directory conventions

The original framework's six parts, five layers, and section numbers 1.1–1.4, 2.1–2.6, 3.1–3.6, 4.1–4.6, and 5.1–5.3 are preserved. The main framework covers definitions, component relationships, parameters, and assessment methods; platform topics explain backend details; `engineering/` retains each device's complete path from environment setup to optimization, alongside the full technical FlowUs articles.

## Fixed inputs for every deployment

|Input|Minimum information to record|
| --- | --- |
|Task|Input form, target output, maximum input/output, concurrency or rate of arrival, TTFT/tail latency/quality threshold|
|Device|CPU architecture, GPU/card number, RAM/VRAM, interconnection, drivers, kernel, allowable memory|
|Artifact|Model ID/revision, weights/index, tokenizer, template, processor, quantization configuration, and checksums|
|Software|Framework commit or version, torch/runtime, native extension, compiler, build variable or image digest|
|Workload|Data files, seeds, samples, input and output tokens, cache cooling, concurrency and request numbers|

## Run directory

```text
deployment/
├── environment/   OS, devices, dependencies, images, CMake and module paths
├── artifacts/     Model manifests, hashes, conversion and quantization commands
├── config/        Service, proxy, templates, and parameters
├── inputs/        Public inputs, expected outputs, and workload definitions
├── runs/<run-id>/ Requests, responses, logs, metrics, resources, and statistics
└── operations/    Start, stop, health, acceptance, and rollback
```

## Evidence status

|Status|Required evidence|
| --- | --- |
|device visible|System and framework device enumeration|
|Build passed|Pinned commit, configuration, and runnable binaries|
|Model executes|Loaded weights, actual output, and finish reason|
|Functional checks passed|Item-by-item comparison of fixed tasks against expected results|
|Performance checks passed|Target workload, actual token counts, successful requests, latency, resources, and thresholds|
|Ready for delivery|Cold start, error handling, shutdown, recovery, and traceable files and versions|

Providing a configuration command does not prove it was executed; a success heading does not override a failure log; successful loading does not prove that long contexts or concurrency passed. Missing historical information remains marked “not recorded”; proposed new procedures remain marked “pending testing.”

## Source records and technical corrections

The technical content of 50 related FlowUs articles is included in the hardware examples, retaining parameters, code blocks, result tables, failures, and follow-up experiments. Private passages, personal attachments, and authentication information are excluded from publication. Paths follow the public deployment conventions and node addresses use placeholders; for multiple nodes, fill in the values for each role separately.

The source contains errors concerning RTX4080 NVLink, MoE bandwidth calculations, endpoint fields, and concurrency definitions. Corrections appear at the example entry points and, where necessary, at the affected passages; recorded measurements are retained while incorrect interpretations are corrected. [Source inventory](../01-deployment-foundations/evidence/source-coverage.json) lists the retained articles, character counts, and code-fence counts.

The historical GPU/NPU experiments were not rerun in this update. [Windows CPU engineering](practice/first-service/README.md) includes files from an actual local run; the public vision card is a new test input and is not paired with fabricated GPU output. Open the relevant platform from the contents and check its versions and resources before execution.
