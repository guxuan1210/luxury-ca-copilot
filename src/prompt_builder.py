"""Builds system and user prompts from brand rules, scenario rules, and test data."""
from __future__ import annotations

import json
import re

import yaml

from . import config
from .schemas import EventInfo, ProductInfo, TestCase


def load_scenario_rules() -> dict:
    path = config.PROMPTS_DIR / "scenario_rules.yaml"
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _format_scenario_rules(scenario: str, rules: dict) -> str:
    """Render a single scenario's YAML block into plain Chinese instructions."""
    block = rules.get(scenario)
    if block is None:
        return "（该场景暂无专属规则，按品牌通用规则处理。）"

    lines: list[str] = []
    lines.append(f"场景：{block.get('name', scenario)}")
    lines.append(f"目标：{block.get('objective', '')}")
    if block.get("allowed"):
        lines.append("允许：")
        lines.extend(f"- {item}" for item in block["allowed"])
    if block.get("prohibited"):
        lines.append("禁止：")
        lines.extend(f"- {item}" for item in block["prohibited"])
    if block.get("focus"):
        lines.append(f"输出重点：{block['focus']}")
    return "\n".join(lines)


# Map prompt version -> system prompt template filename.
_PROMPT_FILES = {
    "v1.0": "system_prompt.md",
    "v2.0": "system_prompt_v2.md",
    "v2.1": "system_prompt_v2.1.md",
}


def build_system_prompt(scenario: str, version: str | None = None) -> str:
    """Return the full system prompt for a given scenario and prompt version."""
    version = version or config.MODEL_VERSION
    filename = _PROMPT_FILES.get(version, "system_prompt.md")
    template = (config.PROMPTS_DIR / filename).read_text(encoding="utf-8")
    rules = load_scenario_rules()
    scenario_text = _format_scenario_rules(scenario, rules)
    # Use .replace so the JSON braces in the template are untouched.
    return template.replace("{scenario_rules}", scenario_text)


def _format_client(client) -> str:
    parts: list[str] = []
    if client.name:
        parts.append(f"客户姓名：{client.name}")
    if client.preferred_tone:
        parts.append(f"偏好的沟通语气：{client.preferred_tone}")
    if client.preferences:
        parts.append("偏好：")
        parts.extend(f"- {p}" for p in client.preferences)
    else:
        parts.append("偏好：无（信息不足）")
    if client.purchase_history:
        parts.append("历史购买记录：")
        parts.extend(f"- {json.dumps(item, ensure_ascii=False)}" for item in client.purchase_history)
    else:
        parts.append("历史购买记录：无（信息不足）")
    if client.notes:
        parts.append(f"备注：{client.notes}")
    return "\n".join(parts)


def _format_product(product: ProductInfo | None) -> str:
    if product is None:
        return "产品信息：无（本场景不涉及，或信息不足）"
    parts: list[str] = ["产品信息（仅可使用以下事实）："]
    if product.name:
        parts.append(f"- 名称：{product.name}")
    if product.category:
        parts.append(f"- 品类：{product.category}")
    if product.notes:
        parts.append(f"- 香调：{', '.join(product.notes)}")
    if product.price_cny is not None:
        parts.append(f"- 价格（人民币）：{product.price_cny}")
    if product.description:
        parts.append(f"- 描述：{product.description}")
    return "\n".join(parts)


def _format_history(history) -> str:
    if not history:
        return "历史对话：无"
    lines = ["历史对话："]
    for msg in history:
        speaker = "客户" if msg.role == "client" else "顾问"
        lines.append(f"[{speaker}] {msg.content}")
    return "\n".join(lines)


def _format_event(event: EventInfo | None) -> str:
    if event is None:
        return ""
    parts: list[str] = ["活动信息（仅可使用以下事实）："]
    if event.title:
        parts.append(f"- 主题：{event.title}")
    if event.date:
        parts.append(f"- 时间：{event.date}")
    if event.location:
        parts.append(f"- 地点：{event.location}")
    if event.format:
        parts.append(f"- 形式：{event.format}")
    if event.note:
        parts.append(f"- 说明：{event.note}")
    return "\n".join(parts)


def _format_send_at(send_at: str) -> str:
    if not send_at:
        return "发送时间：未提供（禁止使用「今天/明天/后天/昨天」等相对时间词）"
    return f"发送时间（话术应在此时间发送）：{send_at}"


def build_user_message(case: TestCase) -> str:
    """Render the concrete input for a single test case."""
    blocks = [
        f"Case ID: {case.case_id}",
        "---",
        format_case_context(case),
        "---",
        "请根据以上信息，生成三条中文微信候选话术，并严格按 JSON 格式输出。",
    ]
    return "\n".join(blocks)


def format_case_context(case: TestCase) -> str:
    """Return the client/history/product/event context block (shared with the judge)."""
    blocks = [
        _format_client(case.client),
        _format_history(case.conversation_history),
        _format_product(case.product_information),
    ]
    event_block = _format_event(case.event_information)
    if event_block:
        blocks.append(event_block)
    blocks.append(_format_send_at(case.send_at))
    return "\n---\n".join(blocks)


def _extract_json(text: str) -> dict | None:
    """Robustly pull the first balanced JSON object out of a model response."""
    if not text:
        return None
    # Try direct parse first.
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    # Fall back to first { ... last } slice.
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return None
    try:
        return json.loads(text[start : end + 1])
    except json.JSONDecodeError:
        return None


def parse_model_json(text: str) -> dict | None:
    """Exposed helper for tests; strips markdown fences before extracting JSON."""
    cleaned = re.sub(r"```(?:json)?", "", text).strip()
    return _extract_json(cleaned)
