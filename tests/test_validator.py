"""Unit tests for the rule-based validator."""
from src.schemas import CandidateMessage, GeneratedOutput
from src.validator import has_chinese, validate_output


def _out(*texts):
    strategies = ["concise_elegant", "warm_personalized", "contextual_consultative"]
    return GeneratedOutput(
        case_id="T",
        messages=[
            CandidateMessage(strategy=s, text=t) for s, t in zip(strategies, texts)
        ],
    )


def test_valid_output_passes():
    r = validate_output(_out("您好，祝您节日愉快。", "感谢您一直以来的信任。", "若您需要，我可以为您介绍。"))
    assert r.valid


def test_duplicate_messages_flagged():
    r = validate_output(_out("同一句话", "同一句话", "第三句"))
    assert not r.valid


def test_no_chinese_fails():
    r = validate_output(_out("hello", "world", "third"))
    assert not r.valid


def test_discount_keyword_flagged():
    r = validate_output(_out("可以给您打折", "第二句", "第三句"))
    assert r.valid  # not a hard fail
    assert any("折扣" in f or "打折" in f for f in r.flags)


def test_excessive_exclamation_flagged():
    r = validate_output(_out("太棒了！！", "第二句", "第三句"))
    assert any("感叹号" in f for f in r.flags)


def test_has_chinese():
    assert has_chinese("你好")
    assert not has_chinese("hello")


def test_relative_time_term_flagged():
    r = validate_output(_out("今天是您的生日，祝您快乐。", "第二句", "第三句"))
    assert r.valid  # not a hard fail
    assert any("relative-time" in f for f in r.flags)
