"""Tests for the Validator Agent (schema validation only — no LLM/Neo4j needed)."""

from app.agents.validator import validate_schema


def test_valid_graph_passes():
    graph = {
        "nodes": [
            {"temp_id": "c1", "label": "Client", "properties": {"name": "田中太郎"}},
            {"temp_id": "ng1", "label": "NgAction", "properties": {"action": "大きな音", "riskLevel": "Panic"}},
        ],
        "relationships": [
            {"source_temp_id": "c1", "target_temp_id": "ng1", "type": "MUST_AVOID", "properties": {}},
        ],
    }
    result = validate_schema(graph)
    assert result.is_valid
    assert len(result.errors) == 0


def test_invalid_label_fails():
    graph = {
        "nodes": [{"temp_id": "x1", "label": "InvalidLabel", "properties": {"name": "test"}}],
        "relationships": [],
    }
    result = validate_schema(graph)
    assert not result.is_valid
    assert any("InvalidLabel" in e for e in result.errors)


def test_invalid_rel_type_fails():
    graph = {
        "nodes": [
            {"temp_id": "c1", "label": "Client", "properties": {"name": "田中"}},
            {"temp_id": "ng1", "label": "NgAction", "properties": {"action": "test"}},
        ],
        "relationships": [
            {"source_temp_id": "c1", "target_temp_id": "ng1", "type": "PROHIBITED", "properties": {}},
        ],
    }
    result = validate_schema(graph)
    assert not result.is_valid
    assert any("PROHIBITED" in e for e in result.errors)


def test_missing_temp_id_warning():
    graph = {
        "nodes": [{"temp_id": "c1", "label": "Client", "properties": {"name": "田中"}}],
        "relationships": [
            {"source_temp_id": "c1", "target_temp_id": "missing_id", "type": "MUST_AVOID", "properties": {}},
        ],
    }
    result = validate_schema(graph)
    assert len(result.warnings) > 0


def test_missing_merge_key_fails():
    """Client node without required 'name' property should fail validation."""
    graph = {
        "nodes": [
            {"temp_id": "c1", "label": "Client", "properties": {}},
        ],
        "relationships": [],
    }
    result = validate_schema(graph)
    assert not result.is_valid
    assert any("name" in e for e in result.errors)


def test_care_preference_missing_merge_keys_fails():
    """CarePreference requires both 'category' and 'instruction' keys."""
    graph = {
        "nodes": [
            {"temp_id": "cp1", "label": "CarePreference", "properties": {"category": "食事"}},
        ],
        "relationships": [],
    }
    result = validate_schema(graph)
    assert not result.is_valid
    assert any("instruction" in e for e in result.errors)


def test_create_only_label_passes():
    """SupportLog is a CREATE-only label — should pass with any properties."""
    graph = {
        "nodes": [
            {"temp_id": "sl1", "label": "SupportLog", "properties": {"note": "通常の支援"}},
        ],
        "relationships": [],
    }
    result = validate_schema(graph)
    assert result.is_valid
    assert len(result.errors) == 0


def test_empty_graph_passes():
    """Empty graph with no nodes/relationships should be valid."""
    graph = {"nodes": [], "relationships": []}
    result = validate_schema(graph)
    assert result.is_valid
    assert len(result.errors) == 0
    assert len(result.warnings) == 0


def test_dangling_source_ref_warns():
    """A relationship with unknown source_temp_id should produce a warning."""
    graph = {
        "nodes": [
            {"temp_id": "ng1", "label": "NgAction", "properties": {"action": "騒音"}},
        ],
        "relationships": [
            {"source_temp_id": "nonexistent", "target_temp_id": "ng1", "type": "MUST_AVOID", "properties": {}},
        ],
    }
    result = validate_schema(graph)
    assert any("nonexistent" in w for w in result.warnings)


def test_multiple_errors_accumulated():
    """Multiple invalid labels and rel types should all be reported."""
    graph = {
        "nodes": [
            {"temp_id": "a1", "label": "FakeLabel1", "properties": {}},
            {"temp_id": "a2", "label": "FakeLabel2", "properties": {}},
        ],
        "relationships": [
            {"source_temp_id": "a1", "target_temp_id": "a2", "type": "FAKE_REL", "properties": {}},
        ],
    }
    result = validate_schema(graph)
    assert not result.is_valid
    assert len(result.errors) >= 3  # 2 invalid labels + 1 invalid rel type
