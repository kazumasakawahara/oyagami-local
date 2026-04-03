"""Embedding module using Ollama nomic-embed-text.

Provides async helpers for:
- Generating text embeddings via Ollama /api/embed
- Batch embedding for multiple texts
- Semantic search against Neo4j vector indexes
- Idempotent creation of Neo4j vector indexes
"""

from __future__ import annotations

import logging
from typing import Any

import httpx

from app.config import settings
from app.lib.db_operations import run_query

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DEFAULT_DIMENSIONS = 768

VECTOR_INDEXES: dict[str, dict[str, Any]] = {
    "support_log_embedding": {
        "label": "SupportLog",
        "property": "embedding",
        "dimensions": 768,
    },
    "care_preference_embedding": {
        "label": "CarePreference",
        "property": "embedding",
        "dimensions": 768,
    },
    "ng_action_embedding": {
        "label": "NgAction",
        "property": "embedding",
        "dimensions": 768,
    },
    "client_summary_embedding": {
        "label": "Client",
        "property": "summaryEmbedding",
        "dimensions": 768,
    },
    "meeting_record_embedding": {
        "label": "MeetingRecord",
        "property": "embedding",
        "dimensions": 768,
    },
    "meeting_record_text_embedding": {
        "label": "MeetingRecord",
        "property": "textEmbedding",
        "dimensions": 768,
    },
}


# ---------------------------------------------------------------------------
# embed_text
# ---------------------------------------------------------------------------

async def embed_text(text: str) -> list[float] | None:
    """Embed a single text string using Ollama.

    Args:
        text: The text to embed. Returns None for empty strings.

    Returns:
        A 768-dimensional float vector, or None if embedding fails.
    """
    if not text:
        return None

    url = f"{settings.ollama_base_url}/api/embed"
    payload = {
        "model": settings.embedding_model,
        "input": text,
    }

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            data = response.json()
            embeddings = data.get("embeddings", [])
            if embeddings:
                return embeddings[0]
            logger.warning("embed_text: Ollama returned empty embeddings list for text: %.50s", text)
            return None
    except httpx.HTTPError as exc:
        logger.error("embed_text: HTTP error calling Ollama: %s", exc)
        return None
    except Exception as exc:
        logger.error("embed_text: Unexpected error: %s", exc)
        return None


# ---------------------------------------------------------------------------
# embed_texts_batch
# ---------------------------------------------------------------------------

async def embed_texts_batch(texts: list[str]) -> list[list[float] | None]:
    """Embed multiple texts, returning None for any that fail.

    Args:
        texts: List of texts to embed.

    Returns:
        List of float vectors (or None for failures), same length as input.
    """
    if not texts:
        return []

    results: list[list[float] | None] = []
    for text in texts:
        vector = await embed_text(text)
        results.append(vector)
    return results


# ---------------------------------------------------------------------------
# semantic_search
# ---------------------------------------------------------------------------

async def semantic_search(
    query_embedding: list[float],
    index_name: str,
    top_k: int = 5,
) -> list[dict]:
    """Search a Neo4j vector index for the most similar nodes.

    Args:
        query_embedding: The query vector.
        index_name: Name of the Neo4j vector index to search (must be in VECTOR_INDEXES).
        top_k: Number of results to return.

    Returns:
        List of dicts with 'node' and 'score' keys, ordered by descending similarity.
    """
    cypher = (
        f"CALL db.index.vector.queryNodes($index_name, $top_k, $embedding) "
        f"YIELD node, score "
        f"RETURN node, score "
        f"ORDER BY score DESC"
    )
    params: dict[str, Any] = {
        "index_name": index_name,
        "top_k": top_k,
        "embedding": query_embedding,
    }

    try:
        rows = run_query(cypher, params)
        return rows if rows else []
    except Exception as exc:
        logger.error("semantic_search: Neo4j error for index '%s': %s", index_name, exc)
        return []


# ---------------------------------------------------------------------------
# ensure_vector_indexes
# ---------------------------------------------------------------------------

async def ensure_vector_indexes() -> None:
    """Idempotently create all vector indexes defined in VECTOR_INDEXES.

    Safe to call multiple times — existing indexes will be silently skipped.
    """
    for index_name, config in VECTOR_INDEXES.items():
        cypher = (
            f"CREATE VECTOR INDEX {index_name} IF NOT EXISTS "
            f"FOR (n:{config['label']}) ON (n.{config['property']}) "
            f"OPTIONS {{indexConfig: {{`vector.dimensions`: {config['dimensions']}, "
            f"`vector.similarity_function`: 'cosine'}}}}"
        )
        try:
            run_query(cypher)
            logger.info("ensure_vector_indexes: index '%s' created or already exists.", index_name)
        except Exception as exc:
            logger.warning(
                "ensure_vector_indexes: could not create index '%s': %s",
                index_name,
                exc,
            )
