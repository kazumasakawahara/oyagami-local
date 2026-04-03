import json, logging, re
import httpx
from app.config import settings
from app.lib.db_operations import run_query
from app.lib.model_manager import model_manager

logger = logging.getLogger(__name__)

CYPHER_SYSTEM_PROMPT = """あなたはNeo4jのCypherクエリ生成の専門家です。
ユーザーの自然言語リクエストを正確なCypherクエリに変換してください。

## Neo4jスキーマ
ノード: Client, Condition, NgAction, CarePreference, KeyPerson, Guardian, Hospital,
        Certificate, Supporter, SupportLog, Organization, ServiceProvider
リレーション: HAS_CONDITION, MUST_AVOID, REQUIRES, HAS_KEY_PERSON, HAS_LEGAL_REP,
             HAS_CERTIFICATE, TREATED_AT, LOGGED, ABOUT, FOLLOWS
プロパティ命名: camelCase (name, dob, riskLevel, nextRenewalDate, effectiveness)

## 出力形式（JSONのみ）
{"cypher": "MATCH (c:Client)...", "params": {"key": "value"}, "description": "クエリの説明"}

## ルール
- パラメータ化クエリを使用（$param形式）
- OPTIONAL MATCHを適切に使用
- LIMIT句を含める（デフォルト50件）
- 読み取りクエリのみ（MERGE/CREATE/DELETE禁止）
"""

async def generate_cypher(question: str) -> dict | None:
    """Generate Cypher from natural language. Returns {"cypher", "params", "description"} or None."""
    await model_manager.ensure_model(settings.cypher_model)
    try:
        async with httpx.AsyncClient(base_url=settings.ollama_base_url, timeout=120) as client:
            resp = await client.post("/api/chat", json={
                "model": settings.cypher_model,
                "messages": [
                    {"role": "system", "content": CYPHER_SYSTEM_PROMPT},
                    {"role": "user", "content": question},
                ],
                "stream": False, "options": {"temperature": 0},
            })
            resp.raise_for_status()
            content = resp.json()["message"]["content"]
            match = re.search(r"\{.*\}", content, re.DOTALL)
            if match:
                return json.loads(match.group())
    except Exception as e:
        logger.error(f"Cypher generation failed: {e}")
    return None

async def query_with_cypher(question: str) -> dict:
    """Generate Cypher, execute, return results."""
    cypher_data = await generate_cypher(question)
    if not cypher_data:
        return {"error": "Failed to generate Cypher query", "results": []}
    cypher = cypher_data.get("cypher", "")
    params = cypher_data.get("params", {})
    # Safety: reject write queries
    upper = cypher.upper()
    if any(kw in upper for kw in ["CREATE", "MERGE", "DELETE", "SET ", "REMOVE"]):
        return {"error": "Write queries are not allowed", "results": []}
    results = run_query(cypher, params)
    return {
        "cypher": cypher, "params": params,
        "description": cypher_data.get("description", ""),
        "results": results, "count": len(results),
    }
