"""数据表定义。"""
from datetime import datetime

from sqlalchemy import Column, DateTime, Float, Integer, String, Text

from .db import Base


class Recipe(Base):
    """菜谱表。"""

    __tablename__ = "recipes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(200), nullable=False)
    ingredients = Column(Text, default="")
    steps = Column(Text, default="")
    created_at = Column(DateTime, default=datetime.utcnow)


class Price(Base):
    """食材价格表（爬虫写入，每次抓取后覆盖为最新快照）。"""

    __tablename__ = "prices"

    id = Column(Integer, primary_key=True, autoincrement=True)
    food = Column(String(50), nullable=False)
    price = Column(Float, nullable=False)  # 单位：元/斤
    place = Column(String(100), default="")
    source = Column(String(50), default="惠农网")
    scraped_at = Column(DateTime, default=datetime.utcnow)
