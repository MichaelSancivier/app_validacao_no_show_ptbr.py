# -*- coding: utf-8 -*-
from __future__ import annotations
import io
import re
import math
import json
import unicodedata
import datetime as dt
from dataclasses import dataclass
from typing import List, Dict

import numpy as np
import pandas as pd
import streamlit as st
from datetime import datetime

# ------------------------------------------------------------
# CONFIG
# ------------------------------------------------------------
st.set_page_config(page_title="Validador de No-show — PT-BR", layout="wide")
st.title("Validador de No-show — PT-BR")

# ============================================================
# Regras embutidas (modelos oficiais de causa/motivo/máscara)
# -> Base normalizada a partir das regras enviadas
# ============================================================
REGRAS_EMBUTIDAS = [
    {"causa": "Agendamento cancelado", "motivo": "Alteração do tipo de serviço  – De assistência para reinstalação", "mascara_modelo": "Não foi possível realizar o atendimento devido 0 . Cliente  foi informado sobre a necessidade de reagendamento."},
    {"causa": "Agendamento cancelado", "motivo": "Atendimento Improdutivo – Ponto Fixo/Móvel", "mascara_modelo": "Veículo compareceu para atendimento, porém por 0, não foi possível realizar o serviço."},
    {"causa": "Agendamento cancelado", "motivo": "Cancelada a Pedido do Cliente", "mascara_modelo": "Cliente 0 , contato via  em  - , informou indisponibilidade para o atendimento."},
    {"causa": "Agendamento cancelado", "motivo": "Cancelada a Pedido do Cliente", "mascara_modelo": "Cliente 0 , contato via  em  - , informou indisponibilidade para o atendimento."},
    {"causa": "Agendamento cancelado", "motivo": "Cancelamento a pedido da RT", "mascara_modelo": "Não foi possível realizar o atendimento devido 0 . Cliente  o  -  foi informado sobre a necessidade de reagendamento."},
    {"causa": "Agendamento cancelado", "motivo": "Cronograma de Instalação/Substituição de Placa", "mascara_modelo": "Realizado atendimento com substituição de placa. Alteração feita pela OS 0."},
    {"causa": "Agendamento cancelado", "motivo": "Erro De Agendamento - Cliente desconhecia o agendamento", "mascara_modelo": "Em contato com o cliente o mesmo informou que desconhecia o agendamento. Nome cliente: 0 / Data contato:  - "},
    {"causa": "Agendamento cancelado", "motivo": "Erro de Agendamento – Endereço incorreto", "mascara_modelo": "Erro identificado no agendamento: 0 . Situação:. Cliente  - informado em "},
    {"causa": "Agendamento cancelado", "motivo": "Erro de Agendamento – Falta de informações na O.S.", "mascara_modelo": "OS agendada apresentou erro de 0  e foi identificado através de . Realizado o contato com o cliente  - no dia  - "},
    {"causa": "Agendamento cancelado", "motivo": "Erro de Agendamento – O.S. agendada incorretamente (tipo/motivo/produto)", "mascara_modelo": "OS agendada apresentou erro de 0  e foi identificado através de . Realizado o contato com o cliente  - no dia  - "},
    {"causa": "Agendamento cancelado", "motivo": "Erro de roteirização do agendamento - Atendimento móvel", "mascara_modelo": "Não foi possível concluir o atendimento devido 0 . Cliente ás  -  foi informado sobre a necessidade de reagendamento. Especialista  informado ás  - "},
    {"causa": "Agendamento cancelado", "motivo": "Erro de roteirização do agendamento - Atendimento móvel", "mascara_modelo": "Não foi possível concluir o atendimento devido 0 . Cliente ás  -  foi informado sobre a necessidade de reagendamento. Especialista  informado ás  - "},
    {"causa": "Agendamento cancelado", "motivo": "Falta De Equipamento - Acessórios Imobilizado", "mascara_modelo": "Atendimento não realizado por falta de  0 . Cliente  Informado em  - "},
    {"causa": "Agendamento cancelado", "motivo": "Falta De Equipamento - Item Reservado Não Compatível", "mascara_modelo": "Atendimento não realizado por falta de  0 . Cliente  Informado em  - "},
    {"causa": "Agendamento cancelado", "motivo": "Falta De Equipamento - Material", "mascara_modelo": "Atendimento não realizado por falta de  0 . Cliente  Informado em  - "},
    {"causa": "Agendamento cancelado", "motivo": "Falta De Equipamento - Principal", "mascara_modelo": "Atendimento não realizado por falta de  0 . Cliente  Informado em  - "},
    {"causa": "Agendamento cancelado", "motivo": "Instabilidade de Equipamento/Sistema", "mascara_modelo": "Atendimento finalizado em 0  não concluído devido à instabilidade de . Registrado teste/reinstalação em  - . Realizado contato com a central  -  e foi gerada a ASM "},
    {"causa": "Agendamento cancelado", "motivo": "No-show Cliente – Ponto Fixo/Móvel", "mascara_modelo": "Cliente não compareceu para atendimento até às 0."},
    {"causa": "Agendamento cancelado", "motivo": "No-show Técnico", "mascara_modelo": "Técnico 0 , em  - , não realizou o atendimento por motivo de "},
    {"causa": "Agendamento cancelado", "motivo": "Ocorrência com Técnico – Não foi possível realizar atendimento", "mascara_modelo": "Técnico 0 , em  - , não realizou o atendimento por motivo de "},
    {"causa": "Agendamento cancelado", "motivo": "Ocorrência Com Técnico - Sem Tempo Hábil Para Realizar O Serviço (Atendimento Parcial)", "mascara_modelo": "Não foi possível concluir o atendimento devido 0 . Cliente  às  -  foi informado sobre a necessidade de reagendamento."},
    {"causa": "Agendamento cancelado", "motivo": "Ocorrência Com Técnico - Sem Tempo Hábil Para Realizar O Serviço (Não iniciado)", "mascara_modelo": "Não foi possível realizar o atendimento devido 0 . Cliente  - informado do reagendamento."},
    {"causa": "Agendamento cancelado", "motivo": "Ocorrência Com Técnico - Sem Tempo Hábil Para Realizar O Serviço (Não iniciado)", "mascara_modelo": "Não foi possível realizar o atendimento devido 0 . Cliente  - informado do reagendamento."},
    {"causa": "Agendamento cancelado", "motivo": "Ocorrência Com Técnico - Técnico Sem Habilidade Para Realizar Serviço", "mascara_modelo": "Não foi possível realizar o atendimento devido 0 . Cliente  foi informado sobre a necessidade de reagendamento."},
    {"causa": "Agendamento cancelado", "motivo": "Perda/Extravio/Falta Do Equipamento/Equipamento Com Defeito", "mascara_modelo": "Não foi possível realizar o atendimento pois 0. Cliente recusou assinar termo."},
    {"causa": "Agendamento cancelado", "motivo": "Serviço incompatível com a OS aberta", "mascara_modelo": "Não foi possível realizar o atendimento devido 0 . Cliente  às  -  foi informado sobre a necessidade de reagendamento."}
]

