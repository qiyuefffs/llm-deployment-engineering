"""Render the editable SVG and PNG knowledge map from the same layout.

Requires Pillow 12.1.1 and a Chinese font. Run from any working directory:
    python tools/render_knowledge_map.py --font /path/to/chinese-font.ttc
"""

import argparse
from html import escape
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


WIDTH, HEIGHT = 1680, 1352
NAVY = "#102D50"
INK = "#233B55"
MUTED = "#5D7086"
BACKGROUND = "#F4F7FB"


def find_font(explicit, bold=False):
    candidates = [explicit] if explicit else []
    candidates += [
        "C:/Windows/Fonts/msyhbd.ttc" if bold else "C:/Windows/Fonts/msyh.ttc",
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc"
        if bold else "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
        "/System/Library/Fonts/PingFang.ttc",
    ]
    for candidate in candidates:
        if candidate and Path(candidate).is_file():
            return candidate
    raise SystemExit("Chinese font not found; pass --font and optionally --font-bold")


class Canvas:
    def __init__(self, regular, bold):
        self.image = Image.new("RGB", (WIDTH, HEIGHT), BACKGROUND)
        self.draw = ImageDraw.Draw(self.image)
        self.font_paths = {False: regular, True: bold}
        self.fonts = {}
        self.svg = [
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" '
            f'height="{HEIGHT}" viewBox="0 0 {WIDTH} {HEIGHT}" role="img" '
            'aria-labelledby="map-title map-desc">',
            '<title id="map-title">大模型部署工程知识地图</title>',
            '<desc id="map-desc">从需求到交付的六步流程，以及硬件、显存、推理、'
            '测量、交付五层能力与各层的证据产物。</desc>',
        ]
        self.rect(0, 0, WIDTH, HEIGHT, BACKGROUND, radius=0)

    def rect(self, x, y, width, height, fill, stroke=None, radius=14):
        self.draw.rounded_rectangle(
            (x, y, x + width, y + height), radius=radius,
            fill=fill, outline=stroke, width=1,
        )
        self.svg.append(
            f'<rect x="{x}" y="{y}" width="{width}" height="{height}" '
            f'rx="{radius}" fill="{fill}" stroke="{stroke or "none"}"/>'
        )

    def line(self, x1, y1, x2, y2, color, width=1):
        self.draw.line((x1, y1, x2, y2), fill=color, width=width)
        self.svg.append(
            f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" '
            f'stroke="{color}" stroke-width="{width}"/>'
        )

    def text(self, x, y, value, size=22, color=INK, bold=False, max_width=None):
        key = (size, bold)
        if key not in self.fonts:
            self.fonts[key] = ImageFont.truetype(self.font_paths[bold], size)
        font = self.fonts[key]
        box = self.draw.textbbox((x, y), value, font=font, anchor="lt")
        if max_width is not None and box[2] - box[0] > max_width:
            raise ValueError(f"Text exceeds its column: {value}")
        if box[2] > WIDTH - 32 or box[3] > HEIGHT - 16:
            raise ValueError(f"Text exceeds the canvas: {value}")
        self.draw.text((x, y), value, font=font, fill=color, anchor="lt")
        family = "'Microsoft YaHei','Noto Sans CJK SC','PingFang SC',sans-serif"
        self.svg.append(
            f'<text x="{x}" y="{y}" dominant-baseline="text-before-edge" '
            f'font-family="{family}" font-size="{size}" '
            f'font-weight="{700 if bold else 400}" fill="{color}">'
            f'{escape(value)}</text>'
        )

    def save(self, output):
        output.mkdir(parents=True, exist_ok=True)
        self.image.save(output / "deployment-engineering-map.png", optimize=True)
        (output / "deployment-engineering-map.svg").write_text(
            "\n".join(self.svg + ["</svg>"]) + "\n", encoding="utf-8"
        )


