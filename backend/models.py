# backend/models.py
from __future__ import annotations

from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.sql import func

from .db import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    username = Column(String(80), unique=True, index=True, nullable=False)
    name = Column(String(120), nullable=False, default="")
    password = Column(String(255), nullable=False)  # hash bcrypt
    role = Column(String(32), nullable=False, default="atendente")
    active = Column(Integer, nullable=False, default=1)  # 1=ativo, 0=inativo

    created_at = Column(DateTime(timezone=True), server_default=func.now())
