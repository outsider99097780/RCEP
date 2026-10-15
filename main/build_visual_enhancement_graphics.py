"""Build source-backed figures that improve the report's visual argument.

The script reads the existing ITC model outputs and Wind JSON export without
modifying them.  Every plotted value is also written to a small CSV, and the
manifest records source hashes and output hashes.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from datetime import datetime, timezone
from pathlib import Path

import pypdfium2 as pdfium
from reportlab.lib.colors import Color, HexColor, white
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas


parser = argparse.ArgumentParser()
parser.add_argument("--project-root", type=Path, required=True)
parser.add_argument("--output", type=Path, required=True)
args = parser.parse_args()

ROOT = args.project_root
OUT = args.output
OUT.mkdir(parents=True, exist_ok=True)
ITC = ROOT / "data" / "macro-market" / "ITC" / "itc-analysis-result"
WIND = ROOT / "data" / "roborock-company" / "wind-financial-data" / "石头科技[688169.SH]-财务摘要--sheet1.json"

FONT = r"C:\Windows\Fonts\simhei.ttf"
pdfmetrics.registerFont(TTFont("CJK", FONT))

INK = "#25313B"
MUTED = "#65717B"
GRID = "#DDE4E8"
TEAL = "#2C7F78"
TEAL_DARK = "#175D59"
TEAL_LIGHT = "#D9ECE8"
BLUE = "#386D8E"
ORANGE = "#D0873E"
ORANGE_LIGHT = "#F5E3CD"
RED = "#B85C55"
GRAY = "#E9EDEF"

COUNTRY_ZH = {
    "Korea, Republic of": "韩国",
    "Australia": "澳大利亚",
    "Malaysia": "马来西亚",
    "New Zealand": "新西兰",
    "Japan": "日本",
}
ORDER = ["Korea, Republic of", "Australia", "Malaysia", "New Zealand", "Japan"]


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def write_csv(path: Path, rows: list[dict]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def ctext(c: canvas.Canvas, x: float, y: float, value, size=10, color=INK, align="left") -> None:
    c.setFillColor(HexColor(color))
    c.setFont("CJK", size)
    value = str(value)
    if align == "center":
        c.drawCentredString(x, y, value)
    elif align == "right":
        c.drawRightString(x, y, value)
    else:
        c.drawString(x, y, value)


def wrap_text(text: str, max_chars: int) -> list[str]:
    parts = []
    for segment in text.split("/"):
        segment = segment.strip()
        if not segment:
            continue
        while len(segment) > max_chars:
            parts.append(segment[:max_chars])
            segment = segment[max_chars:]
        parts.append(segment)
    return parts or [""]


def interpolate(low: str, high: str, t: float) -> Color:
    a, b = HexColor(low), HexColor(high)
    t = min(1.0, max(0.0, t))
    return Color(a.red + (b.red - a.red) * t,
                 a.green + (b.green - a.green) * t,
                 a.blue + (b.blue - a.blue) * t)


def save_png(stem: str, scale: float = 2.5) -> None:
    doc = pdfium.PdfDocument(OUT / f"{stem}.pdf")
    doc[0].render(scale=scale).to_pil().save(OUT / f"{stem}.png")


model_inputs_path = ITC / "model_inputs.csv"
model_norm_path = ITC / "model_normalized.csv"
model_scores_path = ITC / "strategy_topsis_scores.csv"

inputs_all = {r["country_name"]: r for r in read_csv(model_inputs_path)}
norm_all = {r["country_name"]: r for r in read_csv(model_norm_path)}
scores_all = {r["country_name"]: r for r in read_csv(model_scores_path)}

market_rows = []
for country in ORDER:
    raw = inputs_all[country]
    norm = norm_all[country]
    market_rows.append({
        "country_name": country,
        "country_zh": COUNTRY_ZH[country],
        "imports_2025_usd_million": float(raw["imports_2025_usd_thousand"]) / 1000,
        "import_cagr_2020_2025_pct": float(raw["import_cagr_2020_2025_pct"]),
        "china_share_2025_pct": float(raw["china_share_2025_pct"]),
        "untapped_potential_usd_million": float(raw["untapped_potential_usd"]) / 1_000_000,
        "untapped_ratio_pct": 100 * float(raw["untapped_potential_usd"]) / float(raw["epi_potential_usd"]),
        "norm_market_size": float(norm["market_size"]),
        "norm_market_growth": float(norm["market_growth"]),
        "norm_china_share": float(norm["china_share"]),
        "norm_untapped_amount": float(norm["untapped_amount"]),
        "norm_untapped_ratio": float(norm["untapped_ratio"]),
        "topsis_score": float(scores_all[country]["score"]),
    })

write_csv(OUT / "five_market_visual_data.csv", market_rows)


def build_heatmap() -> None:
    W, H = 680, 354
    c = canvas.Canvas(str(OUT / "market_attractiveness_heatmap.pdf"), pagesize=(W, H))
    x0, y0, cw, ch = 124, 54, 101, 50
    columns = [
        ("市场规模", "30%", "norm_market_size", "imports_2025_usd_million", lambda v: f"{v:.2f}百万美元"),
        ("市场增长", "10%", "norm_market_growth", "import_cagr_2020_2025_pct", lambda v: f"{v:.2f}%"),
        ("中国份额", "10%", "norm_china_share", "china_share_2025_pct", lambda v: f"{v:.2f}%"),
        ("未实现额", "30%", "norm_untapped_amount", "untapped_potential_usd_million", lambda v: f"{v:.2f}百万美元"),
        ("潜力占比", "20%", "norm_untapped_ratio", "untapped_ratio_pct", lambda v: f"{v:.2f}%"),
    ]
    for j, (label, weight, *_rest) in enumerate(columns):
        ctext(c, x0 + j * cw + cw / 2, 326, label, 11, INK, "center")
        ctext(c, x0 + j * cw + cw / 2, 309, f"权重{weight}", 8.5, MUTED, "center")
    for i, row in enumerate(market_rows):
        y = y0 + (len(market_rows) - 1 - i) * ch
        ctext(c, x0 - 14, y + 20, row["country_zh"], 11, INK, "right")
        ctext(c, x0 - 14, y + 7, f"TOPSIS {row['topsis_score']:.3f}", 7.5, MUTED, "right")
        for j, (_label, _weight, norm_key, raw_key, formatter) in enumerate(columns):
            value = row[norm_key]
            color = interpolate("#F7EBD9", TEAL_DARK, value)
            c.setFillColor(color)
            c.roundRect(x0 + j * cw + 2, y + 2, cw - 4, ch - 4, 4, stroke=0, fill=1)
            fg = "#FFFFFF" if value >= 0.69 else INK
            ctext(c, x0 + j * cw + cw / 2, y + 27, f"{value:.3f}", 11, fg, "center")
            ctext(c, x0 + j * cw + cw / 2, y + 10, formatter(row[raw_key]), 7.3, fg, "center")
    ctext(c, x0, 24, "颜色与上行数值为全体可评分RCEP候选市场归一化结果；下行保留原始值", 8.5, MUTED)
    c.setFillColor(interpolate("#F7EBD9", TEAL_DARK, 0))
    c.rect(540, 18, 18, 9, stroke=0, fill=1)
    c.setFillColor(interpolate("#F7EBD9", TEAL_DARK, 1))
    c.rect(612, 18, 18, 9, stroke=0, fill=1)
    ctext(c, 563, 18, "低", 8, MUTED)
    ctext(c, 635, 18, "高", 8, MUTED)
    c.save()
    save_png("market_attractiveness_heatmap")


def build_bubble() -> None:
    W, H = 640, 385
    c = canvas.Canvas(str(OUT / "market_opportunity_bubble.pdf"), pagesize=(W, H))
    x0, y0, w, h = 78, 62, 500, 268
    xmin, xmax = math.log10(45), math.log10(900)
    ymin, ymax = 15, 50
    def sx(v): return x0 + w * (math.log10(v) - xmin) / (xmax - xmin)
    def sy(v): return y0 + h * (v - ymin) / (ymax - ymin)

    for tick in [50, 100, 200, 400, 800]:
        x = sx(tick)
        c.setStrokeColor(HexColor(GRID)); c.setLineWidth(0.5); c.line(x, y0, x, y0 + h)
        ctext(c, x, y0 - 20, str(tick), 9, MUTED, "center")
    for tick in [20, 30, 40, 50]:
        y = sy(tick)
        c.setStrokeColor(HexColor(GRID)); c.line(x0, y, x0 + w, y)
        ctext(c, x0 - 12, y - 3, f"{tick}%", 9, MUTED, "right")
    c.setStrokeColor(HexColor("#84919A")); c.setLineWidth(0.8)
    c.line(x0, y0, x0 + w, y0); c.line(x0, y0, x0, y0 + h)
    ctext(c, x0 + w / 2, 24, "2025年进口规模（百万美元，对数轴）", 10, INK, "center")
    c.saveState(); c.translate(22, y0 + h / 2); c.rotate(90)
    ctext(c, 0, 0, "未实现潜力占比", 10, INK, "center")
    c.restoreState()

    offsets = {
        "韩国": (-46, 23), "澳大利亚": (15, -28), "马来西亚": (17, -25),
        "新西兰": (15, 18), "日本": (-45, -31),
    }
    max_gap = max(r["untapped_potential_usd_million"] for r in market_rows)
    for row in market_rows:
        x, y = sx(row["imports_2025_usd_million"]), sy(row["untapped_ratio_pct"])
        radius = 7 + 20 * math.sqrt(row["untapped_potential_usd_million"] / max_gap)
        c.setFillColor(Color(0.17, 0.50, 0.47, alpha=0.74))
        c.setStrokeColor(HexColor("#FFFFFF")); c.setLineWidth(1.2)
        c.circle(x, y, radius, stroke=1, fill=1)
        dx, dy = offsets[row["country_zh"]]
        ctext(c, x + dx, y + dy, row["country_zh"], 10, INK)
        ctext(c, x + dx, y + dy - 13, f"未实现额 {row['untapped_potential_usd_million']:.1f}百万美元", 7.8, MUTED)
    ctext(c, 420, 349, "气泡面积＝未实现潜力金额", 8.5, MUTED)
    c.save()
    save_png("market_opportunity_bubble")


def build_supply_growth() -> None:
    W, H = 660, 332
    c = canvas.Canvas(str(OUT / "supply_growth_comparison.pdf"), pagesize=(W, H))
    y_positions = [258, 212, 166, 120, 74]
    left_x, left_w = 95, 205
    right_zero, right_w = 474, 144
    right_min, right_max = -8, 18
    ctext(c, 196, 306, "中国供应份额（2025年）", 12, INK, "center")
    ctext(c, 495, 306, "目标市场进口CAGR（2020—2025年）", 12, INK, "center")

    for tick in [0, 25, 50, 75, 100]:
        x = left_x + left_w * tick / 100
        c.setStrokeColor(HexColor(GRID)); c.setLineWidth(0.5); c.line(x, 47, x, 280)
        ctext(c, x, 31, f"{tick}%", 8.5, MUTED, "center")
    for tick in [-5, 0, 5, 10, 15]:
        x = right_zero + right_w * tick / (right_max - right_min)
        c.setStrokeColor(HexColor("#AAB4BA") if tick == 0 else HexColor(GRID))
        c.setLineWidth(0.9 if tick == 0 else 0.5); c.line(x, 47, x, 280)
        ctext(c, x, 31, f"{tick}%", 8.5, MUTED, "center")

    for row, y in zip(market_rows, y_positions):
        ctext(c, 76, y - 4, row["country_zh"], 10.5, INK, "right")
        share = row["china_share_2025_pct"]
        c.setFillColor(HexColor(TEAL)); c.roundRect(left_x, y - 9, left_w * share / 100, 19, 3, stroke=0, fill=1)
        ctext(c, left_x + left_w * share / 100 + 5, y - 4, f"{share:.2f}%", 8.8, INK)
        growth = row["import_cagr_2020_2025_pct"]
        zero_x = right_zero + right_w * (0 - right_min) / (right_max - right_min)
        end_x = right_zero + right_w * (growth - right_min) / (right_max - right_min)
        c.setFillColor(HexColor(ORANGE if growth >= 0 else RED))
        c.roundRect(min(zero_x, end_x), y - 9, abs(end_x - zero_x), 19, 3, stroke=0, fill=1)
        ctext(c, end_x + (5 if growth >= 0 else -5), y - 4, f"{growth:+.2f}%", 8.8, INK,
              "left" if growth >= 0 else "right")
    c.save()
    save_png("supply_growth_comparison")


def get_wind_value_rows() -> tuple[list[dict], dict]:
    raw = json.loads(WIND.read_text(encoding="utf-8-sig"))
    values = raw["values"]
    headers = values[0][1:4]
    labels = {
        "revenue": "营业总收入",
        "parent_net_profit": "归属母公司股东的净利润",
        "gross_margin": "销售毛利率(%)",
        "net_margin": "销售净利率(%)",
    }
    found = {}
    for key, label in labels.items():
        found[key] = next((row for row in values if row and str(row[0]).strip() == label), None)
        if found[key] is None:
            raise ValueError(f"Wind row not found: {label}")
    rows = []
    for i, header in enumerate(headers, start=1):
        rows.append({
            "year": str(header)[:4],
            "revenue_cny_100m": float(found["revenue"][i]) / 10000,
            "parent_net_profit_cny_100m": float(found["parent_net_profit"][i]) / 10000,
            "gross_margin_pct": float(found["gross_margin"][i]),
            "net_margin_pct": float(found["net_margin"][i]),
        })
    rows.sort(key=lambda x: x["year"])
    return rows, raw


financial_rows, _wind_raw = get_wind_value_rows()
write_csv(OUT / "company_scale_profitability_data.csv", financial_rows)


def build_financial() -> None:
    W, H = 650, 348
    c = canvas.Canvas(str(OUT / "company_financial_trend.pdf"), pagesize=(W, H))
    x0, y0, w, h = 72, 61, 492, 235
    right_x = x0 + w
    for tick in [0, 50, 100, 150, 200]:
        y = y0 + h * tick / 200
        c.setStrokeColor(HexColor(GRID)); c.setLineWidth(0.5); c.line(x0, y, right_x, y)
        ctext(c, x0 - 10, y - 3, tick, 8.5, MUTED, "right")
    for tick in [0, 15, 30, 45, 60]:
        y = y0 + h * tick / 60
        ctext(c, right_x + 10, y - 3, f"{tick}%", 8.5, MUTED)
    ctext(c, 15, 305, "亿元", 8.5, MUTED)
    ctext(c, 595, 305, "利润率", 8.5, MUTED)

    centers = [155, 318, 481]
    for row, x in zip(financial_rows, centers):
        rev, profit = row["revenue_cny_100m"], row["parent_net_profit_cny_100m"]
        c.setFillColor(HexColor(BLUE)); c.roundRect(x - 43, y0, 34, h * rev / 200, 3, stroke=0, fill=1)
        c.setFillColor(HexColor(ORANGE)); c.roundRect(x + 9, y0, 34, h * profit / 200, 3, stroke=0, fill=1)
        ctext(c, x - 26, y0 + h * rev / 200 + 7, f"{rev:.2f}", 8, INK, "center")
        ctext(c, x + 26, y0 + h * profit / 200 + 7, f"{profit:.2f}", 8, INK, "center")
        ctext(c, x, 39, row["year"], 10, INK, "center")
    for key, color, marker in [("gross_margin_pct", TEAL_DARK, 5.5), ("net_margin_pct", RED, 4.8)]:
        points = [(x, y0 + h * row[key] / 60) for row, x in zip(financial_rows, centers)]
        c.setStrokeColor(HexColor(color)); c.setLineWidth(2)
        for (x1, y1), (x2, y2) in zip(points, points[1:]): c.line(x1, y1, x2, y2)
        for (x, y), row in zip(points, financial_rows):
            c.setFillColor(HexColor(color)); c.circle(x, y, marker, stroke=0, fill=1)
            ctext(c, x, y + 10, f"{row[key]:.2f}%", 8.5, color, "center")
    legend = [(BLUE, "营业收入"), (ORANGE, "归母净利润"), (TEAL_DARK, "销售毛利率"), (RED, "销售净利率")]
    lx = 95
    for color, label in legend:
        c.setFillColor(HexColor(color)); c.roundRect(lx, 318, 11, 8, 2, stroke=0, fill=1)
        ctext(c, lx + 16, 317, label, 8.5, INK)
        lx += 118
    c.save()
    save_png("company_financial_trend")


coverage_rows = [
    {"brand": "Roborock", "Japan": 20, "Korea": 20, "Australia": 7, "Malaysia": 12, "New Zealand": 9},
    {"brand": "Ecovacs", "Japan": 16, "Korea": 16, "Australia": 8, "Malaysia": 13, "New Zealand": 8},
    {"brand": "Xiaomi", "Japan": 6, "Korea": 9, "Australia": None, "Malaysia": 13, "New Zealand": 6},
    {"brand": "Dreame", "Japan": 13, "Korea": 19, "Australia": 4, "Malaysia": 6, "New Zealand": 12},
    {"brand": "Narwal", "Japan": 8, "Korea": 10, "Australia": None, "Malaysia": None, "New Zealand": 2},
]
write_csv(OUT / "brand_sample_coverage_data.csv", coverage_rows)


def build_coverage() -> None:
    W, H = 640, 342
    c = canvas.Canvas(str(OUT / "brand_sample_coverage_heatmap.pdf"), pagesize=(W, H))
    x0, y0, cw, ch = 128, 48, 91, 49
    columns = [("Japan", "日本"), ("Korea", "韩国"), ("Australia", "澳大利亚"), ("Malaysia", "马来西亚"), ("New Zealand", "新西兰")]
    sources = ["Kakaku", "Danawa", "GetPrice", "PriceShop", "PriceSpy"]
    for j, ((_key, label), source) in enumerate(zip(columns, sources)):
        ctext(c, x0 + j*cw + cw/2, 318, label, 11, INK, "center")
        ctext(c, x0 + j*cw + cw/2, 302, source, 8, MUTED, "center")
    max_n = 20
    for i, row in enumerate(coverage_rows):
        y = y0 + (len(coverage_rows)-1-i)*ch
        ctext(c, x0-14, y+17, row["brand"], 10.5, INK, "right")
        for j, (key, _label) in enumerate(columns):
            val = row[key]
            if val is None:
                color, label, fg = HexColor(GRAY), "—", MUTED
            else:
                color, label = interpolate("#F5E5CF", TEAL_DARK, val/max_n), str(val)
                fg = "#FFFFFF" if val >= 13 else INK
            c.setFillColor(color); c.roundRect(x0+j*cw+2, y+2, cw-4, ch-4, 4, stroke=0, fill=1)
            ctext(c, x0+j*cw+cw/2, y+15, label, 12, fg, "center")
    ctext(c, x0, 20, "数值为已采得的扫地机产品页数量；“—”表示未取得可读产品页", 8.5, MUTED)
    c.save()
    save_png("brand_sample_coverage_heatmap")


strategy_rows = [
    ("韩国", "增长承接", "大规模、正增长、潜力额最高", "深化代理服务", "职责／回款／售后"),
    ("澳大利亚", "常态经营", "规模与增速兼具、促销弹性较强", "旺季销量转常态销售", "单台贡献／履约"),
    ("马来西亚", "品牌覆盖", "增速快、中国供应份额高", "价格分层／体验／区域供应", "增长向品牌覆盖转化"),
    ("新西兰", "轻量验证", "相对潜力高、绝对容量有限", "少量核心型号连接零售商", "备货／维修负担"),
    ("日本", "存量升级", "需求池最大、进口规模收缩", "替代升级／多层级产品", "功能价差／常态销售"),
]
write_csv(OUT / "country_strategy_overview_data.csv", [
    {"country": a, "task": b, "opportunity_basis": c, "development_direction": d, "operating_gate": e}
    for a, b, c, d, e in strategy_rows
])


def build_strategy() -> None:
    W, H = 690, 365
    c = canvas.Canvas(str(OUT / "country_strategy_overview.pdf"), pagesize=(W, H))
    x_country, x_task, x_basis, x_direction, x_gate = 20, 92, 178, 382, 555
    widths = [64, 78, 196, 165, 116]
    headers = [(x_country, widths[0], "市场"), (x_task, widths[1], "研究任务"),
               (x_basis, widths[2], "机会依据"), (x_direction, widths[3], "开拓方向"),
               (x_gate, widths[4], "经营门槛")]
    for x, width, label in headers:
        c.setFillColor(HexColor("#E8EEF1")); c.roundRect(x, 321, width, 29, 4, stroke=0, fill=1)
        ctext(c, x+width/2, 330, label, 10, INK, "center")
    row_colors = ["#DCEDEA", "#E4EDF3", "#F5E5CF", "#E9EDF0", "#E7E2F0"]
    for i, (country, task, basis, direction, gate) in enumerate(strategy_rows):
        y = 258 - i*57
        for x, width in zip([x_country,x_task,x_basis,x_direction,x_gate], widths):
            c.setFillColor(HexColor(row_colors[i])); c.roundRect(x, y, width, 47, 5, stroke=0, fill=1)
        ctext(c, x_country+widths[0]/2, y+18, country, 11, INK, "center")
        ctext(c, x_task+widths[1]/2, y+18, task, 10.5, TEAL_DARK, "center")
        for x, width, value, max_chars in [(x_basis,widths[2],basis,14),(x_direction,widths[3],direction,11),(x_gate,widths[4],gate,8)]:
            lines = wrap_text(value, max_chars)
            start = y + 27 + 7*(len(lines)-1)
            for k, line in enumerate(lines):
                ctext(c, x+width/2, start-k*14, line, 9.3, INK, "center")
        if i < len(strategy_rows)-1:
            c.setStrokeColor(HexColor("#FFFFFF")); c.setLineWidth(1); c.line(20, y-5, 671, y-5)
    c.save()
    save_png("country_strategy_overview")


build_heatmap()
build_bubble()
build_supply_growth()
build_financial()
build_coverage()
build_strategy()

sources = [model_inputs_path, model_norm_path, model_scores_path, WIND]
outputs = sorted(p for p in OUT.iterdir() if p.is_file())
manifest = {
    "generated_at_utc": datetime.now(timezone.utc).isoformat(),
    "method": {
        "heatmap": "Uses the report model's normalization across all scoreable RCEP candidates; raw labels are retained.",
        "bubble": "Raw 2025 import scale on a log x-axis, official EPI untapped ratio on y-axis, bubble area proportional to untapped USD.",
        "supply_growth": "Direct comparison of 2025 China supplier share and 2020-2025 import CAGR.",
        "financial": "Wind consolidated summary; CNY 10,000 values divided by 10,000 to CNY 100 million; margins plotted as reported.",
        "coverage": "Counts transcribed from the report's source-backed retail sample table; missing means no readable product page captured.",
        "strategy": "Qualitative synthesis of the existing report sections 4-6; no new external fact or metric.",
    },
    "sources": [{"file": str(p.relative_to(ROOT)), "sha256": sha256(p)} for p in sources],
    "outputs": [{"file": p.name, "sha256": sha256(p)} for p in outputs],
}
(OUT / "visual_enhancement_provenance.json").write_text(
    json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
)

print(json.dumps({"output_dir": str(OUT), "files": [p.name for p in outputs]}, ensure_ascii=False, indent=2))
