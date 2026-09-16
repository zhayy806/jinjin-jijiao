"""数据库连接（MySQL）。

连接信息从环境变量读取（可用 .env 文件配置），
默认连接本机 MySQL 的 root 账号、jinjin 数据库。
"""
import os

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.engine import URL
from sqlalchemy.orm import declarative_base, sessionmaker

load_dotenv()


def _database_url() -> URL:
    return URL.create(
        "mysql+pymysql",
        username=os.getenv("MYSQL_USER", "root"),
        password=os.getenv("MYSQL_PASSWORD", ""),
        host=os.getenv("MYSQL_HOST", "127.0.0.1"),
        port=int(os.getenv("MYSQL_PORT", "3306")),
        database=os.getenv("MYSQL_DB", "jinjin"),
    )


def _connect_args() -> dict:
    """云数据库（如 TiDB）需要 TLS 时，设 MYSQL_SSL=1 开启加密连接。"""
    if os.getenv("MYSQL_SSL", "") == "1":
        return {"ssl": {"ssl_verify_cert": False}}
    return {}


engine = create_engine(_database_url(), connect_args=_connect_args(), pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
Base = declarative_base()
