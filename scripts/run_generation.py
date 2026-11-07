"""Batch-run generation over all 50 test cases.

Writes:
  - data/generated_outputs.csv  (the Brief's 8-column format)
  - data/run_metadata.csv       (version / latency / token tracking)
"""
from __future__ import annotations

import csv
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src import config
from src.generator import generate
from src.schemas import TestCase

RUN_ID = "run_" + datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")


def load_cases(path: Path) -> list[TestCase]:
    cases: list[TestCase] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            cases.append(TestCase.model_validate_json(line))
    return cases


def client_text(c) -> str:
    parts = []
    if c.name:
        parts.append(c.name)
    if c.preferred_tone:
        parts.append(f"语气:{c.preferred_tone}")
    if c.preferences:
        parts.append("偏好:" + ", ".join(c.preferences))
    if c.purchase_history:
        parts.append("购买记录:" + json.dumps(c.purchase_history, ensure_ascii=False))
    if c.notes:
        parts.append("备注:" + c.notes)
    return " | ".join(parts)


def history_text(history) -> str:
    if not history:
        return ""
    lines = []
    for msg in history:
        speaker = "客户" if msg.role == "client" else "顾问"
        lines.append(f"[{speaker}] {msg.content}")
    return "\n".join(lines)


def product_text(p) -> str:
    if p is None:
        return ""
    parts = []
    if p.name:
        parts.append(p.name)
    if p.category:
        parts.append(p.category)
    if p.notes:
        parts.append("香调:" + ", ".join(p.notes))
    if p.price_cny is not None:
        parts.append(f"价格:{p.price_cny}")
    if p.description:
        parts.append(p.description)
    return " | ".join(parts)


def event_text(e) -> str:
    if e is None:
        return ""
    parts = []
    for label, val in [("主题", e.title), ("时间", e.date), ("地点", e.location), ("形式", e.format), ("说明", e.note)]:
        if val:
            parts.append(f"{label}:{val}")
    return " | ".join(parts)


def main() -> None:
    cases = load_cases(config.DATA_DIR / "test_cases.jsonl")
    print(f"Loaded {len(cases)} cases. Run ID: {RUN_ID}")

    out_rows: list[dict] = []
    meta_rows: list[dict] = []
    structured_rows: list[dict] = []
    client = None  # shared client (created lazily inside generate)

    for i, case in enumerate(cases, start=1):
        t0 = time.time()
        result = generate(case, client=client)
        elapsed = time.time() - t0

        structured_rows.append({
            "case_id": case.case_id,
            "scenario": case.scenario,
            "messages": [m.model_dump() for m in result.output.messages] if result.output else None,
        })

        # Serialize the 8-column row.
        history_full = history_text(case.conversation_history)
        event = event_text(case.event_information)
        if event:
            history_full = ("[活动信息] " + event + "\n" + history_full).strip()

        row = {
            "Case ID": case.case_id,
            "Scenario": case.scenario,
            "Client information": client_text(case.client),
            "Conversation history": history_full,
            "Product information": product_text(case.product_information),
            "Output 1": "",
            "Output 2": "",
            "Output 3": "",
        }
        if result.success and result.output:
            texts = [m.text for m in result.output.messages]
            row["Output 1"], row["Output 2"], row["Output 3"] = texts[0], texts[1], texts[2]

        meta_rows.append({
            "Case ID": case.case_id,
            "Run ID": RUN_ID,
            "Model": config.ANTHROPIC_MODEL,
            "Prompt Version": config.MODEL_VERSION,
            "Timestamp": datetime.now(timezone.utc).isoformat(),
            "Generation Status": "success" if result.success else "failed",
            "Latency ms": result.latency_ms,
            "Input Tokens": result.token_usage.get("input_tokens", ""),
            "Output Tokens": result.token_usage.get("output_tokens", ""),
            "Error": result.error,
        })
        out_rows.append(row)
        print(f"[{i}/{len(cases)}] {case.case_id} {case.scenario} "
              f"{'OK' if result.success else 'FAIL: ' + result.error} ({elapsed:.1f}s)")

    # Write 8-column outputs.
    fieldnames = ["Case ID", "Scenario", "Client information", "Conversation history",
                  "Product information", "Output 1", "Output 2", "Output 3"]
    with open(config.DATA_DIR / "generated_outputs.csv", "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(out_rows)

    # Write structured outputs (JSONL) for the evaluator (preserves strategies).
    with open(config.DATA_DIR / "generated_outputs.jsonl", "w", encoding="utf-8") as f:
        for entry in structured_rows:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    # Write metadata.
    meta_fields = ["Case ID", "Run ID", "Model", "Prompt Version", "Timestamp",
                   "Generation Status", "Latency ms", "Input Tokens", "Output Tokens", "Error"]
    with open(config.DATA_DIR / "run_metadata.csv", "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=meta_fields)
        writer.writeheader()
        writer.writerows(meta_rows)

    n_ok = sum(1 for r in meta_rows if r["Generation Status"] == "success")
    print(f"Done: {n_ok}/{len(cases)} succeeded.")
    print(f"Wrote {config.DATA_DIR / 'generated_outputs.csv'} and {config.DATA_DIR / 'run_metadata.csv'}")


if __name__ == "__main__":
    main()
