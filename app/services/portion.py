"""斤两可视化换算 —— 核心逻辑。

中国年轻人对「斤 / 两」没概念：菜谱写「猪肉 300 克」，
他们不知道那到底是多少。这里把抽象重量，翻译成
「几个拳头 / 几个鸡蛋 / 几碗饭」这种一眼就懂的说法。

价格由爬虫从新发地抓取后传入，这里不做任何硬编码价格。
calories 为每 100 克的估算热量（大卡）。
"""

GRAM_PER_JIN = 500    # 1 斤 = 500 克
GRAM_PER_LIANG = 50   # 1 两 = 50 克（1 斤 = 10 两）

# 常见食材对照表
#   ref_noun    日常参照物（接在数字后面的量词 + 名词）
#   ref_grams   这个参照物大概多少克
#   food_emoji  食材本身的图标
#   ref_emoji   参照物的图标
#   calories    每 100 克估算热量（大卡）
FOODS = {
    "猪肉":   {"ref_noun": "个拳头",   "ref_grams": 250, "food_emoji": "🥩", "ref_emoji": "✊", "calories": 143},
    "牛肉":   {"ref_noun": "个拳头",   "ref_grams": 250, "food_emoji": "🥩", "ref_emoji": "✊", "calories": 125},
    "鸡胸肉": {"ref_noun": "个拳头",   "ref_grams": 250, "food_emoji": "🍗", "ref_emoji": "✊", "calories": 133},
    "排骨":   {"ref_noun": "根",       "ref_grams": 100, "food_emoji": "🍖", "ref_emoji": "🍖", "calories": 250},
    "鸡蛋":   {"ref_noun": "个鸡蛋",   "ref_grams": 50,  "food_emoji": "🥚", "ref_emoji": "🥚", "calories": 144},
    "西红柿": {"ref_noun": "个西红柿", "ref_grams": 150, "food_emoji": "🍅", "ref_emoji": "🍅", "calories": 18},
    "土豆":   {"ref_noun": "个土豆",   "ref_grams": 150, "food_emoji": "🥔", "ref_emoji": "🥔", "calories": 77},
    "苹果":   {"ref_noun": "个苹果",   "ref_grams": 200, "food_emoji": "🍎", "ref_emoji": "🍎", "calories": 52},
    "青菜":   {"ref_noun": "把",       "ref_grams": 300, "food_emoji": "🥬", "ref_emoji": "🥬", "calories": 20},
    "大米":   {"ref_noun": "碗米饭",   "ref_grams": 180, "food_emoji": "🍚", "ref_emoji": "🍚", "calories": 130},
    "面粉":   {"ref_noun": "碗面粉",   "ref_grams": 150, "food_emoji": "🌾", "ref_emoji": "🥣", "calories": 364},
    "菌菇":   {"ref_noun": "把",       "ref_grams": 300, "food_emoji": "🍄", "ref_emoji": "🍄", "calories": 22},
    "虾":     {"ref_noun": "只",       "ref_grams": 30,  "food_emoji": "🦐", "ref_emoji": "🦐", "calories": 99},
    "鱼":     {"ref_noun": "条",       "ref_grams": 500, "food_emoji": "🐟", "ref_emoji": "🐟", "calories": 100},
    "小龙虾": {"ref_noun": "只",       "ref_grams": 25,  "food_emoji": "🦞", "ref_emoji": "🦞", "calories": 90},
    "皮皮虾": {"ref_noun": "只",       "ref_grams": 30,  "food_emoji": "🦐", "ref_emoji": "🦐", "calories": 85},
    "豆腐":   {"ref_noun": "块",       "ref_grams": 200, "food_emoji": "🍲", "ref_emoji": "🍲", "calories": 76},
    "青椒":   {"ref_noun": "个",       "ref_grams": 60,  "food_emoji": "🫑", "ref_emoji": "🫑", "calories": 22},
    "洋葱":   {"ref_noun": "个",       "ref_grams": 150, "food_emoji": "🧅", "ref_emoji": "🧅", "calories": 40},
    "白菜":   {"ref_noun": "颗",       "ref_grams": 600, "food_emoji": "🥗", "ref_emoji": "🥗", "calories": 13},
    "黄瓜":   {"ref_noun": "根",       "ref_grams": 200, "food_emoji": "🥒", "ref_emoji": "🥒", "calories": 15},
    "茄子":   {"ref_noun": "个",       "ref_grams": 200, "food_emoji": "🍆", "ref_emoji": "🍆", "calories": 25},
    "韭菜":   {"ref_noun": "把",       "ref_grams": 200, "food_emoji": "🌿", "ref_emoji": "🌿", "calories": 25},
    "羊肉":   {"ref_noun": "个拳头",   "ref_grams": 250, "food_emoji": "🥩", "ref_emoji": "✊", "calories": 200},
    "胡萝卜": {"ref_noun": "根",       "ref_grams": 150, "food_emoji": "🥕", "ref_emoji": "🥕", "calories": 32},
    "白萝卜": {"ref_noun": "根",       "ref_grams": 400, "food_emoji": "🥕", "ref_emoji": "🥕", "calories": 18},
    "包菜":   {"ref_noun": "颗",       "ref_grams": 500, "food_emoji": "🥬", "ref_emoji": "🥬", "calories": 25},
    "芹菜":   {"ref_noun": "把",       "ref_grams": 300, "food_emoji": "🥬", "ref_emoji": "🥬", "calories": 16},
    "莴笋":   {"ref_noun": "根",       "ref_grams": 250, "food_emoji": "🥬", "ref_emoji": "🥬", "calories": 15},
    "西葫芦": {"ref_noun": "根",       "ref_grams": 300, "food_emoji": "🥒", "ref_emoji": "🥒", "calories": 19},
    "花菜":   {"ref_noun": "颗",       "ref_grams": 400, "food_emoji": "🥦", "ref_emoji": "🥦", "calories": 25},
    "木耳":   {"ref_noun": "把",       "ref_grams": 20,  "food_emoji": "🍄", "ref_emoji": "🍄", "calories": 265},
    "海鲜菇": {"ref_noun": "把",       "ref_grams": 300, "food_emoji": "🍄", "ref_emoji": "🍄", "calories": 30},
    "虾仁":   {"ref_noun": "把",       "ref_grams": 200, "food_emoji": "🍤", "ref_emoji": "🍤", "calories": 87},
    "鸡肉":   {"ref_noun": "个拳头",   "ref_grams": 250, "food_emoji": "🍗", "ref_emoji": "✊", "calories": 167},
    "鸡腿":   {"ref_noun": "只",       "ref_grams": 200, "food_emoji": "🍗", "ref_emoji": "🍗", "calories": 181},
    "香肠":   {"ref_noun": "根",       "ref_grams": 100, "food_emoji": "🌭", "ref_emoji": "🌭", "calories": 508},
    "腊肠":   {"ref_noun": "根",       "ref_grams": 80,  "food_emoji": "🌭", "ref_emoji": "🌭", "calories": 584},
    "午餐肉": {"ref_noun": "块",       "ref_grams": 200, "food_emoji": "🥫", "ref_emoji": "🥫", "calories": 334},
    "螃蟹":   {"ref_noun": "只",       "ref_grams": 300, "food_emoji": "🦀", "ref_emoji": "🦀", "calories": 95},
    "毛豆":   {"ref_noun": "把",       "ref_grams": 200, "food_emoji": "🫛", "ref_emoji": "🫛", "calories": 131},
    "花生米": {"ref_noun": "把",       "ref_grams": 100, "food_emoji": "🥜", "ref_emoji": "🥜", "calories": 574},
    "牛奶":   {"ref_noun": "盒",       "ref_grams": 250, "food_emoji": "🥛", "ref_emoji": "🥛", "calories": 54},
    "米饭":   {"ref_noun": "碗",       "ref_grams": 200, "food_emoji": "🍚", "ref_emoji": "🍚", "calories": 116},
    "面包":   {"ref_noun": "片",       "ref_grams": 50,  "food_emoji": "🍞", "ref_emoji": "🍞", "calories": 313},
    "方便面": {"ref_noun": "包",       "ref_grams": 100, "food_emoji": "🍜", "ref_emoji": "🍜", "calories": 473},
    "黄油":   {"ref_noun": "块",       "ref_grams": 20,  "food_emoji": "🧈", "ref_emoji": "🧈", "calories": 717},
}

