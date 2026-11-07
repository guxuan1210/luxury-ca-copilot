"""Three-layer evaluation: rule checks (L1) + LLM-as-judge scoring (L2). L3 is human.

Layer 1 (rule_checks) is deterministic and cheap.
Layer 2 (judge_case) calls the LLM with a fixed rubric.
Layer 3 (human review) is performed manually; this module surfaces the cases that
most need human attention.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import anthropic

from src import config
from src.llm import extract_text, get_client
from src.prompt_builder import format_case_context, parse_model_json
from src.schemas import GeneratedOutput, TestCase
from src.validator import validate_output

# Weighted quality formula: Q = 0.25R + 0.20P + 0.20B + 0.20N + 0.15C
METRIC_WEIGHTS = {
    "relevance": 0.25,
    "personalization": 0.20,
    "brand_consistency": 0.20,
    "naturalness": 0.20,
    "context_fidelity": 0.15,
}
METRICS = list(METRIC_WEIGHTS.keys())

# Human-readable metric names used consistently in results.csv and charts.
METRIC_DISPLAY = {
    "relevance": "Relevance",
    "personalization": "Personalization",
    "brand_consistency": "Brand Consistency",
    "naturalness": "Naturalness",
    "context_fidelity": "Context Fidelity",
}

QUALITY_TARGET = 4.2
DIVERSITY_TARGET = 4.0


@dataclass
class EvaluationResult:
    case_id: str
    scenario: str
    rule_passed: bool
    rule_flags: list[str] = field(default_factory=list)
    scores: dict = field(default_factory=dict)
    weighted_score: float | None = None
    diversity: float | None = None
    factual_error: bool | None = None
    boundary_violation: bool | None = None
    uncertain: bool | None = None
    judge_error: str = ""
    notes: str = ""


def rule_checks(case: TestCase, output: GeneratedOutput) -> tuple[bool, list[str]]:
    """Layer 1: deterministic structural + surface checks."""
    vr = validate_output(output)
    flags = list(vr.flags)
    if vr.errors:
        flags = [f"RULE_ERROR: {e}" for e in vr.errors] + flags
    return vr.valid, flags


def build_judge_user_message(case: TestCase, output: GeneratedOutput) -> str:
    blocks = [
        f"场景：{case.scenario}",
        "--- 输入上下文 ---",
        format_case_context(case),
        "--- 待评审的三条候选话术 ---",
    ]
    for m in output.messages:
        blocks.append(f"[{m.strategy}]\n{m.text}")
    blocks.append("---")
    blocks.append("请按评审规则对以上三条话术打分，并严格按 JSON 格式输出。")
    return "\n".join(blocks)


def judge_case(
    case: TestCase,
    output: GeneratedOutput,
    client: anthropic.Anthropic | None = None,
) -> tuple[dict | None, str]:
    """Layer 2: LLM-as-judge. Returns (parsed_dict_or_None, error)."""
    client = client or get_client()
    judge_prompt = (config.EVALUATION_DIR / "judge_prompt.md").read_text(encoding="utf-8")
    user_message = build_judge_user_message(case, output)

    for attempt, budget in enumerate(config.TOKEN_BUDGETS, start=1):
        try:
            resp = client.messages.create(
                model=config.ANTHROPIC_MODEL,
                max_tokens=budget,
                temperature=0.0,
                system=judge_prompt,
                messages=[{"role": "user", "content": user_message}],
            )
            if getattr(resp, "stop_reason", None) == "max_tokens":
                continue
            raw = extract_text(resp.content)
            parsed = parse_model_json(raw)
            if parsed is None:
                return None, "judge output not parseable as JSON"
            return parsed, ""
        except Exception as exc:  # noqa: BLE001
            return None, f"{type(exc).__name__}: {exc}"
    return None, "judge output truncated by max_tokens on all budgets"


def _average_scores(messages: list[dict]) -> dict:
    avg: dict[str, float] = {}
    for metric in METRICS:
        vals = [m.get("scores", {}).get(metric) for m in messages]
        vals = [v for v in vals if isinstance(v, (int, float))]
        avg[metric] = round(sum(vals) / len(vals), 2) if vals else 0.0
    return avg


def _weighted(avg: dict) -> float:
    return round(sum(avg.get(m, 0) * w for m, w in METRIC_WEIGHTS.items()), 2)


def evaluate_case(
    case: TestCase,
    output: GeneratedOutput,
    client: anthropic.Anthropic | None = None,
    run_judge: bool = True,
    judge_override: dict | None = None,
) -> EvaluationResult:
    """Run L1 + L2 for a single case and compute the weighted quality score.

    judge_override lets callers supply an already-computed judge dict (e.g. from
    a cache) to skip the LLM judge call while reusing the same scoring logic.
    """
    rule_passed, rule_flags = rule_checks(case, output)

    result = EvaluationResult(
        case_id=case.case_id,
        scenario=case.scenario,
        rule_passed=rule_passed,
        rule_flags=rule_flags,
    )

    if not run_judge:
        return result

    judge = judge_override
    if judge is None:
        judge, err = judge_case(case, output, client)
        if judge is None:
            result.judge_error = err
            return result

    messages = judge.get("messages") or []
    result.scores = _average_scores(messages)
    result.weighted_score = _weighted(result.scores)
    result.diversity = judge.get("diversity")
    result.factual_error = judge.get("factual_error")
    result.boundary_violation = judge.get("boundary_violation")
    result.uncertain = judge.get("uncertain")
    result.notes = judge.get("notes", "")
    return result
