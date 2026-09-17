"""购物清单：把「加入清单」的菜 + 手动填的食材，汇总成要买什么 + 一共多少钱。"""
from collections import defaultdict
from pathlib import Path

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session, selectinload

from ..db import SessionLocal
from ..models import Recipe
from ..scraper import get_latest_price
from ..services import portion

router = APIRouter()
templates = Jinja2Templates(directory=Path(__file__).resolve().parent.parent / "templates")

DB_DOWN_MSG = "数据库还没连上，配置好 MySQL 后就能用了。"


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _price_item(food, quantity, unit):
    """单个食材：克数 + 单价(元/斤) + 小计。"""
    grams = portion.grams_from(food, quantity, unit)
    ppj = get_latest_price(food)
    price = round(grams / 500 * ppj, 2) if (grams and ppj) else None
    return {
        "food": food,
        "quantity": quantity,
        "unit": unit,
        "grams": round(grams, 1) if grams else None,
        "jin": round(grams / 500, 2) if grams else None,
        "ppj": ppj,
        "price": price,
    }


def _aggregate(recipes):
    """把多道菜的食材按同名合并，汇总克数 + 价格。"""
    recipe_names = [r.name for r in recipes]
    agg = defaultdict(float)
    for r in recipes:
        for ing in r.ingredients:
            grams = portion.grams_from(ing.food, ing.quantity, ing.unit)
            if grams:
                agg[ing.food] += grams

    items = []
    total = 0.0
    for food, grams in sorted(agg.items(), key=lambda x: -x[1]):
        ppj = get_latest_price(food)
        price = round(grams / 500 * ppj, 2) if ppj else None
        if price:
            total += price
        items.append(
            {
                "food": food,
                "grams": round(grams, 1),
                "jin": round(grams / 500, 2),
                "ppj": ppj,
                "price": price,
            }
        )
    return recipe_names, items, round(total, 2)


def _render(request, direct_items, direct_total, recipe_names, items, total, db_error):
    return templates.TemplateResponse(
        "shopping.html",
        {
            "request": request,
            "foods": portion.FOODS,
            "direct_items": direct_items,
            "direct_total": direct_total,
            "recipe_names": recipe_names,
            "items": items,
            "total": total,
            "db_error": db_error,
        },
    )


@router.get("/shopping", response_class=HTMLResponse)
def shopping_list(request: Request, db: Session = Depends(get_db)):
    try:
        recipes = (
            db.query(Recipe)
            .filter(Recipe.in_list.is_(True))
            .options(selectinload(Recipe.ingredients))
            .all()
        )
        recipe_names, items, total = _aggregate(recipes)
        return _render(request, [], None, recipe_names, items, total, None)
    except Exception:
        return _render(request, [], None, [], [], 0, DB_DOWN_MSG)


@router.post("/shopping", response_class=HTMLResponse)
def shopping_calc(
    request: Request,
    food: list[str] = Form(default=[]),
    quantity: list[str] = Form(default=[]),
    unit: list[str] = Form(default=[]),
    db: Session = Depends(get_db),
):
    direct_items = []
    direct_total = 0.0
    for f, q, u in zip(food, quantity, unit):
        f = (f or "").strip()
        if not f:
            continue
        try:
            q_val = float(q)
        except (ValueError, TypeError):
            continue
        item = _price_item(f, q_val, u)
        if item["price"]:
            direct_total += item["price"]
        direct_items.append(item)

    try:
        recipes = (
            db.query(Recipe)
            .filter(Recipe.in_list.is_(True))
            .options(selectinload(Recipe.ingredients))
            .all()
        )
        recipe_names, items, total = _aggregate(recipes)
    except Exception:
        recipe_names, items, total = [], [], 0

    return _render(request, direct_items, round(direct_total, 2), recipe_names, items, total, None)
