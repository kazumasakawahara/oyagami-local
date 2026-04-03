"""Unit tests for db_operations — no Neo4j needed (constants and logic only)."""

import pytest
from unittest.mock import MagicMock, patch

from app.lib.db_operations import (
    MERGE_KEYS,
    ALLOWED_CREATE_LABELS,
    ALLOWED_LABELS,
    ALLOWED_REL_TYPES,
)


# ---------------------------------------------------------------------------
# Constants: ALLOWED_LABELS
# ---------------------------------------------------------------------------

class TestAllowedLabels:
    def test_allowed_labels_include_core_types(self):
        core_types = {"Client", "Supporter", "NgAction", "CarePreference", "Condition"}
        assert core_types.issubset(ALLOWED_LABELS)

    def test_allowed_labels_include_create_only_types(self):
        create_only = {"SupportLog", "AuditLog", "MeetingRecord"}
        assert create_only.issubset(ALLOWED_LABELS)

    def test_allowed_labels_is_union_of_merge_and_create(self):
        expected = set(MERGE_KEYS.keys()) | ALLOWED_CREATE_LABELS
        assert ALLOWED_LABELS == expected

    def test_client_in_merge_keys(self):
        assert "Client" in MERGE_KEYS

    def test_support_log_in_create_labels(self):
        assert "SupportLog" in ALLOWED_CREATE_LABELS

    def test_audit_log_in_create_labels(self):
        assert "AuditLog" in ALLOWED_CREATE_LABELS

    def test_meeting_record_in_create_labels(self):
        assert "MeetingRecord" in ALLOWED_CREATE_LABELS


# ---------------------------------------------------------------------------
# Constants: ALLOWED_REL_TYPES
# ---------------------------------------------------------------------------

class TestAllowedRelTypes:
    def test_allowed_rel_types_include_core_types(self):
        core_rels = {
            "HAS_CONDITION", "MUST_AVOID", "REQUIRES", "HAS_KEY_PERSON",
            "HAS_LEGAL_REP", "HAS_CERTIFICATE", "TREATED_AT", "LOGGED",
            "ABOUT", "RECORDED",
        }
        assert core_rels.issubset(ALLOWED_REL_TYPES)

    def test_allowed_rel_types_are_upper_snake_case(self):
        for rel in ALLOWED_REL_TYPES:
            assert rel == rel.upper(), f"Relation type {rel!r} is not UPPER_SNAKE_CASE"
            assert " " not in rel, f"Relation type {rel!r} contains a space"

    def test_rel_types_is_a_set(self):
        assert isinstance(ALLOWED_REL_TYPES, (set, frozenset))


# ---------------------------------------------------------------------------
# Constants: MERGE_KEYS
# ---------------------------------------------------------------------------

class TestMergeKeys:
    def test_merge_keys_defined_for_core_labels(self):
        core_labels = {"Client", "Supporter", "NgAction", "CarePreference", "Condition",
                       "KeyPerson", "Organization", "ServiceProvider", "Hospital",
                       "Guardian", "Certificate"}
        assert core_labels.issubset(set(MERGE_KEYS.keys()))

    def test_merge_keys_values_are_lists_of_strings(self):
        for label, keys in MERGE_KEYS.items():
            assert isinstance(keys, list), f"MERGE_KEYS[{label!r}] is not a list"
            assert len(keys) >= 1, f"MERGE_KEYS[{label!r}] is empty"
            for k in keys:
                assert isinstance(k, str), f"Key {k!r} in MERGE_KEYS[{label!r}] is not a str"

    def test_client_merges_on_name(self):
        assert MERGE_KEYS["Client"] == ["name"]

    def test_care_preference_merges_on_category_and_instruction(self):
        assert set(MERGE_KEYS["CarePreference"]) == {"category", "instruction"}

    def test_create_labels_not_in_merge_keys(self):
        """CREATE-only labels must not appear in MERGE_KEYS to prevent accidental MERGE."""
        for label in ALLOWED_CREATE_LABELS:
            assert label not in MERGE_KEYS, (
                f"{label} is in both MERGE_KEYS and ALLOWED_CREATE_LABELS"
            )


# ---------------------------------------------------------------------------
# register_to_database: input validation (no DB)
# ---------------------------------------------------------------------------

class TestRegisterToDatabaseValidation:
    """Test input validation without a real Neo4j connection."""

    def _make_mock_driver(self):
        mock_session = MagicMock()
        mock_session.__enter__ = MagicMock(return_value=mock_session)
        mock_session.__exit__ = MagicMock(return_value=False)
        mock_session.run = MagicMock(return_value=[])
        mock_driver = MagicMock()
        mock_driver.session = MagicMock(return_value=mock_session)
        return mock_driver

    def test_empty_graph_returns_success(self):
        from app.lib.db_operations import register_to_database
        mock_driver = self._make_mock_driver()
        with patch("app.lib.db_operations.get_driver", return_value=mock_driver):
            result = register_to_database({"nodes": [], "relationships": []})
        assert result["status"] == "success"
        assert result["registered_count"] == 0

    def test_missing_nodes_key_returns_success_with_zero(self):
        from app.lib.db_operations import register_to_database
        mock_driver = self._make_mock_driver()
        with patch("app.lib.db_operations.get_driver", return_value=mock_driver):
            result = register_to_database({})
        assert result["status"] == "success"

    def test_invalid_label_is_skipped(self):
        from app.lib.db_operations import register_to_database
        mock_driver = self._make_mock_driver()
        graph = {
            "nodes": [{"label": "INVALID_LABEL", "properties": {"name": "test"}}],
            "relationships": [],
        }
        with patch("app.lib.db_operations.get_driver", return_value=mock_driver):
            result = register_to_database(graph)
        assert result["status"] == "success"
        assert result["registered_count"] == 0

    def test_valid_client_node_is_registered(self):
        from app.lib.db_operations import register_to_database
        mock_driver = self._make_mock_driver()
        graph = {
            "nodes": [{"label": "Client", "properties": {"name": "田中太郎"}}],
            "relationships": [],
        }
        with patch("app.lib.db_operations.get_driver", return_value=mock_driver):
            result = register_to_database(graph)
        assert result["status"] == "success"
        assert result["registered_count"] >= 1
        assert result["client_name"] == "田中太郎"

    def test_result_contains_registered_types(self):
        from app.lib.db_operations import register_to_database
        mock_driver = self._make_mock_driver()
        graph = {
            "nodes": [{"label": "Client", "properties": {"name": "山田花子"}}],
            "relationships": [],
        }
        with patch("app.lib.db_operations.get_driver", return_value=mock_driver):
            result = register_to_database(graph)
        assert "registered_types" in result
        assert isinstance(result["registered_types"], list)

    def test_driver_error_returns_error_status(self):
        from app.lib.db_operations import register_to_database
        mock_driver = MagicMock()
        mock_driver.session.side_effect = Exception("Connection refused")
        graph = {
            "nodes": [{"label": "Client", "properties": {"name": "エラーテスト"}}],
            "relationships": [],
        }
        with patch("app.lib.db_operations.get_driver", return_value=mock_driver):
            result = register_to_database(graph)
        assert result["status"] == "error"
