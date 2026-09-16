"""斤两可视化换算 —— 核心逻辑。

中国年轻人对「斤 / 两」没概念：菜谱写「猪肉 300 克」，
他们不知道那到底是多少。这里把抽象重量，翻译成
「几个拳头 / 几个鸡蛋 / 几碗饭」这种一眼就懂的说法。

价格由爬虫从新发地抓取后传入，这里不做任何硬编码价格。
"""

GRAM_PER_JIN = 500    # 1 斤 = 500 克
GRAM_PER_LIANG = 50   # 1 两 = 50 克（1 斤 = 10 两）

# 常见食材对照表
#   ref_noun    日常参照物（接在数字后面的量词 + 名词）
#   ref_grams   这个参照物大概多少克
#   food_emoji  食材本身的图标
#   ref_emoji   参照物的图标
FOODS = {
    "猪肉":   {"ref_noun": "个拳头",   "ref_grams": 250, "food_emoji": "🥩", "ref_emoji": "✊"},
    "牛肉":   {"ref_noun": "个拳头",   "ref_grams": 250, "food_emoji": "🥩", "ref_emoji": "✊"},
    "鸡胸肉": {"ref_noun": "个拳头",   "ref_grams": 250, "food_emoji": "🍗", "ref_emoji": "✊"},
    "排骨":   {"ref_noun": "根",       "ref_grams": 100, "food_emoji": "🍖", "ref_emoji": "🍖"},
    "鸡蛋":   {"ref_noun": "个鸡蛋",   "ref_grams": 50,  "food_emoji": "🥚", "ref_emoji": "🥚"},
    "西红柿": {"ref_noun": "个西红柿", "ref_grams": 150, "food_emoji": "🍅", "ref_emoji": "🍅"},
    "土豆":   {"ref_noun": "个土豆",   "ref_grams": 150, "food_emoji": "🥔", "ref_emoji": "🥔"},
    "苹果":   {"ref_noun": "个苹果",   "ref_grams": 200, "food_emoji": "🍎", "ref_emoji": "🍎"},
    "青菜":   {"ref_noun": "把",       "ref_grams": 300, "food_emoji": "🥬", "ref_emoji": "🥬"},
    "大米":   {"ref_noun": "碗米饭",   "ref_grams": 180, "food_emoji": "🍚", "ref_emoji": "🍚"},
    "面粉":   {"ref_noun": "碗面粉",   "ref_grams": 150, "food_emoji": "🌾", "ref_emoji": "🥣"},
    "菌菇":   {"ref_noun": "把",       "ref_grams": 300, "food_emoji": "🍄", "ref_emoji": "🍄"},
}

UNITS = {"克": 1, "两": GRAM_PER_LIANG, "斤": GRAM_PER_JIN}


def to_grams(amount: float, unit: str) -> float:
    """把任意单位换算成克。"""
    return amount * UNITS[unit]


def convert(food: str, amount: float, unit: str, price_per_jin: float = None) -> dict:
    """完整换算：斤两 + 可视化。price_per_jin 为爬虫抓到的真实价，没有则为 None。"""
    info = FOODS[food]
    grams = to_grams(amount, unit)

    jin = grams / GRAM_PER_JIN
    liang = grams / GRAM_PER_LIANG
    count = grams / info["ref_grams"]
    price = round(grams / GRAM_PER_JIN * price_per_jin, 1) if price_per_jin else None

    return {
        "food": food,
        "input": f"{amount:g} {unit}",
        "grams": round(grams, 1),
        "jin": round(jin, 2),
        "liang": round(liang, 2),
        "analogy": f"≈ {count:.1f} {info['ref_noun']}",
        "price": price,
        "price_per_jin": price_per_jin,
    }
