# backend/db.py
from __future__ import annotations
import os
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, declarative_base

# >>> garanta a pasta 'data/' e escolha o nome do arquivo
DB_DIR = "data"
DB_FILE = "no_show_v5.db"           # você pode trocar esse nome quando quiser resetar
os.makedirs(DB_DIR, exist_ok=True)  # <- cria a pasta no Cloud
DB_URL = f"sqlite:///{os.path.join(DB_DIR, DB_FILE)}"

engine = create_engine(DB_URL, future=True)

@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_conn, conn_record):
    cur = dbapi_conn.cursor()
    cur.execute("PRAGMA journal_mode=WAL;")
    cur.execute("PRAGMA synchronous=NORMAL;")
    cur.close()

SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False, future=True)
Base = declarative_base()

def init_db():
    from . import models  # registra as tabelas
    Base.metadata.create_all(engine)

def get_session():
    return SessionLocal()
