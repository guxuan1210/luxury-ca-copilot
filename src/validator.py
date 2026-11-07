"""Rule-based output validation: structural (hard) checks plus semantic flags (soft)."""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from . import config
from .schemas import GeneratedOutput

_CN_RE = re.compile(r"[一-鿿]")

# Keywords that commonly signal fabricated discounts/offers/scarcity. These are
# soft flags (escalated to the LLM judge / human review), not hard failures,
# because some legitimate phrasing (e.g. "无法提供折扣") contains the same words.
_DISCOUNT_KEYWORDS = [
    "折扣", "打折", "优惠", "促销", "降价", "特价", "赠品", "买一送一",
    "限时", "最后机会", "错过就没有", "限量", "仅剩", "名额有限",
]

_EXCLAMATION_RE = re.compile(r"！|!")


@dataclass
class ValidationResult:
    valid: bool
    errors: list[str] = field(default_factory=list)
    flags: list[str] = field(default_factory=list)


def has_chinese(text: str) -> bool:
    return bool(_CN_RE.search(text))


def validate_output(output: GeneratedOutput) -> ValidationResult:
    errors: list[str] = []
    flags: list[str] = []

    msgs = output.messages

    # 1. Exactly three messages
    if len(msgs) != 3:
        errors.append(f"expected 3 messages, got {len(msgs)}")

    # 2. Strategy order/set
    strategies = [m.strategy for m in msgs]
    if strategies != config.STRATEGIES:
        if set(strategies) != set(config.STRATEGIES):
            errors.append(f"unexpected strategies: {strategies}")
        else:
            flags.append(f"strategy order differs from contract: {strategies}")

    # 3. Non-empty + Chinese content
    for i, m in enumerate(msgs):
        if not m.text.strip():
            errors.append(f"message {i} is empty")
        elif not has_chinese(m.text):
            errors.append(f"message {i} contains no Chinese characters")

    # 4. Duplicate content
    texts = [m.text for m in msgs]
    if len(set(texts)) < len(texts):
        errors.append("duplicate candidate messages found")

    # 5. Soft flags: fabricated discount/offer/scarcity language
    for i, m in enumerate(msgs):
        for kw in _DISCOUNT_KEYWORDS:
            if kw in m.text:
                flags.append(f"message {i} contains possible offer/discount keyword: '{kw}'")
        bang_count = len(_EXCLAMATION_RE.findall(m.text))
        if bang_count >= 2:
            flags.append(f"message {i} 使用了 {bang_count} 个感叹号（可能过度营销）")

    return ValidationResult(valid=not errors, errors=errors, flags=flags)
