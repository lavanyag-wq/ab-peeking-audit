"""Render the architecture diagram to a committed SVG, deterministically.

Generated rather than drawn so a reviewer can regenerate it, committed with
explicit width and height so it renders identically as an img on GitHub and
offline, with a painted light background because a transparent one puts dark
labels on a near-black page in dark themes.
"""

from __future__ import annotations

from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "docs" / "diagram.svg"

W, H = 960, 380
BOX_FILL = "#eef2f7"
BOX_EDGE = "#4a5a6a"
TEXT = "#1d2733"
ACCENT = "#9a3b3b"


def box(x, y, w, h, lines, fill=BOX_FILL):
    parts = [
        f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="8" '
        f'fill="{fill}" stroke="{BOX_EDGE}" stroke-width="1.5"/>'
    ]
    line_h = 17
    start = y + h / 2 - line_h * (len(lines) - 1) / 2 + 5
    for i, line in enumerate(lines):
        weight = "bold" if i == 0 else "normal"
        parts.append(
            f'<text x="{x + w / 2}" y="{start + i * line_h}" text-anchor="middle" '
            f'font-family="Helvetica, Arial, sans-serif" font-size="12.5" '
            f'font-weight="{weight}" fill="{TEXT}">{line}</text>'
        )
    return "".join(parts)


def arrow(x1, y1, x2, y2, label=""):
    parts = [
        f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{BOX_EDGE}" '
        f'stroke-width="1.5" marker-end="url(#arrow)"/>'
    ]
    if label:
        parts.append(
            f'<text x="{(x1 + x2) / 2}" y="{(y1 + y2) / 2 - 6}" text-anchor="middle" '
            f'font-family="Helvetica, Arial, sans-serif" font-size="11" '
            f'fill="{TEXT}">{label}</text>'
        )
    return "".join(parts)


def main() -> None:
    svg = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" '
        f'viewBox="0 0 {W} {H}">',
        '<defs><marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" '
        'markerWidth="7" markerHeight="7" orient="auto-start-reverse">'
        f'<path d="M 0 0 L 10 5 L 0 10 z" fill="{BOX_EDGE}"/></marker></defs>',
        f'<rect x="0" y="0" width="{W}" height="{H}" fill="#fcfdfe"/>',
        box(20, 140, 180, 100, ["counter-based PRNG", "SplitMix64, owned", "by the repo:",
                                "receipts outlive libs"]),
        box(260, 140, 180, 100, ["null experiment", "stream", "cumulative counts,",
                                 "|z| per (trial, day)"]),
        box(500, 40, 180, 80, ["procedure replay", "peek schedule +", "stopping rule"]),
        box(500, 160, 180, 80, ["boundary search", "bisect z* on seed A,", "score on seed B"]),
        box(500, 280, 180, 70, ["statsmodels", "reference z-test,", "pinned equal by test"]),
        box(740, 30, 200, 70, ["measured FPR", "+ exact interval:", "the number the report",
                               ], fill="#f7e9e9"),
        box(740, 130, 200, 64, ["honest boundary", "alpha restored on", "held-out nulls"]),
        box(740, 224, 200, 64, ["power price tag", "what the correction", "costs, measured"],
            fill="#f3eedd"),
        arrow(200, 190, 260, 190),
        arrow(440, 170, 500, 90),
        arrow(440, 190, 500, 195),
        arrow(440, 215, 500, 305, "same pooled z"),
        arrow(680, 75, 740, 62, "cannot carry"),
        arrow(680, 200, 740, 160),
        arrow(680, 215, 740, 250),
        f'<text x="20" y="25" font-family="Helvetica, Arial, sans-serif" font-size="14" '
        f'font-weight="bold" fill="{ACCENT}">ab-peeking-audit: replaying the decisions '
        'a p-value forgot</text>',
        "</svg>",
    ]
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("\n".join(svg))
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
