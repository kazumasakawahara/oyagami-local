"""ModelManager — Ollama model lifecycle manager.

Memory budget: 128 GB
- Resident models (~14 GB total): always kept loaded with keep_alive="24h".
- Exclusive models: only ONE may be loaded at a time; switching automatically
  unloads the current one before loading the requested one.

Typical usage
-------------
    from app.lib.model_manager import model_manager

    await model_manager.initialize()          # on startup
    await model_manager.ensure_model(name)    # before each inference call
"""

from __future__ import annotations

import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Model sets
# ---------------------------------------------------------------------------

# Populated from settings in _build_singleton().
# Defaults here are only for standalone testing.
RESIDENT_MODELS: frozenset[str] = frozenset()
EXCLUSIVE_MODELS: frozenset[str] = frozenset()

# keep_alive values
_KEEP_ALIVE_RESIDENT = "24h"
_KEEP_ALIVE_EXCLUSIVE = "10m"
_KEEP_ALIVE_UNLOAD = 0  # Ollama interprets 0 as "unload immediately"

# Timeouts (seconds)
_TIMEOUT_LOAD = 300.0
_TIMEOUT_UNLOAD = 60.0
_TIMEOUT_STATUS = 10.0


# ---------------------------------------------------------------------------
# ModelManager
# ---------------------------------------------------------------------------


class ModelManager:
    """Manages Ollama model loading/unloading within a 128 GB memory budget."""

    def __init__(
        self,
        base_url: str,
        resident_models: frozenset[str] | None = None,
        exclusive_models: frozenset[str] | None = None,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._client = httpx.AsyncClient(base_url=self._base_url)
        self._resident = resident_models or RESIDENT_MODELS
        self._exclusive = exclusive_models or EXCLUSIVE_MODELS
        # Name of the currently loaded exclusive model (or None)
        self._current_exclusive: str | None = None

    # ------------------------------------------------------------------
    # Public query helpers
    # ------------------------------------------------------------------

    def is_resident(self, model: str) -> bool:
        """Return True if *model* belongs to the resident set."""
        return model in self._resident

    def needs_switch(self, model: str) -> bool:
        """Return True if loading *model* requires unloading the current exclusive.

        This is True only when:
        - *model* is an exclusive model, AND
        - a *different* exclusive model is currently loaded.
        """
        if model not in self._exclusive:
            return False
        if self._current_exclusive is None:
            return False
        return self._current_exclusive != model

    # ------------------------------------------------------------------
    # Async operations
    # ------------------------------------------------------------------

    async def ensure_model(self, model: str) -> None:
        """Ensure *model* is loaded and ready for inference.

        For exclusive models: unload current exclusive first (if different),
        then load the requested model.
        For resident models: just (re-)load with 24h keep_alive.
        """
        if model in self._exclusive:
            if self.needs_switch(model):
                logger.info(
                    "Switching exclusive model: %s → %s",
                    self._current_exclusive,
                    model,
                )
                await self.unload_model(self._current_exclusive)  # type: ignore[arg-type]
            await self._load_model(model, keep_alive=_KEEP_ALIVE_EXCLUSIVE)
            self._current_exclusive = model
        else:
            # Resident or unknown — just load / warm up
            await self._load_model(
                model,
                keep_alive=_KEEP_ALIVE_RESIDENT if model in self._resident else "10m",
            )

    async def unload_model(self, model: str) -> None:
        """Unload *model* from Ollama memory."""
        logger.info("Unloading model: %s", model)
        try:
            await self._client.post(
                "/api/generate",
                json={"model": model, "keep_alive": _KEEP_ALIVE_UNLOAD},
                timeout=_TIMEOUT_UNLOAD,
            )
        except Exception as e:
            logger.warning("Failed to unload model %s: %s", model, e)
        if self._current_exclusive == model:
            self._current_exclusive = None

    async def get_status(self) -> dict[str, Any]:
        """Return the current list of loaded models from Ollama /api/ps."""
        try:
            resp = await self._client.get("/api/ps", timeout=_TIMEOUT_STATUS)
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            logger.warning("Failed to get Ollama status: %s", e)
            return {"models": []}

    async def initialize(self) -> None:
        """Load all resident models at startup (best-effort)."""
        logger.info("Initializing ModelManager — loading resident models")
        for model in self._resident:
            try:
                logger.info("Loading resident model: %s", model)
                await self._load_model(model, keep_alive=_KEEP_ALIVE_RESIDENT)
                logger.info("Resident model loaded: %s", model)
            except Exception as e:
                logger.warning(
                    "Failed to load resident model %s: %s. "
                    "Run 'ollama pull %s' to install it.",
                    model, e, model,
                )
        logger.info("ModelManager initialization complete")

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _load_model(self, model: str, keep_alive: str | int) -> None:
        """Warm-up a model by sending a trivial generate request."""
        resp = await self._client.post(
            "/api/generate",
            json={
                "model": model,
                "prompt": "ready",
                "keep_alive": keep_alive,
                "stream": False,
            },
            timeout=_TIMEOUT_LOAD,
        )
        resp.raise_for_status()


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------

def _build_singleton() -> ModelManager:
    """Construct the singleton from application settings."""
    try:
        from app.config import settings  # lazy import to keep module testable standalone

        resident = frozenset([settings.coordinator_model, settings.embedding_model])
        exclusive = frozenset([
            settings.intake_model,
            settings.analyst_model,
            settings.cypher_model,
        ])
        return ModelManager(
            base_url=settings.ollama_base_url,
            resident_models=resident,
            exclusive_models=exclusive,
        )
    except Exception:  # pragma: no cover
        logger.warning(
            "Could not import app.config.settings; using default Ollama URL"
        )
        return ModelManager(base_url="http://localhost:11434")


model_manager: ModelManager = _build_singleton()
