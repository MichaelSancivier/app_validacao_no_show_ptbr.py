from __future__ import annotations
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, func
from sqlalchemy.orm import relationship
from .db import Base

class Dataset(Base):
    __tablename__ = "datasets"
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    created_by = Column(String, nullable=False)
    created_at = Column(DateTime, server_default=func.now())
    status = Column(String, default="em_conferencia")
    rows = relationship("PreRow", back_populates="dataset", cascade="all, delete-orphan")

class PreRow(Base):
    __tablename__ = "pre_rows"
    id = Column(Integer, primary_key=True)
    dataset_id = Column(Integer, ForeignKey("datasets.id"), index=True, nullable=False)
    dataset = relationship("Dataset", back_populates="rows")

    # Pré-análise
    os = Column(String)
    causa_detectada = Column(String)
    motivo_detectado = Column(String)
    mascara_preenchida = Column(String)
    mascara_prestador = Column(String)
    causa_motivo_mascara = Column(String)
    class_no_show = Column(String)
    detalhe = Column(String)
    resultado_no_show = Column(String)
    atendente_designado = Column(String, index=True)

    # Conferência (edição no Módulo 2)
    mascara_conferida = Column(String)
    validacao_conferida = Column(String)
    classificacao_ajustada = Column(String)
    status_conferencia = Column(String)
    observacoes = Column(String)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
