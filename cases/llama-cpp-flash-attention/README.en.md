# llama.cpp Flash Attention performance comparison

[简体中文](README.md) | **English**

Start with the [beginner tutorial](CASE.en.md). The [technical appendix](CASE_TECHNICAL.en.md) defines metrics and experimental limitations. For background concepts, see the [deployment knowledge base](../../docs/en/README.md).

```bash
cd /mnt/workspace
git clone https://github.com/qiyuefffs/llm-serving-diagnosis.git
cd llm-serving-diagnosis/cases/llama-cpp-flash-attention
```

These commands only retrieve the project files. Follow the tutorial in order to check the GPU, install dependencies, download and build, start the service, and test it. If already cloned, open the Case directory directly. Preserve existing experimental evidence before replacing files in an older workspace.

| Path | Contents |
| --- | --- |
| `scripts/` | Environment/model preparation, smoke tests, load testing, and reports |
| `data/workload.jsonl` | 8 public deployment questions |
| `figures/` | 8 verification screenshots captured after measurement |
| `results/observed-summary.csv` | 12 transcribed group summaries, not raw request records |

The original workspace was `/mnt/workspace/llm-serving-diagnosis`. After reorganization, new reproductions use the Case subdirectory above. Historical screenshots retain their original paths. `setup.sh` defaults to its own Case directory; `PROJECT` can override the working directory.

Current status: tutorial draft. A complete successful build log, a full reproduction in a second fresh instance, and publicly accessible raw JSONL/GPU samples/logs are still needed. This directory reorganization did not rerun the GPU experiment.
