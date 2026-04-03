"""Intake Agent — text-to-JSON extraction using deepseek-r1:70b via Ollama."""

import json
import logging
import re
from pathlib import Path

import httpx

from app.config import settings
from app.lib.model_manager import model_manager

logger = logging.getLogger(__name__)
PROMPT_DIR = Path(__file__).parent / "prompts"


def get_extraction_prompt() -> str:
    """Load extraction prompt from file."""
    return (PROMPT_DIR / "extraction.md").read_text(encoding="utf-8")


def parse_json_from_response(response_text: str) -> dict | None:
    """Extract JSON from LLM response, handling markdown code blocks."""
    # Try direct parse
    try:
        return json.loads(response_text)
    except json.JSONDecodeError:
        pass
    # Try ```json ... ``` block
    match = re.search(r"```(?:json)?\s*\n?(.*?)\n?```", response_text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            pass
    # Try finding first { ... } block
    match = re.search(r"\{.*\}", response_text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass
    return None


async def extract_from_text(text: str, client_name: str | None = None) -> dict | None:
    """Extract structured graph data from narrative text using deepseek-r1:70b."""
    await model_manager.ensure_model(settings.intake_model)
    prompt = get_extraction_prompt()
    user_message = text
    if client_name:
        user_message = f"【対象クライアント: {client_name}】\n\n{text}"
    try:
        async with httpx.AsyncClient(base_url=settings.ollama_base_url, timeout=300) as client:
            resp = await client.post(
                "/api/chat",
                json={
                    "model": settings.intake_model,
                    "messages": [
                        {"role": "system", "content": prompt},
                        {"role": "user", "content": user_message},
                    ],
                    "stream": False,
                    "options": {"temperature": 0},
                },
            )
            resp.raise_for_status()
            content = resp.json()["message"]["content"]
            return parse_json_from_response(content)
    except Exception as e:
        logger.error(f"Extraction failed: {e}")
        return None
