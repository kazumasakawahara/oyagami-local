"""Tests for the Intake Agent (text-to-JSON extraction)."""

from app.agents.intake import get_extraction_prompt, parse_json_from_response


def test_parse_json_direct():
    raw = '{"nodes": [], "relationships": []}'
    result = parse_json_from_response(raw)
    assert result == {"nodes": [], "relationships": []}


def test_parse_json_markdown_block():
    raw = (
        '```json\n'
        '{"nodes": [{"temp_id": "c1", "label": "Client", "properties": {"name": "田中"}}],'
        ' "relationships": []}\n'
        '```'
    )
    result = parse_json_from_response(raw)
    assert result is not None
    assert len(result["nodes"]) == 1
    assert result["nodes"][0]["label"] == "Client"


def test_parse_json_markdown_block_no_lang():
    raw = '```\n{"nodes": [], "relationships": []}\n```'
    result = parse_json_from_response(raw)
    assert result == {"nodes": [], "relationships": []}


def test_parse_json_embedded_in_text():
    raw = 'Here is the extraction: {"nodes": [], "relationships": []} done.'
    result = parse_json_from_response(raw)
    assert result == {"nodes": [], "relationships": []}


def test_parse_json_invalid():
    assert parse_json_from_response("not json at all") is None


def test_parse_json_empty_string():
    assert parse_json_from_response("") is None


def test_extraction_prompt_exists():
    prompt = get_extraction_prompt()
    assert "Client" in prompt
    assert "NgAction" in prompt
    assert "MUST_AVOID" in prompt
