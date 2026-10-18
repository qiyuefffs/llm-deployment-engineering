"""Run the complete book CPU exercise and stop only the server this script owns."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
import os
from pathlib import Path
import platform
import socket
import statistics
import subprocess
import time
import urllib.error
import urllib.request

BASE = Path(__file__).resolve().parent
SPEC = json.loads((BASE / 'manifest.json').read_text(encoding='utf-8'))


def write_json(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def request_json(url, body=None):
    data = None if body is None else json.dumps(body).encode('utf-8')
    req = urllib.request.Request(url, data=data, headers={'Content-Type': 'application/json'})
    with urllib.request.urlopen(req, timeout=120) as response:
        return json.load(response)


def stream_request(base_url, task):
    request_id, prompt = task
    body = {'model': SPEC['server']['alias'], 'messages': [{'role': 'user', 'content': prompt}],
            'max_tokens': 32, 'temperature': 0, 'stream': True,
            'stream_options': {'include_usage': True}, 'cache_prompt': False}
    req = urllib.request.Request(base_url + '/v1/chat/completions',
                                 data=json.dumps(body).encode('utf-8'),
                                 headers={'Content-Type': 'application/json'})
    start = time.perf_counter()
    first = None
    parts = []
    usage = None
    finish = None
    try:
        with urllib.request.urlopen(req, timeout=120) as response:
            for line in response:
                if not line.startswith(b'data: '):
                    continue
                raw = line[6:].strip()
                if raw == b'[DONE]':
                    break
                event = json.loads(raw)
                if event.get('usage'):
                    usage = event['usage']
                for choice in event.get('choices', []):
                    text = choice.get('delta', {}).get('content') or ''
                    if text:
                        if first is None:
                            first = time.perf_counter()
                        parts.append(text)
                    finish = choice.get('finish_reason') or finish
        elapsed = time.perf_counter() - start
        if first is None or not usage:
            raise RuntimeError('Missing generated content or usage in stream')
        n = usage['completion_tokens']
        ttft = first - start
        return {'id': request_id, 'success': True, 'prompt': prompt, 'content': ''.join(parts),
                'usage': usage, 'finish_reason': finish, 'e2e_s': elapsed, 'ttft_s': ttft,
                'tpot_s': (elapsed - ttft) / (n - 1) if n > 1 else None}
    except Exception as exc:
        return {'id': request_id, 'success': False, 'error_type': type(exc).__name__}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--runtime-dir', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--strict', action='store_true', help='Exit 2 when acceptance fails')
    args = parser.parse_args()
    runtime, output = args.runtime_dir.resolve(), args.output.resolve()
    if output.exists() and any(output.iterdir()):
        raise SystemExit('Use an empty output directory; previous evidence is never overwritten.')
    output.mkdir(parents=True, exist_ok=True)
    model = runtime / SPEC['model']['filename']
    h = hashlib.sha256()
    with model.open('rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            h.update(block)
    if h.hexdigest() != SPEC['model']['sha256']:
        raise RuntimeError('Model checksum mismatch; run prepare.py first')
    config = SPEC['server']
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        try:
            probe.bind((config['host'], config['port']))
        except OSError:
            raise SystemExit('Exercise port is occupied; stop your own instance before running.')
    url = f'http://{config["host"]}:{config["port"]}'
    command = [str(runtime/'llama-server.exe'), '-m', str(model), '--host', config['host'],
               '--port', str(config['port']), '--alias', config['alias'], '-c', str(config['context']),
               '-np', str(config['parallel']), '-t', str(config['threads']), '-tb', str(config['threads']),
               '-ngl', '0', '--metrics', '--chat-template-kwargs', '{"enable_thinking":false}']
    version_run = subprocess.run([str(runtime/'llama-server.exe'), '--version'], capture_output=True, text=True)
    engine_version = (version_run.stdout + version_run.stderr).strip()
    environment = {'date': time.strftime('%Y-%m-%d'), 'system': platform.system(),
                   'os_version': platform.version(), 'machine': platform.machine(),
                   'python': platform.python_version(), 'logical_processors': os.cpu_count(),
                   'engine_version': engine_version, 'execution_backend': 'CPU; -ngl 0',
                   'model_sha256': h.hexdigest(), 'spec': SPEC}
    write_json(output/'environment.json', environment)
    write_json(output/'download-hashes.json', json.loads((runtime/'download-hashes.json').read_text(encoding='utf-8')))
    public_command = [x.replace(str(runtime), '<runtime>') for x in command]
    write_json(output/'server-command.json', public_command)
    raw_log = runtime/'exercise-server.log'
    flags = getattr(subprocess, 'CREATE_NO_WINDOW', 0)
    with raw_log.open('wb') as log:
        process = subprocess.Popen(command, stdout=log, stderr=subprocess.STDOUT, creationflags=flags)
        try:
            deadline = time.monotonic() + 120
            while True:
                if process.poll() is not None:
                    raise RuntimeError('Owned server exited; inspect exercise-server.log in runtime directory')
                try:
                    request_json(url+'/health')
                    break
                except (urllib.error.URLError, TimeoutError):
                    if time.monotonic() > deadline:
                        raise RuntimeError('Server readiness timeout')
                    time.sleep(0.5)
            print('Server ready on loopback; running functional checks.', flush=True)
            write_json(output/'models.json', request_json(url+'/v1/models'))
            samples = [('arithmetic', '计算2+2。只输出一个数字。', '4'),
                       ('capital', '中国首都是哪座城市？只输出城市名。', '北京'),
                       ('json', '只输出这个JSON对象，不要代码块或解释：{"ready":true}', None)]
            functional = []
            for name, prompt, expected in samples:
                start = time.perf_counter()
                result = request_json(url+'/v1/chat/completions', {
                    'model': config['alias'], 'messages': [{'role': 'user', 'content': prompt}],
                    'max_tokens': 64, 'temperature': 0, 'stream': False, 'cache_prompt': False})
                content = result['choices'][0]['message'].get('content') or ''
                if expected is None:
                    try:
                        passed = json.loads(content) == {'ready': True}
                    except ValueError:
                        passed = False
                else:
                    passed = content.strip() == expected
                functional.append({'id': name, 'prompt': prompt, 'expected': expected or {'ready': True},
                                   'passed': passed, 'elapsed_s': time.perf_counter()-start, 'response': result})
            write_json(output/'functional.json', functional)
            bad = urllib.request.Request(url+'/v1/chat/completions', data=b'{',
                                         headers={'Content-Type': 'application/json'})
            try:
                with urllib.request.urlopen(bad, timeout=30) as response:
                    invalid = {'status': response.status, 'passed': False}
            except urllib.error.HTTPError as exc:
                invalid = {'status': exc.code, 'passed': 400 <= exc.code < 500,
                           'body': exc.read().decode('utf-8')}
            invalid['health_after'] = request_json(url+'/health')
            write_json(output/'invalid-request.json', invalid)
            all_rows = []
            summaries = []
            for concurrency in (1, 2):
                tasks = [(f'c{concurrency}-r{i}', f'本轮编号{concurrency}-{i}。依次列出从1到30的整数，用逗号分隔。') for i in range(4)]
                start = time.perf_counter()
                with ThreadPoolExecutor(max_workers=concurrency) as pool:
                    rows = list(pool.map(lambda task: stream_request(url, task), tasks))
                duration = time.perf_counter()-start
                ok = [r for r in rows if r['success']]
                total = sum(r['usage']['completion_tokens'] for r in ok)
                summary = {'concurrency': concurrency, 'requests': len(rows), 'successes': len(ok),
                           'failures': len(rows)-len(ok), 'duration_s': duration, 'generated_tokens': total,
                           'output_token_per_s': total/duration,
                           'mean_ttft_s': statistics.mean(r['ttft_s'] for r in ok) if ok else None,
                           'mean_e2e_s': statistics.mean(r['e2e_s'] for r in ok) if ok else None,
                           'limits': '4 requests per group; no stable tail estimate or quality benchmark. Fixed 32-token cap may truncate listing.'}
                summaries.append(summary)
                all_rows.extend(rows)
                print(f'HTTP c{concurrency}: {len(ok)}/4; {total/duration:.2f} output token/s', flush=True)
            (output/'requests.jsonl').write_text(''.join(json.dumps(r, ensure_ascii=False)+'\n' for r in all_rows), encoding='utf-8')
            write_json(output/'http-summary.json', summaries)
            with urllib.request.urlopen(url+'/metrics', timeout=30) as response:
                text = response.read().decode('utf-8')
            metric_lines = [line for line in text.splitlines() if line.startswith('llamacpp:') and '{' not in line]
            (output/'metrics.txt').write_text('\n'.join(metric_lines)+'\n', encoding='utf-8')
            print('Functional checks and HTTP exercise saved.', flush=True)
        finally:
            process.terminate()
            try:
                process.wait(timeout=15)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=10)
    text = raw_log.read_text(encoding='utf-8', errors='replace').replace(str(runtime), '<runtime>')
    text = text.replace(str(runtime).replace('\\', '/'), '<runtime>')
    text = '\n'.join(line.rstrip() for line in text.splitlines()) + '\n'
    (output/'server.log').write_text(text, encoding='utf-8')
    print('Owned server stopped. Running isolated engine benchmark.', flush=True)
    bench = subprocess.run([str(runtime/'llama-bench.exe'), '-m', str(model), '-ngl', '0',
                            '-t', str(config['threads']), '-p', '64', '-n', '32', '-r', '3', '-o', 'json'],
                           capture_output=True, text=True, check=True, timeout=180)
    raw = json.loads(bench.stdout)
    fields = ('build_commit','build_number','cpu_info','model_type','model_size','model_n_params',
              'n_threads','n_gpu_layers','n_prompt','n_gen','avg_ns','stddev_ns','avg_ts','stddev_ts')
    public = [{k: row[k] for k in fields if k in row} for row in raw]
    write_json(output/'engine-benchmark.json', public)
    passed = all(row['passed'] for row in functional) and invalid['passed'] and all(s['failures']==0 for s in summaries)
    write_json(output/'acceptance.json', {'functional_passed':sum(r['passed'] for r in functional),
               'functional_total':len(functional),'invalid_request_passed':invalid['passed'],
               'http_groups_successful':all(s['failures']==0 for s in summaries),
               'engine_benchmark_rows':len(public),'exercise_passed':passed,
               'scope':'Small CPU teaching exercise; not a large-model capacity or production quality claim.'})
    print(f'Exercise complete: functional {sum(r["passed"] for r in functional)}/{len(functional)}; malformed request HTTP {invalid["status"]}; PASS={passed}', flush=True)
    if args.strict and not passed:
        raise SystemExit(2)


if __name__ == '__main__':
    main()
