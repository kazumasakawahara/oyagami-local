import json
import logging
import re

import httpx

from app.config import settings
from app.schemas.agent import IntentCategory, RoutingDecision

logger = logging.getLogger(__name__)

EMERGENCY_KEYWORDS = {"パニック", "SOS", "事故", "発作", "倒れた", "救急", "助けて", "緊急"}
REGISTRATION_KEYWORDS = {"登録", "記録して", "入力", "保存して", "記載して"}
ANALYSIS_KEYWORDS = {"分析", "比較", "方針", "傾向", "なぜ", "考察", "評価"}
# Use specific phrases to avoid false positives (e.g. "使い方を教えて" should be GENERAL)
QUERY_KEYWORDS = {"一覧を教えて", "検索", "確認して", "見せて", "表示", "リストを", "を教えて", "について教えて"}

GENERAL_PATTERNS = {"こんにちは", "おはよう", "ありがとう", "使い方", "ヘルプ", "help", "Hello", "hello"}

ROUTING_MAP = {
    IntentCategory.EMERGENCY: ("direct_db", None),
    IntentCategory.DATA_REGISTRATION: ("intake", settings.intake_model),
    IntentCategory.QUERY: ("cypher_gen", settings.cypher_model),
    IntentCategory.ANALYSIS: ("analyst", settings.analyst_model),
    IntentCategory.GENERAL: ("self", None),
}

COORDINATOR_SYSTEM_PROMPT = """あなたはユーザーの意図を分類するルーティングエージェントです。
以下の5つのカテゴリから最も適切なものを1つ選び、JSONで回答してください。

カテゴリ:
- emergency: 緊急事態（パニック、事故、SOS、発作、救急）
- data_registration: データの登録・記録の依頼
- query: 情報の検索・一覧表示・確認
- analysis: 分析・比較・方針策定・傾向分析
- general: 挨拶、ヘルプ、雑談

出力形式（JSONのみ）:
{"intent": "カテゴリ名", "reason": "判定理由（10文字以内）"}
"""


def classify_intent(text: str) -> RoutingDecision:
    """Classify user intent using keyword matching (fast, no LLM)."""
    # Emergency check first (safety-critical)
    if any(kw in text for kw in EMERGENCY_KEYWORDS):
        return _build_decision(IntentCategory.EMERGENCY, "緊急キーワード検知")
    # General patterns take priority over query to avoid false positives
    if any(kw in text for kw in GENERAL_PATTERNS):
        return _build_decision(IntentCategory.GENERAL, "一般的な発言")
    if any(kw in text for kw in REGISTRATION_KEYWORDS):
        return _build_decision(IntentCategory.DATA_REGISTRATION, "登録キーワード検知")
    if any(kw in text for kw in ANALYSIS_KEYWORDS):
        return _build_decision(IntentCategory.ANALYSIS, "分析キーワード検知")
    if any(kw in text for kw in QUERY_KEYWORDS):
        return _build_decision(IntentCategory.QUERY, "検索キーワード検知")
    return _build_decision(IntentCategory.GENERAL, "一般的な発言")


async def route_with_llm(text: str) -> RoutingDecision:
    """Classify user intent using mistral-small LLM."""
    # Emergency always uses keyword check (speed critical)
    if any(kw in text for kw in EMERGENCY_KEYWORDS):
        return _build_decision(IntentCategory.EMERGENCY, "緊急キーワード検知")

    try:
        async with httpx.AsyncClient(base_url=settings.ollama_base_url, timeout=30) as client:
            resp = await client.post("/api/chat", json={
                "model": settings.coordinator_model,
                "messages": [
                    {"role": "system", "content": COORDINATOR_SYSTEM_PROMPT},
                    {"role": "user", "content": text},
                ],
                "stream": False,
                "options": {"temperature": 0},
            })
            resp.raise_for_status()
            content = resp.json()["message"]["content"]
            match = re.search(r"\{[^}]+\}", content)
            if match:
                data = json.loads(match.group())
                intent = IntentCategory(data["intent"])
                reason = data.get("reason", "LLM分類")
                return _build_decision(intent, reason)
    except Exception as e:
        logger.warning(f"LLM routing failed, falling back to keywords: {e}")

    return classify_intent(text)


def _build_decision(intent: IntentCategory, reason: str) -> RoutingDecision:
    target_agent, target_model = ROUTING_MAP[intent]
    return RoutingDecision(
        intent=intent,
        target_agent=target_agent,
        reason=reason,
        requires_model_switch=target_model is not None,
        target_model=target_model,
    )
