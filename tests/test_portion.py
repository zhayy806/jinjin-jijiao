from app.services import portion


def test_to_grams():
    assert portion.to_grams(1, "斤") == 500
    assert portion.to_grams(1, "两") == 50
    assert portion.to_grams(300, "克") == 300


def test_convert_basic():
    r = portion.convert("猪肉", 300, "克")
    assert r["grams"] == 300
    assert r["jin"] == 0.6
    assert r["liang"] == 6.0
    assert r["price"] is None  # 无真实价时，不编造价格
    assert r["price_per_jin"] is None


def test_convert_real_price_override():
    r = portion.convert("猪肉", 300, "克", price_per_jin=7.25)
    assert r["price_per_jin"] == 7.25
    assert r["price"] == round(0.6 * 7.25, 1)


def test_convert_analogy():
    r = portion.convert("鸡蛋", 250, "克")  # 半斤 = 5 个鸡蛋
    assert "个鸡蛋" in r["analogy"]
    assert r["liang"] == 5.0


def test_grams_from():
    assert portion.grams_from("西红柿", 2, "个") == 300  # 2 个 × 150 克
    assert portion.grams_from("猪肉", 1, "斤") == 500
    assert portion.grams_from("猪肉", 100, "克") == 100
