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
            "Faça login e troque a senha em *Admin → Usuários*."
        )
        from_db = credentials_from_db()
        if from_db:
            name, key, days = _cookie_cfg()
            return {"credentials": from_db, "cookie": {"name": name, "key": key, "expiry_days": days}}

    # 3) Fallback opcional — Secrets
    if "auth" in st.secrets:
        return _deep_to_dict(st.secrets["auth"])

    raise RuntimeError("Sem configuração de autenticação e sem usuários no banco.")


# -----------------------------
# Bind do streamlit_authenticator
# -----------------------------
def _call_login_compat(authenticator: stauth.Authenticate):
    """
    Chama .login() do streamlit_authenticator e normaliza o retorno
    para (name, auth_status, username), independente de versão.
    """
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

    # Versões antigas retornam tuple(name, auth_status, username)
    if isinstance(res, tuple) and len(res) == 3:
        return res

    # Versões novas retornam um objeto com atributos
    name = getattr(res, "name", None)
    auth_status = getattr(res, "authentication_status", getattr(res, "auth_status", None))
    username = getattr(res, "username", None)
    return name, auth_status, username


# -----------------------------
# Fallback manual (sem cookies)
# -----------------------------
def _fallback_manual_login(cfg: dict):
    """
    Formulário simples que valida usuário/senha com bcrypt,
    sem depender do componente de cookies (extra-streamlit-components).
    Usa st.session_state para manter a sessão.
    """
    st.subheader("Login (modo compatibilidade)")
    users = cfg["credentials"]["usernames"]

    u = st.text_input("Username", key="fb_user")
    p = st.text_input("Password", type="password", key="fb_pass")
    if st.button("Entrar", key="fb_btn"):
        if u in users:
            try:
                ok = bcrypt.checkpw(p.encode("utf-8"), users[u]["password"].encode("utf-8"))
            except Exception:
                ok = False
            if ok:
                st.session_state["_auth_ok"] = True
                st.session_state["_auth_user"] = u
                st.session_state["_auth_name"] = users[u]["name"]
                st.session_state["_auth_role"] = users[u].get("role", "atendente")
                _rerun()
            else:
                st.error("Usuário/senha inválidos.")
        else:
            st.error("Usuário não encontrado.")

    if st.session_state.get("_auth_ok"):
        return True, st.session_state["_auth_user"], st.session_state["_auth_name"], st.session_state["_auth_role"]
    return None, None, None, None


class _DummyAuth:
    """Compatível com app.logout(...). Limpa a sessão do fallback."""

    def logout(self, *args, **kwargs):
        for k in ("_auth_ok", "_auth_user", "_auth_name", "_auth_role"):
            st.session_state.pop(k, None)
        _rerun()


# -----------------------------
# Função pública usada no app
# -----------------------------
def login():
    """
    Retorna: (authenticator, auth_status, username, name, role)

    Fluxo:
    1) Tenta o login oficial do streamlit_authenticator (com cookies).
    2) Se não logar (status None) ou der erro, exibe o fallback manual.
    """
    cfg = _load_auth_config()

    # 1) Tenta o fluxo oficial com cookies
    authenticator = None
    try:
        authenticator = stauth.Authenticate(
            cfg["credentials"],
            cfg["cookie"]["name"],
            cfg["cookie"]["key"],
            cfg["cookie"]["expiry_days"],
        )
        name, auth_status, username = _call_login_compat(authenticator)
    except Exception:
        name = username = None
        auth_status = None

    # Se logou normalmente, retorna
    if auth_status:
        role = cfg["credentials"]["usernames"][username].get("role", "atendente")
        return authenticator, auth_status, username, name, role

    # 2) Fallback manual
    st.divider()
    st.caption("⚠️ Problemas para entrar? Use o **modo compatibilidade** abaixo.")
    ok, u, n, r = _fallback_manual_login(cfg)
    if ok:
        # Usa o DummyAuth para ter .logout() compatível com o app
        return _DummyAuth(), True, u, n, r

    # Ainda não logado
    return authenticator or _DummyAuth(), None, None, None, None
