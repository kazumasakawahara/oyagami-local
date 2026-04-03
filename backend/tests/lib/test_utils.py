"""
Tests for backend/app/lib/utils.py
"""

from datetime import date

import pytest

from app.lib.utils import (
    calculate_age,
    convert_wareki_to_seireki,
    format_date_with_age,
    safe_date_parse,
)


# =============================================================================
# convert_wareki_to_seireki
# =============================================================================

class TestConvertWarekiToSeireki:
    def test_wareki_showa(self):
        assert convert_wareki_to_seireki("昭和50年3月15日") == "1975-03-15"

    def test_wareki_reiwa(self):
        assert convert_wareki_to_seireki("令和5年1月10日") == "2023-01-10"

    def test_wareki_alpha(self):
        assert convert_wareki_to_seireki("S50.3.15") == "1975-03-15"

    def test_wareki_heisei_kanji(self):
        assert convert_wareki_to_seireki("平成7年12月1日") == "1995-12-01"

    def test_wareki_alpha_h(self):
        assert convert_wareki_to_seireki("H7.12.1") == "1995-12-01"

    def test_wareki_alpha_r(self):
        assert convert_wareki_to_seireki("R5.1.10") == "2023-01-10"

    def test_wareki_slash_separator(self):
        assert convert_wareki_to_seireki("昭和50/3/15") == "1975-03-15"

    def test_wareki_dash_separator(self):
        assert convert_wareki_to_seireki("昭和50-3-15") == "1975-03-15"

    def test_wareki_meiji(self):
        assert convert_wareki_to_seireki("明治45年7月1日") == "1912-07-01"

    def test_wareki_taisho(self):
        assert convert_wareki_to_seireki("大正14年5月10日") == "1925-05-10"

    def test_wareki_reiwa_year1(self):
        assert convert_wareki_to_seireki("令和1年5月1日") == "2019-05-01"

    def test_empty_string_returns_none(self):
        assert convert_wareki_to_seireki("") is None

    def test_none_returns_none(self):
        assert convert_wareki_to_seireki(None) is None

    def test_invalid_string_returns_none(self):
        assert convert_wareki_to_seireki("invalid") is None

    def test_seireki_string_returns_none(self):
        # 西暦はこの関数では変換できない
        assert convert_wareki_to_seireki("2026-04-04") is None

    def test_invalid_date_returns_none(self):
        # 存在しない日付
        assert convert_wareki_to_seireki("令和5年13月1日") is None

    def test_alpha_uppercase_insensitive(self):
        assert convert_wareki_to_seireki("s50.3.15") == "1975-03-15"


# =============================================================================
# safe_date_parse
# =============================================================================

class TestSafeDateParse:
    def test_iso_format(self):
        result = safe_date_parse("2026-04-04")
        assert result == date(2026, 4, 4)

    def test_slash_format(self):
        result = safe_date_parse("2026/04/04")
        assert result == date(2026, 4, 4)

    def test_wareki(self):
        result = safe_date_parse("令和8年4月4日")
        assert result == date(2026, 4, 4)

    def test_wareki_alpha(self):
        result = safe_date_parse("S50.3.15")
        assert result == date(1975, 3, 15)

    def test_empty_returns_none(self):
        assert safe_date_parse("") is None

    def test_none_returns_none(self):
        assert safe_date_parse(None) is None

    def test_invalid_returns_none(self):
        assert safe_date_parse("not-a-date") is None

    def test_strips_whitespace(self):
        result = safe_date_parse("  2026-04-04  ")
        assert result == date(2026, 4, 4)


# =============================================================================
# calculate_age
# =============================================================================

class TestCalculateAge:
    def test_basic_age(self):
        age = calculate_age("2000-01-01", reference_date=date(2026, 4, 4))
        assert age == 26

    def test_date_object_input(self):
        age = calculate_age(date(2000, 1, 1), reference_date=date(2026, 4, 4))
        assert age == 26

    def test_birthday_not_yet(self):
        # 誕生日前
        age = calculate_age("2000-12-31", reference_date=date(2026, 4, 4))
        assert age == 25

    def test_birthday_today(self):
        age = calculate_age("2000-04-04", reference_date=date(2026, 4, 4))
        assert age == 26

    def test_wareki_string(self):
        age = calculate_age("昭和50年3月15日", reference_date=date(2026, 4, 4))
        assert age == 51

    def test_none_returns_none(self):
        assert calculate_age(None) is None

    def test_invalid_string_returns_none(self):
        assert calculate_age("not-a-date") is None

    def test_future_birth_returns_none(self):
        # 未来生まれ → 負の年齢 → None
        age = calculate_age("2030-01-01", reference_date=date(2026, 4, 4))
        assert age is None


# =============================================================================
# format_date_with_age
# =============================================================================

class TestFormatDateWithAge:
    def test_date_object(self):
        result = format_date_with_age(date(2000, 1, 1))
        # 今日基準なので年齢は実行時によって変わるが形式確認
        assert "2000-01-01" in result
        assert "歳" in result

    def test_string_input(self):
        result = format_date_with_age("2000-01-01")
        assert "2000-01-01" in result
        assert "歳" in result

    def test_none_returns_fumu(self):
        assert format_date_with_age(None) == "不明"

    def test_invalid_string_returns_original(self):
        result = format_date_with_age("invalid-date")
        assert result == "invalid-date"
