from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from fastapi import FastAPI, Request, Response
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from . import models  # noqa: F401  确保数据表被注册
from .db import Base, engine
from .routers import recipes
from .scraper import get_last_update, get_latest_price, scrape_prices
from .services import portion, visual

BASE_DIR = Path(__file__).resolve().parent

scheduler = BackgroundScheduler()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 建表；MySQL 未配置好时不影响其他功能
    try:
        Base.metadata.create_all(bind=engine)
    except Exception:
        pass
    # 定时任务：每 24 小时抓一次菜价，启动时先跑一次
    try:
        scheduler.add_job(
            scrape_prices, IntervalTrigger(hours=24), next_run_time=datetime.now()
        )
        scheduler.start()
    except Exception:
        pass
    yield
    scheduler.shutdown(wait=False)


app = FastAPI(
    title="斤斤计较",
    description="帮年轻人看懂斤两的智能做饭助手",
    lifespan=lifespan,
)

app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
templates = Jinja2Templates(directory=BASE_DIR / "templates")

app.include_router(recipes.router)


@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/converter", response_class=HTMLResponse)
def converter_page(request: Request):
    return templates.TemplateResponse(
        "converter.html", {"request": request, "foods": portion.FOODS}
    )


@app.get("/api/convert")
def api_convert(food: str, amount: float, unit: str):
    if food not in portion.FOODS:
        return {"error": f"不认识的食材：{food}"}
    if unit not in portion.UNITS:
        return {"error": f"不认识的单位：{unit}"}
    try:
        real_price = get_latest_price(food)
        last_update = get_last_update()
    except Exception:
        real_price = None
        last_update = None
    result = portion.convert(food, amount, unit, price_per_jin=real_price)
    result["price_source"] = "真实" if real_price else "估算"
    result["updated_at"] = last_update.strftime("%Y-%m-%d %H:%M") if last_update else None
    return result


@app.get("/api/visual")
def api_visual(food: str, amount: float, unit: str):
    """返回一张「斤两可视化」SVG 图片。"""
    if food not in portion.FOODS or unit not in portion.UNITS:
        return Response(status_code=400)
    grams = portion.to_grams(amount, unit)
    count = grams / portion.FOODS[food]["ref_grams"]
    svg = visual.generate_svg(food, count)
    return Response(content=svg, media_type="image/svg+xml")


@app.post("/admin/scrape")
def trigger_scrape():
    """手动触发一次爬取（演示/调试用）。"""
    try:
        n = scrape_prices()
        return {"ok": True, "count": n}
    except Exception as e:
        return {"ok": False, "error": str(e)}
