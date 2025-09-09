# app.py
from __future__ import annotations

import io
import re
import unicodedata
from datetime import datetime

import numpy as np
import pandas as pd
import streamlit as st

# --- infraestrutura (banco + login) ---
from backend.db import init_db
from backend.repo import (
    create_dataset,
    list_datasets,
    load_rows_for_user,
    save_conferencia,
)
from utils.auth import login

# =========================================
# Utilidades de normalização/regex
# =========================================
def _rm_acc(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")

def canon(s: str) -> str:
    if s is None or (isinstance(s, float) and pd.isna(s)):
        return ""
    s = str(s).replace("–", "-").replace("—", "-")
    s = _rm_acc(s).lower()
    s = re.sub(r"[.;:\s]+$", "", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s

def _flex(escaped: str) -> str:
    return (
        escaped.replace(r"\ ", r"\s+")
        .replace(r"\,", r"[\s,]*")
        .replace(r"\-", r"[\-\–\—]\s*")
        .replace(r"\.", r"[\.\s]*")
    )

def template_to_regex_flex(t: str):
    if t is None:
        t = ""
    t = re.sub(r"\s+", " ", str(t)).strip()
    parts = re.split(r"0+", t)
    fixed = [_flex(re.escape(p)) for p in parts]
    between = r"[\s\.,;:\-\–\—]*" + r"(.+?)" + r"[\s\.,;:\-\–\—]*"
    body = between.join(fixed)
    pattern = r"^\s*" + body + r"\s*[.,;:\-–—]*\s*$"
    try:
        return re.compile(pattern, flags=re.IGNORECASE | re.DOTALL)
    except re.error:
        return re.compile(r"^\s*" + re.escape(t) + r"\s*$", re.I)

# =========================================
# Regras embutidas + "Regra especial"
# =========================================
REGRAS_EMBUTIDAS = [
    {
        "causa": "Agendamento cancelado.",
        "motivo": "Erro De Agendamento - Cliente desconhecia o agendamento",
        "mascara_modelo": "Em contato com o cliente o mesmo informou que desconhecia o agendamento. Nome cliente: 0 / Data contato:  - ",
    },
    {
        "causa": "Agendamento cancelado.",
        "motivo": "Erro de Agendamento – Endereço incorreto",
        "mascara_modelo": "Erro identificado no agendamento: 0 . Situação:. Cliente  - informado em ",
    },
    {
        "causa": "Agendamento cancelado.",
        "motivo": "No-show Cliente – Ponto Fixo/Móvel",
        "mascara_modelo": "Cliente não compareceu para atendimento até às 0.",
    },
    {
        "causa": "Agendamento cancelado.",
        "motivo": "No-show Técnico",
        "mascara_modelo": "Técnico 0 , em  - , não realizou o atendimento por motivo de ",
    },
]

# valores que disparam a “regra especial” => vira No-show Cliente
ESPECIAIS_NO_SHOW_CLIENTE = ["Automático - PORTAL", "Michelin", "OUTRO"]

def _build_rules_map():
    return {
        (canon(r["causa"]), canon(r["motivo"])): (
            r["motivo"],
            template_to_regex_flex(r["mascara_modelo"]),
            r["mascara_modelo"],
        )
        for r in REGRAS_EMBUTIDAS
    }

RULES_MAP = _build_rules_map()

def recarregar_regras():
    global RULES_MAP
    RULES_MAP = _build_rules_map()

def eh_especial(valor: str) -> bool:
    v = canon(valor)
    return any(canon(g) in v for g in ESPECIAIS_NO_SHOW_CLIENTE if g.strip())

def read_any(f):
    if f is None:
        return None
    n = f.name.lower()
    if n.endswith(".csv"):
        try:
            return pd.read_csv(f, sep=None, engine="python")
        except Exception:
            f.seek(0)
            return pd.read_csv(f)
    try:
        return pd.read_excel(f, engine="openpyxl")
    except Exception:
        f.seek(0)
        return pd.read_excel(f)

def detect(full_text: str):
    """tenta extrair (causa, motivo, máscara) a partir do texto cheio."""
    if not full_text:
        return "", "", ""
    txt = re.sub(r"\s+", " ", str(full_text)).strip()
    txt_c = canon(txt)
    causa_c = canon("Agendamento cancelado.")
    for (c_norm, m_norm), (motivo_oficial, _rx, _mod) in RULES_MAP.items():
        if c_norm != causa_c:
            continue
        if m_norm in txt_c:
            idx = txt_c.find(m_norm) + len(m_norm)
            mascara = txt[idx:].strip(" .")
            return "Agendamento cancelado.", motivo_oficial, mascara
    return "", "", txt

def categoria(motivo: str) -> str:
    m = canon(motivo)
    if not m:
        return ""
    if m.startswith("erro de agendamento") or "erro de roteirizacao do agendamento" in m:
        return "Erro Agendamento"
    if m.startswith("falta de equipamento") or "perda/extravio" in m or "equipamento com defeito" in m:
        return "Falta de equipamentos"
    return ""

# =========================================
# STREAMLIT APP
# =========================================
st.set_page_config(page_title="Validador de No-show", layout="wide")
st.title("Validador de No-show — um app só")

# Inicializa o banco (cria tabelas)
init_db()

# ---- Login (SQLite via utils/auth.py) ----
authenticator, ok, username, name, role = login()
if ok is False:
    st.error("Usuário/senha inválidos.")
    st.stop()
elif ok is None:
    st.info("Faça login para continuar.")
    st.stop()

# Logout (compatibilidade com versões)
try:
    authenticator.logout(location="sidebar")
except TypeError:
    authenticator.logout("Sair", "sidebar")

st.sidebar.write(f"👋 {name} — **{role}**")

# =========================================
# MÓDULO 1 — Pré-análise (ADMIN)
# =========================================
if role == "admin":
    st.header("Módulo 1 — Pré-análise e publicação")

    file = st.file_uploader("Arquivo de entrada (xlsx/csv)", type=["xlsx", "csv"])
    out = None

    with st.expander("Adicionar regras rápidas (opcional)", expanded=False):
        ex = "Agendam
