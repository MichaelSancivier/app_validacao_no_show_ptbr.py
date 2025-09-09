from __future__ import annotations
import pandas as pd
from sqlalchemy import select, update
from .db import get_session
from .models import Dataset, PreRow

def create_dataset(name: str, created_by: str, pre_df: pd.DataFrame) -> int:
    with get_session() as s:
        ds = Dataset(name=name, created_by=created_by)
        s.add(ds); s.flush()  # ds.id disponível

        recs = []
        for _, r in pre_df.iterrows():
            recs.append(PreRow(
                dataset_id=ds.id,
                os=str(r.get("O.S.", "")),
                causa_detectada=str(r.get("Causa detectada","")),
                motivo_detectado=str(r.get("Motivo detectado","")),
                mascara_preenchida=str(r.get("Máscara prestador (preenchida)","")),
                mascara_prestador=str(r.get("Máscara prestador","")),
                causa_motivo_mascara=str(r.get("Causa. Motivo. Máscara (extra)","")),
                class_no_show=str(r.get("Classificação No-show","")),
                detalhe=str(r.get("Detalhe","")),
                resultado_no_show=str(r.get("Resultado No Show","")),
                atendente_designado=str(r.get("Atendente designado","")),
            ))
        s.add_all(recs)
        s.commit()
        return ds.id

def list_datasets():
    with get_session() as s:
        return s.execute(select(Dataset.id, Dataset.name, Dataset.created_at, Dataset.status)).all()

def load_rows_for_user(dataset_id: int, role: str, username: str) -> pd.DataFrame:
    with get_session() as s:
        if role == "admin":
            rows = s.execute(select(PreRow).where(PreRow.dataset_id==dataset_id)).scalars().all()
        else:
            rows = s.execute(select(PreRow).where(
                PreRow.dataset_id==dataset_id, PreRow.atendente_designado==username
            )).scalars().all()

    df = pd.DataFrame([{
        "row_id": r.id,
        "O.S.": r.os,
        "Causa detectada": r.causa_detectada,
        "Motivo detectado": r.motivo_detectado,
        "Máscara prestador (preenchida)": r.mascara_preenchida,
        "Máscara prestador": r.mascara_prestador,
        "Causa. Motivo. Máscara (extra)": r.causa_motivo_mascara,
        "Classificação No-show": r.class_no_show,
        "Detalhe": r.detalhe,
        "Resultado No Show": r.resultado_no_show,
        "Atendente designado": r.atendente_designado,
        # campos de conferência (podem estar vazios)
        "Máscara conferida": r.mascara_conferida or "",
        "Validação automática (conferida)": r.validacao_conferida or "",
        "Classificação ajustada": r.classificacao_ajustada or "",
        "Status da conferência": r.status_conferencia or "",
        "Observações": r.observacoes or "",
    } for r in rows])
    return df

def save_conferencia(df_editado: pd.DataFrame):
    with get_session() as s:
        for _, r in df_editado.iterrows():
            rid = int(r["row_id"])
            s.execute(update(PreRow).where(PreRow.id==rid).values(
                mascara_conferida=str(r.get("Máscara conferida","")),
                validacao_conferida=str(r.get("Validação automática (conferida)","")),
                classificacao_ajustada=str(r.get("Classificação ajustada","")),
                status_conferencia=str(r.get("Status da conferência","")),
                observacoes=str(r.get("Observações","")),
            ))
        s.commit()