# ------------------------------------------------------------
# UTILITÁRIOS (normalização + regex tolerante)
# ------------------------------------------------------------
def rm_acc(s: str) -> str:
    return ''.join(c for c in unicodedata.normalize('NFD', s) if unicodedata.category(c) != 'Mn')

def canon(s: str) -> str:
    if pd.isna(s):
        return ""
    s = str(s)
    s = s.replace("–", "-").replace("—", "-")
    s = rm_acc(s).lower()
    s = re.sub(r"[.;:\s]+$", "", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s

def _flexify_fixed_literal(escaped: str) -> str:
    escaped = escaped.replace(r"\ ", r"\s+")
    escaped = escaped.replace(r"\,", r"[\s,]*")
    escaped = escaped.replace(r"\-", r"[\-\–\—]\s*")
    escaped = escaped.replace(r"\.", r"[\.\s]*")
    return escaped

def template_to_regex_flex(template: str) -> re.Pattern:
    if pd.isna(template):
        template = ""
    t = re.sub(r"\s+", " ", str(template)).strip()
    parts = re.split(r"0+", t)
    fixed = [_flexify_fixed_literal(re.escape(p)) for p in parts]
    between = r"[\s\.,;:\-\–\—]*" + r"(.+?)" + r"[\s\.,;:\-\–\—]*"
    body = between.join(fixed)
    pattern = r"^\s*" + body + r"\s*[.,;:\-–—]*\s*$"
    try:
        return re.compile(pattern, flags=re.IGNORECASE | re.DOTALL)
    except re.error:
        return re.compile(r"^\s*" + re.escape(t) + r"\s*$", flags=re.IGNORECASE)

# Mapa pré-compilado das regras
RULES_MAP = {}
for r in REGRAS_EMBUTIDAS:
    key = (canon(r["causa"]), canon(r["motivo"]))
    RULES_MAP[key] = (r["motivo"], template_to_regex_flex(r["mascara_modelo"]), r["mascara_modelo"])

def detect_motivo_and_mask(full_text: str):
    if not full_text:
        return "", "", ""
    txt = re.sub(r"\s+", " ", str(full_text)).strip()
    txt_c = canon(txt)
    causa_padrao = "Agendamento cancelado."
    causa_padrao_c = canon(causa_padrao)

    for (c_norm, m_norm), (motivo_original, _regex, _modelo) in RULES_MAP.items():
        if c_norm != causa_padrao_c:
            continue
        if m_norm in txt_c:
            idx = txt_c.find(m_norm) + len(m_norm)
            mascara = txt[idx:].strip(" .")
            return causa_padrao, motivo_original, mascara
    return "", "", txt

def read_any(f):
    if f is None:
        return None
    name = f.name.lower()
    if name.endswith(".csv"):
        try:
            return pd.read_csv(f, sep=None, engine="python")
        except Exception:
            f.seek(0); return pd.read_csv(f)
    try:
        return pd.read_excel(f, engine="openpyxl")
    except Exception:
        f.seek(0); return pd.read_excel(f)

# ------------------------------------------------------------
# Gatilhos da REGRA ESPECIAL → viram "No-show Cliente"
# ------------------------------------------------------------
ESPECIAIS_NO_SHOW_CLIENTE = ["Automático - PORTAL", "Michelin", "OUTRO"]

def eh_especial_no_show_cliente(valor: str) -> bool:
    v = canon(valor)
    return any(canon(g) in v for g in ESPECIAIS_NO_SHOW_CLIENTE if g.strip())

# ============================================================
# (Opcional) Adicionar regras rápidas (runtime)
# ============================================================
st.markdown("#### (Opcional) Adicionar regras rápidas (runtime)")
with st.expander("Adicionar novas regras **sem editar** o código"):
    st.caption("Formato: **uma regra por linha**, separando por ponto e vírgula: `causa ; motivo ; mascara_modelo`")
    exemplo = "Agendamento cancelado.; Erro de Agendamento – Documento inválido; OS apresentou erro de 0 identificado via 0. Cliente 0 informado em 0."
    regras_txt = st.text_area("Cole aqui as regras", value="", placeholder=exemplo, height=140)

    col_apply, col_clear = st.columns([1, 1])
    aplicar = col_apply.button("Aplicar regras rápidas")
    limpar  = col_clear.button("Limpar caixa")

    if limpar:
        st.session_state.pop("ultimas_regras_aplicadas", None)
        st.experimental_rerun()

    if aplicar:
        extras, erros = [], []
        for ln, linha in enumerate(regras_txt.splitlines(), start=1):
            linha = linha.strip()
            if not linha:
                continue
            parts = [p.strip() for p in linha.split(";", 2)]
            if len(parts) != 3:
                erros.append(f"Linha {ln}: use 2 ';' (causa ; motivo ; mascara_modelo)")
                continue
            causa, motivo, mascara = parts
            if not causa or not motivo or not mascara:
                erros.append(f"Linha {ln}: 'causa', 'motivo' e 'mascara_modelo' não podem estar vazios")
                continue
            extras.append({"causa": causa, "motivo": motivo, "mascara_modelo": mascara})

        if erros:
            for e in erros:
                st.warning(e)

        if extras:
            base_by_key = {(canon(r["causa"]), canon(r["motivo"])): r for r in REGRAS_EMBUTIDAS}
            for r in extras:
                key = (canon(r["causa"]), canon(r["motivo"]))
                base_by_key[key] = r
            REGRAS_EMBUTIDAS[:] = list(base_by_key.values())

            RULES_MAP.clear()
            for r in REGRAS_EMBUTIDAS:
                key = (canon(r["causa"]), canon(r["motivo"]))
                RULES_MAP[key] = (r["motivo"], template_to_regex_flex(r["mascara_modelo"]), r["mascara_modelo"])

            st.session_state["ultimas_regras_aplicadas"] = extras
            st.success(f"✅ {len(extras)} regra(s) adicionada(s)/atualizada(s). Já estão ativas nesta sessão.")

if "ultimas_regras_aplicadas" in st.session_state and st.session_state["ultimas_regras_aplicadas"]:
    st.markdown("#### Últimas regras aplicadas")
    st.dataframe(pd.DataFrame(st.session_state["ultimas_regras_aplicadas"]), use_container_width=True)

# ============================================================
# Exportar regras (JSON)
# ============================================================
st.markdown("#### Exportar regras (JSON)")

def _sort_key(r):
    return (str(r.get("causa", "")).lower(), str(r.get("motivo", "")).lower())

regras_atuais = sorted(REGRAS_EMBUTIDAS, key=_sort_key)
json_str = json.dumps(regras_atuais, ensure_ascii=False, indent=2)
fname = f"regras_no_show_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

st.download_button(
    label="📥 Baixar regras atuais (JSON)",
    data=json_str.encode("utf-8"),
    file_name=fname,
    mime="application/json",
    help="Exporta todas as regras ativas neste momento (inclui as adicionadas em runtime)."
)

with st.expander("Pré-visualizar regras (tabela)"):
    st.dataframe(pd.DataFrame(regras_atuais), use_container_width=True)

# ------------------------------------------------------------
# MÓDULO 1 — PRÉ-ANÁLISE (VALIDADOR)
# ------------------------------------------------------------
st.header("Módulo 1 — Validador (Pré-análise)")
st.markdown("""
Selecione **uma coluna** com o texto completo no formato:

**`Causa. Motivo. Máscara (preenchida pelo prestador)...`**

E (opcional) selecione uma **coluna especial**: se o valor bater em **qualquer gatilho** (ex.: `Automático - PORTAL`, `Michelin`, `OUTRO`), a linha será classificada como **No-show Cliente**.
""")

# Helper p/ 4 categorias
def categoria_por_motivo(motivo: str) -> str:
    m = canon(motivo)
    if not m:
        return ""
    if m.startswith("erro de agendamento") or "erro de roteirizacao do agendamento" in m:
        return "Erro Agendamento"
    if m.startswith("falta de equipamento") or "perda/extravio" in m or "equipamento com defeito" in m:
        return "Falta de equipamentos"
    return ""

file = st.file_uploader("Exportação (xlsx/csv) — coluna única + (opcional) coluna especial", type=["xlsx","csv"])

out = None  # será populado quando a pré-análise rodar

if file:
    df = read_any(file)
    col_main = st.selectbox("Coluna principal (Causa. Motivo. Máscara...)", df.columns)
    col_especial = st.selectbox(
        "Coluna especial (opcional) — gatilhos forçam No-show Cliente",
        ["(Nenhuma)"] + list(df.columns)
    )

    resultados, detalhes = [], []
    causas, motivos, mascaras_preenchidas = [], [], []
    combos, mascaras_modelo = [], []

    for _, row in df.iterrows():
        causa, motivo, mascara = detect_motivo_and_mask(row.get(col_main, ""))
        causas.append(causa)
        motivos.append(motivo)
        mascaras_preenchidas.append(mascara)
        partes = [p for p in [str(causa).strip(), str(motivo).strip(), str(mascara).strip()] if p]
        combos.append(" ".join(partes))

        mascara_modelo_val = ""

        if col_especial != "(Nenhuma)":
            valor_especial = row.get(col_especial, "")
            if eh_especial_no_show_cliente(valor_especial):
                resultados.append("No-show Cliente")
                detalhes.append(
                    f"Regra especial aplicada: coluna especial = '{valor_especial}'. "
                    f"Gatilhos ativos: {', '.join(ESPECIAIS_NO_SHOW_CLIENTE)}"
                )
                mascaras_modelo.append(mascara_modelo_val)
                continue

        key = (canon(causa), canon(motivo))
        found = RULES_MAP.get(key)
        if not found:
            resultados.append("No-show Técnico")
            detalhes.append("Motivo não reconhecido nas regras embutidas.")
            mascaras_modelo.append(mascara_modelo_val)
            continue

        _motivo_oficial, regex, modelo = found
        mascara_modelo_val = modelo or ""
        mascara_norm = re.sub(r"\s+", " ", str(mascara)).strip()
        if regex.fullmatch(mascara_norm):
            resultados.append("Máscara correta")
            detalhes.append("")
        else:
            resultados.append("No-show Técnico")
            detalhes.append("Não casa com o modelo (mesmo no modo tolerante).")
        mascaras_modelo.append(mascara_modelo_val)

    out = df.copy()
    out["Causa detectada"] = causas
    out["Motivo detectado"] = motivos
    out["Máscara prestador (preenchida)"] = mascaras_preenchidas
    out["Máscara prestador"] = mascaras_modelo
    out["Causa. Motivo. Máscara (extra)"] = combos
    out["Classificação No-show"] = resultados
    out["Detalhe"] = detalhes

    # Resultado No Show (4 categorias)
    resultado_no_show = []
    for r_cls, mot in zip(resultados, motivos):
        cat = categoria_por_motivo(mot)
        if cat:
            resultado_no_show.append(cat)
        elif r_cls in ("Máscara correta", "No-show Cliente"):
            resultado_no_show.append("No-show Cliente")
        else:
            resultado_no_show.append("No-show Técnico")
    out["Resultado No Show"] = resultado_no_show

    # Alocação de atendentes
    st.markdown("### Alocação de atendentes (opcional)")
    qtd_atend = st.number_input("Número de atendentes", min_value=1, max_value=200, value=3, step=1)
    nomes_raw = st.text_area(
        "Nomes dos atendentes (um por linha ou separados por vírgula/;)",
        value="",
        placeholder="Ex.: Ana\nBruno\nCarla  (ou)  Ana, Bruno, Carla"
    )

    nomes_list = [n.strip() for n in re.split(r"[,;\n]+", nomes_raw) if n.strip()]
    if not nomes_list:
        nomes_list = [f"Atendente {i+1}" for i in range(int(qtd_atend))]
    else:
        while len(nomes_list) < int(qtd_atend):
            nomes_list.append(f"Atendente {len(nomes_list)+1}")
    n_final = len(nomes_list)

    total_linhas = len(out)
    bloco = math.ceil(total_linhas / n_final) if n_final else total_linhas
    designados = (nomes_list * bloco)[:total_linhas]

    try:
        pos = out.columns.get_loc("Causa detectada")
        out.insert(pos, "Atendente designado", designados)
    except Exception:
        out["Atendente designado"] = designados

    # Exportação (Pré-análise)
    st.markdown("### Exportação — seleção de colunas")
    export_all_pre = st.checkbox(
        "Exportar **todas** as colunas (originais + geradas)",
        value=True,
        help="Desmarque para escolher manualmente quais colunas vão para o Excel."
    )

    geradas_order = [
        "Atendente designado",
        "Causa detectada",
        "Motivo detectado",
        "Máscara prestador (preenchida)",
        "Máscara prestador",
        "Causa. Motivo. Máscara (extra)",
        "Classificação No-show",
        "Detalhe",
        "Resultado No Show",
    ]
    originais = [c for c in df.columns if c in out.columns]
    geradas   = [c for c in geradas_order if c in out.columns]
    todas_cols_pre = originais + geradas

    if export_all_pre:
        cols_export_pre = todas_cols_pre
    else:
        st.caption("Escolha as colunas que irão para o arquivo (ordem respeitada):")
        default_pre = [c for c in ["O.S.", "MOTIVO CANCELAMENTO", "Atendente designado",
                                   "Causa detectada", "Motivo detectado",
                                   "Classificação No-show", "Resultado No Show"] if c in todas_cols_pre]
        cols_export_pre = st.multiselect("Colunas para exportar", options=todas_cols_pre, default=default_pre)
        if not cols_export_pre:
            st.warning("Nenhuma coluna selecionada. Exportarei todas as colunas.")
            cols_export_pre = todas_cols_pre

    st.success("Validação concluída.")
    st.dataframe(out[cols_export_pre], use_container_width=True)

    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as w:
        out[cols_export_pre].to_excel(w, index=False, sheet_name="Resultado")
    st.download_button(
        "Baixar Excel — Pré-análise (com seleção de colunas)",
        data=buf.getvalue(),
        file_name="resultado_no_show.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
else:
    st.info("Envie a exportação; selecione a coluna única e (opcionalmente) a coluna especial.")

# ============================================
# NOVO MÓDULO 2 — CONFERÊNCIA (NO PRÓPRIO APP)
# ============================================
st.markdown("---")
st.header("Módulo 2 — Conferência (dentro do app)")

if out is None:
    st.info("Para habilitar a conferência, rode a Pré-análise acima (carregue o arquivo e gere o resultado).")
else:
    # ---- Config & Aliases do Módulo 2 ---- #
    RESULTADO_OPCOES_DEFAULT = [
        "No-show Cliente",
        "No-show Técnico",
        "Erro Agendamento",
        "Erro de dados",
        "Falta de equipamentos",
    ]
    ALIASES = {
        "os": ["O.S.", "OS", "Nº O.S.", "Nº OS", "OS_ID", "ID_OS"],
        "motivo_detectado": ["Motivo detectado", "Motivo Detectado"],
        "mascara_preenchida": ["Máscara prestador (preenchida)", "Mascara prestador (preenchida)", "Mascara prestador preenchida"],
        "mascara_prestador": ["Máscara prestador", "Mascara prestador"],
        "causa_motivo_mascara": ["Causa. Motivo. Máscara (extra)", "Causa. Motivo. Máscara", "Causa/Motivo/Máscara"],
        "class_no_show": ["Classificação No-show", "Classificacao No-show", "Classificação No Show"],
        "detalhe": ["Detalhe", "Detalhes"],
        "resultado_no_show": ["Resultado No Show", "Resultado No-show", "Resultado NoShow"],
        "atendente_designado": ["Atendente designado", "Atendente Designado", "Atendente"],
    }
    CONF_COLS_C1 = {
        "motivo_ok_c1": "Motivo detectado correto? (C1)",
        "mascara_ok_c1": "Máscara prestador correta? (C1)",
        "resultado_show2_c1": "Resultado Show2 (C1)",
        "mascara_atendente_c1": "Máscara Atendente (final) (C1)",
        "conferente_c1": "Conferente (C1)",
        "datahora_c1": "Data/Hora (C1)",
    }
    CONF_COLS_C2 = {
        "motivo_ok_c2": "Motivo detectado correto? (C2)",
        "mascara_ok_c2": "Máscara prestador correta? (C2)",
        "resultado_show2_c2": "Resultado Show2 (C2)",
        "mascara_atendente_c2": "Máscara Atendente (final) (C2)",
        "conferente_c2": "Conferente (C2)",
        "datahora_c2": "Data/Hora (C2)",
        "decisao_c2": "Decisão C2",
    }
    DECISAO_C2_OPCOES = ["Concordo com C1", "Corrijo C1 (manter APP)", "Outro (editar campos)"]
    DERIVED_COLS = {"veredito": "Veredito (auto)", "status": "Status"}

    def _first_match(colnames: List[str], aliases: List[str]) -> str | None:
        for a in aliases:
            for c in colnames:
                if c.strip().lower() == a.strip().lower():
                    return c
        return None

    def normalize_pre_df(pre_df: pd.DataFrame) -> pd.DataFrame:
        df = pre_df.copy()
        colmap = {}
        for key, aliases in ALIASES.items():
            found = _first_match(df.columns.tolist(), aliases)
            colmap[key] = found if found else None
        if not colmap.get("resultado_no_show"):
            raise ValueError("Coluna obrigatória ausente: 'Resultado No Show' (ou alias).")
        rename_pairs = {}
        for key, src in colmap.items():
            if src:
                rename_pairs[src] = key
        df = df.rename(columns=rename_pairs)
        for k in ["os", "motivo_detectado", "mascara_preenchida", "mascara_prestador",
                  "causa_motivo_mascara", "class_no_show", "detalhe", "atendente_designado"]:
            if k not in df.columns:
                df[k] = ""
        return df

    def build_review_frame(base_df: pd.DataFrame, dupla: bool, conferente_padrao: str = "") -> pd.DataFrame:
        review = pd.DataFrame(index=base_df.index)
        review[CONF_COLS_C1["motivo_ok_c1"]] = pd.Series(False, index=base_df.index, dtype="bool")
        review[CONF_COLS_C1["mascara_ok_c1"]] = pd.Series(False, index=base_df.index, dtype="bool")
        review[CONF_COLS_C1["resultado_show2_c1"]] = base_df["resultado_no_show"].astype(str)
        review[CONF_COLS_C1["mascara_atendente_c1"]] = ""
        review[CONF_COLS_C1["conferente_c1"]] = conferente_padrao
        review[CONF_COLS_C1["datahora_c1"]] = ""
        if dupla:
            review[CONF_COLS_C2["motivo_ok_c2"]] = pd.Series(False, index=base_df.index, dtype="bool")
            review[CONF_COLS_C2["mascara_ok_c2"]] = pd.Series(False, index=base_df.index, dtype="bool")
            review[CONF_COLS_C2["resultado_show2_c2"]] = base_df["resultado_no_show"].astype(str)
            review[CONF_COLS_C2["mascara_atendente_c2"]] = ""
            review[CONF_COLS_C2["conferente_c2"]] = ""
            review[CONF_COLS_C2["datahora_c2"]] = ""
            review[CONF_COLS_C2["decisao_c2"]] = ""
        review[DERIVED_COLS["veredito"]] = "PENDENTE"
        review[DERIVED_COLS["status"]] = "Pendente"
        return review

    @dataclass
    class EncerramentoConfig:
        dupla_checagem: bool = False

    def compute_veredito_and_status(row: pd.Series, app_res_col: str, cfg: EncerramentoConfig) -> Dict[str, str]:
        motivo_ok_c1 = bool(row.get(CONF_COLS_C1["motivo_ok_c1"], False))
        mascara_ok_c1 = bool(row.get(CONF_COLS_C1["mascara_ok_c1"], False))
        show2_c1 = (row.get(CONF_COLS_C1["resultado_show2_c1"], "") or "").strip()
        mascarafinal_c1 = (row.get(CONF_COLS_C1["mascara_atendente_c1"], "") or "").strip()
        app_res = (row.get(app_res_col, "") or "").strip()

        if motivo_ok_c1 and mascara_ok_c1 and show2_c1 == app_res:
            if not cfg.dupla_checagem:
                return {"veredito": "APP_CORRETO", "status": "Aprovado (1/1)"}
            else:
                ver = "APP_CORRETO"
                motivo_ok_c2 = bool(row.get(CONF_COLS_C2["motivo_ok_c2"], False))
                mascara_ok_c2 = bool(row.get(CONF_COLS_C2["mascara_ok_c2"], False))
                show2_c2 = (row.get(CONF_COLS_C2["resultado_show2_c2"], "") or "").strip()
                decisao_c2 = (row.get(CONF_COLS_C2["decisao_c2"], "") or "").strip()
                if motivo_ok_c2 and mascara_ok_c2 and show2_c2 == app_res:
                    return {"veredito": ver, "status": "Aprovado (2/2)"}
                elif decisao_c2 == "Corrijo C1 (manter APP)":
                    return {"veredito": "ATENDENTE_ERRADO_APP_CORRETO", "status": "Aprovado (2/2)"}
                elif decisao_c2 == "Concordo com C1":
                    return {"veredito": ver, "status": "Aprovado (2/2)"}
                else:
                    return {"veredito": ver, "status": "Conferência 1"}

        houve_divergencia_c1 = (not motivo_ok_c1) or (not mascara_ok_c1) or (show2_c1 != app_res)
        c1_preenchido = len(mascarafinal_c1) > 0 or show2_c1 != ""

        if houve_divergencia_c1 and c1_preenchido:
            if not cfg.dupla_checagem:
                return {"veredito": "APP_ERRADO_ATENDENTE_CORRETO", "status": "Aprovado (1/1)"}
            else:
                decisao_c2 = (row.get(CONF_COLS_C2["decisao_c2"], "") or "").strip()
                show2_c2 = (row.get(CONF_COLS_C2["resultado_show2_c2"], "") or "").strip()
                if decisao_c2 == "Concordo com C1":
                    return {"veredito": "APP_ERRADO_ATENDENTE_CORRETO", "status": "Aprovado (2/2)"}
                elif decisao_c2 == "Corrijo C1 (manter APP)" and show2_c2 == app_res:
                    return {"veredito": "ATENDENTE_ERRADO_APP_CORRETO", "status": "Aprovado (2/2)"}
                elif decisao_c2 == "Outro (editar campos)":
                    return {"veredito": "AMBOS_ERRADOS_REVISAR", "status": "Divergência"}
                else:
                    return {"veredito": "APP_ERRADO_ATENDENTE_CORRETO", "status": "Conferência 1"}

        return {"veredito": "PENDENTE", "status": "Pendente"}

    # ---------- UI do Módulo 2 ---------- #
    conferente = st.text_input("Seu nome (conferente)", value="")
    dupla = st.toggle("Ativar dupla checagem?", value=False, help="Se ligado, exige decisão do C2 para encerrar 2/2.")

    base = normalize_pre_df(out)

    fila_opts = ["(Todos)"] + sorted([x for x in base["atendente_designado"].astype(str).unique() if x])
    fila_sel = st.selectbox("Filtrar por Atendente designado", fila_opts)
    if fila_sel != "(Todos)":
        base = base[base["atendente_designado"].astype(str) == str(fila_sel)]

    if "_review_store" not in st.session_state:
        st.session_state._review_store = {}

    cache_key = f"review:{hash(tuple(base.index))}:{dupla}"
    review = st.session_state._review_store.get(cache_key)
    if review is None:
        review = build_review_frame(base, dupla, conferente_padrao=conferente)
        st.session_state._review_store[cache_key] = review
    else:
        if conferente and not review[CONF_COLS_C1["conferente_c1"]].any():
            review[CONF_COLS_C1["conferente_c1"]] = conferente

    composed = pd.concat([base.reset_index(drop=True), review.reset_index(drop=True)], axis=1)

    col_cfg = {}
    for c in ["os","motivo_detectado","mascara_preenchida","mascara_prestador",
              "causa_motivo_mascara","class_no_show","detalhe","resultado_no_show","atendente_designado"]:
        if c in composed.columns:
            col_cfg[c] = st.column_config.TextColumn(c, disabled=True)

    col_cfg[CONF_COLS_C1["motivo_ok_c1"]] = st.column_config.CheckboxColumn(CONF_COLS_C1["motivo_ok_c1"])
    col_cfg[CONF_COLS_C1["mascara_ok_c1"]] = st.column_config.CheckboxColumn(CONF_COLS_C1["mascara_ok_c1"])

    opcoes_result = sorted(list(set(list(RESULTADO_OPCOES_DEFAULT) + base["resultado_no_show"].astype(str).unique().tolist())))
    col_cfg[CONF_COLS_C1["resultado_show2_c1"]] = st.column_config.SelectboxColumn(CONF_COLS_C1["resultado_show2_c1"], options=opcoes_result)
    col_cfg[CONF_COLS_C1["mascara_atendente_c1"]] = st.column_config.TextColumn(CONF_COLS_C1["mascara_atendente_c1"], help="Preencha se discordar do app.")
    col_cfg[CONF_COLS_C1["conferente_c1"]] = st.column_config.TextColumn(CONF_COLS_C1["conferente_c1"], default=conferente)
    col_cfg[CONF_COLS_C1["datahora_c1"]] = st.column_config.TextColumn(CONF_COLS_C1["datahora_c1"], help="Preenchido automaticamente ao editar.")

    if dupla:
        col_cfg[CONF_COLS_C2["motivo_ok_c2"]] = st.column_config.CheckboxColumn(CONF_COLS_C2["motivo_ok_c2"])
        col_cfg[CONF_COLS_C2["mascara_ok_c2"]] = st.column_config.CheckboxColumn(CONF_COLS_C2["mascara_ok_c2"])
        col_cfg[CONF_COLS_C2["resultado_show2_c2"]] = st.column_config.SelectboxColumn(CONF_COLS_C2["resultado_show2_c2"], options=opcoes_result)
        col_cfg[CONF_COLS_C2["mascara_atendente_c2"]] = st.column_config.TextColumn(CONF_COLS_C2["mascara_atendente_c2"])
        col_cfg[CONF_COLS_C2["conferente_c2"]] = st.column_config.TextColumn(CONF_COLS_C2["conferente_c2"])
        col_cfg[CONF_COLS_C2["datahora_c2"]] = st.column_config.TextColumn(CONF_COLS_C2["datahora_c2"])
        col_cfg[CONF_COLS_C2["decisao_c2"]] = st.column_config.SelectboxColumn(CONF_COLS_C2["decisao_c2"], options=[""] + DECISAO_C2_OPCOES)

    col_cfg[DERIVED_COLS["veredito"]] = st.column_config.TextColumn(DERIVED_COLS["veredito"], disabled=True)
    col_cfg[DERIVED_COLS["status"]] = st.column_config.TextColumn(DERIVED_COLS["status"], disabled=True)

    st.markdown("### Fila para conferência")
    st.caption("À esquerda: pré-análise (somente leitura). Edite as colunas azuis para confirmar/ajustar.")

    edited = st.data_editor(
        composed,
        num_rows="fixed",
        use_container_width=True,
        key="grid_conferencia",
        column_config=col_cfg,
        hide_index=True,
    )

    def _fill_ts(orig: pd.DataFrame, edt: pd.DataFrame) -> pd.DataFrame:
        now = dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        for fld in [CONF_COLS_C1["motivo_ok_c1"], CONF_COLS_C1["mascara_ok_c1"], CONF_COLS_C1["resultado_show2_c1"], CONF_COLS_C1["mascara_atendente_c1"]]:
            if not edt.equals(orig):
                mask_changed = edt[fld].astype(str) != orig.get(fld, edt[fld]).astype(str)
                edt.loc[mask_changed, CONF_COLS_C1["datahora_c1"]] = now
                if conferente:
                    edt.loc[mask_changed, CONF_COLS_C1["conferente_c1"]] = conferente
        if dupla:
            for fld in [CONF_COLS_C2["motivo_ok_c2"], CONF_COLS_C2["mascara_ok_c2"], CONF_COLS_C2["resultado_show2_c2"], CONF_COLS_C2["mascara_atendente_c2"], CONF_COLS_C2["decisao_c2"]]:
                mask_changed = edt[fld].astype(str) != orig.get(fld, edt[fld]).astype(str)
                edt.loc[mask_changed, CONF_COLS_C2["datahora_c2"]] = now
        return edt

    edited = _fill_ts(composed, edited)

    cfg = EncerramentoConfig(dupla_checagem=dupla)
    verdicts, statuses = [], []
    for _, r in edited.iterrows():
        out_vs = compute_veredito_and_status(r, app_res_col="resultado_no_show", cfg=cfg)
        verdicts.append(out_vs["veredito"])
        statuses.append(out_vs["status"])
    edited[DERIVED_COLS["veredito"]] = verdicts
    edited[DERIVED_COLS["status"]] = statuses

    keep_cols = list(CONF_COLS_C1.values()) + (list(CONF_COLS_C2.values()) if dupla else []) + list(DERIVED_COLS.values())
    st.session_state._review_store[cache_key] = edited[keep_cols].copy()

    st.divider()
    st.subheader("Exportação / Progresso")

    def _export_xlsx(df_out: pd.DataFrame) -> bytes:
        buf = io.BytesIO()
        with pd.ExcelWriter(buf, engine="openpyxl") as writer:
            df_out.to_excel(writer, index=False, sheet_name="Resultado")
        buf.seek(0)
        return buf.read()

    merged_out = edited.copy()

    c1, c2, c3 = st.columns(3)
    with c1:
        xlsx_bytes = _export_xlsx(merged_out)
        st.download_button("⬇️ Baixar Excel consolidado", data=xlsx_bytes, file_name="validacao_conferencia.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    with c2:
        json_bytes = merged_out.to_json(orient="records").encode("utf-8")
        st.download_button("💾 Baixar checkpoint (JSON)", data=json_bytes, file_name="checkpoint_conferencia.json", mime="application/json")
    with c3:
        st.write(" ")
        st.info("O Excel inclui colunas da pré-análise (read-only) + conferência (editáveis) + veredito/status.")

    st.subheader("Resumo")
    resumo = (
        merged_out[DERIVED_COLS["status"]]
        .value_counts(dropna=False)
        .rename_axis("Status")
        .reset_index(name="Qtd")
    )
    st.dataframe(resumo, use_container_width=True)

    st.caption(
        "Encerramento por linha: 'Aprovado (1/1)' quando checagem simples concluir; "
        "'Aprovado (2/2)' quando dupla checagem concluir; 'Divergência' quando há conflito sem decisão."
    )

# Fim — V1.1.0 (Pré-análise + Conferência integrada)

