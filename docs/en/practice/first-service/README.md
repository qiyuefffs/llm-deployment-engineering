# Full Operating Example: The first local inference service

[简体中文](../../../01-deployment-foundations/practice/first-service/README.md) | **English**

[List of knowledge systems](../../SUMMARY.md) · [llama.cpp principles and build](../../chapters/frameworks/llama-cpp.md) · [Performance analytics](../../chapters/performance/benchmarking.md)

## What did this exercise accomplish?

Starting with the empty running directory, download the fixed version of llama.cpp with public GGUF, validate the artifact, start the native service, send functionality with the flow request, collect indicators, and then stop the service running engine benchmark. Every step has a complete process and real results that can be opened.

Practice using small models to run a complete engineering link on a regular Windows computer. It cannot represent the capacity of a large language model, nor does it require a GPU. In 2026-10-18, implementation has been implemented. **Link completed, but overall acceptance testing failed** Three functionality queries passed, and malformed JSON returned 500. The following lists the original failures and does not write the expected response as the actual result.

## 1. Knowing the directory and environment

```text
practice/first-service/
Readme.md This is a tutorial.
JSON Fixed model, engine and service parameters
Prepar.py download, test and decompress
- run_exercise.py admin services, requests, records and benchmarks
└── results/
    Windows - 2026-10-18-windows-cpu/ Real running records have been made public
```

This environment is for Windows 10.0.26200, AMD64, i5-12600KF, 16 logic threads, Python 3.13.12; The program is limited to four threads.`-ngl 0` It's a pure CPU. Python code uses standard libraries only, without installing PyTorch or CUDA. Recommended at least 8GiB of memory, about 2GiB of free disk, and confirmation of 18080 port free disk; The specific CPU instruction requires that it be set to official binary.

|Artifact|Fixed identity|
| --- | --- |
| llama.cpp |Official release b9557, measured Submitted 0f7fada56|
|Windows Compressed Package| llama-b9557-bin-win-cpu-x64.zip |
|Model| Qwen/Qwen3-0.6B-GGUF,Q8_0 |
|model revision| 23749fefcc72300e3a2ad315e1317431b06b590a |
|Documents|Qwen3-0.6B-Q8_0.gguf,639446688bytes|
|Services|127.0.0.1:18080, also known as book-qwen3-06b|
|resources parameter|Ctx 2048, parallel 2, thread 4, CPU|

The fixed download addresses and summaries are available. [manifest.json](../../../01-deployment-foundations/practice/first-service/manifest.json). model license Apache 2.0, engine project license MIT; Weights is not stored in the repository and is available under the terms of the original model page.

## 2. Access the repository and access the correct directory

PowerShell is used. If you have already cloned the repository, you can access it from an existing directory:

```powershell
git clone https://github.com/qiyuefffs/llm-deployment-engineering.git
cd llm-deployment-engineering
cd docs/01-deployment-foundations/practice/first-service
python --version
```

All of the following commands are `first-service` The directory is executed. Don't guess where the model is after running from another location; Running directories, code directories and model cache directories are different concepts.

## 3. Download and verify models and engines

```powershell
python prepare.py --runtime-dir .runtime
```

The program downloads the fixed official compression packet with GGUF, checks the compression packet abstract, model byte number with SHA256, decompresses to `.runtime ` and preservation.`download-hashes.json`. Repeat execution of documents that have passed the validation test. When a network failure or abstract is inconsistent, stop and do not continue to start the model.

The Model SHA256 is designed to:

```text
9465e63a22add5354d9bb4b99e90117043c7124007664907259bd16d043bb031
```

I see.`Prepared ` Then check it out.`.runtime/llama-server.exe `, ` llama-bench.exe`And the model files are there. dependency DLL and executable programs remain in the decompression directory; Don't just copy an exe to another location.

