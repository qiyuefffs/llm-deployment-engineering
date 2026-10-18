"""Fetch the public, fixed Windows CPU engine and GGUF for the book exercise."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import time
import urllib.request
import zipfile


def sha256(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def download(url, target, expected_size=None, expected_sha=None):
    if target.exists() and (expected_size is None or target.stat().st_size == expected_size):
        if expected_sha is None or sha256(target) == expected_sha:
            print(f'Already present: {target.name}', flush=True)
            return
    partial = target.with_suffix(target.suffix + '.partial')
    req = urllib.request.Request(url, headers={'User-Agent': 'deployment-book-exercise'})
    with urllib.request.urlopen(req, timeout=60) as response, partial.open('wb') as output:
        count = 0
        last = time.monotonic()
        while True:
            block = response.read(1024 * 1024)
            if not block:
                break
            output.write(block)
            count += len(block)
            if time.monotonic() - last >= 10:
                print(f'{target.name}: {count / 1024**2:.1f} MiB', flush=True)
                last = time.monotonic()
    if expected_size is not None and partial.stat().st_size != expected_size:
        raise RuntimeError('Downloaded size does not match manifest')
    if expected_sha is not None and sha256(partial) != expected_sha:
        raise RuntimeError('Downloaded SHA256 does not match manifest')
    partial.replace(target)
    print(f'Downloaded: {target.name}', flush=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--runtime-dir', required=True, type=Path)
    args = parser.parse_args()
    if platform.system() != 'Windows' or platform.machine().lower() not in ('amd64', 'x86_64'):
        raise SystemExit('This preparation script targets Windows x64; use the source-build chapter for other platforms.')
    spec = json.loads(Path(__file__).with_name('manifest.json').read_text(encoding='utf-8'))
    runtime = args.runtime_dir.resolve()
    runtime.mkdir(parents=True, exist_ok=True)
    binary = runtime / 'llama-b9557-bin-win-cpu-x64.zip'
    download(spec['engine']['url'], binary, expected_sha=spec['engine']['archive_sha256'])
    with zipfile.ZipFile(binary) as archive:
        for member in archive.infolist():
            dest = (runtime / member.filename).resolve()
            if not dest.is_relative_to(runtime):
                raise RuntimeError('Archive path outside runtime directory')
        archive.extractall(runtime)
    model = spec['model']
    download(model['url'], runtime / model['filename'], model['bytes'], model['sha256'])
    hashes = {'engine_archive_sha256': sha256(binary), 'model_sha256': sha256(runtime / model['filename'])}
    (runtime / 'download-hashes.json').write_text(json.dumps(hashes, indent=2) + '\n', encoding='utf-8')
    print('Prepared. The model SHA256 matches the public LFS manifest.', flush=True)


if __name__ == '__main__':
    main()
