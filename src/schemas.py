"""Pydantic data models for input and output validation."""
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator


class ClientInfo(BaseModel):
    name: str = ""
    preferred_tone: str = "elegant"
    preferences: list[str] = Field(default_factory=list)
    purchase_history: list[dict[str, Any]] = Field(default_factory=list)
    notes: str = ""


class Message(BaseModel):
    role: Literal["client", "advisor"]
    content: str


class ProductInfo(BaseModel):
    name: str = ""
    category: str = ""
    notes: list[str] = Field(default_factory=list)
    price_cny: int | float | None = None
    description: str = ""


class EventInfo(BaseModel):
    title: str = ""
    date: str = ""
    location: str = ""
    format: str = ""
    note: str = ""


class TestCase(BaseModel):
    """A single test case input, mirroring the Brief's suggested fields."""

    __test__ = False  # avoid pytest collecting this model as a test class

    case_id: str
    scenario: str
    client: ClientInfo = Field(default_factory=ClientInfo)
    conversation_history: list[Message] = Field(default_factory=list)
    product_information: ProductInfo | None = None
    event_information: EventInfo | None = None


class CandidateMessage(BaseModel):
    strategy: str
    text: str

    @field_validator("text")
    @classmethod
    def _nonempty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("message text must be non-empty")
        return v.strip()


class GeneratedOutput(BaseModel):
    """The three-candidate output for a single case."""

    case_id: str
    model_version: str = "v1.0"
    messages: list[CandidateMessage] = Field(default_factory=list)

    @field_validator("messages")
    @classmethod
    def _exactly_three(cls, v: list[CandidateMessage]) -> list[CandidateMessage]:
        if len(v) != 3:
            raise ValueError(f"expected exactly 3 messages, got {len(v)}")
        return v
