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
    lines.append('PASS: covered counts and rounded arithmetic agree; source runs and quality are not verified.')
    print('\n'.join(lines))


if __name__ == '__main__':
    main()
