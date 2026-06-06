import os
import sqlite3
from pathlib import Path

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, declarative_base
from dotenv import load_dotenv

load_dotenv()

_ROOT = Path(__file__).parent.parent
DB_FILE = _ROOT / "data" / "viabilidad.db"

DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{DB_FILE}")

connect_args = {}
if DATABASE_URL.startswith("sqlite"):
    connect_args = {"check_same_thread": False}

engine = create_engine(
    DATABASE_URL,
    connect_args=connect_args,
    echo=False,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_raw_conn():
    return sqlite3.connect(str(DB_FILE))


def init_db():
    from db import models  # noqa: F401
    Base.metadata.create_all(bind=engine)
