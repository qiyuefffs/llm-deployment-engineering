#!/usr/bin/env python3
"""Render the chapter reading path as SVG and PNG (Pillow, local Chinese font)."""
from html import escape
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'docs' / '01-deployment-foundations' / 'assets'
GROUPS = [
    ('准备', '#2563eb', [('01', '明确部署目标', '设备、任务、验收'), ('02', '检查设备与环境', '驱动、工具链、后端'), ('03', '准备模型制品', '格式、量化、哈希'), ('04', '计算内存预算', '权重、KV、并发')]),
    ('跑通', '#0f766e', [('05', '建立单机服务', '构建、加载、API'), ('06', '迁移目标设备', 'AMD、Intel、Mac'), ('07', '配置服务调度', '批处理、缓存、长度')]),
    ('验证与优化', '#7c3aed', [('08', '保存性能基线', '输入、延迟、质量'), ('09', '开展对照实验', '假设、单变量、代价'), ('10', '按阶段排障', '日志、最小复现'), ('11', '按需求扩展设备', '通信、切分、容量')]),
    ('交付', '#b45309', [('12', '交付可用服务', '启停、监控、恢复'), ('13', '查词与查证据', '来源、口径、限制')]),
]


def main():
    candidates = [Path('C:/Windows/Fonts/msyh.ttc'), Path('/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc')]
    font_path = next((p for p in candidates if p.exists()), None)
    if font_path is None:
        raise SystemExit('Install a Chinese font or add its path to candidates.')
    im = Image.new('RGB', (1440, 940), '#f8fafc')
    draw = ImageDraw.Draw(im)
    fonts = {size: ImageFont.truetype(str(font_path), size) for size in (20, 22, 24, 28, 42)}
    svg = ['<svg xmlns="http://www.w3.org/2000/svg" width="1440" height="940" viewBox="0 0 1440 940" role="img" aria-labelledby="title desc">',
           '<title id="title">大模型部署适配工程阅读路线</title>',
           '<desc id="desc">从目标、环境、模型和内存开始，经过服务、迁移、测量、优化和排障，最终完成交付。</desc>',
           '<rect width="1440" height="940" fill="#f8fafc"/>',
           '<g font-family="Microsoft YaHei, Noto Sans CJK SC, sans-serif">']

    def rect(x, y, w, h, fill, stroke='#e2e8f0', radius=14):
        draw.rounded_rectangle((x, y, x+w, y+h), radius=radius, fill=fill, outline=stroke, width=1)
        svg.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{radius}" fill="{fill}" stroke="{stroke}"/>')

    def text(x, y, value, size=24, fill='#0f172a'):
        draw.text((x, y), value, font=fonts[size], fill=fill)
        svg.append(f'<text x="{x}" y="{y+size}" font-size="{size}" fill="{fill}">{escape(value)}</text>')

    text(40, 35, '大模型部署适配：从设备到可交付服务', 42)
    text(42, 104, '按操作顺序学习，每一步都留下文件、日志或可复查的结果。', 24, '#475569')
    for i, (title, color, steps) in enumerate(GROUPS):
        x = 40 + i * 350
        rect(x, 175, 310, 65, color, color)
        text(x+22, 189, title, 28, '#ffffff')
        for j, (number, name, detail) in enumerate(steps):
            y = 263 + j*129
            rect(x, y, 310, 110, '#ffffff')
            text(x+18, y+12, number, 22, color)
            text(x+58, y+10, name, 24)
            text(x+19, y+58, detail, 20, '#475569')
        if i < 3:
            text(x+318, 190, '→', 24, '#64748b')
    rect(40, 827, 1360, 74, '#e2e8f0', '#e2e8f0')
    text(63, 847, '记录原则：固定版本与输入  ·  实测、估算、待验证分清  ·  原始证据可追溯', 24)
    svg.append('</g></svg>')
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT/'deployment-workflow.svg').write_text('\n'.join(svg)+'\n', encoding='utf-8')
    im.save(OUT/'deployment-workflow.png')
    print('Rendered deployment-workflow.svg and deployment-workflow.png')


if __name__ == '__main__':
    main()
