# utils/auth.py
from __future__ import annotations
import os
import streamlit as st
import streamlit_authenticator as stauth
from collections.abc import Mapping

def _deep_to_dict(obj):
    if isinstance(obj, Mapping):
        return {k: _deep_to_dict(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_deep_to_dict(v) for v in obj]
    return obj

def _load_auth_config():
    if "auth" in st.secrets:
        return _deep_to_dict(st.secrets["auth"])  # st.secrets -> dict mutável
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

    # versões novas não aceitam 'preauthorized'
    authenticator = stauth.Authenticate(
        cfg["credentials"],
        cfg["cookie"]["name"],
        cfg["cookie"]["key"],
        cfg["cookie"]["expiry_days"],
    )

    # --- Compatível com versões NOVA e ANTIGA ---
    try:
        # NOVA API: só 'location'
        name, auth_status, username = authenticator.login(location="main")
    except TypeError:
        # ANTIGA API: (form_name, location)
        name, auth_status, username = authenticator.login("Login", "main")

    role = None
    if auth_status:
        role = cfg["credentials"]["usernames"][username].get("role", "atendente")

    # botão de logout (compatível com as duas APIs)
    try:
        authenticator.logout(location="sidebar")
    except TypeError:
        authenticator.logout("Sair", "sidebar")

    return authenticator, auth_status, username, name, role
