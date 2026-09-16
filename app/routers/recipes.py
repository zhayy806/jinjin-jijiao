"""菜谱：浏览 + 添加。"""
from pathlib import Path

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from ..db import SessionLocal
from ..models import Recipe

router = APIRouter()
templates = Jinja2Templates(directory=Path(__file__).resolve().parent.parent / "templates")

DB_DOWN_MSG = "数据库还没连上，配置好 MySQL 后就能用了。"


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.get("/recipes", response_class=HTMLResponse)
def list_recipes(request: Request, db: Session = Depends(get_db)):
    try:
        recipes = db.query(Recipe).order_by(Recipe.id.desc()).all()
        return templates.TemplateResponse(
            "recipes.html", {"request": request, "recipes": recipes, "db_error": None}
        )
    except Exception:
        return templates.TemplateResponse(
            "recipes.html", {"request": request, "recipes": [], "db_error": DB_DOWN_MSG}
        )


@router.post("/recipes")
def create_recipe(
    name: str = Form(...),
    ingredients: str = Form(""),
    steps: str = Form(""),
    db: Session = Depends(get_db),
):
    try:
        recipe = Recipe(name=name.strip(), ingredients=ingredients.strip(), steps=steps.strip())
        db.add(recipe)
        db.commit()
    except Exception:
        db.rollback()
    return RedirectResponse("/recipes", status_code=303)


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
