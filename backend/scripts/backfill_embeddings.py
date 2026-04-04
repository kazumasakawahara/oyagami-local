"""Backfill embeddings for existing nodes that don't have them yet.

Usage:
    cd ~/Dev-Work/oyagami-local/backend
    uv run python scripts/backfill_embeddings.py
"""
import asyncio
import sys
from pathlib import Path

# Add backend to path so we can import app modules
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.lib.db_operations import run_query
from app.lib.embedding import embed_text

TARGETS = [
    ("SupportLog", "embedding", "note"),
    ("NgAction", "embedding", "action"),
    ("CarePreference", "embedding", "instruction"),
]


async def backfill():
    total_processed = 0
    for label, prop, text_field in TARGETS:
        records = run_query(
            f"MATCH (n:{label}) WHERE n.{prop} IS NULL AND n.{text_field} IS NOT NULL "
            f"RETURN elementId(n) AS eid, n.{text_field} AS text LIMIT 100"
        )
        print(f"\n{label}: {len(records)} nodes to backfill")

        for i, r in enumerate(records):
            embedding = await embed_text(r["text"])
            if embedding:
                run_query(
                    f"MATCH (n) WHERE elementId(n) = $eid SET n.{prop} = $emb",
                    {"eid": r["eid"], "emb": embedding},
                )
                print(f"  [{i+1}/{len(records)}] Embedded: {r['text'][:50]}...")
                total_processed += 1
            else:
                print(f"  [{i+1}/{len(records)}] SKIP (embedding failed): {r['text'][:50]}...")

        print(f"{label}: done")

    print(f"\nTotal processed: {total_processed} nodes")


if __name__ == "__main__":
    print("=== Embedding Backfill ===")
    print("Ensure Ollama is running with nomic-embed-text loaded.")
    asyncio.run(backfill())
    print("=== Complete ===")
