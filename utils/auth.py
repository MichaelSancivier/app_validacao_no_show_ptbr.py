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

def _call_login_compat(authenticator: stauth.Authenticate):
    """
    Chama authenticator.login() compatível com versões novas/antigas
    e NORMALIZA o retorno para (name, auth_status, username).
    """
    # 1) Tenta assinatura nova (keyword 'location'), com enum se existir
    try:
        try:
            from streamlit_authenticator.utilities.constants import Location
            res = authenticator.login(location=Location.MAIN)
        except Exception:
            res = authenticator.login(location="main")
    except TypeError:
        # 2) Assinatura antiga: (form_name, location)
        res = authenticator.login("Login", "main")
    except ValueError:
        # 3) Algumas builds exigem string em vez do enum (ou vice-versa)
        try:
            res = authenticator.login(location="main")
        except Exception:
            res = authenticator.login("Login", "main")

    # 4) Normaliza retorno
    if isinstance(res, tuple) and len(res) == 3:
        return res  # (name, auth_status, username)

    # Algumas versões retornam um objeto com atributos
    name = getattr(res, "name", None)
    auth_status = getattr(res, "authentication_status", getattr(res, "auth_status", None))
    username = getattr(res, "username", None)
    return name, auth_status, username

def login():
    cfg = _load_auth_config()

    authenticator = stauth.Authenticate(
        cfg["credentials"],
        cfg["cookie"]["name"],
        cfg["cookie"]["key"],
        cfg["cookie"]["expiry_days"],
    )

    name, auth_status, username = _call_login_compat(authenticator)

    role = None
    if auth_status:
        role = cfg["credentials"]["usernames"][username].get("role", "atendente")

    return authenticator, auth_status, username, name, role
