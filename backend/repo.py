# backend/repo_reviews.py
from __future__ import annotations
from typing import Optional
import pandas as pd
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from backend.db import SessionLocal, Review

def upsert_reviews_from_df(df: pd.DataFrame, username: str, batch_id: Optional[str] = None) -> int:
    """
    Grava/atualiza as linhas de conferência do atendente no banco.
    Retorna quantidade de linhas gravadas.
    """
    if df.empty:
        return 0

    wanted_cols = [
        "O.S.", "Máscara conferida", "Classificação ajustada", "Status da conferência",
        "Observações", "Validação automática (conferida)", "Causa detectada",
        "Motivo detectado", "Resultado No Show"
    ]
    for c in wanted_cols:
        if c not in df.columns:
            df[c] = ""

    n = 0
    with SessionLocal() as s:
        for _, row in df.iterrows():
            os = str(row.get("O.S.", "")).strip() or None
            if not os:
                continue
            # tenta localizar já existente
            r = s.execute(
                select(Review).where(Review.os == os, Review.atendente == username)
            ).scalar_one_or_none()

            if r is None:
                r = Review(os=os, atendente=username)
                s.add(r)

            r.batch_id = batch_id or r.batch_id
            r.mask_conferida = str(row.get("Máscara conferida", "") or "")
            r.class_ajustada = str(row.get("Classificação ajustada", "") or "")
            r.status = str(row.get("Status da conferência", "") or "")
            r.obs = str(row.get("Observações", "") or "")
            r.validacao = str(row.get("Validação automática (conferida)", "") or "")
            r.causa = str(row.get("Causa detectada", "") or "")
            r.motivo = str(row.get("Motivo detectado", "") or "")
            r.resultado_no_show = str(row.get("Resultado No Show", "") or "")
            try:
                s.commit()
                n += 1
            except IntegrityError:
                s.rollback()
    return n


def list_all_reviews_df() -> pd.DataFrame:
    """Retorna tudo consolidado."""
    with SessionLocal() as s:
        q = s.execute(select(Review)).scalars().all()
    if not q:
        return pd.DataFrame()
    return pd.DataFrame([{
        "O.S.": r.os,
        "Atendente": r.atendente,
        "Máscara conferida": r.mask_conferida,
        "Classificação ajustada": r.class_ajustada,
        "Status da conferência": r.status,
        "Observações": r.obs,
        "Validação automática (conferida)": r.validacao,
        "Causa detectada": r.causa,
        "Motivo detectado": r.motivo,
        "Resultado No Show": r.resultado_no_show,
        "Atualizado em": r.updated_at or r.created_at,
        "Lote": r.batch_id,
    } for r in q])
