import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    """FastAPI test client with mocked external dependencies."""
    # Patch model_manager at the module level before importing app
    with patch("app.lib.model_manager.model_manager") as mock_mm:
        mock_mm.initialize = AsyncMock(return_value=None)
        mock_mm.get_status = AsyncMock(return_value={
            "models": [
                {
                    "name": "mistral-small:latest",
                    "size_vram": 0,
                }
            ]
        })
        mock_mm._current_exclusive = None

        from app.main import app
        with TestClient(app) as tc:
            yield tc
