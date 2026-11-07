"""Batch-run evaluation (rule checks + LLM-as-judge) over all generated outputs.

Reads data/test_cases.jsonl + data/generated_outputs.jsonl.
Writes:
  - evaluation/results.csv      (per-case scores)
  - evaluation/summary.json     (aggregate statistics)
  - evaluation/defect_log.csv   (auto-populated defect candidates)

Judge results are cached in evaluation/.judge_cache.json so re-running after a
partial failure does not re-invoke the LLM for already-judged cases.
"""
from __future__ import annotations

import csv
import hashlib
import json
import statistics
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src import config
from src.llm import get_client
from src.schemas import GeneratedOutput, TestCase
from evaluation.evaluator import (
    METRICS,
    METRIC_DISPLAY,
    DIVERSITY_TARGET,
    QUALITY_TARGET,
    evaluate_case,
    judge_case,
)

RUN_ID = "eval_" + datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
CACHE_PATH = config.EVALUATION_DIR / ".judge_cache.json"


def load_cases(path: Path) -> dict[str, TestCase]:
    cases: dict[str, TestCase] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            c = TestCase.model_validate_json(line)
            cases[c.case_id] = c
    return cases


def load_outputs(path: Path) -> dict[str, GeneratedOutput]:
    outputs: dict[str, GeneratedOutput] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            obj = json.loads(line)
            if obj.get("messages"):
                outputs[obj["case_id"]] = GeneratedOutput(
                    case_id=obj["case_id"], model_version=config.MODEL_VERSION, messages=obj["messages"]
                )
    return outputs


def load_cache() -> dict:
    if CACHE_PATH.exists():
        return json.loads(CACHE_PATH.read_text(encoding="utf-8"))
    return {}


def save_cache(cache: dict) -> None:
    CACHE_PATH.write_text(json.dumps(cache, ensure_ascii=False), encoding="utf-8")


def _output_key(case_id: str, output: GeneratedOutput) -> str:
    raw = json.dumps([m.model_dump() for m in output.messages], ensure_ascii=False, sort_keys=True)
    digest = hashlib.md5(raw.encode("utf-8")).hexdigest()[:12]
    return f"{case_id}|{config.MODEL_VERSION}|{digest}"


def _judge_with_cache(case, output, client) -> tuple[dict | None, str]:
    key = _output_key(case.case_id, output)
    cache = load_cache()
    if key in cache:
        return cache[key], ""
    judge, err = judge_case(case, output, client)
    if judge is None:
        return None, err
    cache[key] = judge
    save_cache(cache)
    return judge, ""


