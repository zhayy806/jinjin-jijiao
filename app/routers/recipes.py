"""菜谱：浏览、添加、删除，并自动算出食材重量和价格。"""
import re
from pathlib import Path

from fastapi import APIRouter, Depends, Form, Query, Request
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
    """给一道菜谱的每个食材，算出克数、价格和热量，并汇总。"""
    items = []
    total = 0.0
    total_kcal = 0
    for ing in recipe.ingredients:
        grams = portion.grams_from(ing.food, ing.quantity, ing.unit)
        ppj = get_latest_price(ing.food)
        price = round(grams / 500 * ppj, 2) if (grams and ppj) else None
        if price:
            total += price
        info = portion.FOODS.get(ing.food, {})
        kcal = round(grams * info.get("calories", 0) / 100) if grams else None
        if kcal:
            total_kcal += kcal
        items.append(
            {
                "food": ing.food,
                "emoji": info.get("food_emoji", "🍽️"),
                "quantity": ing.quantity,
                "unit": ing.unit,
                "grams": round(grams, 1) if grams else None,
                "price": price,
                "kcal": kcal,
            }
        )
    return {"recipe": recipe, "items": items, "total": round(total, 2), "total_kcal": total_kcal}


CATEGORY_ORDER = ["中餐", "西餐", "汤羹", "主食", "早餐"]
CATEGORY_COLORS = {
    "中餐": "#ef4444",
    "西餐": "#3b82f6",
    "汤羹": "#16a34a",
    "主食": "#f59e0b",
    "早餐": "#ec4899",
}


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
            {
                "request": request,
                "groups": ordered,
                "foods": portion.FOODS,
                "cat_colors": CATEGORY_COLORS,
                "db_error": None,
            },
        )
    except Exception:
        return templates.TemplateResponse(
            "recipes.html",
            {
                "request": request,
                "groups": [],
                "foods": portion.FOODS,
                "cat_colors": CATEGORY_COLORS,
                "db_error": DB_DOWN_MSG,
            },
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
            if not f:
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


@router.get("/cook", response_class=HTMLResponse)
def cook(request: Request, foods: list[str] = Query(default=[]), custom: str = Query(default=""), db: Session = Depends(get_db)):
    """选食材，看能做出哪些菜（可勾选 + 自由输入其他食材）。"""
    try:
        selected = set(foods)
        # 支持顿号、逗号、空格等多种分隔符
        for c in re.split(r"[,，、\s]+", custom):
            c = c.strip()
            if c:
                selected.add(c)
        recipes = db.query(Recipe).options(selectinload(Recipe.ingredients)).all()
        matches = []
        if selected:
            for r in recipes:
                r_foods = {ing.food for ing in r.ingredients}
                if r_foods and r_foods.issubset(selected):
                    matches.append(_enrich(r))
        return templates.TemplateResponse(
            "cook.html",
            {
                "request": request,
                "foods": portion.FOODS,
                "selected": selected,
                "custom_input": custom,
                "matches": matches,
                "cat_colors": CATEGORY_COLORS,
                "db_error": None,
            },
        )
    except Exception:
        return templates.TemplateResponse(
            "cook.html",
            {
                "request": request,
                "foods": portion.FOODS,
                "selected": set(),
                "custom_input": custom,
                "matches": [],
                "cat_colors": CATEGORY_COLORS,
                "db_error": DB_DOWN_MSG,
            },
        )


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
            "recommend.html",
            {"request": request, "row": row, "cat_colors": CATEGORY_COLORS, "db_error": None},
        )
    except Exception:
        return templates.TemplateResponse(
            "recommend.html",
            {"request": request, "row": None, "cat_colors": CATEGORY_COLORS, "db_error": DB_DOWN_MSG},
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
