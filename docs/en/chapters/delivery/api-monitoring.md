# API, monitoring and acceptance testing: making the status of the service visible

[简体中文](../../../01-deployment-foundations/chapters/delivery/api-monitoring.md) | **English**

[Contents](../../SUMMARY.md) · [General Chapter of Engineering Delivery](../../02-capability-layers/05-engineering-delivery.md) · [Environment and Transport](environment-operations.md)

## Overview of this chapter

The application sees the interface and the answer, and the engineer also needs to know if the request is in line, if the resources are insufficient, if the error has increased. This chapter combines API agreements, health, indicators, quality and acceptance testing to avoid a single snapshot of the successful launch of the service.

Content is organized based on FlowUs service and load testing articles; An example of an indicator is from the actual CPU exercises of the system. Interface compatibility is verified according to specific capabilities, and not all fields are understood to be compatible with the OpenAI API.

## 1. Pre-arranged interface and scope of tasks

At least write down the address, model, alias, request, field, context and output limits, sampling, reasoning, flow, overtime, cancellation and error formats. Applications that use images, tool calls, JSON constraints, or multiple rounds of caches should be single-row tested.

In the deployment directory, save a few fixed requests: normal short queries, long inputs, JSON tasks, flow patterns, wrong models, malformed JSON and overloaded inputs. The request uses public or sanitization materials to preserve HTTP status, response, termination cause and usage.

## 2. Health, readiness and functionality separated

The process is alive and the process is still alive; Indicates that the model is loaded and ready to receive the request; Functionality checks are used to verify interfaces and task results. They complement each other, and cannot rely solely on the state of the operating system process.

The health interface of llama-server and vLLM is confirmed in a fixed version. The system's CPU exerciser returns 500 after the malformed JSON.`/health ` Still coming back `{"status":"ok"}`. This indicates that service recovery is available, but the error protocol check still failed because the expectation is clear 4xx.

Health consultation should not lead to additional workloads from continuous submission of long-generation tasks. Periodic functionality The probe can use controlled short tasks, record frequency and resource expenditure, and avoid confusion with formal load testing scores.

## 3. What do stream customers see?

The SSE can be sorted by event, with characters or blank content appearing first, and then a formal text. The first valid legal time is recorded; Check the final end of the mark, usage and error. Network disconnection, client cancellation and service termination should be distinguished, and not the complete success of a partial text.

Model reasoning content, ultimate answers, and the transmission fields of tool parameters may differ. Read-only apps `content` It is important to note that the final answer is indeed there. I can't get any of the strings to mark success.

Standard library analytics used by the system's clients `data: ` Events and preserve the correctness, use, finish_reason, TTFT and E2E. It is a small instructional implementation, with no token-by-token arrival time and re-connection mechanism; Formal services should be supplemented with verification of these capabilities.

## 4. Four groups of monitoring indicators

|Scope|Indicators|Useful|
| --- | --- | --- |
|The customer|Success/Failure, TTFT, E2E, Cancellation, Overtime|Judging real experiences and mistakes|
|Scheduling of services|Activities/Lines, KVs, hits, recounting|Explaining Waiting and Capacity|
|system resources|CPU/GPU, RSS/VRAM, swap, temperature/power consumption|Discovering resources and heat constraints|
|Quality of tasks|Complete answers, accuracy, formatting legitimacy|Preventing speed from covering up mistakes|

High TTFT may come from a queue, prefill, compilation or network; High TPOT may come from decoding, bandwidth, batching or resources competition. To reduce the cause, aligning requests in the same time window with service indicators can help.

## 5. A real metrics document

Activate the CPU exercises `--metrics`, the collected [metrics.txt](../../../01-deployment-foundations/practice/first-service/results/2026-10-18-windows-cpu/metrics.txt) These include:

```text
llamacpp:prompt_tokens_total 355
llamacpp:tokens_predicted_total 266
llamacpp:requests_processing 0
llamacpp:requests_deferred 0
```

This is the cumulative and instantaneous state of the exercise sample, including functionality checks and HTTP tests, and not just the 128+128 output token of the performance group. Therefore, the cumulative 266 divided by a set of time cannot be used to calculate the throughput, nor can the entire test process be waited on because the sample is lined up at 0.

The counter looks at the increment, the instantaneous value looks at the time sequence, and the countdown may be zero after restarting. The names and units of different versions of the indicator may change, and the original indicator description and sampling method should be preserved. Public files only retain the necessary indicators, and the label with the request text, path or device identifier must be checked first.

## 6. Acceptance testing is divided into functionality, quality, performance and recovery

Functionality acceptance testing checks interfaces, flows and products; Quality acceptance testing to check the response to the task; Performance acceptance testing by target workload and threshold; Restore acceptance testing to check for error requests, stop, start and rollback. Individual records passed, failed and not tested.

The system CPU exercises HTTP eight performance requests successfully, with only two of the three functionality queries passed, and malformed JSON returns 500, so overall `exercise_passed=false`. If failure is retained, it can guide the next step: verify the quality of the small model and the template, handle the error protocol, rather than continuing to improve concurrency.

For real projects, the threshold should come from demand. For example, the P95 TTFT and the success rate are defined under a given input distribution, concurrency and quality standard. An unidentified threshold is written for the definition, and a temporary modification of the threshold has just been passed without reference to this data.

## 7. Deliver a valid conclusion

Conclusions describing device and version running, model identity, range of functionality, target length and workload, quality and performance, failure, input, location monitoring and recovery inputs. Link each key conclusion to the actual document.

Knowledge systems are used to explain how to make judgments, and project directories are responsible for keeping specific running records. When publishing publicly, copy only the necessary fields of engineering that have been inspected; Original private space, credentials, internal nodes and business materials remain within the scope of authorization.

