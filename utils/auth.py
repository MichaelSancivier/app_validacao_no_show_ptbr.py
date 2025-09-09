from __future__ import annotations
import streamlit as st
import yaml
from yaml.loader import SafeLoader
import streamlit_authenticator as stauth

def _load_auth_config():
    # 1º: tenta Streamlit Secrets (produção)
    if "auth" in st.secrets:
        return st.secrets["auth"]
    # 2º: fallback DEV (opcional, local) -> auth.yaml (NÃO subir no GitHub)
    with open("auth.yaml", "r", encoding="utf-8") as f:
        return yaml.load(f, Loader=SafeLoader)

def login():
    cfg = _load_auth_config()
    authenticator = stauth.Authenticate(
        cfg["credentials"],
        cfg["cookie"]["name"],
        cfg["cookie"]["key"],
        cfg["cookie"]["expiry_days"],
        cfg.get("preauthorized", {})
    )
    name, auth_status, username = authenticator.login("Login", "main")
    role = None
    if auth_status:
        role = cfg["credentials"]["usernames"][username].get("role", "atendente")
    return authenticator, auth_status, username, name, role
