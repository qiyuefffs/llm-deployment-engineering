# Model artifact Engineering records: HF converts GGUF, quantization and Ollama imports

[简体中文](../../01-deployment-foundations/appendices/gguf-ollama.md) | **English**

[Index of engineering examples](README.md) · [General directory of knowledge systems](../SUMMARY.md)

Technical labels: `safetensors / GGUF / quantize / Modelfile`

## Link to artifact

```text
HF high precision source directory+revision → converter commit → F16/BF16 GGUF
 ← Q4/Q5/Q8 Candidate → llama.cpp Loading and quality → Modelfile → Ollama API
```

Conversion, quantization, and import are three independent checkpoints. GGUF is not equal to quantization; Model disk shard is not equal to GPU split; Once Ollama is successfully imported, you will need to check the template and actual GPU offloading. The complete original conversion and Modelfile operations are maintained as follows, supporting the Unified Directory examples see [GGUF artifact process](../chapters/models/gguf-conversion.md).

## Agreement on the use of complete technical records

The following technical correctness, commands, tables, logs, failures and subsequent experiments of the relevant FlowUs articles are retained directly, without abbreviating the original process. private paths, nodes, authentication and sanitization of attached addresses; `<NODE_IP>` For example, the placeholder needs to be filled in the current environment. The original suggestion or prediction is still a suggestion or prediction. The above execution sequence and technical revisions are used to explain conflicts in historical records, and historical GPU/NPU experiments have not been repeated in this round.

## R50 · Model conversion and quantization using llama.cpp, followed by custom model use of ollama.

llama.cpp quantization link: [https://blog.csdn.net/shebao3333/article/details/139428868](https://blog.csdn.net/shebao3333/article/details/139428868)

ipex-llm link: [https://ipex-llm-latest.readthedocs.io/en/latest/doc/LLM/Quickstart/ollama_quickstart.html](https://ipex-llm-latest.readthedocs.io/en/latest/doc/LLM/Quickstart/ollama_quickstart.html)

Ollama defines a large language model as: [https://blog.csdn.net/spiderwower/article/details/138506271](https://blog.csdn.net/spiderwower/article/details/138506271)

Quantization is defined as:

[Original note image: image.png; [Unpublished transcript]

1.1 Benefits of quantization

Quantization has several advantages:

Reduce memory usage: passed, reduced parameter precision, quantization significantly reduced model memory requirements, which are critical for deployment on memory-limited devices.

Increased speed: lower precision computing speeds are faster, thus speeding up model inference, which is particularly beneficial for real-time applications.

Keeping performance: Quantization aims to simplify models while maintaining their performance, ensuring that rural communities still have all the necessary facilities after scale-up.


[Original note image: image.png; [Unpublished transcript]

[Original note image: image.png; [Unpublished transcript]

1.4 What does Q#_K_M mean in a quantization model?

In the context of llama.cpp, Q4_K_M refers to a specific type of quantization method. The name of the agreement is as follows:

Q stands for quantization.

4 represents the number of digits used in the quantization process.

K represents the use of k-average clusters in quantization.

M represents the size of the model after quantization. S = small, M = in, L = large.

The real war process:

1. First, use conda to create a new environment: llamacpp.

    Create with: conda create -n llamacpp python=3.10

    Activation command: conda activate llamacpp
    Download the source code of llama.cpp, you can download the compilation bin yourself or download the compilation bin directly.

1. The model can be downloaded from the Models directory.

2. Enter the llama.cpp directory and use the convert_hf_gguf.py script to download the good model and convert it to gguf format.

  The model conversion command:

python convert_hf_to_gguf.py --outfile <to export file address.gguf> <minimized model source directory>

For example: python convert_hf_to_gguf.py ./modles/xxxx.gguf ./models/xxxx model files

Example 1: Python convert_hf_to_gguf.py --outfile /root/autodl-tmp/ggufs/qwen7b_lora.gguf /root/autodl-tmp/exports

1. model quantization

Quantization can help us. **Reducing the size of the model** But the cost is **Loss of model precision** This means that the model's ability to respond may decrease. After weighing, we can select the right quantization parameter to ensure the maximum efficiency of the model.

Further quantization of the model can be done using llama-quantize executable files.

Quantization numbers:

```text
    量化位数使用q表示，它代表存储权重（精度）的位数。q2、q3、q4… 表示模型的量化位数。例如，q2表示2位量化，q3表示3位量化，以此类推。量化位数越高，模型的精度损失就越小，模型的磁盘占用和计算需求也会越大。

     我们使用llama-quantize量化模型，它提供各种量化位数的模型：Q2、Q3、Q4、Q5、Q6、Q8、F16。量化模型的命名方法遵循: Q + 量化比特位 + 变种。具体的量化参数可以在llama.cpp目录下使用./llama-quantize查看。部分示例如下：
```

[Original note image: image.png; [Unpublished transcript]

```text
llama-quantize <原模型目录> <转换后的模型保存路径> <量化位数>
```

```text
./llama-quantize /root/autodl-tmp/ggufs/qwen7b_lora.gguf /root/autodl-tmp/ggufs/qwen7b_lora_q4.gguf q4_0
```

```text
# quantize the model to 4-bits (using Q4_K_M method)
./quantize ./models/nous-hermes-2-mistral-7B-DPO/ggml-model-f16.gguf ./models/nous-hermes-2-mistral-7B-DPO/ggml-model-Q4_K_M.gguf Q4_K_M
```

Passed conversion and quantization can be obtained from a model source file deployed in ollama.

1. Create custom large language models using ollama

      Create a Modelfile and add the following:

```text
FROM /srv/llm/data/ollama-file/models/MiniCPM-Llama3-V-2_5/model/model-Q4_K_M.gguf
TEMPLATE [INST] {{ if .System }}{{ .System }} {{ end }}{{ .Prompt }} [/INST]
PARAMETER stop [INST]
PARAMETER stop [/INST]

LICENSE """ Apache License  Version 2.0, January 2004 """
```

### Ollama create model name -f Modelfile file path

ollama create panda -f C:/llm\Desktop\ollama\test.Modelfile

The generated model file will be placed in the model folder under the .ollama directory, and run

ollama run panda
