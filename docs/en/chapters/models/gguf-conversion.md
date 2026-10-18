# From raw weights to loadable GGUF

[简体中文](../../../01-deployment-foundations/chapters/models/gguf-conversion.md) | **English**

[Contents](../../SUMMARY.md) · [Chapter: Model formatting and quantization](../../02-capability-layers/02-model-formats-quantization.md) · [Next: Quantization Selection and Verification](quantization.md)

## Overview of this chapter

After receiving the model, it is first necessary to verify which artifact the operating framework can read. The llama.cpp usually reads GGUF; Downloading the SafeTensors directory from Hugging Face cannot be done by simply changing the name of the extension to GGUF. The conversion program must understand the model structure, tensor name, tokenizer and configuration to write a file that the executor can use.

This chapter builds on the author's GB10 in FlowUs with Qwen's conversion, quantization records. The original notebook contained the command to convert F16 from FP8, but the conversion would not restore information that had been lost to FP8. The following instructional operation changes to a small original model, first converting to F16, then entering quantization, making the steps easier to check. This round did not carry out the group conversion; GGUF exercises that are already in operation [The first local service](../../practice/first-service/README.md).

## 1. Before converting, check the model directory

It's a complete model, not just weights.`config.json ` Describe the model structure; `tokenizer.json ` And the word tables convert the text into tokens; `tokenizer_config.json` It is possible to save the chat template; Weights shard linked by index. In the absence of these files, conversion may fail, or there may be models that can be loaded, but the dialog format is incorrect.

First, answer four questions: Does the converter support this architecture? Do you support current weights? Are the text and visual components handled separately? Does the target engine version support the GGUF type after conversion? A special GGUF-type failure in the author's Mac notebook indicates that the file has been downloaded and that the CPU and CPU executor can read the CPU as two check ports.

This case deals with text-only models and does not involve visual projectors, LoRA mergers or custom remote code. Directory unification using the current work directory `artifacts/` It is also important to avoid duplicating the private path on the machine into the tutorial.

## 2. Preparation of fixed versions and models

The following are examples of Linux, Python 3.12, Git, CMake, and C++ compilers. Prepare at least 8GiB free memory and about 6GiB free disk; This is a reserve recommendation for small model exercises, and the conversion peak is still monitored in practice. Large language model to accommodate source files, F16 intermediate files, quantization files and conversion workspaces at the same time, space cannot be allocated only by the final Q4 file size.

```bash
mkdir -p deployment-conversion
cd deployment-conversion
git clone --branch b9557 --depth 1 https://github.com/ggml-org/llama.cpp.git
git -C llama.cpp rev-parse HEAD
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -r llama.cpp/requirements/requirements-convert_hf_to_gguf.txt
python -m pip install huggingface-hub==0.36.0
python -m pip freeze > conversion-packages.txt
mkdir -p artifacts/source artifacts/gguf records
```

`b9557 ` The series of engines used by the system's CPU practitioners, briefly submitted as `0f7fada56 `. After dependency is installed ` conversion-packages.txt`It's a quick snapshot of the environment of the transformation. For long-term replication of the same construct, a verified dependency snapshot, Python version and wheel should be filed together. The source code tag is fixed and does not automatically fix all download dependencies.

Download the original Qwen3-0.6B to the fixed directory. The model revision is a specific submission to the public repository, recorded separately with the finished product GGUF revision by the CPU practitioner:

```bash
python - <<'PY'
from huggingface_hub import snapshot_download
snapshot_download(
    repo_id="Qwen/Qwen3-0.6B",
    revision="c1899de289a04d12100db370d81485cdf75e47ca",
    local_dir="artifacts/source/Qwen3-0.6B",
)
PY
```

