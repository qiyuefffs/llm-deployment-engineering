# Part IV: project retrospective

[简体中文](../01-deployment-foundations/04-project-review.md) | **English**

[Contents](README.md) · [Previous: Core Concepts](03-core-concepts.md) · [Next section: List of knowledge libraries](05-knowledge-base.md)

Project retrospectives are used to preserve engineering facts that can continue to work: objectives at the time, operating combinations, problems encountered, modifications to the basis and final boundaries. Complete, order and digital link authentic documents according to the ten structures of the manuscript.

Can be copied when filled in [Deploying a project retrospective template](templates/deployment-review.md) and [Adapted records](templates/adaptation-record.md), [Experimental records](templates/experiment-record.md) keep them in the same project directory.

## 4.1 Standard project retrospective

### I. Project background

Explain who is experiencing a problem on what device, on what mission. Write down the input form, the required output, the target length, the concurrency and latency constraints. Don't start with introducing framework functionality.

```text
Requirements: Create local text on a 16GB shared memory device.
Input: Public Short Text and Subsequent Prepared Long Text Tasks.
Outputs: Complete answers, running indicators and deployment steps.
Boundaries: Pre-verification of text, not making visual and NPU success as the default conditions.
```

If a threshold value has not yet been established, it cannot be added to a seemingly reasonable number, i.e. it has been reached.

### II. Hardware and environment

It is used for recording models, CPU architecture, physical memory, backend memory, system/core, driver, runtime, compiler, Python, framework and source code/image identity. Order to collect [Hardware layer](02-capability-layers/01-hardware-backends.md).

Version changes are recorded separately, especially drivers, runtime, and framework threes. In the end, we should be able to judge which environment a result corresponds to.

### III. Model and inputs

It records models, repositories, revisions, licenses, quantization, conversion processes, tokenizers, templates, shards and validations. Information on the source, format, size and preprocessing of imported materials; Private samples are replaced by authorized public or sanitization samples.

### IV. Inference framework

Write the reasons for choosing with alternate routes, retaining the help of switches, installation commands, final environments, and procedures. It supports lithium quantization, lithium functionality, and lithium inspection.

### V. Deployment design

Provide execution order, start commands, port with aliases, resources, budget, health checks, normal request and stop methods. Each step describes the input, output and verification methods.

### VI. Issues encountered

The problem record at least includes trigger inputs, first errors, failure stages and effects. Distinguish between observation and speculation: erroneous observation that a kernel may not support a speculation is a validating hypothesis.

### VII. Troubleshooting

Button proof → Assumptions → Checks → Modifications → Repeat writing Only the steps to help understand the root cause are retained; It's hard to see the ultimate basis for trying to avoid stacking up all the attempts.

|Fields|Examples|
| --- | --- |
|The phenomenon|GPUs can be compiled, NPU model compilation failure|
|Stages|Compilation, not yet generated|
|Evidence|Compilation error with full log location|
|Suppose|Current plugins/graphs/form combinations are not supported|
|Check it out|It runs on the same model as the GPU. Verified version and operator support|
|Conclusions|GPU routing can continue and the NPU combination fails|

### VIII. Optimization experiments

First, the baseline, then the changes. Each group keeps the model, input, output, concurrency, sampling, cache and timing consistent. Write combinations when multiple variables are connected. Template see [Experimental records](templates/experiment-record.md).

### IX. Performance and quality

Keep the total number of requests, successful failures, actual tokens, total time, throughput, TTFT/TPOT/ITL, tail latency, resources and quality. The reason for not applying indicators. Semantic quality is not replaced by speed, scanning is not replaced by statistics.

### X. Conclusions and limitations

List the available ranges, failures, combinations, not tested items and the next steps. Uncertain results are kept for verification; Each number in the external conclusion should be dated to the original document or a clearly marked historical transcript.

## 4.2 Excerpt based on the Intel engineering record

The following is compiled from the historical records of E02 to show the depth of filling; The entire original running file was not followed by a public note, and was not packaged into a new end-to-end reproduction experiment.

|Projects|There are facts.|
| --- | --- |
|Device|Core Ultra 7 256V / Arc Lunar Lake /16GB unified memory|
|The system| Ubuntu24.04.4 |
|The backend|OpenVINO2026.2.1,GenAI/Tokenizers2026.2.1.0; Other Vulkan/SYCL routes|
|Model|Qwen 3.5-9B, IR INT4/INT8, revision see source table|
|GPU pipes|Finished 19 inputs/128 output restricted generation|
|INT4 results| 21.1599token/s,TTFT184.02ms,TPOT47.26ms |
|Results from INT8| 10.1047token/s,TTFT169.73ms,TPOT98.96ms |
|Results of the NPU|INT4 compilation failed; INT8 is over 420 seconds, with no inference throughput.|
|Quality gaps|Both GPU outputs reach the ceiling at the reasoning stage, and the full answer remains to be verified.|
|Follow-up work|Full set of answers, long inputs, multiple rounds of the same caliber, continuous operation|

**It should be concluded:** On this fixed combination, the IR GPU routes have generated records; INT4 has a higher short generation rate. NPU failed, full mission quality and service capacity still need to be met with acceptance testing.

**Conclusions the evidence does not support:** Not all Intel NPUs support this class of models, or the GPU route must be faster than all llama.cpp routes. Hardware, artifact, version and timing boundaries are not enough to support this promotion.