def render(regular, bold, output):
    c = Canvas(regular, bold)
    c.rect(0, 0, WIDTH, 128, NAVY, radius=0)
    c.text(64, 27, "大模型部署工程知识地图", 44, "#FFFFFF", bold=True)
    c.text(66, 88, "从模型可运行，到性能可验证、服务可交付", 23, "#D6E4F5")

    steps = [
        ("明确需求", "输入 / 输出 / 质量与延迟目标"),
        ("确认兼容", "硬件 / 模型 / 精度 / 后端"),
        ("跑通服务", "加载 / 就绪 / API 与异常"),
        ("测量性能", "固定负载 / 保存基线"),
        ("定位优化", "提出假设 / 单变量对照"),
        ("验收交付", "证据 / 监控 / 恢复与回滚"),
    ]
    for i, (title, subtitle) in enumerate(steps):
        x = 64 + i * 262
        c.rect(x, 157, 240, 112, "#FFFFFF", "#D7E1EE")
        c.text(x + 18, 171, f"0{i + 1}", 18, "#4C79B3", bold=True)
        c.text(x + 18, 200, title, 27, NAVY, bold=True)
        c.text(x + 18, 241, subtitle, 15, MUTED, max_width=210)
        if i < 5:
            c.text(x + 244, 201, "›", 24, "#7391B3")

    c.text(64, 304, "五层能力：每一层，都要留下可检查的结果", 26, NAVY, bold=True)
    c.text(84, 356, "能力层", 18, MUTED, bold=True)
    c.text(332, 356, "关键知识与判断", 18, MUTED, bold=True)
    c.text(1146, 356, "应留下的证据", 18, MUTED, bold=True)

    rows = [
        ("硬件与兼容", "#E8F0FC", "#2462AB",
         "模型、算子和精度，能否在目标设备运行？",
         "设备 → 驱动 / Runtime → 框架后端 → 架构 / kernel",
         "支持列表只是入口；按固定版本逐项验证",
         "环境版本清单", "设备识别 · 依赖核对", "最小请求与结果核验"),
        ("模型与显存", "#E7F5F0", "#187A66",
         "权重能放下，请求运行时还有余量吗？",
         "格式 ≠ 精度 ≠ 量化方法；质量与速度分别验证",
         "预算 = 权重 + KV + 中间工作区 + 运行开销",
         "模型哈希与容量预算", "实测峰值 · 质量对照样例", "架构差异与量化边界"),
        ("推理与调度", "#F0EBFC", "#7050A8",
         "请求怎样排队、计算并持续输出？",
         "Prefill / Decode · 持续批处理 · 缓存 · 并行",
         "选型依据：模型 + 设备 + 负载 + 运维约束",
         "服务配置与接口结果", "启动参数 · 正常 / 异常响应", "模板、流式输出与工具支持"),
        ("测量与优化", "#FFF1E3", "#A86117",
         "慢在哪里，改动是否改善了目标？",
         "TTFT · TPOT / ITL · 吞吐 · 尾延迟 · 成功率",
         "固定负载、预热与缓存条件；比较达标吞吐",
         "基线与逐请求证据", "重复对照 · 资源采样", "失败边界与测量口径"),
        ("工程交付", "#FBE9EC", "#AC455E",
         "重启、监控、升级和回滚能否操作？",
         "接口约定 · 鉴权限流 · 监控告警 · 发布回滚",
         "先验证功能，再验证质量、性能与恢复能力",
         "可复现交付包", "代码 / 输入 / 日志 / 报告", "部署手册与验收边界"),
    ]
    for i, (name, tint, accent, question, detail, check, proof, p1, p2) in enumerate(rows):
        y = 392 + i * 148
        c.rect(64, y, 1552, 132, "#FFFFFF", "#DCE5F0")
        c.rect(64, y, 236, 132, tint)
        c.text(84, y + 20, f"0{i + 1}", 18, accent, bold=True)
        c.text(84, y + 58, name, 28, accent, bold=True, max_width=200)
        c.text(332, y + 17, question, 25, NAVY, bold=True, max_width=756)
        c.text(332, y + 59, detail, 21, INK, max_width=756)
        c.text(332, y + 95, check, 20, MUTED, max_width=756)
        c.line(1114, y + 22, 1114, y + 110, "#E0E7F0")
        c.text(1146, y + 19, proof, 25, accent, bold=True, max_width=440)
        c.text(1146, y + 61, p1, 21, INK, max_width=440)
        c.text(1146, y + 96, p2, 20, MUTED, max_width=440)

    c.rect(64, 1152, 1552, 116, NAVY)
    c.text(90, 1174, "优化闭环", 25, "#FFFFFF", bold=True)
    c.text(250, 1177, "固定负载 → 保存基线 → 提出假设 → 对照实验 → 重复验证 → 记录边界",
           25, "#FFFFFF", max_width=1330)
    c.text(90, 1222, "先证明现象，再解释原因；同时检查质量、延迟、吞吐与资源成本。",
           23, "#D6E4F5")
    c.text(64, 1304, "2026-10-17  ·  工程基础概念图；具体后端与参数支持以固定版本文档及实测为准。",
           19, MUTED)
    c.save(output)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--font", help="Path to a Chinese TTF/OTF/TTC font")
    parser.add_argument("--font-bold", help="Optional bold font path")
    parser.add_argument(
        "--output", type=Path,
        default=Path(__file__).resolve().parents[1]
        / "docs/01-deployment-foundations/assets",
    )
    args = parser.parse_args()
    regular = find_font(args.font)
    bold = find_font(args.font_bold, bold=True) if args.font_bold else regular
    render(regular, bold, args.output)
    print(f"Generated SVG and PNG in {args.output}")


if __name__ == "__main__":
    main()
