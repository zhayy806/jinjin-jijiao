"""购物清单：把「加入清单」的菜谱，汇总成要买什么 + 一共多少钱。"""
from collections import defaultdict
from pathlib import Path

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session, selectinload

from ..db import SessionLocal
from ..models import Recipe
from ..scraper import get_latest_price
from ..services import portion

router = APIRouter()
templates = Jinja2Templates(directory=Path(__file__).resolve().parent.parent / "templates")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.get("/shopping", response_class=HTMLResponse)
def shopping_list(request: Request, db: Session = Depends(get_db)):
    try:
        recipes = (
            db.query(Recipe)
            .filter(Recipe.in_list.is_(True))
            .options(selectinload(Recipe.ingredients))
            .all()
        )
        recipe_names = [r.name for r in recipes]

        # 按食材合并：同名食材的克数累加
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
                    "price": price,
                }
            )

        return templates.TemplateResponse(
            "shopping.html",
            {
                "request": request,
                "items": items,
                "total": round(total, 2),
                "recipe_names": recipe_names,
                "db_error": None,
            },
        )
    except Exception:
        return templates.TemplateResponse(
            "shopping.html",
            {
                "request": request,
                "items": [],
                "total": 0,
                "recipe_names": [],
                "db_error": "数据库还没连上，配置好 MySQL 后就能用了。",
            },
        )
