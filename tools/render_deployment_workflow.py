#!/usr/bin/env python3
"""Render the five-layer knowledge structure as SVG and PNG."""
from html import escape
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'docs' / '01-deployment-foundations' / 'assets'
WIDTH, HEIGHT = 1600, 1360
LAYERS = [
    ('01', '硬件后端适配', '设备 · 驱动 · Runtime · 编译 · 通信', '兼容记录 / 最小计算', '#2563eb'),
    ('02', '模型格式与量化', '模型身份 · 格式 · 精度 · 转换 · 质量', '制品清单 / 校验结果', '#0f766e'),
    ('03', '推理框架', '加载 · 算子 · 调度 · API · 并行', '服务入口 / 功能矩阵', '#7c3aed'),
    ('04', '显存与性能优化', '权重/KV · 负载 · 指标 · 瓶颈 · 实验', '资源预算 / 对照结果', '#b45309'),
    ('05', '工程交付', '环境 · 启停 · 验收 · 监控 · 回滚', '可运行材料 / 运维手册', '#be185d'),
]


def main():
    candidates = [Path('C:/Windows/Fonts/msyh.ttc'),
                  Path('/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc'),
                  Path('/System/Library/Fonts/PingFang.ttc')]
    font_path = next((p for p in candidates if p.exists()), None)
    if font_path is None:
        raise SystemExit('Install a Chinese font or add a path to candidates.')
    fonts = {n: ImageFont.truetype(str(font_path), n) for n in (23, 25, 26, 28, 30, 34, 48)}
    im = Image.new('RGB', (WIDTH, HEIGHT), '#f5f7fb')
    draw = ImageDraw.Draw(im)
    svg = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" height="{HEIGHT}" viewBox="0 0 {WIDTH} {HEIGHT}" role="img" aria-labelledby="title desc">',
           '<title id="title">大模型部署适配基础知识体系</title>',
           '<desc id="desc">一条工程主线、五层能力和七个模块。五层依次为硬件后端、模型格式量化、推理框架、显存性能、工程交付。</desc>',
           f'<rect width="{WIDTH}" height="{HEIGHT}" fill="#f5f7fb"/>',
           '<g font-family="Microsoft YaHei, Noto Sans CJK SC, sans-serif">']

    def rect(x, y, w, h, fill, stroke='#dbe3ed', radius=12):
        draw.rounded_rectangle((x, y, x+w, y+h), radius=radius, fill=fill, outline=stroke, width=1)
        svg.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{radius}" fill="{fill}" stroke="{stroke}"/>')

    def text(x, y, value, size=26, fill='#172b4d', max_width=None):
        if max_width is not None and draw.textlength(value, font=fonts[size]) > max_width:
            raise ValueError(f'Text overflow: {value}')
        draw.text((x, y), value, font=fonts[size], fill=fill)
        svg.append(f'<text x="{x}" y="{y+size}" font-size="{size}" fill="{fill}">{escape(value)}</text>')

    text(48, 35, '大模型部署适配基础知识体系', 48)
    text(50, 112, '一条主线串联工程步骤，五层能力组织知识，七个模块覆盖交付。', 28, '#52657c')
    rect(48, 179, 1504, 180, '#eaf1ff', '#d2e0fa')
    text(72, 198, '工程主线', 30, '#1d4ed8')
    text(72, 250, '模型选择  →  转换 / 量化  →  硬件后端  →  框架部署  →  内存与并发', 28, max_width=1450)
    text(72, 300, '性能压测  →  瓶颈定位  →  优化实验  →  API 服务  →  监控与交付', 28, max_width=1450)
    text(50, 397, '五层能力：对应第二部分的五个详细章节', 34)
    text(75, 457, '知识层', 25, '#52657c')
    text(505, 457, '主要内容', 25, '#52657c')
    text(1190, 457, '工程产物', 25, '#52657c')
    for i, (number, name, detail, output, color) in enumerate(LAYERS):
        y = 503 + i * 104
        rect(48, y, 1504, 91, '#ffffff')
        rect(65, y+18, 54, 54, color, color, 10)
        text(75, y+26, number, 26, '#ffffff')
        text(138, y+25, name, 30, max_width=345)
        text(505, y+30, detail, 26, '#334c67', max_width=655)
        text(1190, y+30, output, 25, '#334c67', max_width=342)
    text(50, 1041, '七个工程模块', 34)
    modules = ['硬件与后端', '模型与量化', '推理框架', '显存与 KV', '性能与瓶颈', '多卡与多节点', '监控与交付']
    for i, label in enumerate(modules):
        row, col = divmod(i, 4)
        x, y = 48+col*380, 1104+row*69
        rect(x, y, 364, 53, '#e9eef5', '#dbe3ed')
        text(x+19, y+10, f'{i+1}. {label}', 26)
    text(50, 1274, '每层讲清：是什么 → 怎么做 → 怎么检查；实例保留设备、版本、负载与限制。', 26, '#52657c', max_width=1500)
    svg.append('</g></svg>')
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT/'deployment-workflow.svg').write_text('\n'.join(svg)+'\n', encoding='utf-8')
    im.save(OUT/'deployment-workflow.png')
    print('Rendered five-layer map: deployment-workflow.svg / deployment-workflow.png')


if __name__ == '__main__':
    main()