The model used in this chapter is [Qwen/Qwen3-0.6B](https://huggingface.co/Qwen/Qwen3-0.6B) It is licensed under the Apache 2.0 license. Both the downloader and the conversion dependency remain in the same environment, and do not confuse Python with virtual environments on different terminals.

Check the download directory for config, tokenizer, template and weights files. Calculate summaries of weights and key configurations, store inventories, revisions and lists of files; Don't just keep the progress shot down.

## 3. Converted to F16 GGUF

```bash
python llama.cpp/convert_hf_to_gguf.py \
  artifacts/source/Qwen3-0.6B \
  --outfile artifacts/gguf/Qwen3-0.6B-F16.gguf \
  --outtype f16 > records/convert-f16.log 2>&1
```

The input here is a complete directory and the output is a GGUF file.`--outtype f16` The output tensor is specified; It cannot guarantee that every tensor in the source model is stored with the same precision, nor can it correct an incorrect tokenizer or template. When a converter encounters unknown architecture, shard absence, and unprocessed quantization, the input should be checked first, without skipping the error to continue quantization.

The verification method is to simultaneously look at exit status, log termination, output files and subsequent loading. The model structure, number of layers, word structure and source configuration identified in the log corresponds. The existence of documents alone is not enough: interrupted processes can also leave incomplete documents.

## 4. Build loading and quantization tools

This chapter only requires CPU tools that can pre-verify documents and text links:

```bash
cmake -S llama.cpp -B llama.cpp/build-cpu -DCMAKE_BUILD_TYPE=Release
cmake --build llama.cpp/build-cpu \
  --target llama-cli llama-server llama-quantize -j 4
llama.cpp/build-cpu/bin/llama-cli --version
```

If the configuration phase prompt is missing from the CURL development library, install according to the distribution.`libcurl4-openssl-dev` and the corresponding software packages; CURLs can also be turned off with fixed version support without the need for network download functionality. A failure in the author's GB10 record occurred during the dependency detection phase and cannot be attributed to GPU computing capabilities.

## 5. First load the original precision artifact, then quantization

```bash
llama.cpp/build-cpu/bin/llama-cli \
  -m artifacts/gguf/Qwen3-0.6B-F16.gguf \
  -ngl 0 -c 2048 -t 4 -n 64 \
  -p '计算2+2。只输出一个数字。'
```

This command is used to check the load and once generated, the chat task must still pass the correct template test. Check the architecture, tensor and tokenizer alerts in the log; Save the output. If the original precision artifact has been decoded, empty output, or template error, first fix it so that it cannot be determined from where the problem was introduced after quantization is avoided.

Then you generate a Q4 candidate:

```bash
llama.cpp/build-cpu/bin/llama-quantize \
  artifacts/gguf/Qwen3-0.6B-F16.gguf \
  artifacts/gguf/Qwen3-0.6B-Q4_K_M.gguf Q4_K_M
sha256sum artifacts/gguf/*.gguf > records/gguf-sha256.txt
```

Keep the F16 source files, quantization commands, logs, output summaries and tool submissions. Subsequent Q5 or Q8 generations are generated from higher-precision sources, avoiding repeatedly quantizing low-bit width files as the same source after quantization.

## 6. What about acceptance testing?

The first step is artifact acceptance testing: the input revision and output summary are complete, conversion and load are error-free. The second step is functionality acceptance testing: check Chinese, computing, JSON and actual business tasks under the same template. The third step is performance acceptance testing: fixed input, output, thread, backend and cache status, engine and HTTP respectively.

It is recommended to put the results in the following structure. Input and conversion logs remain in a single record, avoiding a GGUF from an unknown source for a few weeks:

```text
records/conversion-run/
├── source-manifest.json
├── conversion-packages.txt
├── convert-f16.log
├── quantize-command.txt
├── gguf-sha256.txt
├── functional-results.json
└── conclusion.md
```

When faced with unsupported architectures, you can choose the fixed converter and executor that supports the model, or go back to the original format to run the framework. Modifying architecture names, removing unknown tensors or forcing other model templates to be used, both require structural proof and regression, and cannot be used as a general fix.

After completion of this chapter, candidates for the F16 and Q4 with a clear source should be obtained, rather than models with proven quality standards. The following chapter explains how to decide which quantization scheme to keep.

## Seven, large language model download project: list first, then use aria2 concurrency

FlowUs original model download records include SDK downloads and multi-catalog model management, and actual deployments also need to handle disruptions, shards and disk residues. concurrency downloads only change transmission efficiency and do not replace artifact integrity. The standard for the completion of the model download should be to verify the completion of all necessary documents of the fixed revision of the pump, rather than the pump progression bar to 100% pump.

### 7.1 When to use SDK, when to use ARIA2

The SDK is suitable for downloading complete repositories, processing revisions and filtering files; aria2 is suitable for public file URLs that have already been identified, requiring intermittent forwarding and multi-connection tasks. Licensed models use the platform's official certification process, with no credentials written into the command list or submitted documents.

Don't give the model's repository URL directly to the aria2 for speed, the repository page is not a weights file. Don't just download the safety sensors and miss the config, tokenizer and processor and then blame the conversion error on the engine.

### 7.2 Generate fixed download lists for public sources

Following the Qwen3-0.6B revision defined in this chapter, the list of repository files and the list of aria2 are generated. For example, the URL of the downloaded file does not contain authentication information, and is validated by using the model card before use.

```python
from pathlib import Path
from huggingface_hub import HfApi, hf_hub_url

repo = 'Qwen/Qwen3-0.6B'
revision = 'c1899de289a04d12100db370d81485cdf75e47ca'
target = Path('artifacts/source/Qwen3-0.6B').resolve()
lines = []
for name in sorted(HfApi().list_repo_files(repo_id=repo, revision=revision)):
    relative = Path(name)
    if relative.is_absolute() or '..' in relative.parts:
        raise ValueError('Unexpected file path')
    if name.startswith('.git/') or name.startswith('.cache/'):
        continue
    directory = target / relative.parent
    directory.mkdir(parents=True, exist_ok=True)
    lines.extend([
        hf_hub_url(repo_id=repo, filename=name, revision=revision),
        '  dir=' + str(directory),
        '  out=' + relative.name,
    ])
Path('records/aria2-public.txt').write_text('\n'.join(lines) + '\n', encoding='utf-8')
```

Each URL in the list follows the dir/out option to avoid all shard redirects being saved to the same filename. Larger repositories can generate necessary file sets based on indexing, but do not arbitrarily exclude auxiliary components when the model structure is not yet understood.

```bash
aria2c --input-file=records/aria2-public.txt \
  --continue=true --max-concurrent-downloads=2 \
  --max-connection-per-server=8 --split=8 \
  --min-split-size=16M --max-tries=5 --retry-wait=5
```

`-j `/max-concurrent-downloads limits the number of files that can be downloaded at the same time.`-x ` Limit the number of connections to each server.`-s` The request section. In practice, even if the server accepts Range support, bandwidth, limit flow and single file size, it is not possible to write 8×2 as a necessity 16 times faster.

The first two files, 8 connections per file, observe the throughput and 429/503; Too high concurrency leads to decreased connectivity when retesting. Keeping `.aria2` For breakdowns, download failure first confirms the disk, network and remote state to avoid mistakenly deleting the completed large shard.

### 7.3 Four inspections after completion

First verify the file list and shard index, then verify the number of bytes/trusted source summaries, then analyze the model configuration with the tokenizer, and finally load with the target converter or executor. Self-calculating SHA256 can track the local artifact identity, but if there is no credible upstream value, a single summary calculation does not constitute source integrity verification.

HF files are sometimes stored in LFS/Xet, and summary types of metadata fields may vary. Do not use any HTTP ETag as a SHA256 file. Using the integrity logic provided by the SDK, the final list of files and the necessary source metadata will still be archived.

A large language model requires a simultaneous budget source model, conversion of intermediate files, quantization of candidates, download of temporary files and cache. The 350G-grade model, if you need an intermediate artifact, requires a significantly higher demand than the 350G. Download directories are separated from service models, so that semi-finished products are not automatically detected by the service.

## Eight: GGUF to Ollama: What to verify after import

The original notes contained the end-to-end process for the conversion, quantization, Modelfile, create, run, etc. A model can be created along the Q4 file in this chapter, first confirming that the current Ollama version supports its architecture with the GGUF tensor type.

Create a Modelfile in the same directory as the GGUF file:

```text
FROM ./Qwen3-0.6B-Q4_K_M.gguf
PARAMETER num_ctx 2048
PARAMETER num_predict 256
PARAMETER temperature 0
```

```bash
ollama create book-qwen-q4 -f Modelfile
ollama show book-qwen-q4 --modelfile
ollama run book-qwen-q4
```

First, check the imported template, parameter and artifact information, and then submit the same functionality question as llama.cpp. Don't use the Mistral.`[INST]` The template is copied to Qwen, and the results of the original llama.cpp CLI prompt are not considered to be the exact same as the results of the Ollama chat template.

Importing may result in independent blob or storage management expense, confirming delivery and fallback requests before deleting the source file; Use corresponding tools to manage specified models when cleaning, avoiding deleting shared model libraries. The number of layers running Ollama and the backend are identical to the actual log and state.

## How to keep a minimum of problems when converting failure

Unknown architecture, unknown tensor type, missing shard and tokenizer not matched should be positioned respectively. Save the source code, dependency, model revision, commands and early errors. If the problem involves only configuration, public sanitization configuration and stack can be used first. Don't ask to upload the entire private work directory.

When the source model is a low-precision format and the converter is not currently supported, select the engine or the official conversion route that supports the artifact. Simply changing the model_type in the configuration to a similar name will allow the loader to interpret the tensor according to another structure and cannot be used as a secure general adaptation method.

Once the converter is complete, it also passes tokenizer/template and real-world task acceptance testing. Macfork specifically `hc_head_base` Error and Metal type42 failure separately: the name of the artifact matches that of the backend operator. Support is two separate terminals, and the same file format does not eliminate them.
