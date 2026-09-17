"""导入 YunYouJun/cook 开源中文菜谱数据集（约 600 道真实家常菜）。

数据来源：https://github.com/YunYouJun/cook
字段：name 菜名 / stuff 食材(顿号分隔) / tags 标签 / methods 烹饪方式 / tools 厨具 / bv 视频号

注意：该数据集只有食材名、没有克数，食材统一按「1 份」导入，
换算时「份/适量/少许」不折算克数（见 services/portion.py）。

用法：
    python -m app.import_recipes
"""
import csv
import io
import logging
import re

import httpx

from .db import SessionLocal
from .models import Ingredient, Recipe

logger = logging.getLogger("jinjin.importer")

CSV_URL = "https://raw.githubusercontent.com/YunYouJun/cook/main/app/data/recipe.csv"

# 分类推断关键词（按优先级：西餐 > 主食 > 汤羹 > 默认中餐）
_CAT_WESTERN = ("蛋糕", "面包", "饼干", "披萨", "意面", "牛排", "沙拉", "吐司", "玛芬", "甜点", "冰淇淋")
_CAT_STAPLE = ("面", "饭", "饼", "包", "馒头", "饺子", "馄饨", "米线", "米粉", "年糕")
_CAT_SOUP = ("汤", "羹", "粥")


def infer_category(name: str, tags: str, methods: str) -> str:
    """根据菜名/标签/做法方式，粗略推断分类。"""
    text = f"{name} {tags} {methods}"
    if any(k in text for k in _CAT_WESTERN):
        return "西餐"
    if any(k in text for k in _CAT_STAPLE):
        return "主食"
    if any(k in text for k in _CAT_SOUP):
        return "汤羹"
    return "中餐"


def _split_foods(stuff: str) -> list[str]:
    """把「腊肠、米」拆成食材名列表。"""
    return [f.strip() for f in re.split(r"[、，,;；\s]+", stuff or "") if f.strip()]


def _build_steps(methods: str, tools: str, bv: str) -> str:
    """没有现成做法步骤，用烹饪方式 + 厨具 + 视频链接合成。"""
    parts = []
    if methods:
        parts.append(f"烹饪方式：{methods}")
    if tools:
        parts.append(f"厨具：{tools}")
    if bv:
        parts.append(f"视频教程：https://www.bilibili.com/video/{bv}")
    return "；".join(parts)


def import_recipes(url: str = CSV_URL) -> dict:
    """下载并导入菜谱，返回 {added, skipped_dup, skipped_empty}。"""
    resp = httpx.get(url, timeout=30, follow_redirects=True)
    resp.raise_for_status()
    reader = csv.DictReader(io.StringIO(resp.text))
    added = skipped_dup = skipped_empty = 0
    with SessionLocal() as db:
        for row in reader:
            name = (row.get("name") or "").strip()
            foods = _split_foods(row.get("stuff") or "")
            if not name or not foods:
                skipped_empty += 1
                continue
            if db.query(Recipe).filter(Recipe.name == name).first():
                skipped_dup += 1
                continue
            category = infer_category(name, row.get("tags") or "", row.get("methods") or "")
            steps = _build_steps(row.get("methods") or "", row.get("tools") or "", row.get("bv") or "")
            recipe = Recipe(name=name, category=category, steps=steps)
            db.add(recipe)
            db.flush()
            for food in foods:
                db.add(Ingredient(recipe_id=recipe.id, food=food[:50], quantity=1.0, unit="份"))
            added += 1
        db.commit()
    return {"added": added, "skipped_dup": skipped_dup, "skipped_empty": skipped_empty}


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    stats = import_recipes()
    print(
        f"导入完成：新增 {stats['added']} 道，"
        f"跳过重复 {stats['skipped_dup']} 道，空数据 {stats['skipped_empty']} 道"
    )
