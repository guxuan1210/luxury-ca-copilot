"""Generate evaluation charts from evaluation/results.csv using pandas + matplotlib."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

from src import config

plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "SimSun", "Arial Unicode MS"]
plt.rcParams["axes.unicode_minus"] = False

SCENARIO_LABELS = {
    "birthday_festive": "生日节日",
    "product_recommendation": "产品推荐",
    "post_purchase_care": "售后关怀",
    "reactivation": "唤醒",
    "event_invitation": "活动邀请",
    "price_objection": "价格异议",
}

METRIC_CN = {
    "Relevance": "相关性",
    "Personalization": "个性化",
    "Brand Consistency": "品牌一致性",
    "Naturalness": "自然度",
    "Context Fidelity": "上下文一致性",
}


def main() -> None:
    out_dir = config.REPORTS_DIR / "screenshots"
    out_dir.mkdir(parents=True, exist_ok=True)

    results_path = config.EVALUATION_DIR / "results.csv"
    if not results_path.exists():
        print("results.csv not found; run scripts/run_evaluation.py first.")
        return

    df = pd.read_csv(results_path, encoding="utf-8-sig")
    df["Weighted Score"] = pd.to_numeric(df["Weighted Score"], errors="coerce")

    # 1. Average score by scenario.
    by_scenario = df.groupby("Scenario")["Weighted Score"].mean().dropna()
    fig, ax = plt.subplots(figsize=(8, 4.5))
    labels = [SCENARIO_LABELS.get(s, s) for s in by_scenario.index]
    ax.bar(labels, by_scenario.values, color="#6b8cae")
    ax.axhline(4.2, color="red", linestyle="--", label="目标 4.2")
    ax.set_ylim(0, 5)
    ax.set_ylabel("平均加权分")
    ax.set_title("六场景平均质量分")
    ax.legend()
    fig.tight_layout()
    fig.savefig(out_dir / "eval_scenario_scores.png", dpi=120)
    plt.close(fig)

    # 2. Average score by metric.
    metric_cols = [c for c in METRIC_CN if c in df.columns]
    metric_means = df[metric_cols].apply(pd.to_numeric, errors="coerce").mean().dropna()
    fig, ax = plt.subplots(figsize=(8, 4.5))
    labels = [METRIC_CN[c] for c in metric_means.index]
    ax.bar(labels, metric_means.values, color="#8cae6b")
    ax.set_ylim(0, 5)
    ax.set_ylabel("平均分")
    ax.set_title("五项质量维度平均分")
    fig.tight_layout()
    fig.savefig(out_dir / "eval_metric_scores.png", dpi=120)
    plt.close(fig)

    # 3. Diversity + factual/boundary breakdown as a simple summary (text chart).
    summary = {
        "平均加权分": round(df["Weighted Score"].mean(), 3),
        "平均差异度": round(pd.to_numeric(df["Diversity"], errors="coerce").mean(), 3),
        "事实错误数": int((df["Factual Error"].astype(str).str.lower() == "true").sum()),
        "边界违规数": int((df["Boundary Violation"].astype(str).str.lower() == "true").sum()),
    }
    fig, ax = plt.subplots(figsize=(6, 3))
    ax.axis("off")
    rows = "\n".join(f"{k}: {v}" for k, v in summary.items())
    ax.text(0.05, 0.5, rows, fontsize=13, va="center", family="Microsoft YaHei")
    fig.tight_layout()
    fig.savefig(out_dir / "eval_summary_text.png", dpi=120)
    plt.close(fig)

    print("Charts written to", out_dir)
    print(summary)


if __name__ == "__main__":
    main()