## 4.3 Multi-hardware adaptation template

Keep input and acceptance testing standards consistent when the same task is moved to multiple devices; The platform model format may vary, and should be indicated in the table.

|Platform/Version|artifact / precision|The text|Seeing|Length and concurrency|Performance scores|Failure and Evidence|
| --- | --- | --- | --- | --- | --- | --- |
|device A|revision and quantization|passed / failure / not tested|To the left.|Actual test value|Engine/pipe/HTTP|log links|
|device B|revision and quantization|To the left.|To the left.|To the left.|To the left.|To the left.|

Rules for filling out the form: successfully not filling out the form passed; The short request does not fill in the context passed; Text is not a substitute for vision. Upstream claims support is not equal to the current device tested. Cross-platform numeric values first unify length, quality and timing, then profit.

Details can be found at: [Adapted records](templates/adaptation-record.md) It starts.

## 4.4 Completed example: local CPU service walkthrough

This example corresponds to the actual implementation of the system. [Full course](practice/first-service/README.md) The following is a brief engineering record of the original ten. The original request, response, log and indicator are kept in the same result directory, and the conclusions can be reviewed on a case-by-case basis.

**One, the background of the project.** On a typical Windows computer, a model of dependency-free GPU deploys links to check downloads, tests, services, functionality, flow and performance files. The goal is to test the teaching process and engineering acceptance without committing the small model to the actual business quality.

**Second, hardware and environment.** Windows 10.0.26200, AMD64, i5-12600KF, 16 logic threads, and Python 3.13.12. llama.cpp b9557, commit 0f7fada56, CPU only, 4 threads. Environmental fields see [environment.json](../01-deployment-foundations/cases/C14-windows-cpu/results/2026-10-18-windows-cpu/environment.json).

**Three, model and input.** Qwen3-0.6B-Q8_0, fixed revision with SHA256 See list. The input includes three functionality queries, single-character malformed JSON, and two sets of four listing tasks. All prompts are stored in the process and results, not dependency private samples.

**Four, the inference framework.** Using a fixed official Windows CPU binary, the Python standard library is responsible for HTTP, SSE, and process management. It was chosen to complete a low-resource link first and then learn the backend of the GPU without the additional installation of PyTorch.

**Five, deployment of the program.** `.runtime` Save the engine and model, listen back to the 18080 loop, otherwise known as book-qwen3-06b, ctx2048, parallel 2, 4 threads. The program waits for the request to be ready, gathers metrics, stops its service, and then runs the engine benchmark.

**Six: Problems faced.** Calculate 2+2 output of 2 tonnes of hydrogen; The wrong JSON returned to HTTP500. The other two functionality queries were passed, and the performance request was received in both standard and usage.

**Seven, the screening process.** Save the original model response, terminate the cause and service log, check the wrong request and the health is still ok. Current evidence can be located on task output errors and error protocol issues; No further controls have been made to prove that the arithmetic error is due to models, templates or other specific factors, so no root cause has been constructed.

**Eight: optimizing experiments.** Keep the model, thread and service unchanged, and observe c1/c2 HTTP groups. Each set of four requests, with a maximum output of 32, is a small sample concurrency exercise and is not a sufficient long-term optimization experiment; There is no need to modify the functionality problem to improve the pass rate.

**9th, performance and quality.** C1/c2 output throughput is 53.18/82.12 tokens/s, mean TTFT131.16/217.49ms, mean E2E601.56/778.99ms. Engine pp64 is 319.08±17.26; tg32 is 69.88±0.22 tokens/s, with other timing limits. Functionality 2/3, error protocol failure.

**10 - Conclusions and limitations** The link is complete, total acceptance testing is false. First check quality and error handling, then add task sets, repeat rounds and test steady state resources. It does not support large language model capacity, stable tail latency, or producing availability promotional conclusions.

## 4.5 Saving file-level evidence

Each run is run with an independent run-id, storing environmental snapshots, models, lists, final commands, input and request, original response, errors, resources, sampling and statistics. The statistical scripts read these documents and the result table is not changed.

```text
results/2026xxxx-platform-model-c2-r1/
├── manifest.json
├── command.txt
├── requests.jsonl
├── responses.jsonl
├── errors.jsonl
├── resource.csv
├── server.log
└── summary.json
```

The name of the file is to recommend that the organization retain the original material in the actual format of the tool, rather than creating blank evidence to fit the directory. Public versions are licensed and sanitized first; Private copies are separated from public copies.

## 4.6 Updating existing project records

New versions and new evidence are written when the conclusions change. For example, the original title is written successfully, but the subsequent run has a clear kernel failure, and the output should be modified according to the specific failure, keeping the necessary version updated.

Knowledge entries refer to the latest applicable conclusions while maintaining the corresponding versions of the old results. In this way, it is possible to judge whether the recording is environmentally modified, model modified, or incomplete.

After completing a project record, extract reusable methods once: which layer the project addressed, what evidence was used, and under which conditions the result applies. Shared methods belong in the [General Performance Optimization and Testing Methodology](engineering/edge-llm-performance-methodology.md); project experience belongs in the [project index](engineering/projects/README.md). Commands and measurements remain in the original project record; the method page is not new runtime evidence.
