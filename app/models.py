"""数据表定义。"""
from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from .db import Base


class Recipe(Base):
    """菜谱表。"""

    __tablename__ = "recipes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(200), nullable=False)
    steps = Column(Text, default="")
    in_list = Column(Boolean, default=False)  # 是否加入购物清单
    created_at = Column(DateTime, default=datetime.utcnow)

    ingredients = relationship(
        "Ingredient", back_populates="recipe", cascade="all, delete-orphan"
    )


class Ingredient(Base):
    """菜谱食材表（结构化：每条 = 食材 + 数量 + 单位）。"""

    __tablename__ = "ingredients"

    id = Column(Integer, primary_key=True, autoincrement=True)
    recipe_id = Column(Integer, ForeignKey("recipes.id"), nullable=False)
    food = Column(String(50), nullable=False)
    quantity = Column(Float, nullable=False)
    unit = Column(String(10), nullable=False, default="个")

    recipe = relationship("Recipe", back_populates="ingredients")


class Price(Base):
    """食材价格表（爬虫写入，每次抓取后覆盖为最新快照）。"""

    __tablename__ = "prices"

    id = Column(Integer, primary_key=True, autoincrement=True)
    food = Column(String(50), nullable=False)
    price = Column(Float, nullable=False)  # 单位：元/斤
    place = Column(String(100), default="")
    source = Column(String(50), default="新发地")
    scraped_at = Column(DateTime, default=datetime.utcnow)
