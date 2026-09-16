from app import scraper


def test_parse_payload():
    payload = {
        "list": [
            {"prodName": "番茄", "avgPrice": 1.5},
            {"prodName": "土豆", "avgPrice": "0.85"},
            {"prodName": "", "avgPrice": 1.0},        # 空名 → 跳过
            {"prodName": "坏数据", "avgPrice": None},  # 空价 → 跳过
            {"prodName": "烂数据", "avgPrice": "abc"},  # 非数字 → 跳过
        ]
    }
    rows = scraper.parse_payload(payload)
    assert len(rows) == 2
    assert rows[0]["food"] == "番茄"
    assert rows[0]["price"] == 1.5
    assert rows[1]["price"] == 0.85


def test_alias_mapping():
    assert "番茄" in scraper.FOOD_ALIASES["西红柿"]
    assert "白条猪" in scraper.FOOD_ALIASES["猪肉"]
