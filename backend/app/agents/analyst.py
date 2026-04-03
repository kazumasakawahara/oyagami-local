import logging
import httpx
from app.config import settings
from app.lib.model_manager import model_manager

logger = logging.getLogger(__name__)

ANALYST_SYSTEM_PROMPT = """あなたは障害福祉支援の専門アナリストです。
グラフデータベースから取得した支援データを分析し、支援方針を策定します。

## 分析の観点
1. 支援記録の傾向分析（effectiveness の推移、situation の分布）
2. リスク評価（NgAction の重要度と頻度）
3. ケアの改善提案（CarePreference の見直し）
4. 類似事例との比較分析
5. 親の機能移行の進捗確認

## 出力ルール
- 日本語で回答
- 根拠となるデータを引用
- 具体的なアクション提案を含める
- 安全に関する警告は最優先で表示
"""

async def analyze(question: str, context_data: list[dict]) -> str:
    """Analyze data and provide support insights."""
    await model_manager.ensure_model(settings.analyst_model)
    context_str = "\n".join([f"- {str(record)}" for record in context_data[:20]])
    try:
        async with httpx.AsyncClient(base_url=settings.ollama_base_url, timeout=300) as client:
            resp = await client.post("/api/chat", json={
                "model": settings.analyst_model,
                "messages": [
                    {"role": "system", "content": ANALYST_SYSTEM_PROMPT},
                    {"role": "user", "content": f"## 質問\n{question}\n\n## データ\n{context_str}"},
                ],
                "stream": False, "options": {"temperature": 0.3},
            })
            resp.raise_for_status()
            return resp.json()["message"]["content"]
    except Exception as e:
        logger.error(f"Analysis failed: {e}")
        return f"分析中にエラーが発生しました: {e}"
