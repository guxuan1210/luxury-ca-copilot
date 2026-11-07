"""Unit tests for prompt building and JSON parsing (no API calls)."""
from src.prompt_builder import build_system_prompt, build_user_message, parse_model_json
from src.schemas import ClientInfo, Message, ProductInfo, TestCase


def test_system_prompt_fills_scenario_rules():
    sp = build_system_prompt("price_objection")
    assert "价格异议" in sp
    assert "{scenario_rules}" not in sp


def test_user_message_includes_context():
    case = TestCase(
        case_id="TC001",
        scenario="product_recommendation",
        client=ClientInfo(name="林女士", preferences=["茶香"]),
        conversation_history=[Message(role="client", content="我喜欢茶香")],
        product_information=ProductInfo(name="CHENGYU Tea Mist", price_cny=1280),
    )
    um = build_user_message(case)
    assert "林女士" in um
    assert "茶香" in um
    assert "CHENGYU Tea Mist" in um


def test_parse_model_json_direct():
    parsed = parse_model_json('{"case_id": "T", "messages": []}')
    assert parsed["case_id"] == "T"


def test_parse_model_json_with_fence():
    raw = '```json\n{"a": 1}\n```'
    assert parse_model_json(raw) == {"a": 1}


def test_parse_model_json_bad_returns_none():
    assert parse_model_json("not json at all") is None
