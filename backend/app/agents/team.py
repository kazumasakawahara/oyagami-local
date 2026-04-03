import json, logging, re
from app.agents.analyst import analyze
from app.agents.coordinator import route_with_llm
from app.agents.cypher_gen import query_with_cypher
from app.agents.intake import extract_from_text
from app.agents.validator import check_safety_compliance, validate_schema
from app.lib.db_operations import run_query
from app.schemas.agent import IntentCategory, RoutingDecision

logger = logging.getLogger(__name__)

async def process_message(text: str, session_id: str | None = None) -> dict:
    """Main entry: route user message to appropriate agent(s).
    Returns: {"routing": RoutingDecision, "response": str, "metadata": dict}
    """
    decision = await route_with_llm(text)
    metadata = {"agents_used": [decision.target_agent], "model_switches": 0}

    if decision.intent == IntentCategory.EMERGENCY:
        response = await _handle_emergency(text)
    elif decision.intent == IntentCategory.DATA_REGISTRATION:
        response = await _handle_registration(text)
        metadata["model_switches"] = 1
    elif decision.intent == IntentCategory.QUERY:
        response = await _handle_query(text)
        metadata["model_switches"] = 1
        metadata["agents_used"].append("cypher_gen")
    elif decision.intent == IntentCategory.ANALYSIS:
        response = await _handle_analysis(text)
        metadata["model_switches"] = 2
        metadata["agents_used"].extend(["analyst", "cypher_gen"])
    else:
        response = "何かお手伝いできることはありますか？支援記録の登録、クライアント情報の検索、支援傾向の分析などが可能です。"

    return {"routing": decision, "response": response, "metadata": metadata}

async def _handle_emergency(text: str) -> str:
    """Safety First: direct DB search, no LLM."""
    name_match = re.search(r"([一-龯]{2,4})\s?さん", text)
    if not name_match:
        return "クライアント名を特定できません。「〇〇さんの緊急情報」のように指定してください。"
    client_name = name_match.group(1)
    records = run_query("""
        MATCH (c:Client {name: $name})
        OPTIONAL MATCH (c)-[:MUST_AVOID]->(ng:NgAction)
        OPTIONAL MATCH (c)-[:REQUIRES]->(cp:CarePreference)
        OPTIONAL MATCH (c)-[:HAS_KEY_PERSON]->(kp:KeyPerson)
        OPTIONAL MATCH (c)-[:TREATED_AT]->(h:Hospital)
        OPTIONAL MATCH (c)-[:HAS_LEGAL_REP]->(g:Guardian)
        RETURN c, collect(DISTINCT ng) AS ng_actions,
               collect(DISTINCT cp) AS care_prefs,
               collect(DISTINCT kp) AS key_persons, h, g
    """, {"name": client_name})
    if not records:
        return f"「{client_name}」さんの情報が見つかりません。"
    r = records[0]
    parts = [f"## {client_name}さんの緊急情報\n"]
    ng_actions = r.get("ng_actions", [])
    if ng_actions:
        parts.append("### 禁忌事項（最優先）")
        for ng in ng_actions:
            ng = dict(ng)
            parts.append(f"- **{ng.get('action', '')}** [{ng.get('riskLevel', '')}]: {ng.get('reason', '')}")
    care_prefs = r.get("care_prefs", [])
    if care_prefs:
        parts.append("\n### 推奨ケア")
        for cp in care_prefs:
            cp = dict(cp)
            parts.append(f"- {cp.get('category', '')}: {cp.get('instruction', '')}")
    key_persons = r.get("key_persons", [])
    if key_persons:
        parts.append("\n### 緊急連絡先")
        for kp in key_persons:
            kp = dict(kp)
            parts.append(f"- {kp.get('name', '')} ({kp.get('relationship', '')}): {kp.get('phone', 'N/A')}")
    return "\n".join(parts)

async def _handle_registration(text: str) -> str:
    extracted = await extract_from_text(text)
    if not extracted:
        return "テキストからデータを抽出できませんでした。入力内容を確認してください。"
    validation = validate_schema(extracted)
    if not validation.is_valid:
        return f"抽出データにエラーがあります:\n" + "\n".join(validation.errors)
    preview = json.dumps(extracted, ensure_ascii=False, indent=2)
    node_count = len(extracted.get("nodes", []))
    rel_count = len(extracted.get("relationships", []))
    return f"以下のデータを抽出しました（ノード{node_count}件、リレーション{rel_count}件）。\n登録画面で確認・承認してください。\n\n```json\n{preview}\n```"

async def _handle_query(text: str) -> str:
    result = await query_with_cypher(text)
    if "error" in result:
        return f"クエリの生成に失敗しました: {result['error']}"
    results_str = json.dumps(result["results"][:10], ensure_ascii=False, indent=2)
    return f"{result.get('description', '')}\n\n結果（{result['count']}件）:\n```json\n{results_str}\n```"

async def _handle_analysis(text: str) -> str:
    query_result = await query_with_cypher(text)
    data = query_result.get("results", [])
    if not data:
        return "分析に必要なデータが見つかりませんでした。質問を具体的にしてください。"
    return await analyze(text, data)