def main() -> None:
    cases = load_cases(config.DATA_DIR / "test_cases.jsonl")
    outputs = load_outputs(config.DATA_DIR / "generated_outputs.jsonl")
    print(f"Loaded {len(cases)} cases, {len(outputs)} outputs. Run ID: {RUN_ID}")

    client = get_client()

    # results.csv: written incrementally so partial runs keep their work.
    fieldnames = ["Case ID", "Scenario", "Status", "Rule Passed",
                  *[METRIC_DISPLAY[m] for m in METRICS],
                  "Weighted Score", "Diversity", "Factual Error", "Boundary Violation",
                  "Uncertain", "Judge Error", "Notes"]
    results_path = config.EVALUATION_DIR / "results.csv"
    with open(results_path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

    result_rows: list[dict] = []
    defects: list[dict] = []

    for i, case_id in enumerate(sorted(cases.keys()), start=1):
        case = cases[case_id]
        output = outputs.get(case_id)
        t0 = time.time()

        if output is None:
            row = {
                "Case ID": case_id, "Scenario": case.scenario, "Status": "no_output",
                "Rule Passed": False, **{METRIC_DISPLAY[m]: "" for m in METRICS},
                "Weighted Score": "", "Diversity": "",
                "Factual Error": "", "Boundary Violation": "", "Uncertain": "",
                "Judge Error": "no output to evaluate", "Notes": "",
            }
            result_rows.append(row)
            with open(results_path, "a", newline="", encoding="utf-8-sig") as f:
                csv.DictWriter(f, fieldnames=fieldnames).writerow(row)
            print(f"[{i}/{len(cases)}] {case_id} NO_OUTPUT")
            continue

        # L1 + L2 (judge cached). When the judge dict is available (cached or
        # freshly fetched) we compute scores from it; when the LLM judge failed
        # we do NOT re-call it and instead record the error on a rule-only result.
        judge, judge_err = _judge_with_cache(case, output, client)
        if judge is not None:
            ev = evaluate_case(case, output, client=client, run_judge=True, judge_override=judge)
        else:
            ev = evaluate_case(case, output, client=client, run_judge=False)
            ev.judge_error = judge_err or "judge output not parseable"
        elapsed = time.time() - t0

        row = {
            "Case ID": case_id,
            "Scenario": case.scenario,
            "Status": "ok" if ev.rule_passed else "rule_fail",
            "Rule Passed": ev.rule_passed,
            **{METRIC_DISPLAY[m]: ev.scores.get(m, "") for m in METRICS},
            "Weighted Score": ev.weighted_score if ev.weighted_score is not None else "",
            "Diversity": ev.diversity if ev.diversity is not None else "",
            "Factual Error": "" if ev.factual_error is None else ev.factual_error,
            "Boundary Violation": "" if ev.boundary_violation is None else ev.boundary_violation,
            "Uncertain": "" if ev.uncertain is None else ev.uncertain,
            "Judge Error": ev.judge_error,
            "Notes": ev.notes,
        }
        result_rows.append(row)
        with open(results_path, "a", newline="", encoding="utf-8-sig") as f:
            csv.DictWriter(f, fieldnames=fieldnames).writerow(row)
        print(f"[{i}/{len(cases)}] {case_id} {case.scenario} "
              f"score={ev.weighted_score} div={ev.diversity} "
              f"fact_err={ev.factual_error} bnd_viol={ev.boundary_violation} ({elapsed:.1f}s)")

        # Auto-populate defect candidates.
        if ev.factual_error:
            defects.append(_defect("factual", case_id, "Critical", "LLM Judge 标记存在事实错误", ev))
        if ev.boundary_violation:
            defects.append(_defect("boundary", case_id, "Critical", "LLM Judge 标记存在客户边界违规", ev))
        if ev.weighted_score is not None and ev.weighted_score < 4.0:
            defects.append(_defect("low_score", case_id, "Major", f"加权质量分 {ev.weighted_score} 低于目标 4.2", ev))
        if ev.diversity is not None and ev.diversity < 3.0:
            defects.append(_defect("low_diversity", case_id, "Major", f"候选差异度 {ev.diversity} 偏低", ev))
        for flag in ev.rule_flags:
            defects.append(_defect("rule_flag", case_id, "Minor", flag, ev))

    _write_summary(result_rows)
    _write_defects(defects)
    print(f"Done. Wrote results.csv, summary.json, defect_log.csv")


def _defect(kind: str, case_id: str, severity: str, desc: str, ev) -> dict:
    return {
        "Defect ID": f"{kind.upper()}-{case_id}",
        "Case ID": case_id,
        "Version": config.MODEL_VERSION,
        "Severity": severity,
        "Description": desc,
        "Evidence": "",
        "Root Cause": "",
        "Fix": "",
        "Retest Result": "",
        "Status": "Open",
    }


def _write_summary(rows: list[dict]) -> None:
    scored = [r for r in rows if r["Weighted Score"] not in ("", None)]
    n = len(scored)

    def avg(key, cast=float):
        vals = [cast(r[key]) for r in scored if r[key] not in ("", None)]
        return round(statistics.mean(vals), 3) if vals else None

    per_scenario: dict[str, list[float]] = {}
    for r in scored:
        per_scenario.setdefault(r["Scenario"], []).append(float(r["Weighted Score"]))

    summary = {
        "run_id": RUN_ID,
        "model": config.ANTHROPIC_MODEL,
        "prompt_version": config.MODEL_VERSION,
        "n_cases": len(rows),
        "n_scored": n,
        "structured_output_success_rate": round(n / len(rows), 4) if rows else 0,
        "avg_weighted_score": avg("Weighted Score"),
        "avg_diversity": avg("Diversity"),
        "quality_target": QUALITY_TARGET,
        "diversity_target": DIVERSITY_TARGET,
        "avg_by_metric": {METRIC_DISPLAY[m]: avg(METRIC_DISPLAY[m]) for m in METRICS},
        "avg_by_scenario": {k: round(statistics.mean(v), 3) for k, v in sorted(per_scenario.items())},
        "factual_error_count": sum(1 for r in scored if str(r["Factual Error"]).lower() == "true"),
        "boundary_violation_count": sum(1 for r in scored if str(r["Boundary Violation"]).lower() == "true"),
        "rule_fail_count": sum(1 for r in rows if not r["Rule Passed"]),
        "judge_error_count": sum(1 for r in rows if r["Judge Error"]),
    }
    with open(config.EVALUATION_DIR / "summary.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    print("SUMMARY:", json.dumps(summary, ensure_ascii=False))


def _write_defects(defects: list[dict]) -> None:
    fieldnames = ["Defect ID", "Case ID", "Version", "Severity", "Description",
                  "Evidence", "Root Cause", "Fix", "Retest Result", "Status"]
    with open(config.EVALUATION_DIR / "defect_log.csv", "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(defects)


if __name__ == "__main__":
    main()
