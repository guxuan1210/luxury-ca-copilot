"""Render the system architecture (Bonus question) as a clean PNG diagram.

Matches the Mermaid flow in reports/methodology.md B.3. Uses matplotlib so it
runs with no extra dependencies and shares the visual style of make_charts.py.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

from src import config

plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "SimSun", "Arial Unicode MS"]
plt.rcParams["axes.unicode_minus"] = False

# Palette: a muted luxury tone (matches the bar charts).
C_MAIN = "#6b8cae"      # main pipeline boxes
C_INPUT = "#8cae6b"     # context inputs
C_DECIDE = "#c9a227"    # decision diamond
C_OUTPUT = "#4a7a5c"    # final output
C_EVAL = "#9b7bb5"      # evaluation loop
C_EDGE = "#555555"

def box(ax, x, y, w, h, text, fc, fs=11, tc="white", bold=True):
    p = FancyBboxPatch(
        (x, y), w, h,
        boxstyle="round,pad=0.02,rounding_size=0.08",
        linewidth=1.0, edgecolor="#333333", facecolor=fc, zorder=3,
    )
    ax.add_patch(p)
    ax.text(x + w / 2, y + h / 2, text, ha="center", va="center",
            fontsize=fs, color=tc, zorder=4, fontweight="bold" if bold else "normal")


def diamond(ax, x, y, w, h, text, fc=C_DECIDE, fs=11):
    pts = [(x + w / 2, y + h), (x + w, y + h / 2), (x + w / 2, y), (x, y + h / 2)]
    from matplotlib.patches import Polygon
    ax.add_patch(Polygon(pts, closed=True, linewidth=1.0, edgecolor="#333333", facecolor=fc, zorder=3))
    ax.text(x + w / 2, y + h / 2, text, ha="center", va="center",
            fontsize=fs, color="white", zorder=4, fontweight="bold")


def arrow(ax, x1, y1, x2, y2, color=C_EDGE, style="-|>", ls="-", label=None, lx=0, ly=0):
    a = FancyArrowPatch((x1, y1), (x2, y2), arrowstyle=style, mutation_scale=14,
                        linewidth=1.3, color=color, linestyle=ls, zorder=2,
                        connectionstyle="arc3,rad=0.0")
    ax.add_patch(a)
    if label:
        ax.text(x1 + (x2 - x1) / 2 + lx, y1 + (y2 - y1) / 2 + ly, label,
                fontsize=9, color=color, ha="center", va="center", zorder=5,
                bbox=dict(fc="white", ec="none", pad=0.5))


def main() -> None:
    out_dir = config.REPORTS_DIR / "screenshots"
    out_dir.mkdir(parents=True, exist_ok=True)

    fig, ax = plt.subplots(figsize=(11, 9))
    ax.set_xlim(0, 11)
    ax.set_ylim(0, 9)
    ax.axis("off")

    BW, BH = 2.6, 0.7  # box width / height

    # --- Center main pipeline (x from 4.2 to 6.8) ---
    cx = 4.2
    cw = 2.6

    nodes = [
        ("用户输入 User Input", C_MAIN),
        ("输入校验 Input Validation", C_MAIN),
        ("场景路由 Scenario Router", C_MAIN),
        ("Prompt 组装 Prompt Builder", C_MAIN),
        ("LLM 生成 LLM Generation", C_MAIN),
        ("结构化输出解析\nOutput Parser", C_MAIN),
    ]
    y0 = 8.1
    gap = 1.35
    positions = {}
    for i, (label, col) in enumerate(nodes):
        y = y0 - i * gap
        positions[label] = (cx, y)
        box(ax, cx, y, cw, BH, label, col, fs=10.5)

    # Decision diamond
    dy = y0 - 6 * gap
    dw, dh = 2.6, 0.85
    diamond(ax, cx, dy - dh / 2, dw, dh, "校验通过?\nValidation", C_DECIDE, fs=10)

    # Final output + retry
    out_y = dy - dh / 2 - 1.7
    box(ax, cx - 3.6, out_y, 2.6, BH, "三条中文话术\nThree Messages", C_OUTPUT, fs=10.5)
    box(ax, cx + 1.0, out_y, 2.4, BH, "重试 / 错误处理\nRetry", "#c05a5a", fs=10.5)

    # Vertical main arrows
    prev_y = positions[nodes[0][0]]
    for i in range(1, len(nodes)):
        label = nodes[i][0]
        y = positions[label][1]
        arrow(ax, cx + cw / 2, y + BH, cx + cw / 2, y + BH + 0.65, color=C_EDGE)

    # LLM generation -> parser -> decision
    arrow(ax, cx + cw / 2, dy + dh / 2 + 0.5, cx + cw / 2, dy + dh / 2 + 0.15, color=C_EDGE)

    # Decision -> output (yes) and -> retry (no)
    arrow(ax, cx - 0.4, dy + dh / 2 - 0.1, cx - 2.3, out_y + BH + 0.1, color="#2e7d32", label="是 / Yes")
    arrow(ax, cx + cw + 0.4, dy + dh / 2 - 0.1, cx + cw + 1.0, out_y + BH + 0.1, color="#b71c1c", label="否 / No")

    # Retry loops back to LLM generation
    arrow(ax, cx + cw + 2.2, out_y + BH / 2, cx + cw + 2.2, positions[nodes[4][0]][1] + BH / 2,
          color="#b71c1c", ls="--")
    arrow(ax, cx + cw + 2.2, positions[nodes[4][0]][1] + BH / 2, cx + cw, positions[nodes[4][0]][1] + BH / 2,
          color="#b71c1c", ls="--")

    # --- Left context inputs -> Prompt Builder ---
    lx = 0.35
    lw = 2.6
    ctx = [
        ("品牌指南\nBrand Guidelines", 8.1),
        ("场景规则\nScenario Rules", 6.9),
        ("对话上下文\nConversation Context", 5.7),
    ]
    pb_x, pb_y = positions["Prompt 组装 Prompt Builder"]
    for label, yy in ctx:
        box(ax, lx, yy, lw, BH, label, C_INPUT, fs=10.5)
        arrow(ax, lx + lw, yy + BH / 2, cx, pb_y + BH / 2, color=C_EDGE)

    # --- Right evaluation loop ---
    rx = 8.6
    rw = 2.2
    ev_y = out_y + 0.0
    box(ax, rx, ev_y, rw, BH, "评估管线\nEvaluation", C_EVAL, fs=10.5)
    box(ax, rx, ev_y - 1.35, rw, BH, "指标与缺陷日志\nMetrics/Defects", C_EVAL, fs=10.5)
    box(ax, rx, ev_y - 2.7, rw, BH, "Prompt 迭代\nRevision", C_EVAL, fs=10.5)

    # output -> evaluation
    arrow(ax, cx - 3.6 + 2.6, out_y + BH / 2, rx, out_y + BH / 2, color="#7b5e9b")
    # evaluation chain down
    arrow(ax, rx + rw / 2, ev_y, rx + rw / 2, ev_y - 0.65, color="#7b5e9b")
    arrow(ax, rx + rw / 2, ev_y - 1.35, rx + rw / 2, ev_y - 2.0, color="#7b5e9b")
    # revision -> prompt builder (feedback)
    arrow(ax, rx + rw / 2, ev_y - 2.7, rx + rw / 2, 1.2, color="#7b5e9b", ls="--")
    arrow(ax, rx + rw / 2, 1.2, cx + cw, 1.2, color="#7b5e9b", ls="--")
    arrow(ax, cx + cw, 1.2, cx + cw, pb_y + 0.1, color="#7b5e9b", ls="--")

    # Streamlit UI output
    box(ax, 8.6, 8.1, 2.2, BH, "Streamlit UI", "#5a8cae", fs=10.5)
    arrow(ax, cx - 3.6 + 1.3, out_y + BH, 9.7, 8.1, color=C_EDGE, ls=":")

    ax.set_title("CHENGYU 客户顾问 AI Copilot — 系统架构", fontsize=14, pad=14, fontweight="bold")

    out = out_dir / "architecture.png"
    fig.savefig(out, dpi=130, bbox_inches="tight")
    plt.close(fig)
    print("Architecture diagram written to", out)


if __name__ == "__main__":
    main()
