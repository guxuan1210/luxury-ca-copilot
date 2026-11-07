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

    fig, ax = plt.subplots(figsize=(13.5, 12))
    ax.set_xlim(0, 13.5)
    ax.set_ylim(0, 12)
    ax.axis("off")

    BH = 0.7          # box height
    cx = 4.8          # main spine left x
    cw = 2.6          # main box width
    mid_x = cx + cw / 2  # 6.1

    # --- Center main pipeline (top to bottom; value = box bottom y) ---
    pos = {
        "用户输入 User Input": 10.6,
        "输入校验 Input Validation": 9.3,
        "场景路由 Scenario Router": 7.4,
        "Prompt 组装 Prompt Builder": 5.9,
        "LLM 生成 LLM Generation": 4.4,
        "结构化输出解析\nOutput Parser": 2.9,
    }
    for label, y in pos.items():
        box(ax, cx, y, cw, BH, label, C_MAIN, fs=10.5)

    # Do-not-contact decision (inline, between 输入校验 and 场景路由).
    dnc_cy = 8.7
    dnc_h = 0.8
    diamond(ax, cx, dnc_cy - dnc_h / 2, cw, dnc_h, "客户要求停联?\nDo-not-contact?", C_DECIDE, fs=9.5)
    # 停联确认 terminal (branch right on "是 / Yes").
    box(ax, 8.4, dnc_cy - BH / 2, 2.6, BH, "停联确认\nStop-contact Ack", C_OUTPUT, fs=10.5)

    # Validation decision (after 输出解析).
    val_cy = 1.9
    val_h = 0.8
    diamond(ax, cx, val_cy - val_h / 2, cw, val_h, "校验通过?\nValidation", C_DECIDE, fs=10)

    # Final output + retry (bottom row).
    out_y = 0.5
    box(ax, 0.6, out_y, 2.6, BH, "三条中文话术\nThree Messages", C_OUTPUT, fs=10.5)
    box(ax, 6.0, out_y, 2.4, BH, "重试 / 错误处理\nRetry", "#c05a5a", fs=10.5)

    # --- Main spine arrows (top-down) ---
    arrow(ax, mid_x, pos["用户输入 User Input"], mid_x, pos["输入校验 Input Validation"] + BH, color=C_EDGE)
    arrow(ax, mid_x, pos["输入校验 Input Validation"], mid_x, dnc_cy + dnc_h / 2, color=C_EDGE)
    arrow(ax, mid_x, dnc_cy - dnc_h / 2, mid_x, pos["场景路由 Scenario Router"] + BH, color=C_EDGE, label="否 / No", lx=0.6, ly=0.0)
    arrow(ax, cx + cw, dnc_cy, 8.4, dnc_cy, color="#2e7d32", label="是 / Yes", lx=0.25, ly=0.2)
    arrow(ax, mid_x, pos["场景路由 Scenario Router"], mid_x, pos["Prompt 组装 Prompt Builder"] + BH, color=C_EDGE)
    arrow(ax, mid_x, pos["Prompt 组装 Prompt Builder"], mid_x, pos["LLM 生成 LLM Generation"] + BH, color=C_EDGE)
    arrow(ax, mid_x, pos["LLM 生成 LLM Generation"], mid_x, pos["结构化输出解析\nOutput Parser"] + BH, color=C_EDGE)
    arrow(ax, mid_x, pos["结构化输出解析\nOutput Parser"], mid_x, val_cy + val_h / 2, color=C_EDGE)

    # Validation -> output (yes) / retry (no).
    arrow(ax, cx - 0.5, val_cy - val_h / 2 + 0.15, 1.9, out_y + BH, color="#2e7d32", label="是 / Yes", lx=0.0, ly=-0.2)
    arrow(ax, cx + cw + 0.4, val_cy - val_h / 2 + 0.15, 7.2, out_y + BH, color="#b71c1c", label="否 / No", lx=0.0, ly=-0.2)

    # Retry loops back to LLM generation.
    arrow(ax, 8.4, out_y + BH / 2, 9.6, out_y + BH / 2, color="#b71c1c", ls="--")
    arrow(ax, 9.6, out_y + BH / 2, 9.6, pos["LLM 生成 LLM Generation"] + BH / 2, color="#b71c1c", ls="--")
    arrow(ax, 9.6, pos["LLM 生成 LLM Generation"] + BH / 2, cx + cw, pos["LLM 生成 LLM Generation"] + BH / 2, color="#b71c1c", ls="--")

    # --- Left context inputs -> Prompt Builder ---
    lx, lw = 0.35, 2.6
    ctx = [
        ("品牌指南\nBrand Guidelines", 9.6),
        ("场景规则\nScenario Rules", 8.2),
        ("对话上下文\nConversation Context", 6.8),
    ]
    pb_y = pos["Prompt 组装 Prompt Builder"]
    for label, yy in ctx:
        box(ax, lx, yy, lw, BH, label, C_INPUT, fs=10.5)
        arrow(ax, lx + lw, yy + BH / 2, cx, pb_y + BH / 2, color=C_EDGE)

    # --- Right evaluation loop ---
    rx, rw = 10.4, 2.6
    box(ax, rx, 5.4, rw, BH, "评估管线\nEvaluation", C_EVAL, fs=10.5)
    box(ax, rx, 4.05, rw, BH, "指标与缺陷日志\nMetrics/Defects", C_EVAL, fs=10.5)
    box(ax, rx, 2.7, rw, BH, "Prompt 迭代\nRevision", C_EVAL, fs=10.5)

    # output -> evaluation
    arrow(ax, 3.2, out_y + BH / 2, rx, 5.4 + BH / 2, color="#7b5e9b", ls="--")
    # evaluation chain down
    arrow(ax, rx + rw / 2, 5.4, rx + rw / 2, 4.75, color="#7b5e9b")
    arrow(ax, rx + rw / 2, 4.05, rx + rw / 2, 3.4, color="#7b5e9b")
    # revision -> prompt builder (feedback)
    arrow(ax, rx + rw / 2, 2.7, rx + rw / 2, 2.2, color="#7b5e9b", ls="--")
    arrow(ax, rx + rw / 2, 2.2, cx + cw, 2.2, color="#7b5e9b", ls="--")
    arrow(ax, cx + cw, 2.2, cx + cw, pb_y + 0.15, color="#7b5e9b", ls="--")

    # Streamlit UI output
    box(ax, 10.4, 10.6, 2.6, BH, "Streamlit UI", "#5a8cae", fs=10.5)
    arrow(ax, 1.9, out_y + BH, 10.4, 10.6, color=C_EDGE, ls=":")

    ax.set_title("CHENGYU 客户顾问 AI Copilot — 系统架构", fontsize=14, pad=14, fontweight="bold")

    out = out_dir / "architecture.png"
    fig.savefig(out, dpi=130, bbox_inches="tight")
    plt.close(fig)
    print("Architecture diagram written to", out)


if __name__ == "__main__":
    main()
