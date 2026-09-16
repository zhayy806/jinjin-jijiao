"""新发地蔬菜批发价爬虫 + 价格查询。

数据源：北京新发地农产品批发市场（公开批发价，元/斤）。
流程：POST 请求价格接口 → 解析「品名 + 平均价」→ 覆盖写入 MySQL。
"""
import logging
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
}


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
    now = datetime.utcnow()
    with SessionLocal() as db:
        db.query(Price).delete()
        for r in rows:
            db.add(Price(**r, scraped_at=now))
        db.commit()
    logger.info("抓取价格完成：%d 条", len(rows))
    return len(rows)


def get_latest_price(food: str):
    """查询某食材的最新均价（元/斤），没抓到返回 None。"""
    aliases = FOOD_ALIASES.get(food, [food])
    with SessionLocal() as db:
        avg = db.query(func.avg(Price.price)).filter(Price.food.in_(aliases)).scalar()
    return round(float(avg), 2) if avg else None


def get_last_update():
    """最近一次抓取的时间，没数据返回 None。"""
    with SessionLocal() as db:
        latest = db.query(func.max(Price.scraped_at)).scalar()
    return latest
