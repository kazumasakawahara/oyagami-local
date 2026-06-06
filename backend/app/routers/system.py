"""System router — model status, load/unload operations."""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException

from app.lib.db_operations import is_db_available
from app.lib.model_manager import model_manager
from app.schemas.agent import ModelStatusResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/system", tags=["system"])


@router.get("/status", response_model=ModelStatusResponse)
async def get_status() -> ModelStatusResponse:
    """Ollama モデルの状態と Neo4j の接続状況を返す。"""
    neo4j_available = is_db_available()

    try:
        ps_data = await model_manager.get_status()
        loaded_models: list[str] = [m.get("name", "") for m in ps_data.get("models", [])]
        # Compute approximate memory usage (sum of size_vram fields in bytes → GB)
        total_bytes: int = sum(m.get("size_vram", 0) for m in ps_data.get("models", []))
        memory_usage_gb = round(total_bytes / (1024 ** 3), 2) if total_bytes else None
        ollama_available = True
    except Exception as exc:
        logger.warning("Ollama /api/ps unavailable: %s", exc)
        loaded_models = []
        memory_usage_gb = None
        ollama_available = False

    return ModelStatusResponse(
        ollama_available=ollama_available,
        neo4j_available=neo4j_available,
        loaded_models=loaded_models,
        current_exclusive=model_manager._current_exclusive,
        memory_usage_gb=memory_usage_gb,
    )


@router.post("/models/{model_name}/load")
async def load_model(model_name: str) -> dict:
    """指定したモデルを Ollama にロードする。"""
    if model_name not in model_manager.managed_models:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown model '{model_name}'. Managed models: {sorted(model_manager.managed_models)}",
        )
    try:
        await model_manager.ensure_model(model_name)
        return {"status": "loaded", "model": model_name}
    except Exception as exc:
        logger.error("load_model failed for %s: %s", model_name, exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/models/{model_name}/unload")
async def unload_model(model_name: str) -> dict:
    """指定したモデルを Ollama からアンロードする。"""
    if model_name not in model_manager.managed_models:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown model '{model_name}'. Managed models: {sorted(model_manager.managed_models)}",
        )
    try:
        await model_manager.unload_model(model_name)
        return {"status": "unloaded", "model": model_name}
    except Exception as exc:
        logger.error("unload_model failed for %s: %s", model_name, exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc)) from exc
