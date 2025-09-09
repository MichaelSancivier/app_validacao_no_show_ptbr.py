# backend/models.py
from __future__ import annotations

from sqlalchemy import Column, Integer, String, DateTime, Text
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


class Review(Base):
    __tablename__ = "reviews"

    id = Column(Integer, primary_key=True)

    # quem salvou / agrupamento
    batch_id = Column(String(32), index=True, nullable=False)
    username = Column(String(80), index=True, nullable=False)

    # dados da linha conferida
    os_code = Column(String(64), index=True, default="")
    causa_detectada = Column(Text, default="")
    motivo_detectado = Column(Text, default="")
    mascara_conferida = Column(Text, default="")
    classificacao_ajustada = Column(String(64), default="")
    status_conferencia = Column(String(64), default="")
    observacoes = Column(Text, default="")
    validacao_conferida = Column(String(64), default="")
    detalhe_app = Column(Text, default="")

    created_at = Column(DateTime(timezone=True), server_default=func.now())
