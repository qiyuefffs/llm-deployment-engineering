"""Send a local public image to a compatible chat service and preserve SSE evidence."""
import argparse
import base64
import hashlib
import json
import mimetypes
from pathlib import Path
import time
from urllib.error import HTTPError
from urllib.request import Request, urlopen


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--url', default='http://127.0.0.1:8007/v1/chat/completions')
    parser.add_argument('--model', required=True)
    parser.add_argument('--image', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--image-style', choices=['openai', 'mlx'], default='openai')
    parser.add_argument('--max-tokens', type=int, default=512)
    parser.add_argument('--timeout', type=float, default=300)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    raw = args.image.read_bytes()
    mime = mimetypes.guess_type(args.image.name)[0] or 'application/octet-stream'
    uri = 'data:' + mime + ';base64,' + base64.b64encode(raw).decode('ascii')
    picture = ({'type': 'image_url', 'image_url': {'url': uri}}
               if args.image_style == 'openai'
               else {'type': 'input_image', 'image_url': uri})
    payload = {
        'model': args.model,
        'messages': [{'role': 'user', 'content': [
            {'type': 'text', 'text': '逐行读取全部文字。再按从左到右的顺序描述三个图形和颜色。不要推测图片外的信息。'},
            picture,
        ]}],
        'temperature': 0, 'max_tokens': args.max_tokens, 'stream': True,
    }
    encoded = json.dumps(payload, ensure_ascii=False).encode('utf-8')
    (args.output / 'request.json').write_bytes(encoded)
    request = Request(args.url, data=encoded, headers={'Content-Type': 'application/json'})
    start = time.perf_counter()
    first_content_s = None
    done = False
    finish = None
    usage = None
    pieces = []
    status = None
    try:
        with urlopen(request, timeout=args.timeout) as response, \
                (args.output / 'events.jsonl').open('w', encoding='utf-8') as events:
            status = response.status
            for line in response:
                text = line.decode('utf-8').strip()
                if not text.startswith('data:'):
                    continue
                data = text[5:].strip()
                now = time.perf_counter() - start
                events.write(json.dumps({'elapsed_s': now, 'data': data}, ensure_ascii=False) + '\n')
                events.flush()
                if data == '[DONE]':
                    done = True
                    break
                event = json.loads(data)
                if event.get('error'):
                    raise RuntimeError('Server returned an error event; inspect events.jsonl')
                if event.get('usage') is not None:
                    usage = event['usage']
                for choice in event.get('choices', []):
                    content = choice.get('delta', {}).get('content')
                    if content:
                        if first_content_s is None:
                            first_content_s = now
                        pieces.append(content)
                        print(content, end='', flush=True)
                    if choice.get('finish_reason') is not None:
                        finish = choice['finish_reason']
    except HTTPError as error:
        status = error.code
        (args.output / 'http-error.txt').write_bytes(error.read())
        raise SystemExit(f'HTTP {error.code}; inspect http-error.txt') from None
    finally:
        report = {
            'model': args.model, 'image_sha256': hashlib.sha256(raw).hexdigest(),
            'http_status': status, 'first_content_s': first_content_s,
            'wall_s': time.perf_counter() - start, 'sse_done': done,
            'finish_reason': finish, 'usage': usage,
            'content_fragments': len(pieces),
        }
        (args.output / 'summary.json').write_text(
            json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
        (args.output / 'answer.txt').write_text(''.join(pieces), encoding='utf-8')
    print()
    if not pieces or not (done or finish):
        raise SystemExit('No complete text stream; inspect events and server log')


if __name__ == '__main__':
    main()
