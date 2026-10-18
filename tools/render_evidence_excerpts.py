#!/usr/bin/env python3
"""Remove empty lower space from copies of existing Case screenshots.

The originals are read-only. Each excerpt keeps the full width and the top
480 pixels, including the application header, command and complete output.
Chapter captions link to the original, uncropped screenshot.
"""
from pathlib import Path

from PIL import Image


def main():
    root = Path(__file__).resolve().parents[1]
    source = root / 'cases' / 'llama-cpp-flash-attention' / 'figures'
    target = root / 'docs' / '01-deployment-foundations' / 'assets' / 'screenshots'
    target.mkdir(parents=True, exist_ok=True)
    files = sorted(source.glob('*.png'))
    if len(files) != 8:
        raise SystemExit('Expected the eight existing Case screenshots; review sources before regenerating.')
    for path in files:
        with Image.open(path) as original:
            if original.size != (1247, 956):
                raise SystemExit(f'Unexpected dimensions for {path.name}; review crop coordinates.')
            original.crop((0, 0, 1247, 480)).save(target / path.name)
        print(f'{path.name}: full width, top 480 px; original unchanged')


if __name__ == '__main__':
    main()
