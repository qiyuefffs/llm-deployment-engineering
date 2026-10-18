# Appendix B: Reference and revision of the original

[简体中文](../../01-deployment-foundations/appendices/references.md) | **English**

[Contents](../README.md) · [Frequently used commands](commands.md) · [Sources of engineering](../evidence/README.md)

## B.1 Official data entry

The official documentation is used to verify supporting terms and concepts, performance figures, and author engineering records. The list below may change with upstream; In the old experiment, continue to check the fixed commit, release and corresponding documentation.

|Subjects|The information|Read More|
| --- | --- | --- |
| llama.cpp | [Source code and documentation](https://github.com/ggml-org/llama.cpp) |Build, model architecture, backend, server and quantization|
|llama.cpp builds| [build.md](https://github.com/ggml-org/llama.cpp/blob/master/docs/build.md) |CMake variables, dependency and platform conditions|
| vLLM | [Documentation](https://docs.vllm.ai/) / [source code](https://github.com/vllm-project/vllm) |Installing platforms, supporting models, scheduling, quantization and benchmarks|
| NVIDIA CUDA | [Compatibility explanation](https://docs.nvidia.com/deploy/cuda-compatibility/) |Relationship between driver and runtime|
|NVIDIA architecture| [CUDA GPUs](https://developer.nvidia.com/cuda-gpus) |Accurate GPU computing capabilities|
|NVIDIA container| [Container Toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/) |Host driver, container device access|
| ROCm | [Documentation](https://rocm.docs.amd.com/) |device/system matrix, HIP, library and installation|
| HIP | [Documentation](https://rocm.docs.amd.com/projects/HIP/en/latest/) |Compilation Goals and Execution Interfaces|
| OpenVINO | [Documentation](https://docs.openvino.ai/) / [GenAI](https://github.com/openvinotoolkit/openvino.genai) |IR, device plugins, Pipeline, and PerfMetrics|
| oneAPI | [Development tools](https://www.intel.com/content/www/us/en/developer/tools/oneapi/overview.html) |SYCL compiler and runtime|
| MLX | [The Framework](https://github.com/ml-explore/mlx) / [MLX-LM](https://github.com/ml-explore/mlx-lm) |Apple execution and model support|
|MLX vision| [MLX-VLM](https://github.com/Blaizzy/mlx-vlm) |Models, processors and visual generators|
|Ascend vLLM| [vllm-ascend](https://github.com/vllm-project/vllm-ascend) |Supported by chips, cann, plugins and vLLM versions|
| ModelScope | [Documentation and SDK](https://github.com/modelscope/modelscope) |model download, revision and artifact|
| EvalScope | [Source code and documentation](https://github.com/modelscope/evalscope) |request workloads, indicators and versions|

This is a reference entry list, which does not mean that this round has re-verified the latest version on all platforms.

## B.2 Expressions that need to be revised in the draft

|Expressions in manuscripts or old notes|Explanation of the use of this system|
| --- | --- |
|GGUF is a quantization algorithm.|GGUF is a format; It preserves different types of accuracy and quantization.|
|Q4_K_M's K is k-means|K is the K-quant family; Not explained by k-means|
|AWQ/GPTQ/GGUF are in the same category|Separate record formats, quantization methods, bit width, layout and execution kernel|
|Low bit width is fast.|It requires matching kernel, device and workload, quality and separate acceptance testing.|
|FP8 switches to FP16 to restore original precision|Only changes indicate that lost information will not be automatically restored|
|The FP8 model uses FP8 KV.|Weights and KV are separate configurations|
|Model parameter times bit width is all VRAM.|It also counts KV, activation, workspace, graphs, pools and surpluses.|
|MoE only needs to load the activation parameter|Total weights still need to be stored, offloaded/distributed|
|Double RTX4080 can be installed on NVLink Bridge|RTX4080 does not support NVLink, verified by actual PCIe topology|
|Two VRAM cards can be used directly as a single card.|Framework, kernel, communication and resources budgets need support separately|
|Gpu-memory-utilization improves compute throughput|This is an example of an engine memory budget, not a GPU utilization target.|
|Unified memory is a device that can allocate capacity.|Other systems, drivers, runtime and application budgets|
|Compilation Success or device|It also requires targeted models, functionality, length, workload and quality acceptance testing.|
|Continuous Batching is like increasing concurrency.|Dynamic scheduling mechanisms differ from activity sequence limits in configuration|
|Prefix Cache will speed up all requests|Prefix matching, capacity and fulfilment requirements|
|It's the speed of the user that increases throughput.|Track TTFT, ITL, E2E, and tail latency together|
|Dividing engine tg directly by HTTP throughput|Unified time boundaries and workload comparisons|
|A request configuration concurrency 10 is a 10 concurrency test.|See the actual simultaneous request and sample number|
|Multi-parameter program benefits attributable to single switches|recording combined observations; Causal judgments need to control variables|

## B.3 How is it read?

Provided by Author [Original framework chart](../../01-deployment-foundations/assets/edge-llm-deployment-framework-original.png) It is not changed, as a reference to knowledge. The classification and abbreviation in the diagram are explained in this appendix and in the original text.

## B.4 Source and reference rules

Prioritizing the corresponding official documentation of concepts and supporting conditions; Performance and failures refer to the author's specific engineering records. Private pages are not public and are created using the E01 E20 number and technical title [The source index](../evidence/README.md).

Formal descriptions of historical observations, command templates, instructional calculations and pending testing. The example code is a public path rewriting; There is no evidence of this wheel being executed by the hardware, and it is not written as this wheel is measured.

External models and data are available under their respective licenses, and repository documentation licenses do not automatically grant model redistribution permissions. Prototypes and logs without access to public rights are not preserved.

## B.5 Model and Implementation of the Expanded Model

|Content of correspondence|Public data entry|
| --- | --- |
|OpenVINO Qwen3-TTS conversion and operation| [The official notebook](https://github.com/openvinotoolkit/openvino_notebooks/blob/latest/notebooks/qwen3-tts/qwen3-tts.ipynb) |
|Kokoro OpenVINO/NPUW method| [The official notebook](https://github.com/openvinotoolkit/openvino_notebooks/blob/latest/notebooks/kokoro/kokoro.ipynb) |
|Kokoro model, license and sound| [Model card](https://huggingface.co/hexgrad/Kokoro-82M) · [Audio description](https://huggingface.co/hexgrad/Kokoro-82M/blob/main/VOICES.md) |
|BabelVox INT8 model and device| [Model card](https://huggingface.co/djwarf/babelvox-openvino-int8) |
|Qwen3-TTS original model and source of CPU finished product| [Qwen model card](https://huggingface.co/Qwen/Qwen3-TTS-12Hz-0.6B-CustomVoice) · [Community IR](https://huggingface.co/aurora2035/Qwen3-TTS-12Hz-0.6B-CustomVoice-OpenVINO-INT8) |
| MLX-VLM | [Project and model support](https://github.com/Blaizzy/mlx-vlm) |
| llama.cpp RPC | [RPC description](https://github.com/ggml-org/llama.cpp/tree/master/tools/rpc) |
|Ray/vLLM multi-node| [VLLM distributed service documentation](https://docs.vllm.ai/en/latest/serving/distributed_serving/) |

The above latest/main/master links are used to continue browsing; Officially measured reading by historical date and version as indicated. The reproduction experiment should also fix the used notebook/code to a specific commit and cannot cover the original support conditions with today's default branch.

## B.6 Hardware and compute software stack basics

This information is used to understand the responsibilities of the components; The specific installation is still executed according to the supported version of the target hardware, OS and engine.

|Platform/theme|Official data|Check the content|
| --- | --- | --- |
|The CUDA platform| [CUDA Platform](https://docs.nvidia.com/cuda/cuda-programming-guide/01-introduction/cuda-platform.html) |Driver, Driver API, Runtime and the relationship between Toolkit|
|NVIDIA matrix library| [cuBLAS/cuBLASLt](https://docs.nvidia.com/cuda/cublas/index.html) |Matrix computation, layout, data types and algorithms|
|NVIDIA communication| [NCCL](https://docs.nvidia.com/deeplearning/nccl/user-guide/docs/overview.html) |Collective communication and interconnect|
|The AMD platform| [What is ROCm](https://rocm.docs.amd.com/en/latest/what-is-rocm.html) |Compiler, runtime, compute library and tools|
|Support for AMD devices| [ROCm on Radeon/Ryzen](https://rocm.docs.amd.com/projects/radeon-ryzen/en/latest/) |Accurate model, OS and software coverage|
|AMD communication| [RCCL](https://rocm.docs.amd.com/projects/rccl/en/latest/) |Multi-GPU or multi-node collective communication|
|The Apple GPU interface| [Metal](https://developer.apple.com/metal/) |GPU commands, shaders and computational execution|
|Apple's machine learning framework| [MLX](https://ml-explore.github.io/mlx/build/html/index.html) / [unified memory](https://ml-explore.github.io/mlx/build/html/usage/unified_memory.html) |Computers, CPUs/GPUs, shared memory, inertial values|
|Apple text model| [MLX-LM](https://github.com/ml-explore/mlx-lm) |Model implementation and generation tools on top of MLX|
|Intel develops the chip| [oneAPI](https://www.intel.com/content/www/us/en/developer/tools/oneapi/overview.html) / [OpenVINO](https://docs.openvino.ai/) |Development tools, compute library, inference Runtime and generated pipelines|
|Ascend software stack| [CANN](https://www.hiascend.com/en/software/cann) |Runtime, operators, development tools and upstream support|
