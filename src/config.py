"""Central configuration: loads environment, paths, and model settings."""
from __future__ import annotations

import os
from pathlib import Path

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent.parent
PROMPTS_DIR = PROJECT_ROOT / "prompts"
DATA_DIR = PROJECT_ROOT / "data"
EVALUATION_DIR = PROJECT_ROOT / "evaluation"
REPORTS_DIR = PROJECT_ROOT / "reports"

# ---------------------------------------------------------------------------
# Minimal .env loader (no external dependency). Environment variables win.
# ---------------------------------------------------------------------------
def _load_dotenv(path: Path | None = None) -> None:
    env_path = path or (PROJECT_ROOT / ".env")
    if not env_path.exists():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


_load_dotenv()

# ---------------------------------------------------------------------------
# LLM settings (Anthropic-compatible endpoint)
# ---------------------------------------------------------------------------
ANTHROPIC_BASE_URL = os.environ.get("ANTHROPIC_BASE_URL", "https://api.deepseek.com/anthropic")
ANTHROPIC_AUTH_TOKEN = os.environ.get("ANTHROPIC_AUTH_TOKEN", "")
ANTHROPIC_MODEL = os.environ.get("ANTHROPIC_MODEL", "deepseek-v4-pro")

# Generation parameters
# Prompt version is selectable via CHENGYU_MODEL_VERSION so V1.0/V2.0 runs can
# share the same scripts without editing source between iterations. V2.0 is the
# final shipped version; set the env var to "v1.0" to reproduce the baseline.
MODEL_VERSION = os.environ.get("CHENGYU_MODEL_VERSION", "v2.0")
TEMPERATURE = float(os.environ.get("CHENGYU_TEMPERATURE", "0.7"))
# The thinking model (deepseek-v4-pro) spends a large, variable number of tokens
# on reasoning before producing the final text. 8000 gives headroom for both
# generation and the judge; escalated on truncation.
MAX_TOKENS = int(os.environ.get("CHENGYU_MAX_TOKENS", "8000"))
MAX_RETRIES = int(os.environ.get("CHENGYU_MAX_RETRIES", "3"))
# Escalating budgets used when a response is truncated by max_tokens.
TOKEN_BUDGETS = [8000, 12000, 16000]

# ---------------------------------------------------------------------------
# Output strategy ordering (must match the three-strategy contract)
# ---------------------------------------------------------------------------
STRATEGIES = ["concise_elegant", "warm_personalized", "contextual_consultative"]

SCENARIOS = [
    "birthday_festive",
    "product_recommendation",
    "post_purchase_care",
    "reactivation",
    "event_invitation",
    "price_objection",
]
