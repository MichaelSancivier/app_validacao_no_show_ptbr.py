# utils/auth.py
from __future__ import annotations

import inspect
from collections.abc import Mapping
from typing import Tuple

import bcrypt
import streamlit as st
import streamlit_authenticator as stauth

from backend.repo_users import credentials_from_db, ensure_bootstrap_admin


# -----------------------------
# Util: rerun compatível (v1.4x+)
# -----------------------------
def _rerun():
    try:
        st.rerun()
    except Exception:
        try:
            st.experimental_rerun()
        except Exception:
            pass


# -----------------------------
# Helpers de configuração
# -----------------------------
def _deep_to_dict(obj):
    if isinstance(obj, Mapping):
        return {k: _deep_to_dict(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_deep_to_dict(v) for v in obj]
    return obj


def _cookie_cfg() -> Tuple[str, str, int]:
    """
    Lê a config de cookie dos Secrets (se existir).
    Caso contrário, usa defaults seguros (troque a key em produção!).
    """
    if "auth" in st.secrets and "cookie" in st.secrets["auth"]:
        c = _deep_to_dict(st.secrets["auth"]["cookie"])
        return c["name"], c["key"], c["expiry_days"]
    # defaults
    return "vns_auth", "mude_esta_chave_em_prod", 14


def _load_auth_config() -> dict:
    """
    Carrega credenciais (prioriza SQLite).
    Se não houver usuários, cria o admin inicial (bootstrap) e avisa na tela.
    Como fallback opcional, aceita Secrets['auth'].
    """
    # 1) Banco (preferido)
    from_db = credentials_from_db()
    if from_db:
        name, key, days = _cookie_cfg()
        return {"credentials": from_db, "cookie": {"name": name, "key": key, "expiry_days": days}}

    # 2) Bootstrap do admin se banco está vazio
    first_pwd = ensure_bootstrap_admin()
    if first_pwd:
        st.warning(
            f"👑 Admin inicial criado: **usuário `admin`** / **senha `{first_pwd}`**. "
            "Faça login e troque a
