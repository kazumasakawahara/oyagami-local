from fastapi import APIRouter, Query

from app.lib.db_operations import run_query

router = APIRouter(prefix="/api/search", tags=["search"])


@router.get("/fulltext")
async def fulltext_search(q: str = Query(...), limit: int = Query(20)):
    records = run_query(
        """
        CALL db.index.fulltext.queryNodes('idx_supportlog_fulltext', $query)
        YIELD node, score
        OPTIONAL MATCH (node)-[:ABOUT]->(c:Client)
        RETURN node.date AS date, node.note AS note, node.situation AS situation,
               c.name AS client_name, score
        ORDER BY score DESC LIMIT $limit
        """,
        {"query": q, "limit": limit},
    )
    return records
