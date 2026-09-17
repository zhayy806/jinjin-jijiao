"""豆果美食菜谱爬虫：抓取真实菜谱，存进 MySQL。

用法：
    python -m app.recipe_crawler 3357000 300
    （从菜谱 ID 3357000 开始，抓到 300 道为止）
"""
import logging
import re
import sys
import time

import httpx
from bs4 import BeautifulSoup

from .db import SessionLocal
from .models import Ingredient, Recipe

logger = logging.getLogger("jinjin.crawler")

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"
    ),
}

UNIT_MAP = {
    "g": "克", "克": "克", "kg": "千克", "千克": "千克",
    "ml": "毫升", "毫升": "毫升", "l": "升", "片": "片",
    "勺": "勺", "个": "个", "根": "根", "只": "只", "条": "条",
}


def parse_ingredient(text: str):
    """'排骨 600g' → (食物名, 数量, 单位)。"""
    text = re.sub(r"\s+", " ", text).strip()
    m = re.match(r"^(.+?)\s*([0-9][0-9.\-/]*)\s*([^\d\s]*)", text)
    if not m:
        return text, None, None
    name = m.group(1).strip()
    qty_str = m.group(2)
    unit_raw = m.group(3).strip()
    try:
        qty = float(qty_str.split("-")[0].split("/")[0])
    except ValueError:
        qty = None
    unit = UNIT_MAP.get(unit_raw.lower(), unit_raw or None)
    return name, qty, unit


def parse_recipe(html: str):
    """解析菜谱详情页，返回 {name, ingredients, steps}。"""
    soup = BeautifulSoup(html, "html.parser")
    title = soup.title.string if soup.title else ""
    name = title.split("的做法")[0].split("_")[0].strip()
    if not name:
        return None

    ingredients = []
    for td in soup.select("div.metarial td"):
        txt = td.get_text(" ", strip=True)
        if not txt:
            continue
        food, qty, unit = parse_ingredient(txt)
        ingredients.append({"food": food, "quantity": qty, "unit": unit})

    steps = ""
    for el in soup.select(".step"):
        steps += el.get_text(" ", strip=True) + " "
    steps = re.sub(r"\s+", " ", steps).strip()

    return {"name": name, "ingredients": ingredients, "steps": steps}


def _save(recipe: dict):
    with SessionLocal() as db:
        exists = db.query(Recipe).filter(Recipe.name == recipe["name"]).first()
        if exists:
            return False
        r = Recipe(name=recipe["name"], category="家常菜", steps=recipe["steps"])
        db.add(r)
        db.flush()
        for ing in recipe["ingredients"]:
            if not ing["food"] or not ing["quantity"]:
                continue
            db.add(
                Ingredient(
                    recipe_id=r.id,
                    food=ing["food"],
                    quantity=ing["quantity"],
                    unit=ing["unit"] or "克",
                )
            )
        db.commit()
    return True


def crawl(start_id: int, target: int, delay: float = 0.4) -> int:
    """从 start_id 开始抓，直到抓到 target 道菜，返回抓到数量。"""
    got = 0
    recipe_id = start_id
    while got < target:
        url = f"https://www.douguo.com/cookbook/{recipe_id}.html"
        recipe_id += 1
        try:
            resp = httpx.get(url, headers=HEADERS, timeout=(5, 8), follow_redirects=True)
            if resp.status_code != 200:
                continue
            recipe = parse_recipe(resp.text)
            if recipe is None or not recipe["name"] or not recipe["ingredients"]:
                continue
            if _save(recipe):
                got += 1
                if got % 20 == 0:
                    print(f"已抓 {got} 道菜（当前 ID {recipe_id}）", flush=True)
        except Exception as e:
            logger.warning("抓取 %s 失败：%s", url, e)
        time.sleep(delay)
    return got


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    start = int(sys.argv[1]) if len(sys.argv) > 1 else 3357000
    target = int(sys.argv[2]) if len(sys.argv) > 2 else 200
    print(f"开始爬取：从 ID {start} 起，目标 {target} 道", flush=True)
    n = crawl(start, target)
    print(f"完成，共抓到 {n} 道菜")
