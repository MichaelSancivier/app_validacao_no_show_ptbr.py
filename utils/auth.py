# utils/auth.py
from __future__ import annotations

import os
from collections.abc import Mapping
from typing import Tuple

import bcrypt
import streamlit as st

from backend.repo_users import credentials_from_db, ensure_bootstrap_admin


# -----------------------------
# Util: rerun compatível
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
# Helpers
# -----------------------------
def _deep_to_dict(obj):
    if isinstance(obj, Mapping):
        return {k: _deep_to_dict(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_deep_to_dict(v) for v in obj]
    return obj


def _show_bootstrap_banner(password: str):
    """
    Mostra um aviso persistente com a senha do admin.
    Fica visível até marcar "Já copiei / ocultar".
    Disponibiliza download de admin.txt.
    """
    if st.session_state.get("_hide_bootstrap_banner"):
        return

    st.warning(
        "👑 **Admin inicial criado**. Use as credenciais abaixo e depois troque a senha em "
        "*Admin → Usuários*."
    )

    txt = f"usuario: admin\nsenha: {password}\n"
    st.code(txt, language="bash")

    st.download_button(
        "Baixar credenciais (admin.txt)",
        data=txt,
        file_name="admin.txt",
        mime="text/plain",
        use_container_width=True,
    )

    st.checkbox("Já copiei / ocultar este aviso", key="_hide_bootstrap_banner")


def _persist_bootstrap_password(pwd: str):
    """Guarda a senha de bootstrap na sessão e tenta salvar em data/ADMIN_BOOTSTRAP.txt."""
    st.session_state["_bootstrap_admin_pwd"] = pwd
    try:
        os.makedirs("data", exist_ok=True)
        with open(os.path.join("data", "ADMIN_BOOTSTRAP.txt"), "w", encoding="utf-8") as f:
            f.write(f"usuario: admin\nsenha: {pwd}\n")
    except Exception:
        pass


def _load_auth_config() -> dict:
    """
    Carrega credenciais a partir do SQLite.
    Se não houver usuários, cria o admin inicial e mostra um banner persistente.
    (Sem cookies; não usa streamlit_authenticator.)
    """
    # Reexibe banner se já houver senha na sessão
    if "_bootstrap_admin_pwd" in st.session_state:
        _show_bootstrap_banner(st.session_state["_bootstrap_admin_pwd"])

    # 1) Banco
    from_db = credentials_from_db()
    if from_db:
        return {"credentials": from_db}

    # 2) Bootstrap admin e recarrega
    first_pwd = ensure_bootstrap_admin()
    if first_pwd:
        _persist_bootstrap_password(first_pwd)
        _show_bootstrap_banner(first_pwd)
        from_db = credentials_from_db()
        if from_db:
            return {"credentials": from_db}

    # 3) Sem credenciais
    raise RuntimeError("Sem usuários no banco. Use o bloque 'Setup rápido' para criar o admin.")


# -----------------------------
# Login compatibilidade (sem cookies)
# -----------------------------
def _fallback_manual_login(cfg: dict):
    """
    Formulário simples que valida usuário/senha com bcrypt
    e mantém sessão em st.session_state.
    """
    st.subheader("Login")
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
    """Objeto com .logout() compatível com o app (aceita *args, **kwargs)."""

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

    Aqui mostramos **apenas** o login em modo compatibilidade.
    Não usamos streamlit_authenticator nem cookies.
    """
    cfg = _load_auth_config()

    ok, u, n, r = _fallback_manual_login(cfg)
    if ok:
        return _DummyAuth(), True, u, n, r

    return _DummyAuth(), None, None, None, None