The download time is approximately 0.64GB, depending on the network. GitHub API limits flow and release resources Failure is a different problem: Direct verification when necessary [Fixed release](https://github.com/ggml-org/llama.cpp/releases/tag/b9557) Resources and addresses on the list.

## 4. An order to complete the entire process

```powershell
python run_exercise.py --runtime-dir .runtime --output output/run-01
```

Select an empty result directory. The program refuses to cover existing records and checks the port before launching. It only stops the sub-server processes it creates; When the 18080 is occupied, it should first confirm and discontinue its former instances.

The program does the following:

1. Test the model and record the engine version, system, parameter and start commands.
2. Start the server, wait for healthy ready, check the model list.
3. Send three functionality queries, save the original request, answer, use and judgment.
4. Send malformed JSON, record the status, and then check if the service is healthy.
5. c1/c2 sends four streaming requests, keeping the original, TTFT, E2E and Summary.
6. Collect metrics, stop your service, save the sanitization log.
7. Separately run the three-wheeled pp64/tg32 engine benchmark, generating total acceptance testing files.

The default output is 0, which indicates that the script process is complete. **Please read if you have reached the standard `acceptance.json`**. Hopefully automation returns non-zero when acceptance testing fails, and can run:

```powershell
python run_exercise.py --runtime-dir .runtime --output output/run-strict --strict
```

`--strict` In the case of total acceptance testing failure, withdraw 2. Network, loading or program error will be disrupted and errors will occur. Directories and port checks to protect the original results are operational protections that are supplemented after the actual run, and the historical performance records below remain the same, with no repeated results generated for these protections.

## 5. How does the hand work when it is started?

To see the boot log, you can run on the same PowerShell frontend:

```powershell
$modelPath = (Resolve-Path .runtime/Qwen3-0.6B-Q8_0.gguf).Path
$templateArgs = '{"enable_thinking":false}'
& ./.runtime/llama-server.exe -m $modelPath `
  --host 127.0.0.1 --port 18080 --alias book-qwen3-06b `
  -c 2048 -np 2 -t 4 -tb 4 -ngl 0 --metrics `
  --chat-template-kwargs $templateArgs
```

PowerShell 7 may be different from the original Windows PowerShell in that it does not transmit live commands; If you encounter a JSON parameter parsing error, prioritize the Python input above, which starts the program by the parameter array. After the first stage service is stopped in Ctrl+C, automatic exercises are run again to avoid port and resource conflicts.

The boot log should identify the model, CPU backend, 2048 total context and two slots; This version has 1024 slots. The actual request is that the length should leave the output space, and the total of 2048 cannot be considered as the separate budget for each slot.

The second terminal is available to send stable requests across Python versions:

```powershell
@'
import json, urllib.request
url = 'http://127.0.0.1:18080/v1/chat/completions'
body = {'model':'book-qwen3-06b',
        'messages':[{'role':'user','content':'中国首都是哪座城市？只输出城市名。'}],
        'max_tokens':64, 'temperature':0}
req = urllib.request.Request(url, data=json.dumps(body).encode('utf-8'),
                             headers={'Content-Type':'application/json'})
with urllib.request.urlopen(req, timeout=120) as response:
    print(json.dumps(json.load(response), ensure_ascii=False, indent=2))
'@ | python -X utf8 -
```

Old terminals may also be affected by the encoding of the terminal when transmitting Chinese to the Python pipeline. Automatically exercised prompts are stored in UTF-8 source code, without dependency manual pasting or piping coding.

## 6. Real functionality results

Original output view [functional.json](../../../01-deployment-foundations/practice/first-service/results/2026-10-18-windows-cpu/functional.json):

|Input|Rules for acceptance testing|It's actually legal.|Results|
| --- | --- | --- | --- |
|Calculate 2 + 2, output only one number|Roughly equal to 4| 2 |Failed|
|China's capital city, only city names|Strictly equal to Beijing|Beijing|Passed|
|Only output specified JSON objects|It's equal to an object.| {"ready":true} |Passed|

Mathematical problem errors need to be preserved, and one easy problem cannot be replaced to make overall acceptance testing green. This small sample is used to check the process and does not provide a general model accuracy. If a business model is to be selected, the representative task should be increased and compared with other models or the original precision baseline.

The shape of the input is single.`{`. Primitive [invalid-request.json](../../../01-deployment-foundations/practice/first-service/results/2026-10-18-windows-cpu/invalid-request.json) Record HTTP500 and JSON parsing errors, and then health is ok. Our protocol acceptance testing expects 4xx, so this failure; Health recovery passed alone.

## 7. True HTTP and Engine Results

HTTP performance request requires a list of integers, but the output limit of 32 tokens may be interrupted. They are used only for time and flow links, not as a complete listing assignment. There are four sets of 128 tokens in total:

|concurrency|Successful|Testing window|Output throughput|Average TTFT|Average E2E|
| --- | --- | --- | --- | --- | --- |
| 1 | 4/4 | 2.406964s | 53.18token/s | 131.16ms | 601.56ms |
| 2 | 4/4 | 1.558745s | 82.12token/s | 217.49ms | 778.99ms |

concurrency 2 total throughput increases, but the average request is expected to increase. The sample size was only 4, and no stable P99 was reported. For individual records, see [requests.jsonl](../../../01-deployment-foundations/practice/first-service/results/2026-10-18-windows-cpu/requests.jsonl) The results of the calculations [http-summary.json](../../../01-deployment-foundations/practice/first-service/results/2026-10-18-windows-cpu/http-summary.json).

After the server was shut down, the result of the three-wheeled engine was pp64.`319.08±17.26token/s `,tg32 `69.88±0.22token/s` See you later. [engine-benchmark.json](../../../01-deployment-foundations/practice/first-service/results/2026-10-18-windows-cpu/engine-benchmark.json). These numbers do not include HTTP rows and cannot be directly considered as the same metric as HTTP total throughput.

## 8. Where does the inspection end up?

|Documents|Check the content|
| --- | --- |
| [environment.json](../../../01-deployment-foundations/practice/first-service/results/2026-10-18-windows-cpu/environment.json) |System, version and this parameter|
| [server-command.json](../../../01-deployment-foundations/practice/first-service/results/2026-10-18-windows-cpu/server-command.json) |The actual start parameter, path has been changed to public placeholder|
| [models.json](../../../01-deployment-foundations/practice/first-service/results/2026-10-18-windows-cpu/models.json) |Real model name|
| [functional.json](../../../01-deployment-foundations/practice/first-service/results/2026-10-18-windows-cpu/functional.json) |Functionality, input, response and judgment|
| [invalid-request.json](../../../01-deployment-foundations/practice/first-service/results/2026-10-18-windows-cpu/invalid-request.json) |error status and health recovery|
| [requests.jsonl](../../../01-deployment-foundations/practice/first-service/results/2026-10-18-windows-cpu/requests.jsonl) |Eight performance requests and timing|
| [http-summary.json](../../../01-deployment-foundations/practice/first-service/results/2026-10-18-windows-cpu/http-summary.json) |Clustering and throughput|
| [metrics.txt](../../../01-deployment-foundations/practice/first-service/results/2026-10-18-windows-cpu/metrics.txt) |Service indicators at the time of sampling|
| [server.log](../../../01-deployment-foundations/practice/first-service/results/2026-10-18-windows-cpu/server.log) |Loading, slot and request log|
| [engine-benchmark.json](../../../01-deployment-foundations/practice/first-service/results/2026-10-18-windows-cpu/engine-benchmark.json) |Independent engine measurement|
| [acceptance.json](../../../01-deployment-foundations/practice/first-service/results/2026-10-18-windows-cpu/acceptance.json) |Finally passed and failed|
| [download-hashes.json](../../../01-deployment-foundations/practice/first-service/results/2026-10-18-windows-cpu/download-hashes.json) |Download the document summary|

The conclusion is: `exercise_passed=false`. Run links, HTTP performance groups and engine benchmarks are completed; The quality and error protocols clearly fail. Different CPUs, instruction sets, system workloads, and hot states vary in speed, and reproduction aims at linking controllable results, not requiring exactly the same subset.

The next step is to look at the cause of the failure and then do a more complete set of quality and performance experiments. This exercise should be able to independently explain what the pump has downloaded, how to start, what is input, where is output, why the pump cannot be delivered, and then enter the five-tier framework learning.
