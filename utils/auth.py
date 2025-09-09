# utils/auth.py
from __future__ import annotations
import os
import inspect
import streamlit as st
import streamlit_authenticator as stauth
from collections.abc import Mapping
from backend.repo_users import credentials_from_db, ensure_bootstrap_admin

def _deep_to_dict(obj):
    if isinstance(obj, Mapping):
        return {k: _deep_to_dict(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_deep_to_dict(v) for v in obj]
    return obj

def _cookie_cfg():
    # usa secrets se houver; senão, defaults (mude a key em produção)
    if "auth" in st.secrets and "cookie" in st.secrets["auth"]:
        c = _deep_to_dict(st.secrets["auth"]["cookie"])
        return c["name"], c["key"], c["expiry_days"]
    return "vns_auth", "mude_esta_chave_em_prod", 14

def _load_auth_config():
    # 1) Banco de dados (preferido)
    from_db = credentials_from_db()
    if from_db:
        name, key, days = _cookie_cfg()
        return {"credentials": from_db, "cookie": {"name": name, "key": key, "expiry_days": days}}

    # 2) Se não há usuários, bootstrap admin e tenta de novo
    first_pwd = ensure_bootstrap_admin()
    if first_pwd:
        st.warning(f"👑 Admin inicial criado: **usuário `admin`** / **senha `{first_pwd}`**. "
                   "Faça login e troque a senha em *Admin → Usuários*.")
        from_db = credentials_from_db()
        if from_db:
            name, key, days = _cookie_cfg()
            return {"credentials": from_db, "cookie": {"name": name, "key": key, "expiry_days": days}}

    # 3) Fallback (opcional) — Secrets, se você ainda quiser manter
    if "auth" in st.secrets:
        return _deep_to_dict(st.secrets["auth"])

    raise RuntimeError("Sem configuração de autenticação e sem usuários no banco.")

def _call_login_compat(authenticator: stauth.Authenticate):
    """Chama .login() e normaliza o retorno para (name, auth_status, username)."""
    try:
        params = inspect.signature(authenticator.login).parameters
    except Exception:
        params = {}

    if "location" in params and "form_name" not in params:
        try:
            from streamlit_authenticator.utilities.constants import Location
            res = authenticator.login(location=Location.MAIN)
        except Exception:
            res = authenticator.login(location="main")
    else:
        res = authenticator.login("Login", "main")

    if isinstance(res, tuple) and len(res) == 3:
        return res
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
