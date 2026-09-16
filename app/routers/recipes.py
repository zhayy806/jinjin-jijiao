"""菜谱：浏览、添加、删除，并自动算出食材重量和价格。"""
from pathlib import Path

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import func
from sqlalchemy.orm import Session, selectinload

from ..db import SessionLocal
from ..models import Ingredient, Recipe
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


def _enrich(recipe: Recipe) -> dict:
    """给一道菜谱的每个食材，算出克数和价格，并汇总总价。"""
    items = []
    total = 0.0
    for ing in recipe.ingredients:
        grams = portion.grams_from(ing.food, ing.quantity, ing.unit)
        ppj = get_latest_price(ing.food)
        price = round(grams / 500 * ppj, 2) if (grams and ppj) else None
        if price:
            total += price
        items.append(
            {
                "food": ing.food,
                "emoji": portion.FOODS.get(ing.food, {}).get("food_emoji", "🍽️"),
                "quantity": ing.quantity,
                "unit": ing.unit,
                "grams": round(grams, 1) if grams else None,
                "price": price,
            }
        )
    return {"recipe": recipe, "items": items, "total": round(total, 2)}


CATEGORY_ORDER = ["中餐", "西餐", "汤羹", "主食", "早餐"]


@router.get("/recipes", response_class=HTMLResponse)
def list_recipes(request: Request, db: Session = Depends(get_db)):
    try:
        recipes = (
            db.query(Recipe)
            .options(selectinload(Recipe.ingredients))
            .order_by(Recipe.id.desc())
            .all()
        )
        rows = [_enrich(r) for r in recipes]
        groups = {}
        for r in rows:
            cat = r["recipe"].category or "其他"
            groups.setdefault(cat, []).append(r)
        ordered = [(c, groups[c]) for c in CATEGORY_ORDER if c in groups]
        for c in groups:
            if c not in CATEGORY_ORDER:
                ordered.append((c, groups[c]))
        return templates.TemplateResponse(
            "recipes.html",
            {"request": request, "groups": ordered, "foods": portion.FOODS, "db_error": None},
        )
    except Exception:
        return templates.TemplateResponse(
            "recipes.html",
            {"request": request, "groups": [], "foods": portion.FOODS, "db_error": DB_DOWN_MSG},
        )


@router.post("/recipes")
def create_recipe(
    name: str = Form(...),
    category: str = Form("中餐"),
    steps: str = Form(""),
    food: list[str] = Form(default=[]),
    quantity: list[str] = Form(default=[]),
    unit: list[str] = Form(default=[]),
    db: Session = Depends(get_db),
):
    try:
        recipe = Recipe(name=name.strip(), category=category.strip(), steps=steps.strip())
        db.add(recipe)
        db.flush()  # 拿到 recipe.id
        for f, q, u in zip(food, quantity, unit):
            f = (f or "").strip()
            if not f or f not in portion.FOODS:
                continue
            try:
                q_val = float(q)
            except (ValueError, TypeError):
                continue
            db.add(Ingredient(recipe_id=recipe.id, food=f, quantity=q_val, unit=u))
        db.commit()
    except Exception:
        db.rollback()
    return RedirectResponse("/recipes", status_code=303)


@router.get("/recommend", response_class=HTMLResponse)
def recommend(request: Request, db: Session = Depends(get_db)):
    """随机推荐一道菜（今晚吃什么）。"""
    try:
        recipe = (
            db.query(Recipe)
            .options(selectinload(Recipe.ingredients))
            .order_by(func.rand())
            .first()
        )
        if recipe is None:
            return RedirectResponse("/recipes", status_code=303)
        row = _enrich(recipe)
        return templates.TemplateResponse(
            "recommend.html", {"request": request, "row": row, "db_error": None}
        )
    except Exception:
        return templates.TemplateResponse(
            "recommend.html", {"request": request, "row": None, "db_error": DB_DOWN_MSG}
        )


@router.post("/recipes/{recipe_id}/delete")
def delete_recipe(recipe_id: int, db: Session = Depends(get_db)):
    try:
        recipe = db.get(Recipe, recipe_id)
        if recipe is not None:
            db.delete(recipe)
            db.commit()
    except Exception:
        db.rollback()
    return RedirectResponse("/recipes", status_code=303)


@router.post("/recipes/{recipe_id}/toggle-list")
def toggle_list(recipe_id: int, db: Session = Depends(get_db)):
    try:
        recipe = db.get(Recipe, recipe_id)
        if recipe is not None:
            recipe.in_list = not recipe.in_list
            db.commit()
    except Exception:
        db.rollback()
    return RedirectResponse("/recipes", status_code=303)