## Eight: Set up a fixed set of acceptance testing for the interface.

A set of practical acceptance testing first covers the normal path and then covers the boundaries that are most likely to destabilize the service. It is not necessary to plug in all the complex functionality at once, but the ability to apply dependence must have clear results.

|Input|Check the content|What should be preserved|
| --- | --- | --- |
|Short Questions|Template, in Greek, natural ending|request , response ,usage,finish_reason|
|Identify the answers|quality baseline|Expectations, original output and ratings|
|Multi-round dialogue|History and Characters Right|Complete messages and final answers|
|Fixed JSON fields|Format and field meanings|Primary strings, parsing results, field acceptance testing|
|The flowers answer|It's officially over, it's cancelled.|SSE events, time, status after cancellation|
|Wrong model name/malformed JSON|Parameter Testing and Error Protocol|HTTP status, wrong body, then health|
|Over-length input/over-sized images|Boundary tips and resources|Error types, resources and subsequent availability|

JSON is legally and correctly distinguished from JSON content, e.g.`{"count":2}` It can be solved, but expect count3 to still fail. A tool call should also check the tool name, parameter and call order, and not only judge the response that contains the tool_calls field.

In this system, the CPU's three functionality queries are both passed, error JSON gets 500, which is a verifiable failure instance. The historical performance of the hardware sections is judged by their original quality materials, without the use of this subset of model questions to validate other models.

## Reverse agent access to verify the SSE

The service is connected normally, and the proxy will wait until the last display, possibly the proxy buffer; A request for a long time without output may trigger overtime reading. Compare the same flow request as the proxy, observe the event arrives, and do not change the model parameter immediately.

Below is a reverse-proxy instruction clip of the in-house experiment, which does not include an external release configuration. Overtime in Nginx should be set to the actual input with SLO, 600 seconds is just an example:

```nginx
server {
    listen 127.0.0.1:8088;
    location /v1/ {
        proxy_pass http://127.0.0.1:8001;
        proxy_http_version 1.1;
        proxy_set_header Connection "";
        proxy_set_header X-Request-Id $request_id;
        proxy_buffering off;
        proxy_cache off;
        proxy_read_timeout 600s;
    }
}
```

Acceptance testing after logging in, first correct, add, end, error, cancel and request ID. The backend doesn't necessarily automatically write X-Request-Id into the log, it needs to be configured according to its supported configuration. Don't claim that end-to-end tracking is already established by adding a header.

Overtime can also be divided into: connection overtime, request upload, service queue, first output, reading blank and overall deadline. Each layer of overtime is set up to cover up a long-term risk of queuing out of control, and services beyond the agreed budget should have identifiable cancellation and recovery behaviour.

## Read Prometheus' calculator, instantaneous value and distribution

The meters record cumulative events, such as the total number of output tokens; The instant value represents the sampling time state, such as the activity/ queue request; Distribution indicators are used to calculate interval latency. The meters cannot be directly measured at the value per second, and the instantaneous queue is zero, nor does it indicate that there was no waiting before.

Based on the actual llama.cpp indicator of the system, the following PromQL can be written to understand how to sample, and the actual crawling of the label should be selected as a corresponding instance:

```promql
rate(llamacpp:tokens_predicted_total[5m])
rate(llamacpp:prompt_tokens_total[5m])
llamacpp:requests_processing
llamacpp:requests_deferred
```

The first two are the token rate estimates for the 5-minute window, and the last two are the current value. They are not automatically equivalent to the exact throughput of a load test; Load testing is still calculated using this actual token/wall clock when the boundary is clear. Application restarting results in counting to zero, repositioning of the rate function and scarcity sampling are also understood.

If P95 is calculated using a rectangle, first confirm the unit and the label of the barrel; The cross-example mean P95 usually has no clear overall percentage meaning. Tail latency is not falsified without distributed data, and algorithms are calculated and stored using the client's original request.

### A minimal collection of configurations

```yaml
scrape_configs:
  - job_name: local_llama
    scrape_interval: 5s
    static_configs:
      - targets: ['127.0.0.1:18080']
```

configuration Assume that Prometheus and llama-server are on the same host network and that the server has enabled metrics. If Prometheus is in an independent container, 127.0.0.1 refers to the container itself, it should be adjusted according to the actual network mapping. When the graph shows no data, first verify the destination and endpoint and then check the index name.

## Eleven, from four monitoring combinations of positioning problems

TTFT high, waiting for continuous growth, running close to budget, showing the rate of arrival and capacity first; TTFT high, waiting low but prefill heavy, check input length, image tokens and compilation; TPOT as the swap/frequency decreases, memory checks and thermal constraints; The client is slow but the service timing is normal, check agents, network and the client.

These are screening entrances, not just finding the root cause with a curve. The client request ID, service logs, indicators and resources are aligned in the same time window and verified using small workloads or single-variable controls.

Intel Kokoro CPUs in the remaining NPU compilation coexist when P95 RTF0.290, after clearing 0.189, are examples of backward competition; The allocation failure of AMD395 is mutually reinforcing with the visibility of 63215 MiB, an example of resources budget. After the Mac Vision 500 EngineDead was an unusable example of a lack of functionality triggering the process.

## Acceptance testing: How to clearly report pass, fail and not tested

Each acceptance test lists the input, operating environment, goals, actual values, documentation and conclusions. Missing data write not tested; overlapping failure; The functionality is correct but the performance has not been met and the functionality has been passed. Don't successfully deploy a pump to cover all dimensions.

For historical engineering, the system retains known parameters with a true summary, missing parts of the original documentation in the source page. The new operating system maintains the complete material in the previous directory so that the same acceptance testing standards can be used continuously for upgrades and returns.
