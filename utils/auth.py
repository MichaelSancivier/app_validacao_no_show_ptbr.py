# utils/auth.py
from __future__ import annotations
import os
import streamlit as st
import streamlit_authenticator as stauth

def _load_auth_config():
    # PRODUÇÃO: usa st.secrets (Streamlit Cloud)
    if "auth" in st.secrets:
        return st.secrets["auth"]

    # DEV (opcional): só tenta auth.yaml se existir localmente
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
        "Defina st.secrets['auth'] no Streamlit Cloud (Settings → Secrets)."
    )

def login():
    cfg = _load_auth_config()

    # 👇 NOVO: sem 'preauthorized'
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
