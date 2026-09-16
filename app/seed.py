"""种子菜谱：首次启动时灌入家常菜，避免冷启动空库。"""
from .db import SessionLocal
from .models import Ingredient, Recipe

SEED_RECIPES = [
    # 中餐
    {"name": "西红柿炒鸡蛋", "category": "中餐", "steps": "1.鸡蛋打散炒熟盛出；2.下西红柿炒软；3.倒回鸡蛋翻炒调味。",
     "ingredients": [("西红柿", 2, "个"), ("鸡蛋", 3, "个")]},
    {"name": "红烧排骨", "category": "中餐", "steps": "1.排骨焯水；2.炒糖色下排骨；3.加水炖30分钟收汁。",
     "ingredients": [("排骨", 500, "克")]},
    {"name": "土豆炖牛肉", "category": "中餐", "steps": "1.牛肉切块焯水；2.土豆切块；3.一起炖40分钟调味。",
     "ingredients": [("牛肉", 300, "克"), ("土豆", 2, "个")]},
    {"name": "醋溜土豆丝", "category": "中餐", "steps": "1.土豆切丝泡水；2.热油爆香；3.下土豆丝炒熟加醋。",
     "ingredients": [("土豆", 2, "个")]},
    {"name": "清炒时蔬", "category": "中餐", "steps": "1.青菜洗净；2.热油下蒜末；3.大火快炒出锅。",
     "ingredients": [("青菜", 300, "克")]},
    {"name": "香菇鸡胸肉", "category": "中餐", "steps": "1.鸡胸肉切片腌制；2.香菇切片；3.一起翻炒至熟。",
     "ingredients": [("鸡胸肉", 200, "克"), ("菌菇", 200, "克")]},
    {"name": "番茄炖牛腩", "category": "中餐", "steps": "1.牛腩切块焯水；2.西红柿切块；3.一起炖1小时。",
     "ingredients": [("牛肉", 300, "克"), ("西红柿", 2, "个")]},
    {"name": "菌菇炒肉", "category": "中餐", "steps": "1.猪肉切片；2.菌菇洗净；3.一起爆炒调味。",
     "ingredients": [("猪肉", 200, "克"), ("菌菇", 200, "克")]},
    # 西餐
    {"name": "番茄意面", "category": "西餐", "steps": "1.面粉和面做面条；2.煮面；3.炒番茄酱拌面。",
     "ingredients": [("面粉", 150, "克"), ("西红柿", 2, "个")]},
    {"name": "黑椒牛排", "category": "西餐", "steps": "1.牛肉切厚片；2.煎至两面金黄；3.撒黑椒调味。",
     "ingredients": [("牛肉", 250, "克")]},
    {"name": "奶油蘑菇汤", "category": "西餐", "steps": "1.菌菇切片炒香；2.加面粉和牛奶煮；3.搅至浓稠。",
     "ingredients": [("菌菇", 200, "克"), ("面粉", 50, "克")]},
    {"name": "蔬菜沙拉", "category": "西餐", "steps": "1.青菜洗净；2.西红柿苹果切块；3.拌沙拉酱。",
     "ingredients": [("青菜", 200, "克"), ("西红柿", 1, "个"), ("苹果", 1, "个")]},
    # 汤羹
    {"name": "番茄蛋花汤", "category": "汤羹", "steps": "1.水烧开；2.下西红柿煮2分钟；3.淋入蛋液搅散。",
     "ingredients": [("西红柿", 1, "个"), ("鸡蛋", 2, "个")]},
    {"name": "排骨青菜汤", "category": "汤羹", "steps": "1.排骨焯水炖30分钟；2.下青菜煮软；3.调味。",
     "ingredients": [("排骨", 300, "克"), ("青菜", 200, "克")]},
    {"name": "菌菇蛋汤", "category": "汤羹", "steps": "1.菌菇煮5分钟；2.淋入蛋液；3.调味出锅。",
     "ingredients": [("菌菇", 150, "克"), ("鸡蛋", 2, "个")]},
    # 主食
    {"name": "煮米饭", "category": "主食", "steps": "1.大米淘洗；2.加适量水；3.煮饭键煮熟。",
     "ingredients": [("大米", 200, "克")]},
    {"name": "牛肉面", "category": "主食", "steps": "1.牛肉切片煮汤；2.下面条；3.放青菜煮熟。",
     "ingredients": [("牛肉", 200, "克"), ("面粉", 200, "克"), ("青菜", 150, "克")]},
    {"name": "鸡蛋饼", "category": "主食", "steps": "1.面粉加水调糊；2.打鸡蛋搅匀；3.平底锅摊成饼。",
     "ingredients": [("面粉", 150, "克"), ("鸡蛋", 2, "个")]},
    {"name": "蛋炒饭", "category": "主食", "steps": "1.米饭炒散；2.下鸡蛋青菜；3.翻炒调味。",
     "ingredients": [("大米", 150, "克"), ("鸡蛋", 2, "个"), ("青菜", 100, "克")]},
    {"name": "番茄鸡蛋面", "category": "主食", "steps": "1.下面条煮熟；2.炒番茄鸡蛋；3.浇在面上。",
     "ingredients": [("面粉", 150, "克"), ("西红柿", 1, "个"), ("鸡蛋", 2, "个")]},
    # 早餐
    {"name": "煎蛋", "category": "早餐", "steps": "1.平底锅热油；2.打鸡蛋煎熟；3.撒盐出锅。",
     "ingredients": [("鸡蛋", 2, "个")]},
    {"name": "苹果燕麦粥", "category": "早餐", "steps": "1.大米煮粥；2.苹果切丁；3.放入粥中煮软。",
     "ingredients": [("大米", 100, "克"), ("苹果", 1, "个")]},
]


def seed_recipes() -> int:
    """若菜谱表为空，灌入种子菜谱，返回灌入数量。"""
    with SessionLocal() as db:
        if db.query(Recipe).count() > 0:
            return 0
        for r in SEED_RECIPES:
            recipe = Recipe(name=r["name"], category=r["category"], steps=r["steps"])
            db.add(recipe)
            db.flush()
            for food, qty, unit in r["ingredients"]:
                db.add(Ingredient(recipe_id=recipe.id, food=food, quantity=qty, unit=unit))
        db.commit()
    return len(SEED_RECIPES)
