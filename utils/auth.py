# utils/auth.py
from __future__ import annotations
import os
import streamlit as st
import streamlit_authenticator as stauth
from collections.abc import Mapping, Sequence

def _deep_to_dict(obj):
    """Converte Secrets (e aninhados) em dict/list normais."""
    if isinstance(obj, Mapping):
        return {k: _deep_to_dict(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_deep_to_dict(v) for v in obj]
    return obj

def _load_auth_config():
    # 1) PRODUÇÃO: Secrets do Streamlit Cloud
    if "auth" in st.secrets:
        return _deep_to_dict(st.secrets["auth"])  # <<< transforma em dict mutável

    # 2) DEV opcional: auth.yaml local (NÃO subir no GitHub)
    if os.path.exists("auth.yaml"):
        try:
            import yaml
            from yaml.loader import SafeLoader
            with open("auth.yaml", "r", encoding="utf-8") as f:
                return yaml.load(f, Loader=SafeLoader)
        except Exception as e:
            raise RuntimeError(f"Falha ao ler auth.yaml: {e}")

    raise RuntimeError(
        "Config de autenticação não encontrada. "
        "Preencha st.secrets['auth'] no Streamlit Cloud (Settings → Secrets)."
    )

def login():
    cfg = _load_auth_config()

    # Versões novas do streamlit-authenticator (sem 'preauthorized')
    authenticator = stauth.Authenticate(
        cfg["credentials"],
        cfg["cookie"]["name"],
        cfg["cookie"]["key"],
        cfg["cookie"]["expiry_days"],
    )

    name, auth_status, username = authenticator.login("Login", "main")
    role = None
    if auth_status:
        role = cfg["credentials"]["usernames"][username].get("role", "atendente")
    return authenticator, auth_status, username, name, role
