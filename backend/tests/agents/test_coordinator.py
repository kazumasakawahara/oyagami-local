import pytest
from app.agents.coordinator import classify_intent
from app.schemas.agent import IntentCategory


@pytest.mark.parametrize("text,expected", [
    # 現在進行中の危機 → EMERGENCY
    ("助けて！田中さんが倒れた", IntentCategory.EMERGENCY),
    ("SOS 山田健太", IntentCategory.EMERGENCY),
    ("田中さんがパニック中です", IntentCategory.EMERGENCY),
    # 情報照会 → QUERY（Safety First を発動しない）
    ("緊急連絡先を教えてください", IntentCategory.QUERY),
    ("山田健太さんの禁忌事項を調べて", IntentCategory.QUERY),
    # データ登録
    ("昨日の通所の様子を記録して", IntentCategory.DATA_REGISTRATION),
    ("以下の内容を登録してください", IntentCategory.DATA_REGISTRATION),
    # 検索
    ("佐藤さんの禁忌事項の一覧を教えて", IntentCategory.QUERY),
    ("クライアント一覧を見せて", IntentCategory.QUERY),
    # 分析
    ("最近の支援傾向を分析して", IntentCategory.ANALYSIS),
    ("田中さんと佐藤さんを比較して", IntentCategory.ANALYSIS),
    # 一般
    ("こんにちは", IntentCategory.GENERAL),
    ("使い方を教えて", IntentCategory.GENERAL),
])
def test_classify_intent_keyword_fallback(text, expected):
    result = classify_intent(text)
    assert result.intent == expected
