#!/usr/bin/env python3
"""Check historical note arithmetic; never run inference or network calls."""
import json
from pathlib import Path


def require(condition, message):
    if not condition:
        raise ValueError(message)


def throughput_consistent(tokens, seconds, reported):
    calculated = tokens / seconds
    require(abs(calculated - reported) < 0.011,
            f'Throughput mismatch: {calculated} vs {reported}')
    return calculated


def main():
    root = Path(__file__).resolve().parents[1]
    data = json.loads((root / 'evidence' / 'measurements.json').read_text(encoding='utf-8'))
    lines = ['Offline arithmetic checks (no model, GPU, NPU or network calls)']
    dgx = data['dgx_qwen_fp8']
    require(dgx['successes'] + dgx['failures'] == dgx['requests'], 'DGX counts')
    tps = throughput_consistent(dgx['generated_tokens'], dgx['duration_s'], dgx['output_token_per_s'])
    lines.append(f'DGX FP8: {dgx["successes"]}/{dgx["requests"]}; {tps:.2f} output token/s')
    intel = data['intel_openvino']
    ratio = intel['int4']['throughput_token_per_s'] / intel['int8']['throughput_token_per_s']
    lines.append(f'Intel IR INT4/INT8: observed generation-rate ratio {ratio:.2f}x (quality incomplete)')
    omlx = data['omlx_concurrency']['rows']
    require([r['concurrency'] for r in omlx] == [1, 2, 4], 'oMLX groups')
    require(all(r['requests'] >= r['concurrency'] for r in omlx), 'oMLX sample counts')
    lines.append('oMLX: c1/c2/c4 groups present; sample sizes 20/10/10 (not stable tail estimates)')
    mtp = data['gemma_mtp']
    require(len(mtp['base']) == len(mtp['mtp']) == 3, 'MTP group count')
    for base, candidate in zip(mtp['base'], mtp['mtp']):
        require((base['concurrency'], base['requests']) ==
                (candidate['concurrency'], candidate['requests']), 'MTP pair mismatch')
        gain = (candidate['output_token_per_s'] / base['output_token_per_s'] - 1) * 100
        lines.append(f'Gemma MTP c{base["concurrency"]}: observed throughput gain {gain:.2f}%')
    dflash = data['dflash_observation']
    for label in ('base', 'dflash'):
        run = dflash[label]
        throughput_consistent(dflash['generated_tokens'], run['duration_s'], run['output_token_per_s'])
    ratio = dflash['dflash']['output_token_per_s'] / dflash['base']['output_token_per_s']
    lines.append(f'DFlash configurations: observed ratio {ratio:.2f}x (multiple parameters differ)')
    awq = data['gemma_awq']
    require(awq['successes'] + awq['failures'] == awq['requests'], 'AWQ counts')
    for label in ('awq4', 'awq8'):
        run = awq[label]
        throughput_consistent(awq['generated_tokens'], run['duration_s'], run['output_token_per_s'])
    ratio = awq['awq4']['output_token_per_s'] / awq['awq8']['output_token_per_s']
    lines.append(f'Gemma AWQ4/AWQ8: observed throughput ratio {ratio:.2f}x (quality unverified)')
    amd = data['amd_rpc']
    require(amd['gtt_requested_bytes'] > amd['ttm_actual_bytes'], 'AMD memory ordering')
    lines.append('AMD RPC: requested GTT exceeds recorded TTM; no single-machine speedup computed')
    rtx = data['rtx2060_hybrid']
    for count_key, time_key, rate_key in [
        ('prompt_tokens', 'prompt_ms', 'prompt_token_per_s'),
        ('generated_tokens', 'generation_ms', 'generation_token_per_s'),
    ]:
        throughput_consistent(rtx[count_key], rtx[time_key] / 1000, rtx[rate_key])
    require(abs(rtx['prompt_ms'] + rtx['generation_ms'] - rtx['combined_ms']) < .001,
            'RTX combined timing')
    lines.append('RTX2060 Q6: 9 prompt / 182 generated tokens; 9.04 / 5.26 token/s')
    awq31 = data['gemma_awq_31b']
    for label in ('awq4', 'awq8'):
        run = awq31[label]
        throughput_consistent(awq31['generated_tokens'], run['duration_s'], run['output_token_per_s'])
    lines.append('Gemma31B AWQ4/AWQ8: rounded throughput and shared token totals agree')
    for label in ('base', 'mtp'):
        for run in mtp[label]:
            throughput_consistent(run['requests'] * 256, run['duration_s'], run['output_token_per_s'])
    asr = data['intel_whisper_asr']
    computed_rtf = sum(asr['infer_s']) / len(asr['infer_s']) / asr['audio_s']
    lines.append(f'Whisper: RTF from rounded core timings {computed_rtf:.5f}; source rounded-RTF mean ~0.0387')
    full_npu = data['intel_babelvox_full_npu']
    for seconds, duration, rtf in zip(full_npu['core_generation_s'], full_npu['audio_s'], full_npu['reported_rtf']):
        require(abs(seconds / duration - rtf) < .001, 'Full-NPU TTS RTF')
    require(not full_npu['quality_passed'], 'Do not mark invalid audio as passing')
    kokoro = data['intel_kokoro_cpu']
    require(kokoro['samples'] == kokoro['voices'] * kokoro['text_types'] == 48, 'Kokoro samples')
    require(kokoro['peak_rss_kib'] / 1024**2 > kokoro['rss_target_gib'], 'Kokoro RSS target failure')
    require(not data['intel_kokoro_npuw']['deployment_passed'] and data['intel_kokoro_npuw']['rtf'] is None,
            'No NPUW throughput without generated audio')
    lines.append(f'Kokoro CPU: 48 samples; {1 / kokoro["rtf_mean"]:.2f}x realtime; RSS target failed')
    lines.append('Speech: full-NPU quality failure and NPUW load failure remain explicit')
    apu = data['amd_8060s_vulkan']
    q4 = apu['q4_k_m']
    offload_ratio = q4['gpu_initial_decode_token_per_s'] / q4['cpu_decode_token_per_s']
    tuning_ratio = q4['gpu_parameter_group_decode_token_per_s'] / q4['gpu_initial_decode_token_per_s']
    lines.append(f'AMD8060S: observed CPU/GPU ratio {offload_ratio:.2f}x; '
                 f'GPU configuration-group ratio {tuning_ratio:.2f}x (not causal estimates)')
    lines.append('PASS: covered counts and rounded arithmetic agree; source runs and quality are not verified.')
    print('\n'.join(lines))


if __name__ == '__main__':
    main()
