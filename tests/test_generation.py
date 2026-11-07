"""Unit tests for prompt building and JSON parsing (no API calls)."""
from src.generator import _detect_do_not_contact, generate
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


def test_detect_do_not_contact_in_notes():
    case = TestCase(
        case_id="T", scenario="reactivation",
        client=ClientInfo(name="林女士", notes="客户明确表示别再联系"),
    )
    assert _detect_do_not_contact(case)


def test_detect_do_not_contact_in_history():
    case = TestCase(
        case_id="T", scenario="reactivation",
        conversation_history=[Message(role="client", content="请勿再联系我，谢谢")],
    )
    assert _detect_do_not_contact(case)


def test_generate_blocks_do_not_contact_without_api_key():
    # The block happens before any client/API access, so this must not raise.
    case = TestCase(
        case_id="T", scenario="reactivation",
        client=ClientInfo(notes="请停止联系"),
    )
    result = generate(case)
    assert result.blocked
    assert result.block_reason == "do_not_contact"
    assert result.block_message


def test_send_at_appears_in_context():
    case = TestCase(
        case_id="T", scenario="birthday_festive",
        client=ClientInfo(name="林女士", notes="生日：11月6日"),
        send_at="2026-11-06 09:00",
    )
    um = build_user_message(case)
    assert "2026-11-06" in um
