"""新发地蔬菜批发价爬虫 + 价格查询。

数据源：北京新发地农产品批发市场（公开批发价，元/斤）。
流程：POST 请求价格接口 → 解析「品名 + 平均价」→ 覆盖写入 MySQL。
"""
import logging
import time
from datetime import datetime

import httpx
from sqlalchemy import func

from .db import SessionLocal
from .models import Price

logger = logging.getLogger("jinjin.scraper")

URL = "http://www.xinfadi.com.cn/getPriceData.html"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
}
SOURCE = "新发地"

# 我们关心的食材 → 新发地里的品名
FOOD_ALIASES = {
    "猪肉": ["白条猪"],
    "牛肉": ["牛腩"],
    "鸡胸肉": ["鸡胸"],
    "排骨": ["牛排骨", "猪排骨"],
    "鸡蛋": ["散鸡蛋", "柴鸡蛋"],
    "西红柿": ["番茄"],
    "土豆": ["土豆"],
    "苹果": ["红富士", "红富士苹果", "苹果"],
    "青菜": ["小白菜", "油菜", "菠菜"],
    "大米": ["东北大米"],
    "面粉": ["好面缘面粉"],
    "菌菇": ["香菇", "平菇", "金针菇"],
    "虾": ["基围虾", "白虾", "大虾", "虾"],
    "鱼": ["草鱼", "鲤鱼", "鲫鱼", "鲈鱼"],
    "小龙虾": ["小龙虾"],
    "皮皮虾": ["皮皮虾", "虾蛄", "爬虾"],
    "豆腐": ["豆腐"],
    "青椒": ["青椒", "尖椒"],
    "洋葱": ["洋葱"],
    "白菜": ["大白菜", "白菜"],
    "黄瓜": ["黄瓜"],
    "茄子": ["茄子"],
    "韭菜": ["韭菜"],
    "羊肉": ["羊肉", "羊腩"],
    "胡萝卜": ["胡萝卜"],
    "白萝卜": ["白萝卜"],
    "包菜": ["圆白菜", "包菜", "洋白菜"],
    "芹菜": ["芹菜", "西芹"],
    "莴笋": ["莴笋", "青笋"],
    "西葫芦": ["西葫芦", "西胡"],
    "花菜": ["菜花", "花菜", "有机菜花"],
    "木耳": ["木耳"],
    "海鲜菇": ["海鲜菇", "白玉菇", "蟹味菇"],
    "虾仁": ["虾仁"],
    "鸡肉": ["白条鸡", "三黄鸡", "整鸡"],
    "鸡腿": ["鸡腿", "琵琶腿"],
    "螃蟹": ["螃蟹", "大闸蟹", "河蟹"],
    "毛豆": ["毛豆"],
    "花生米": ["花生米", "花生"],
}

# 我们只关心这些品名；抓取时过滤掉无关数据，避免每次给数据库塞进几千条
ALIAS_NAMES = {name for names in FOOD_ALIASES.values() for name in names}


def parse_payload(payload: dict) -> list:
    """把接口返回的 JSON 解析成 [{food, price, place, source}, ...]。"""
    rows = []
    for item in payload.get("list", []):
        name = (item.get("prodName") or "").strip()
        price = item.get("avgPrice")
        if not name or price is None:
            continue
        try:
            price = float(price)
        except (TypeError, ValueError):
            continue
        rows.append({"food": name, "price": price, "place": "北京新发地", "source": SOURCE})
    return rows


def fetch_prices() -> list:
    """请求新发地价格接口并解析。"""
    resp = httpx.post(URL, headers=HEADERS, data={"limit": 3000, "current": 1}, timeout=25)
    resp.raise_for_status()
    return parse_payload(resp.json())


def scrape_prices() -> int:
    """抓取最新价格并覆盖写入数据库，返回写入条数。"""
    try:
        rows = fetch_prices()
    except Exception as e:
        logger.warning("抓取价格失败：%s", e)
        return 0
    if not rows:
        return 0
    # 只存我们关心的品名，避免每次给 TiDB 塞进几千条无关数据
    rows = [r for r in rows if r["food"] in ALIAS_NAMES]
    if not rows:
        return 0
    now = datetime.utcnow()
    with SessionLocal() as db:
        db.query(Price).delete()
        for r in rows:
            db.add(Price(**r, scraped_at=now))
        db.commit()
    logger.info("抓取价格完成：%d 条", len(rows))
    return len(rows)


# 进程内缓存：一次页面渲染会反复查同一批食材，避免给 TiDB 开成百上千个连接
_price_cache = {}


def get_latest_price(food: str):
    """查询某食材的最新均价（元/斤），没抓到返回 None。结果缓存 5 分钟。"""
    hit = _price_cache.get(food)
    if hit and time.monotonic() - hit[0] < 300:
        return hit[1]
    aliases = FOOD_ALIASES.get(food, [food])
    with SessionLocal() as db:
        avg = db.query(func.avg(Price.price)).filter(Price.food.in_(aliases)).scalar()
    price = round(float(avg), 2) if avg else None
    _price_cache[food] = (time.monotonic(), price)
    return price


def get_last_update():
    """最近一次抓取的时间，没数据返回 None。"""
    with SessionLocal() as db:
        latest = db.query(func.max(Price.scraped_at)).scalar()
    return latest
