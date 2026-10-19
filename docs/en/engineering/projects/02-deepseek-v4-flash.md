# DeepSeek V4 Flash Deployment and Performance

[Project index](README.md) · [General methodology](../edge-llm-performance-methodology.md)

## 1. Applicable scenario

- DeepSeek V4 Flash on one, two, or three devices.
- Runtime selection among DwarfStar, llama.cpp RPC, Lemonade, Lucebox, and vLLM.
- Targets include short interaction, long context, multi-device prefill, speculation, and W4A16.

## 2. Route selection

| Target | Route |
| --- | --- |
| Single-device low latency | DwarfStar + DS4-aligned GGUF |
| General llama.cpp/ROCm | Unsloth UD-Q2_K_XL + Lemonade b1301 |
| Fast normal dialogue | Lucebox ROCmFPX quality |
| Long-prompt multi-device | DwarfStar distributed prefill |
| vLLM/Ray | W4A16 TP1/TP2 |
| Speculation | A/B only; off by default |

## 3. Minimum procedure

1. Check kernel, ROCm, AMDGPU firmware, GTT/TTM, and device enumeration.
2. Run HIP device, malloc, memset, kernel, and hipBLAS smoke.
3. Pin weights, runtime, build, KV, context, and sampling.
4. Pass single-device API and short output first.
5. Test 5K-250K context.
6. Then test dual/triple device and MTP/DSpark.

## 4. Performance method

| Test | Parameters | Metrics |
| --- | --- | --- |
| Short generation | 32/128/256 output | Decode, TTFT, E2E |
| Long context | 5K/10K/30K/50K/100K/250K | Prefill, decode, TTFT, resources |
| Multi-device | Same model/context/split | Worker load, prefill, decode |
| MTP/DSpark | Same target, off/on | Acceptance, TTFT, decode, E2E |
| W4A16 | TP1/TP2, prefix cache off | Load, effective prefill, decode, KV |

## 5. Representative results

| Route | Result |
| --- | --- |
| DwarfStar short single | About 16.07-16.20 tok/s |
| DwarfStar single 50K | Prefill 186.19; decode 13.10 |
| DwarfStar dual 50K | Prefill 348.56; decode 12.58 |
| DwarfStar triple 50K | Prefill 473.35; decode 11.89 |
| Unsloth b1301 single | Short decode 14.27; 2K prefill 176.63 |
| Unsloth b1301 dual | TG128 7.81; 8K frontier crash |
| Lucebox single quality | About 23 tok/s |
| W4A16 TP1/TP2 decode | About 4.5-4.7 tok/s |

## 6. Problems and boundary

- A GPU page fault began at a 4-byte memset; the root cause was a firmware overlay mismatch.
- DwarfStar multi-device raises long-prefill but lowers decode.
- General llama.cpp RPC provides no useful prefill scaling here.
- MTP is negative in the tested 5K-30K range and remains off.
- Different quantization and runtime measurements cannot form one absolute ranking.

