# utils/auth.py
from __future__ import annotations
import os
import inspect
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
    # PRODUÇÃO: Secrets do Streamlit Cloud
    if "auth" in st.secrets:
        return _deep_to_dict(st.secrets["auth"])
    # DEV (opcional): auth.yaml local (NÃO subir no GitHub)
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
        "Defina st.secrets['auth'] em Settings → Secrets do Streamlit Cloud."
    )

def _call_login(authenticator: stauth.Authenticate):
    """Chama .login() de forma compatível com versões novas/antigas."""
    try:
        params = inspect.signature(authenticator.login).parameters
    except Exception:
        params = {}

    if "location" in params and "form_name" not in params:
        # Versões novas: só 'location'
        try:
            from streamlit_authenticator.utilities.constants import Location
            return authenticator.login(location=Location.MAIN)
        except Exception:
            return authenticator.login(location="main")
    else:
        # Versões antigas: (form_name, location)
        return authenticator.login("Login", "main")

def login():
    cfg = _load_auth_config()

    authenticator = stauth.Authenticate(
        cfg["credentials"],
        cfg["cookie"]["name"],
        cfg["cookie"]["key"],
        cfg["cookie"]["expiry_days"],
    )

    name, auth_status, username = _call_login(authenticator)

    role = None
    if auth_status:
        role = cfg["credentials"]["usernames"][username].get("role", "atendente")

    return authenticator, auth_status, username, name, role
