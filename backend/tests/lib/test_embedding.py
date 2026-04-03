"""Unit tests for the embedding module — no Ollama or Neo4j needed (all external calls are mocked)."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import httpx

from app.lib.embedding import (
    DEFAULT_DIMENSIONS,
    VECTOR_INDEXES,
    embed_text,
    embed_texts_batch,
    semantic_search,
    ensure_vector_indexes,
)


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

class TestConstants:
    def test_default_dimensions(self):
        assert DEFAULT_DIMENSIONS == 768

    def test_vector_indexes_defined(self):
        assert "support_log_embedding" in VECTOR_INDEXES
        assert "ng_action_embedding" in VECTOR_INDEXES
        assert "client_summary_embedding" in VECTOR_INDEXES

    def test_all_expected_indexes_present(self):
        expected = {
            "support_log_embedding",
            "care_preference_embedding",
            "ng_action_embedding",
            "client_summary_embedding",
            "meeting_record_embedding",
            "meeting_record_text_embedding",
        }
        assert expected == set(VECTOR_INDEXES.keys())

    def test_vector_index_structure(self):
        idx = VECTOR_INDEXES["support_log_embedding"]
        assert idx["label"] == "SupportLog"
        assert idx["property"] == "embedding"
        assert idx["dimensions"] == 768

    def test_care_preference_index_structure(self):
        idx = VECTOR_INDEXES["care_preference_embedding"]
        assert idx["label"] == "CarePreference"
        assert idx["property"] == "embedding"
        assert idx["dimensions"] == 768

    def test_ng_action_index_structure(self):
        idx = VECTOR_INDEXES["ng_action_embedding"]
        assert idx["label"] == "NgAction"
        assert idx["property"] == "embedding"
        assert idx["dimensions"] == 768

    def test_client_summary_index_structure(self):
        idx = VECTOR_INDEXES["client_summary_embedding"]
        assert idx["label"] == "Client"
        assert idx["property"] == "summaryEmbedding"
        assert idx["dimensions"] == 768

    def test_meeting_record_embedding_structure(self):
        idx = VECTOR_INDEXES["meeting_record_embedding"]
        assert idx["label"] == "MeetingRecord"
        assert idx["property"] == "embedding"
        assert idx["dimensions"] == 768

    def test_meeting_record_text_embedding_structure(self):
        idx = VECTOR_INDEXES["meeting_record_text_embedding"]
        assert idx["label"] == "MeetingRecord"
        assert idx["property"] == "textEmbedding"
        assert idx["dimensions"] == 768


# ---------------------------------------------------------------------------
# embed_text
# ---------------------------------------------------------------------------

class TestEmbedText:
    @pytest.mark.asyncio
    async def test_returns_embedding_on_success(self):
        fake_vector = [0.1] * 768
        fake_response = MagicMock(spec=httpx.Response)
        fake_response.raise_for_status = MagicMock()
        fake_response.json = MagicMock(return_value={"embeddings": [fake_vector]})

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client.post = AsyncMock(return_value=fake_response)
            mock_client_cls.return_value = mock_client

            result = await embed_text("テストテキスト")

        assert result == fake_vector
        assert len(result) == 768

    @pytest.mark.asyncio
    async def test_returns_none_on_http_error(self):
        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client.post = AsyncMock(
                side_effect=httpx.HTTPError("connection refused")
            )
            mock_client_cls.return_value = mock_client

            result = await embed_text("テストテキスト")

        assert result is None

    @pytest.mark.asyncio
    async def test_returns_none_on_empty_text(self):
        result = await embed_text("")
        assert result is None

    @pytest.mark.asyncio
    async def test_posts_to_correct_endpoint(self):
        fake_vector = [0.0] * 768
        fake_response = MagicMock(spec=httpx.Response)
        fake_response.raise_for_status = MagicMock()
        fake_response.json = MagicMock(return_value={"embeddings": [fake_vector]})

        captured_calls: list[dict] = []

        async def fake_post(url, **kwargs):
            captured_calls.append({"url": url, "json": kwargs.get("json", {})})
            return fake_response

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client.post = AsyncMock(side_effect=fake_post)
            mock_client_cls.return_value = mock_client

            await embed_text("hello")

        assert len(captured_calls) == 1
        call = captured_calls[0]
        assert "/api/embed" in call["url"]
        assert call["json"]["input"] == "hello"


# ---------------------------------------------------------------------------
# embed_texts_batch
# ---------------------------------------------------------------------------

class TestEmbedTextsBatch:
    @pytest.mark.asyncio
    async def test_returns_list_of_same_length(self):
        texts = ["テキスト1", "テキスト2", "テキスト3"]
        fake_vector = [0.1] * 768

        async def fake_embed(text: str):
            return fake_vector if text else None

        with patch("app.lib.embedding.embed_text", side_effect=fake_embed):
            results = await embed_texts_batch(texts)

        assert len(results) == len(texts)

    @pytest.mark.asyncio
    async def test_none_for_failed_embeddings(self):
        texts = ["OK", ""]

        async def fake_embed(text: str):
            return [0.1] * 768 if text else None

        with patch("app.lib.embedding.embed_text", side_effect=fake_embed):
            results = await embed_texts_batch(texts)

        assert results[0] is not None
        assert results[1] is None

    @pytest.mark.asyncio
    async def test_empty_list_returns_empty(self):
        results = await embed_texts_batch([])
        assert results == []


# ---------------------------------------------------------------------------
# semantic_search
# ---------------------------------------------------------------------------

class TestSemanticSearch:
    @pytest.mark.asyncio
    async def test_returns_results_from_neo4j(self):
        fake_rows = [
            {"node": {"name": "利用者A"}, "score": 0.95},
            {"node": {"name": "利用者B"}, "score": 0.87},
        ]

        with patch("app.lib.embedding.run_query", return_value=fake_rows):
            results = await semantic_search(
                query_embedding=[0.1] * 768,
                index_name="support_log_embedding",
                top_k=5,
            )

        assert len(results) == 2
        assert results[0]["score"] == 0.95

    @pytest.mark.asyncio
    async def test_uses_correct_index_name(self):
        captured: list[dict] = []

        def fake_run_query(cypher, params=None):
            captured.append({"cypher": cypher, "params": params or {}})
            return []

        with patch("app.lib.embedding.run_query", side_effect=fake_run_query):
            await semantic_search(
                query_embedding=[0.0] * 768,
                index_name="ng_action_embedding",
                top_k=3,
            )

        assert len(captured) == 1
        # index_name is passed as a query parameter, not interpolated into the Cypher string
        assert captured[0]["params"].get("index_name") == "ng_action_embedding"

    @pytest.mark.asyncio
    async def test_returns_empty_list_on_no_results(self):
        with patch("app.lib.embedding.run_query", return_value=[]):
            results = await semantic_search(
                query_embedding=[0.1] * 768,
                index_name="care_preference_embedding",
                top_k=5,
            )

        assert results == []


# ---------------------------------------------------------------------------
# ensure_vector_indexes
# ---------------------------------------------------------------------------

class TestEnsureVectorIndexes:
    @pytest.mark.asyncio
    async def test_creates_all_indexes(self):
        call_count = 0

        def fake_run_query(cypher, params=None):
            nonlocal call_count
            call_count += 1
            return []

        with patch("app.lib.embedding.run_query", side_effect=fake_run_query):
            await ensure_vector_indexes()

        # Should call run_query at least once per index defined in VECTOR_INDEXES
        assert call_count >= len(VECTOR_INDEXES)

    @pytest.mark.asyncio
    async def test_idempotent_on_existing_index_error(self):
        """ensure_vector_indexes must not raise if index already exists."""
        def fake_run_query(cypher, params=None):
            raise Exception("Index already exists")

        with patch("app.lib.embedding.run_query", side_effect=fake_run_query):
            # Should not raise
            await ensure_vector_indexes()
