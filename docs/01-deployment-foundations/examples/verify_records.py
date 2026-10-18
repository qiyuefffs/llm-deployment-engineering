#!/usr/bin/env python3
"""Recheck published transcriptions and calculations; does not run model inference."""
import csv
import hashlib
import json
from pathlib import Path


def main():
    chapter_dir = Path(__file__).resolve().parents[1]
    repo = chapter_dir.parents[1]
    case = repo / 'cases' / 'llama-cpp-flash-attention'
    workload = case / 'data' / 'workload.jsonl'
    prompts = [json.loads(line) for line in workload.read_text(encoding='utf-8').splitlines() if line.strip()]
    with (case / 'results' / 'observed-summary.csv').open(encoding='utf-8-sig', newline='') as f:
        rows = list(csv.DictReader(f))
    data = json.loads((chapter_dir / 'evidence' / 'measurements.json').read_text(encoding='utf-8'))
    assert len(prompts) == 8
    assert len(rows) == 12
    assert hashlib.sha256(workload.read_bytes()).hexdigest() == '18de6bb66f8cfe3e5dcad5df776cc200728c564aa781516dd5670007d73571f3'
    selected = {r['config_id']: r for r in rows if r['bucket'] == 'long' and int(r['concurrency']) == 2}
    off, on = selected['fa_off_repeat'], selected['fa_on_repeat']
    for row in (off, on):
        assert int(row['requests']) == 20 and int(row['successes']) == 20
    ttft_reduction = (1 - float(on['ttft_p95_s']) / float(off['ttft_p95_s'])) * 100
    throughput_gain = (float(on['output_token_per_s']) / float(off['output_token_per_s']) - 1) * 100
    dgx = data['dgx_qwen_fp8']
    calculated_tps = dgx['generated_tokens'] / dgx['duration_s']
    assert abs(calculated_tps - dgx['output_token_per_s']) < 0.01
    assert dgx['successes'] + dgx['failures'] == dgx['requests']
    intel = data['intel_openvino']
    ratio = intel['int4']['throughput_token_per_s'] / intel['int8']['throughput_token_per_s']
    lines = [
        'Offline record checks (no GPU inference)',
        f'Public workload: {len(prompts)} prompts; SHA256 verified',
        f'A10 transcribed summary: {len(rows)} groups',
        f'A10 long/c2, 20 requests/group: TTFT P95 reduction = {ttft_reduction:.2f}%',
        f'A10 long/c2, 20 requests/group: output throughput gain = {throughput_gain:.2f}%',
        f'DGX FP8: {dgx["generated_tokens"]}/{dgx["duration_s"]:.2f} = {calculated_tps:.2f} output token/s',
        f'Intel OpenVINO: INT4/INT8 throughput ratio = {ratio:.2f}x',
    ]
    for base, mtp in zip(data['gemma_mtp']['base'], data['gemma_mtp']['mtp']):
        assert base['concurrency'] == mtp['concurrency']
        assert base['requests'] == mtp['requests']
        gain = (mtp['output_token_per_s'] / base['output_token_per_s'] - 1) * 100
        lines.append(f'Gemma MTP c{base["concurrency"]}: transcribed output throughput gain = {gain:.2f}%')
    dflash = data['dflash_observation']
    for label in ('base', 'dflash'):
        run = dflash[label]
        assert abs(dflash['generated_tokens'] / run['duration_s'] - run['output_token_per_s']) < 0.01
    observed_ratio = dflash['dflash']['output_token_per_s'] / dflash['base']['output_token_per_s']
    lines.append(f'DFlash configurations: observed throughput ratio = {observed_ratio:.2f}x (multiple parameters differ)')
    lines.append('PASS: arithmetic and stated counts are consistent; source authenticity/quality require original runs.')
    print('\n'.join(lines))


if __name__ == '__main__':
    main()
