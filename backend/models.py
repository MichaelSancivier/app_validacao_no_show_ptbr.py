# backend/models.py
from __future__ import annotations

from sqlalchemy import (
    Column, Integer, String, Text, DateTime, func, UniqueConstraint
)
from .db import Base


class User(Base):
    __tablename__ = "users"

    id         = Column(Integer, primary_key=True)
    username   = Column(String(64), unique=True, index=True, nullable=False)
    name       = Column(String(120), nullable=False)
    password   = Column(String(255), nullable=False)   # hash bcrypt
    role       = Column(String(32),  nullable=False, default="atendente")  # 'admin' | 'atendente'
    active     = Column(Integer,    nullable=False, default=1)             # 1=ativo, 0=inativo
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now(), server_default=func.now())


class Review(Base):
    """
    Consolidação das conferências feitas no Módulo 2.
    Uma linha por (O.S., atendente). Se salvar de novo, atualiza.
    """
    __tablename__ = "reviews"

    id                  = Column(Integer, primary_key=True)
    batch_id            = Column(String(64), nullable=True)        # opcional: id do lote
    os                  = Column(String(128), index=True, nullable=True)
    atendente           = Column(String(64),  index=True, nullable=False)  # username logado

    mask_conferida      = Column(Text,       nullable=True)
    class_ajustada      = Column(String(64), nullable=True)
    status              = Column(String(64), nullable=True)        # "✅ App acertou" etc.
    obs                 = Column(Text,       nullable=True)
    validacao           = Column(String(64), nullable=True)        # "✅ Máscara correta" etc.

    causa               = Column(Text,       nullable=True)
    motivo              = Column(Text,       nullable=True)
    resultado_no_show   = Column(String(64), nullable=True)

    created_at          = Column(DateTime, server_default=func.now())
    updated_at          = Column(DateTime, onupdate=func.now(), server_default=func.now())

    # evita duplicar a mesma OS para o mesmo atendente
    __table_args__ = (UniqueConstraint("os", "atendente", name="uq_reviews_os_user"),)

