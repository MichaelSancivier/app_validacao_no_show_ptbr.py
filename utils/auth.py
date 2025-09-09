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
    # PRODUÇÃO: usa Secrets do Streamlit Cloud
    if "auth" in st.secrets:
        return _deep_to_dict(st.secrets["auth"])
    # DEV opcional: auth.yaml (não subir no GitHub)
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

def login():
    cfg = _load_auth_config()

    authenticator = stauth.Authenticate(
        cfg["credentials"],
        cfg["cookie"]["name"],
        cfg["cookie"]["key"],
        cfg["cookie"]["expiry_days"],
    )

    # --- Chamada compatível com TODAS as versões ---
    # 1) tente com enum Location (versões novas)
    try:
        try:
            from streamlit_authenticator.utilities.constants import Location
            loc = Location.MAIN
        except Exception:
            loc = "main"  # se enum não existir, use string
        name, auth_status, username = authenticator.login(location=loc)
    except TypeError:
        # assinatura antiga: (form_name, location)
        name, auth_status, username = auth_
