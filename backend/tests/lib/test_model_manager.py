"""Unit tests for ModelManager — no Ollama needed (all HTTP calls are mocked)."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import httpx

from app.lib.model_manager import ModelManager, RESIDENT_MODELS, EXCLUSIVE_MODELS


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_TEST_RESIDENT = frozenset(["mistral-small:latest", "nomic-embed-text"])
_TEST_EXCLUSIVE = frozenset(["deepseek-r1:70b", "llama4:latest", "qwen3-coder:30b"])


def _make_manager() -> ModelManager:
    """Return a fresh ModelManager pointed at a fake Ollama URL."""
    return ModelManager(
        base_url="http://fake-ollama:11434",
        resident_models=_TEST_RESIDENT,
        exclusive_models=_TEST_EXCLUSIVE,
    )


# ---------------------------------------------------------------------------
# is_resident
# ---------------------------------------------------------------------------

class TestIsResident:
    def test_resident_model_always_available(self):
        mgr = _make_manager()
        for model in RESIDENT_MODELS:
            assert mgr.is_resident(model) is True

    def test_exclusive_model_is_not_resident(self):
        mgr = _make_manager()
        for model in EXCLUSIVE_MODELS:
            assert mgr.is_resident(model) is False

    def test_unknown_model_is_not_resident(self):
        mgr = _make_manager()
        assert mgr.is_resident("some-unknown-model") is False


# ---------------------------------------------------------------------------
# needs_switch
# ---------------------------------------------------------------------------

class TestNeedsSwitch:
    def test_needs_switch_when_different_exclusive(self):
        mgr = _make_manager()
        mgr._current_exclusive = "deepseek-r1:70b"
        assert mgr.needs_switch("llama4:latest") is True

    def test_no_switch_needed_for_same_exclusive(self):
        mgr = _make_manager()
        mgr._current_exclusive = "deepseek-r1:70b"
        assert mgr.needs_switch("deepseek-r1:70b") is False

    def test_no_switch_needed_when_none_loaded(self):
        mgr = _make_manager()
        assert mgr._current_exclusive is None
        assert mgr.needs_switch("deepseek-r1:70b") is False

    def test_no_switch_needed_for_resident_model(self):
        mgr = _make_manager()
        mgr._current_exclusive = "deepseek-r1:70b"
        # Resident models never require an exclusive switch
        for model in RESIDENT_MODELS:
            assert mgr.needs_switch(model) is False


# ---------------------------------------------------------------------------
# exclusive model tracking
# ---------------------------------------------------------------------------

class TestExclusiveModelTracking:
    @pytest.mark.asyncio
    async def test_exclusive_model_tracking_after_ensure(self):
        """ensure_model should update _current_exclusive for exclusive models."""
        mgr = _make_manager()

        async def fake_post(url, **kwargs):
            resp = MagicMock(spec=httpx.Response)
            resp.raise_for_status = MagicMock()
            return resp

        with patch.object(mgr._client, "post", side_effect=fake_post):
            await mgr.ensure_model("deepseek-r1:70b")

        assert mgr._current_exclusive == "deepseek-r1:70b"

    @pytest.mark.asyncio
    async def test_ensure_exclusive_unloads_previous(self):
        """ensure_model for a new exclusive should first unload the old one."""
        mgr = _make_manager()
        mgr._current_exclusive = "deepseek-r1:70b"

        post_calls: list[dict] = []

        async def fake_post(url, **kwargs):
            post_calls.append({"url": url, "json": kwargs.get("json", {})})
            resp = MagicMock(spec=httpx.Response)
            resp.raise_for_status = MagicMock()
            return resp

        with patch.object(mgr._client, "post", side_effect=fake_post):
            await mgr.ensure_model("llama4:latest")

        # First call must be an unload (keep_alive=0) for the old model
        assert len(post_calls) >= 2
        unload_call = post_calls[0]
        assert unload_call["json"].get("model") == "deepseek-r1:70b"
        assert unload_call["json"].get("keep_alive") == 0

        assert mgr._current_exclusive == "llama4:latest"

    @pytest.mark.asyncio
    async def test_ensure_resident_does_not_update_exclusive(self):
        """ensure_model for a resident model must NOT change _current_exclusive."""
        mgr = _make_manager()
        mgr._current_exclusive = "deepseek-r1:70b"

        async def fake_post(url, **kwargs):
            resp = MagicMock(spec=httpx.Response)
            resp.raise_for_status = MagicMock()
            return resp

        with patch.object(mgr._client, "post", side_effect=fake_post):
            await mgr.ensure_model("mistral-small:latest")

        # Exclusive tracking must be unchanged
        assert mgr._current_exclusive == "deepseek-r1:70b"

    @pytest.mark.asyncio
    async def test_exclusive_cleared_after_unload(self):
        """unload_model for the current exclusive should clear _current_exclusive."""
        mgr = _make_manager()
        mgr._current_exclusive = "deepseek-r1:70b"

        async def fake_post(url, **kwargs):
            resp = MagicMock(spec=httpx.Response)
            resp.raise_for_status = MagicMock()
            return resp

        with patch.object(mgr._client, "post", side_effect=fake_post):
            await mgr.unload_model("deepseek-r1:70b")

        assert mgr._current_exclusive is None


# ---------------------------------------------------------------------------
# get_status
# ---------------------------------------------------------------------------

class TestGetStatus:
    @pytest.mark.asyncio
    async def test_get_status_returns_model_list(self):
        mgr = _make_manager()

        fake_payload = {
            "models": [
                {"name": "mistral-small:latest", "size": 5_000_000_000},
                {"name": "nomic-embed-text:latest", "size": 274_000_000},
            ]
        }

        async def fake_get(url, **kwargs):
            resp = MagicMock(spec=httpx.Response)
            resp.raise_for_status = MagicMock()
            resp.json = MagicMock(return_value=fake_payload)
            return resp

        with patch.object(mgr._client, "get", side_effect=fake_get):
            status = await mgr.get_status()

        assert "models" in status
        assert len(status["models"]) == 2
        names = [m["name"] for m in status["models"]]
        assert "mistral-small:latest" in names


# ---------------------------------------------------------------------------
# initialize
# ---------------------------------------------------------------------------

class TestInitialize:
    @pytest.mark.asyncio
    async def test_initialize_loads_all_resident_models(self):
        mgr = _make_manager()
        loaded_models: list[str] = []

        async def fake_post(url, **kwargs):
            json_body = kwargs.get("json", {})
            loaded_models.append(json_body.get("model", ""))
            resp = MagicMock(spec=httpx.Response)
            resp.raise_for_status = MagicMock()
            return resp

        with patch.object(mgr._client, "post", side_effect=fake_post):
            await mgr.initialize()

        for model in RESIDENT_MODELS:
            assert model in loaded_models, f"{model} was not loaded during initialize()"
