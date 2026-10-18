# Deploying a project retrospective template

[简体中文](../../01-deployment-foundations/templates/deployment-review.md) | **English**

[Knowledge base home](../README.md) · [Retrospective methods](../04-project-review.md)

Below is the template to be filled in. No measurement data write not tested metals, no material obtained write missing metals, do not fill in the expected value as a result.

## 1. Borders between demand and acceptance testing

- Who is using, what is input and output:
- Input/output length distribution, request access, target concurrency:
- The quality and latency thresholds, the success rate thresholds:
- Delivery platforms, costs/resources, limits, scope of completion:

## 2. Fixed environment and model

|Projects|Actual value|
| --- | --- |
|It's not the same thing as running a computer.|To be completed|
|GPU/NPU, number, capacity, interconnect|To be completed|
|Drivers, operating libraries, communication libraries|To be completed|
|Framework, package locking files, source code commit / image summary|To be completed|
|Model source, revision, weights SHA256, license|To be completed|
|Model architecture, precision / quantization, tokenizer and template|To be completed|
|Input documents, source and SHA256|To be completed|

## 3. Execute input and effective configuration

- Access, install, build commands and log locations:
- How to start / stop / restart commands, service address configuration:
- Context, concurrency, scheduling, budget, KV type, parallelism and offloading:
- In this case, it's not the same thing as the default mode, sample parameters, output limits:
- Valid requests, error requests, and model readiness checks:

## 4. workload and quality measurement

- Fixed concurrency or fixed rate of arrival; Number of samples and repeat rounds:
- Cold/hot start, warm-up mode, prefix cache and hit conditions:
- TTFT's starting point, whether it contains inference content; TPOT/ITL measurement methods:
- How to define success, disruption processing, and failure request statistics:
- Token number sources, resources, sampling frequency, whether the network and queue are included:

## 5. Assumptions, changes and actual results

|It's the turn|Assumptions to be verified / Changes to single items|Success / Total| TTFT P95 |Total latency of P95|Output of tokens/s|Memory peak|Primary evidence|
| --- | --- | --- | --- | --- | --- | --- | --- |
|baseline|To be completed|Not tested|Not tested|Not tested|Not tested|Not tested|To be completed|
|Contrasting|To be completed|Not tested|Not tested|Not tested|Not tested|Not tested|To be completed|

- Quality baseline and similar examples:
- In the meantime, we're going to discuss whether to meet the previous threshold and repeat the fluctuations of the experiment:
- improvement, degradation or no significant change; The following conclusions are supported:
- Typical failure, proof of cause and degradation:

## 6. Delivery and Restrictions

- Complete code, public input, original results, snippets and report links:
- Monitoring, alerting, capacity recommendations, configuration changes and rollback steps:
- Unverified device/model/workload and lack of evidence:
- Authorization of data with screen sanitization, external code / model / data:
