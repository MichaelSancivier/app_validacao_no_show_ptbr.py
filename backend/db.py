from __future__ import annotations
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, declarative_base

DB_URL = "sqlite:///data/no_show_v3.db"  # mude o nome

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
