"""菜谱：浏览、添加、删除，并自动算出食材重量和价格。"""
import math
import re
from collections import defaultdict
from pathlib import Path

from fastapi import APIRouter, Depends, Form, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import func
from sqlalchemy.orm import Session, selectinload

from ..db import SessionLocal
from ..models import Ingredient, Recipe
from ..scraper import get_latest_price
from ..services import pairings, portion

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


def _enrich_kcal(recipe: Recipe) -> dict:
    """只算热量、不查价格（热量页用，避免给每条食材各开一次数据库连接）。"""
    total_kcal = 0
    for ing in recipe.ingredients:
        grams = portion.grams_from(ing.food, ing.quantity, ing.unit)
        info = portion.FOODS.get(ing.food, {})
        kcal = round(grams * info.get("calories", 0) / 100) if grams else None
        if kcal:
            total_kcal += kcal
    return {"recipe": recipe, "total_kcal": total_kcal}


CATEGORY_ORDER = ["中餐", "西餐", "汤羹", "主食", "早餐"]
CATEGORY_COLORS = {
    "中餐": "#ef4444",
    "西餐": "#3b82f6",
    "汤羹": "#16a34a",
    "主食": "#f59e0b",
    "早餐": "#ec4899",
}


PER_PAGE = 24


@router.get("/recipes", response_class=HTMLResponse)
def list_recipes(request: Request, page: int = Query(1, ge=1), db: Session = Depends(get_db)):
    try:
        total = db.query(func.count(Recipe.id)).scalar() or 0
        total_pages = max(1, math.ceil(total / PER_PAGE))
        page = min(page, total_pages)
        recipes = (
            db.query(Recipe)
            .options(selectinload(Recipe.ingredients))
            .order_by(Recipe.id.desc())
            .offset((page - 1) * PER_PAGE)
            .limit(PER_PAGE)
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
                "page": page,
                "total_pages": total_pages,
                "total": total,
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
                "page": 1,
                "total_pages": 1,
                "total": 0,
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
    """选食材，看能做出哪些菜。

    分三层：
      1. 能一起做的菜（用上 >=2 样所选食材）；
      2. 食材搭配灵感（图谱里的常见组合，如 面粉+排骨 → 炸排骨）；
      3. 都没覆盖到的食材，各推荐一道合适的菜。
    """
    try:
        selected = set(foods)
        for c in re.split(r"[,，、\s]+", custom):
            c = c.strip()
            if c:
                selected.add(c)
        recipes = db.query(Recipe).options(selectinload(Recipe.ingredients)).all()

        # 食材 → 用到它的菜谱
        by_food = defaultdict(list)
        for r in recipes:
            for ing in r.ingredients:
                by_food[ing.food].append(r)

        combos = []  # 能一起做的菜
        combo_ids = set()
        covered = set()
        if selected:
            for r in recipes:
                r_foods = {ing.food for ing in r.ingredients}
                used = r_foods & selected
                if len(used) >= 2:
                    row = _enrich(r)
                    row["used"] = sorted(used)
                    row["missing"] = sorted(selected - used)
                    row["also_needs"] = sorted(r_foods - selected)
                    combos.append(row)
                    combo_ids.add(r.id)
                    covered |= used
            combos.sort(key=lambda x: (-len(x["used"]), len(x["recipe"].ingredients)))

        # 食材搭配灵感：图谱里的常见组合，不依赖菜谱库（比如 面粉+排骨 → 炸排骨）
        combo_used = {frozenset(m["used"]) for m in combos}
        pairing_hits = [
            p for p in pairings.PAIRINGS
            if frozenset(p["foods"]).issubset(selected) and frozenset(p["foods"]) not in combo_used
        ]
        pairing_hits.sort(key=lambda p: (-len(p["foods"]), p["dish"]))

        # 每样没被“混合菜”覆盖的食材，单独推荐一道
        per_food = []
        no_recipe = []
        for f in sorted(selected - covered):
            candidates = [r for r in by_food.get(f, []) if r.id not in combo_ids]
            if not candidates:
                no_recipe.append(f)
                continue
            candidates.sort(
                key=lambda r: (
                    -len({ing.food for ing in r.ingredients} & selected),
                    len(r.ingredients),
                )
            )
            best = candidates[0]
            r_foods = {ing.food for ing in best.ingredients}
            row = _enrich(best)
            row["main_food"] = f
            row["also_needs"] = sorted(r_foods - selected)
            per_food.append(row)

        return templates.TemplateResponse(
            "cook.html",
            {
                "request": request,
                "foods": portion.FOODS,
                "selected": selected,
                "custom_input": custom,
                "combos": combos,
                "pairing_hits": pairing_hits,
                "per_food": per_food,
                "no_recipe": no_recipe,
                "selected_count": len(selected),
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
                "combos": [],
                "pairing_hits": [],
                "per_food": [],
                "no_recipe": [],
                "selected_count": 0,
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


@router.get("/calories", response_class=HTMLResponse)
def calories_page(request: Request, db: Session = Depends(get_db)):
    """菜品热量：食材热量表 + 热量计算器 + 菜谱热量榜。"""
    food_rows = []
    for name, info in portion.FOODS.items():
        food_rows.append(
            {
                "name": name,
                "emoji": info["food_emoji"],
                "ref_noun": info["ref_noun"],
                "per100": info["calories"],
                "serving_kcal": round(info["ref_grams"] * info["calories"] / 100),
            }
        )
    food_rows.sort(key=lambda x: -x["per100"])

    recipe_rows = []
    try:
        recipes = db.query(Recipe).options(selectinload(Recipe.ingredients)).all()
        recipe_rows = [_enrich_kcal(r) for r in recipes]
        recipe_rows = [r for r in recipe_rows if r["total_kcal"] > 0]
        recipe_rows.sort(key=lambda x: x["total_kcal"])
    except Exception:
        recipe_rows = []

    return templates.TemplateResponse(
        "calories.html",
        {
            "request": request,
            "foods": portion.FOODS,
            "food_rows": food_rows,
            "recipe_rows": recipe_rows,
            "db_error": None,
        },
    )


@router.post("/recipes/{recipe_id}/delete")
def delete_recipe(recipe_id: int, page: int = Form(1), db: Session = Depends(get_db)):
    try:
        recipe = db.get(Recipe, recipe_id)
        if recipe is not None:
            db.delete(recipe)
            db.commit()
    except Exception:
        db.rollback()
    return RedirectResponse(f"/recipes?page={page}", status_code=303)


@router.post("/recipes/{recipe_id}/toggle-list")
def toggle_list(recipe_id: int, page: int = Form(1), db: Session = Depends(get_db)):
    try:
        recipe = db.get(Recipe, recipe_id)
        if recipe is not None:
            recipe.in_list = not recipe.in_list
            db.commit()
    except Exception:
        db.rollback()
    return RedirectResponse(f"/recipes?page={page}", status_code=303)
