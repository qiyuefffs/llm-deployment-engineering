# Deployment performance cases

[简体中文](README.md) | **English**

Each case keeps its documentation, code, inputs, parameters, and results together. Add a separate directory for a new experiment; do not reuse previous results as measurements for new hardware or models.

| Case | Environment and question | Available materials |
| --- | --- | --- |
| [Flash Attention comparison](llama-cpp-flash-attention/README.en.md) | A10 24GB, Qwen3.8-27B Q4; compare FA off/on at concurrency 2 | Tutorial, scripts, public input, 8 verification screenshots, and 12 transcribed groups. Public raw evidence and fresh-environment reproduction are still incomplete. |

Each new case should include environment and model versions, the complete execution sequence, sample inputs, runnable code, actual results, and limitations. Mark unexecuted procedures clearly; do not present expected performance as a measured result.
