"""Shared Anthropic-compatible client factory and response helpers."""
from __future__ import annotations

import anthropic

from . import config


def get_client() -> anthropic.Anthropic:
    if not config.ANTHROPIC_AUTH_TOKEN:
        raise RuntimeError(
            "ANTHROPIC_AUTH_TOKEN 未设置。请在 .env 或环境变量中配置 API 密钥。"
        )
    return anthropic.Anthropic(
        base_url=config.ANTHROPIC_BASE_URL,
        api_key=config.ANTHROPIC_AUTH_TOKEN,
    )


def extract_text(content: list) -> str:
    """Concatenate only TextBlock contents, skipping ThinkingBlock / others."""
    parts: list[str] = []
    for block in content:
        text = getattr(block, "text", None)
        if text:
            parts.append(text)
    return "".join(parts)
