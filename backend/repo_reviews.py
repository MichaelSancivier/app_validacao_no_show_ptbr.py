# backend/repo_reviews.py
from __future__ import annotations
from typing import Optional
import pandas as pd
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from .db import get_session
from .models import Review


def upsert_reviews_from_df(
    df: pd.DataFrame,
    username: str,
    batch_id: Optional[str] = None,
) -> int:
    """
    Grava/atualiza no banco as linhas conferidas pelo atendente.
    Retorna a quantidade de registros persistidos.
    """
    if df is None or df.empty:
        return 0

    # Garante colunas esperadas
    wanted = [
        "O.S.",
        "Máscara conferida",
        "Classificação ajustada",
        "Status da conferência",
        "Observações",
        "Validação automática (conferida)",
        "Causa detectada",
        "Motivo detectado",
        "Resultado No Show",
    ]
    for c in wanted:
        if c not in df.columns:
            df[c] = ""

    n = 0
    with get_session() as s:
        for _, row in df.iterrows():
            os = str(row.get("O.S.", "")).strip() or None
            if not os:
                continue

            r = s.execute(
                select(Review).where(Review.os == os, Review.atendente == username)
            ).scalar_one_or_none()

            if r is None:
                r = Review(os=os, atendente=username)
                s.add(r)

            r.batch_id          = batch_id or r.batch_id
            r.mask_conferida    = str(row.get("Máscara conferida", "") or "")
            r.class_ajustada    = str(row.get("Classificação ajustada", "") or "")
            r.status            = str(row.get("Status da conferência", "") or "")
            r.obs               = str(row.get("Observações", "") or "")
            r.validacao         = str(row.get("Validação automática (conferida)", "") or "")
            r.causa             = str(row.get("Causa detectada", "") or "")
            r.motivo            = str(row.get("Motivo detectado", "") or "")
            r.resultado_no_show = str(row.get("Resultado No Show", "") or "")

            try:
                s.commit()
                n += 1
            except IntegrityError:
                s.rollback()

    return n


def list_all_reviews_df() -> pd.DataFrame:
    """Retorna a consolidação total das conferências salvas."""
    with get_session() as s:
        rows = s.execute(select(Review)).scalars().all()

    if not rows:
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
        "Lote": r.batch_id,
        "Atualizado em": r.updated_at or r.created_at,
    } for r in rows])