UNITS = {"克": 1, "两": GRAM_PER_LIANG, "斤": GRAM_PER_JIN}

# 无固定重量的单位：菜谱里写「份/适量/少许」时，无法换算成克数
NO_WEIGHT_UNITS = {"份", "适量", "少许"}

# 计数单位：按食材的参照物重量换算成克（个/只/条/根/颗/块/把）
COUNT_UNITS = {"个", "只", "条", "根", "颗", "块", "把"}


def to_grams(amount: float, unit: str) -> float:
    """把任意单位换算成克。"""
    return amount * UNITS[unit]


def grams_from(food: str, quantity: float, unit: str):
    """根据食材、数量、单位算出克数（个/只/条/根/颗/块/把 按参照物重量换算）。"""
    if unit in UNITS:
        return to_grams(quantity, unit)
    if unit in NO_WEIGHT_UNITS:
        return None  # 份/适量/少许：没有固定重量，不算克数
    info = FOODS.get(food)
    if info is None:
        return None  # 未知食材，无法按计数单位换算重量
    return quantity * info["ref_grams"]


def convert(food: str, amount: float, unit: str, price_per_jin: float = None) -> dict:
    """完整换算：斤两 + 可视化。price_per_jin 为爬虫抓到的真实价，没有则为 None。

    unit 可以是重量单位（克/两/斤），也可以是计数单位（个/只/条/根/颗/块/把），
    后者按食材的参照物重量换算成克。
    """
    info = FOODS[food]
    grams = grams_from(food, amount, unit)

    jin = grams / GRAM_PER_JIN
    liang = grams / GRAM_PER_LIANG
    count = grams / info["ref_grams"]
    price = round(grams / GRAM_PER_JIN * price_per_jin, 1) if price_per_jin else None

    # 重量输入 → 用「几个拳头/几个鸡蛋」可视化；计数输入 → 直接给克数
    if unit in UNITS:
        analogy = f"≈ {count:.1f} {info['ref_noun']}"
    else:
        analogy = f"≈ {grams:g} 克"

    return {
        "food": food,
        "input": f"{amount:g} {unit}",
        "grams": round(grams, 1),
        "jin": round(jin, 2),
        "liang": round(liang, 2),
        "analogy": analogy,
        "price": price,
        "price_per_jin": price_per_jin,
    }
