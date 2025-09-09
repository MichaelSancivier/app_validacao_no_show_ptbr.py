# backend/repo_reviews.py
from __future__ import annotations

from typing import List, Dict, Any
import pandas as pd
from sqlalchemy import delete, select

from .db import get_session
from .models import Review


def _norm(x) -> str:
    return (str(x) if x is not None else "").strip()


def upsert_reviews_from_df(df: pd.DataFrame, *, username: str, batch_id: str) -> int:
    """
    Grava a conferência de um atendente.
    Estratégia: apaga o batch_id informado (idempotente) e insere novamente.
    Retorna a quantidade de linhas gravadas.
    """
    if df is None or df.empty:
        return 0

    registros: List[Review] = []
    for _, row in df.iterrows():
        registros.append(
            Review(
                batch_id=batch_id,
                username=_norm(username),

                os_code=_norm(row.get("O.S.", "")),
                causa_detectada=_norm(row.get("Causa detectada", "")),
                motivo_detectado=_norm(row.get("Motivo detectado", "")),
                mascara_conferida=_norm(row.get("Máscara conferida", "")),
                classificacao_ajustada=_norm(row.get("Classificação ajustada", "")),
                status_conferencia=_norm(row.get("Status da conferência", "")),
                observacoes=_norm(row.get("Observações", "")),
                validacao_conferida=_norm(row.get("Validação automática (conferida)", "")),
                detalhe_app=_norm(row.get("Detalhe (app)", "")),
            )
        )

    with get_session() as s:
        # remove qualquer lote anterior com o mesmo batch_id (idempotência)
        s.execute(delete(Review).where(Review.batch_id == batch_id))
        if registros:
            s.bulk_save_objects(registros)
        s.commit()

    return len(registros)


def list_all_reviews_df() -> pd.DataFrame:
    """Retorna todas as conferências salvas em um DataFrame pronto para exportar."""
    with get_session() as s:
        rows = s.execute(select(Review)).scalars().all()

    if not rows:
        return pd.DataFrame()

    data: List[Dict[str, Any]] = []
    for r in rows:
        data.append(
            {
                "batch_id": r.batch_id,
                "username": r.username,
                "O.S.": r.os_code,
                "Causa detectada": r.causa_detectada,
                "Motivo detectado": r.motivo_detectado,
                "Máscara conferida": r.mascara_conferida,
                "Classificação ajustada": r.classificacao_ajustada,
                "Status da conferência": r.status_conferencia,
                "Observações": r.observacoes,
                "Validação automática (conferida)": r.validacao_conferida,
                "Detalhe (app)": r.detalhe_app,
                "created_at": r.created_at,
            }
        )

    return pd.DataFrame(data)
