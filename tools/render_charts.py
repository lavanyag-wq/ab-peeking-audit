"""Render the headline charts to committed SVGs, from the experiment JSON.

Data-bound like the prose: the charts read docs/experiments/*.json at render
time, and CI regenerates them and fails on any diff. Explicit dimensions,
painted background, every axis labelled, and the invalid procedure drawn so
it cannot be mistaken for a result.
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EXP = ROOT / "docs" / "experiments"
OUT = ROOT / "docs"

INK = "#1d2733"
TEAL = "#2b6777"
WARM = "#9a3b3b"
GOLD = "#b8860b"
BG = "#fcfdfe"
FONT = 'font-family="Helvetica, Arial, sans-serif"'


def text(x, y, s, size=12, anchor="middle", fill=INK, weight="normal"):
    return (f'<text x="{x}" y="{y}" {FONT} font-size="{size}" text-anchor="{anchor}" '
            f'font-weight="{weight}" fill="{fill}">{s}</text>')


def frame(w, h, title):
    return [f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" '
            f'viewBox="0 0 {w} {h}">',
            f'<rect width="{w}" height="{h}" fill="{BG}"/>',
            text(w / 2, 26, title, size=15, weight="bold")]


def chart_inflation() -> None:
    data = json.loads((EXP / "inflation.json").read_text())
    rows = data["rows"]
    w, h = 820, 340
    left, top, bottom = 80, 56, 64
    px, py = w - left - 40, h - top - bottom
    ymax = max(r["ci_high_pct"] for r in rows) * 1.15

    def sy(v):
        return top + py * (1 - v / ymax)

    svg = frame(w, h, "What each peeking cadence actually runs (nominal alpha 5%)")
    for v in range(0, int(ymax) + 1, 5):
        svg.append(f'<line x1="{left}" y1="{sy(v)}" x2="{w - 40}" y2="{sy(v)}" '
                   f'stroke="#dde5ec"/>')
        svg.append(text(left - 8, sy(v) + 4, f"{v}%", size=11, anchor="end"))
    svg.append(f'<line x1="{left}" y1="{sy(5)}" x2="{w - 40}" y2="{sy(5)}" '
               f'stroke="{GOLD}" stroke-width="2" stroke-dasharray="7 5"/>')
    svg.append(text(w - 44, sy(5) - 7, "nominal alpha 5%", anchor="end",
                    fill=GOLD, size=12))
    bw = px / len(rows) * 0.4
    for i, r in enumerate(rows):
        cx = left + px * (i + 0.5) / len(rows)
        color = TEAL if r["verdict"] == "CONSISTENT" else WARM
        y = sy(r["fpr_pct"])
        svg.append(f'<rect x="{cx - bw / 2}" y="{y}" width="{bw}" '
                   f'height="{h - bottom - y}" fill="{color}"/>')
        ylo, yhi = sy(r["ci_low_pct"]), sy(r["ci_high_pct"])
        svg.append(f'<line x1="{cx}" y1="{ylo}" x2="{cx}" y2="{yhi}" '
                   f'stroke="{INK}" stroke-width="1.6"/>')
        for yy in (ylo, yhi):
            svg.append(f'<line x1="{cx - 7}" y1="{yy}" x2="{cx + 7}" y2="{yy}" '
                       f'stroke="{INK}" stroke-width="1.6"/>')
        svg.append(text(cx, yhi - 8, f"{r['fpr_pct']}%", weight="bold"))
        svg.append(text(cx, h - bottom + 16, f"{r['policy']} ({r['peeks']} peeks)",
                        size=12))
        svg.append(text(cx, h - bottom + 32, r["verdict"], size=11,
                        fill=TEAL if r["verdict"] == "CONSISTENT" else WARM))
    svg.append(text(left + px / 2, h - 8,
                    f"measured false positive rate with exact 95% intervals, "
                    f"{data['trials']} seeded null experiments per policy", size=12))
    svg.append("</svg>")
    (OUT / "chart-inflation.svg").write_text("\n".join(svg))


def chart_power() -> None:
    data = json.loads((EXP / "correction_cost.json").read_text())
    daily_fpr = json.loads((EXP / "inflation.json").read_text())["rows"][2]["fpr_pct"]
    rows = data["rows"]
    w, h = 820, 330
    left, top, bottom = 80, 56, 76
    px, py = w - left - 40, h - top - bottom
    ymax = 100.0

    def sy(v):
        return top + py * (1 - v / ymax)

    svg = frame(w, h, "Power at the same horizon, and which number is real")
    for v in range(0, 101, 20):
        svg.append(f'<line x1="{left}" y1="{sy(v)}" x2="{w - 40}" y2="{sy(v)}" '
                   f'stroke="#dde5ec"/>')
        svg.append(text(left - 8, sy(v) + 4, f"{v}%", size=11, anchor="end"))
    svg.append('<defs><pattern id="hatch" width="7" height="7" '
               'patternTransform="rotate(45)" patternUnits="userSpaceOnUse">'
               f'<rect width="7" height="7" fill="{BG}"/>'
               f'<line x1="0" y1="0" x2="0" y2="7" stroke="{WARM}" '
               'stroke-width="2.5"/></pattern></defs>')
    bw = px / len(rows) * 0.42
    for i, r in enumerate(rows):
        cx = left + px * (i + 0.5) / len(rows)
        y = sy(r["power_pct"])
        fill = TEAL if r["valid"] else "url(#hatch)"
        svg.append(f'<rect x="{cx - bw / 2}" y="{y}" width="{bw}" '
                   f'height="{h - bottom - y}" fill="{fill}" stroke="{WARM}" '
                   f'stroke-width="{0 if r["valid"] else 1.5}"/>')
        svg.append(text(cx, y - 8, f"{r['power_pct']}%", weight="bold",
                        fill=INK if r["valid"] else WARM))
        for j, part in enumerate(r["procedure"].split(" ")):
            svg.append(text(cx, h - bottom + 16 + 13 * j, part, size=11))
        if not r["valid"]:
            svg.append(text(cx, y - 24, f"invalid: bought with the {daily_fpr}% FPR",
                            size=11, fill=WARM))
    cost = data["power_cost_points"]
    svg.append(text(left + px / 2, h - 8,
                    f"effect 0.05 vs {data['effect']['p_b']}; honest daily peeking "
                    f"costs {cost} points against one pre-registered look; corrected "
                    f"boundary z* {data['z_star']}", size=12))
    svg.append("</svg>")
    (OUT / "chart-power.svg").write_text("\n".join(svg))


def main() -> None:
    chart_inflation()
    chart_power()
    print(f"wrote {OUT / 'chart-inflation.svg'} and {OUT / 'chart-power.svg'}")


if __name__ == "__main__":
    main()
