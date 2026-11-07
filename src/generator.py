"""LLM generation with structured output parsing, validation, and bounded retries."""
from __future__ import annotations

import time
from dataclasses import dataclass, field

import anthropic

from . import config
from .llm import extract_text, get_client
from .prompt_builder import build_system_prompt, build_user_message, parse_model_json
from .schemas import GeneratedOutput, TestCase
from .validator import validate_output


@dataclass
class GenerationResult:
    case_id: str
    scenario: str
    success: bool
    output: GeneratedOutput | None = None
    blocked: bool = False
    block_reason: str = ""
    block_message: str = ""
    error: str = ""
    latency_ms: int = 0
    retries: int = 0
    raw_text: str = ""
    token_usage: dict = field(default_factory=dict)


def _detect_do_not_contact(case: TestCase) -> bool:
    """True when the client has explicitly asked to stop receiving contact."""
    text = (case.client.notes or "") + "\n" + "\n".join(
        m.content for m in case.conversation_history if m.role == "client"
    )
    return any(kw in text for kw in config.DO_NOT_CONTACT_KEYWORDS)


def generate(case: TestCase, client: anthropic.Anthropic | None = None) -> GenerationResult:
    """Generate three candidate messages for a test case with retries.

    Hard guardrail: if the client has explicitly requested no further contact,
    no LLM call is made and a single non-marketing acknowledgment is returned.
    """
    if _detect_do_not_contact(case):
        return GenerationResult(
            case_id=case.case_id,
            scenario=case.scenario,
            success=True,
            blocked=True,
            block_reason="do_not_contact",
            block_message=config.DO_NOT_CONTACT_REPLY,
        )

    client = client or get_client()
    system_prompt = build_system_prompt(case.scenario)
    user_message = build_user_message(case)

    start = time.time()
    last_error = ""
    last_raw = ""

    for attempt in range(1, config.MAX_RETRIES + 1):
        try:
            budget = config.TOKEN_BUDGETS[min(attempt - 1, len(config.TOKEN_BUDGETS) - 1)]
            resp = client.messages.create(
                model=config.ANTHROPIC_MODEL,
                max_tokens=budget,
                temperature=config.TEMPERATURE,
                system=system_prompt,
                messages=[{"role": "user", "content": user_message}],
            )
            if getattr(resp, "stop_reason", None) == "max_tokens":
                last_error = "输出被 max_tokens 截断（思考占用过多 token）"
                continue
            raw = extract_text(resp.content)
            last_raw = raw
            parsed = parse_model_json(raw)

            if parsed is None:
                last_error = "输出无法解析为 JSON"
                continue

            output = _to_generated_output(parsed, case.case_id)
            if output is None:
                last_error = "输出校验失败"
                continue

            latency_ms = int((time.time() - start) * 1000)
            usage = _usage_to_dict(getattr(resp, "usage", None))
            return GenerationResult(
                case_id=case.case_id,
                scenario=case.scenario,
                success=True,
                output=output,
                latency_ms=latency_ms,
                retries=attempt - 1,
                raw_text=raw,
                token_usage=usage,
            )
        except Exception as exc:  # noqa: BLE001 - surface all API/parse errors to caller
            last_error = f"{type(exc).__name__}: {exc}"

    latency_ms = int((time.time() - start) * 1000)
    return GenerationResult(
        case_id=case.case_id,
        scenario=case.scenario,
        success=False,
        error=last_error,
        latency_ms=latency_ms,
        retries=config.MAX_RETRIES,
        raw_text=last_raw,
    )


def _to_generated_output(parsed: dict, case_id: str) -> GeneratedOutput | None:
    messages = parsed.get("messages")
    if not isinstance(messages, list):
        return None
    try:
        output = GeneratedOutput(
            case_id=case_id,
            model_version=config.MODEL_VERSION,
            messages=messages,
        )
    except Exception:  # noqa: BLE001 - validation failure signals an unusable output
        return None
    if not validate_output(output).valid:
        return None
    return output


def _usage_to_dict(usage) -> dict:
    if usage is None:
        return {}
    return {
        "input_tokens": getattr(usage, "input_tokens", None),
        "output_tokens": getattr(usage, "output_tokens", None),
    }
