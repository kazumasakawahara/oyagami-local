import pytest
from app.agents.coordinator import classify_intent
from app.schemas.agent import IntentCategory


@pytest.mark.parametrize("text,expected", [
    ("田中さんがパニックを起こしている", IntentCategory.EMERGENCY),
    ("SOS 助けて", IntentCategory.EMERGENCY),
    ("昨日の通所の様子を記録して", IntentCategory.DATA_REGISTRATION),
    ("以下の内容を登録してください", IntentCategory.DATA_REGISTRATION),
    ("佐藤さんの禁忌事項の一覧を教えて", IntentCategory.QUERY),
    ("クライアント一覧を見せて", IntentCategory.QUERY),
    ("最近の支援傾向を分析して", IntentCategory.ANALYSIS),
    ("田中さんと佐藤さんを比較して", IntentCategory.ANALYSIS),
    ("こんにちは", IntentCategory.GENERAL),
    ("使い方を教えて", IntentCategory.GENERAL),
])
def test_classify_intent_keyword_fallback(text, expected):
    result = classify_intent(text)
    assert result.intent == expected
