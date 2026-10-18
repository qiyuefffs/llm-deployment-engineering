"""Generate a public, deterministic input card; this does not run a model."""
import argparse
import hashlib
import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    card = Image.new('RGB', (960, 640), 'white')
    draw = ImageDraw.Draw(card)
    try:
        font = ImageFont.load_default(size=32)
    except TypeError:
        font = ImageFont.load_default()
    draw.text((50, 40), 'LOCAL INFERENCE TEST', fill='black', font=font)
    draw.text((50, 110), 'Order: DEMO-042', fill='black', font=font)
    draw.text((50, 170), 'Quantity: 3', fill='black', font=font)
    draw.text((50, 230), 'Total: 128.50', fill='black', font=font)
    draw.rectangle((70, 350, 270, 550), fill=(220, 40, 40))
    draw.ellipse((390, 350, 590, 550), fill=(40, 90, 220))
    draw.polygon([(750, 350), (650, 550), (850, 550)], fill=(40, 150, 70))
    image_path = args.output / 'vision-card.png'
    card.save(image_path)
    expected = {
        'width': 960, 'height': 640,
        'text': ['LOCAL INFERENCE TEST', 'Order: DEMO-042', 'Quantity: 3', 'Total: 128.50'],
        'shapes_left_to_right': ['red square', 'blue circle', 'green triangle'],
        'sha256': hashlib.sha256(image_path.read_bytes()).hexdigest(),
    }
    (args.output / 'expected.json').write_text(
        json.dumps(expected, indent=2), encoding='utf-8')
    print(json.dumps(expected, indent=2))


if __name__ == '__main__':
    main()
