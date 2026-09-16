"""种子菜谱：首次启动时灌入家常菜，避免冷启动空库。"""
from .db import SessionLocal
from .models import Ingredient, Recipe

SEED_RECIPES = [
    {"name": "西红柿炒鸡蛋", "steps": "1.鸡蛋打散炒熟盛出；2.下西红柿炒软；3.倒回鸡蛋翻炒调味。",
     "ingredients": [("西红柿", 2, "个"), ("鸡蛋", 3, "个")]},
    {"name": "土豆炖牛肉", "steps": "1.牛肉切块焯水；2.土豆切滚刀块；3.一起炖40分钟调味。",
     "ingredients": [("牛肉", 300, "克"), ("土豆", 2, "个")]},
    {"name": "红烧排骨", "steps": "1.排骨焯水；2.炒糖色下排骨；3.加水炖30分钟收汁。",
     "ingredients": [("排骨", 500, "克")]},
    {"name": "清炒时蔬", "steps": "1.青菜洗净；2.热油下蒜末爆香；3.大火快炒出锅。",
     "ingredients": [("青菜", 300, "克")]},
    {"name": "番茄蛋花汤", "steps": "1.水烧开；2.下西红柿煮2分钟；3.淋入蛋液搅散。",
     "ingredients": [("西红柿", 1, "个"), ("鸡蛋", 2, "个")]},
    {"name": "香菇鸡胸肉", "steps": "1.鸡胸肉切片腌制；2.香菇切片；3.一起翻炒至熟。",
     "ingredients": [("鸡胸肉", 200, "克"), ("菌菇", 200, "克")]},
    {"name": "醋溜土豆丝", "steps": "1.土豆切丝泡水；2.热油爆香；3.下土豆丝炒熟加醋。",
     "ingredients": [("土豆", 2, "个")]},
    {"name": "煮米饭", "steps": "1.大米淘洗；2.加适量水；3.煮饭键煮熟。",
     "ingredients": [("大米", 200, "克")]},
    {"name": "鸡蛋饼", "steps": "1.面粉加水调糊；2.打鸡蛋搅匀；3.平底锅摊成饼。",
     "ingredients": [("面粉", 150, "克"), ("鸡蛋", 2, "个")]},
    {"name": "牛肉面", "steps": "1.牛肉切片煮汤；2.下面条；3.放青菜煮熟。",
     "ingredients": [("牛肉", 200, "克"), ("面粉", 200, "克"), ("青菜", 150, "克")]},
]


def seed_recipes() -> int:
    """若菜谱表为空，灌入种子菜谱，返回灌入数量。"""
    with SessionLocal() as db:
        if db.query(Recipe).count() > 0:
            return 0
        for r in SEED_RECIPES:
            recipe = Recipe(name=r["name"], steps=r["steps"])
            db.add(recipe)
            db.flush()
            for food, qty, unit in r["ingredients"]:
                db.add(Ingredient(recipe_id=recipe.id, food=food, quantity=qty, unit=unit))
        db.commit()
    return len(SEED_RECIPES)
