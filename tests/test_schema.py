"""Unit tests for Pydantic schemas."""
import pytest

from src.schemas import CandidateMessage, ClientInfo, GeneratedOutput, TestCase


def test_client_defaults():
    c = ClientInfo()
    assert c.name == ""
    assert c.preferences == []


def test_generated_output_requires_exactly_three():
    with pytest.raises(Exception):
        GeneratedOutput(case_id="T", messages=[CandidateMessage(strategy="concise_elegant", text="你好")])


def test_candidate_text_stripped():
    m = CandidateMessage(strategy="concise_elegant", text="  你好  ")
    assert m.text == "你好"


def test_candidate_empty_text_rejected():
    with pytest.raises(Exception):
        CandidateMessage(strategy="concise_elegant", text="   ")


def test_testcase_product_optional():
    c = TestCase(case_id="T", scenario="birthday_festive")
    assert c.product_information is None
