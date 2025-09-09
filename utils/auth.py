# utils/auth.py
from __future__ import annotations

import os
import json
import time
import hmac
import base64
import hashlib
from collections.abc import Mapping

import bcrypt
import streamlit as st

from backend.repo_users import credentials_from_db, ensure_bootstrap_admin

# Ligue para ver diagnósticos do login na sidebar
DEBUG_AUTH = False


# -----------------------------
# Helpers gerais
# -----------------------------
def _deep_to_dict(obj):
    if isinstance(obj, Mapping):
        return {k: _deep_to_dict(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_deep_to_dict(v) for v in obj]
    return obj


def _get_secret_key() -> str:
    """Chave para assinar o token do URL (use algo forte em produção)."""
    try:
        return str(st.secrets["auth"]["cookie"]["key"])
    except Exception:
        return "mude_esta_chave_em_producao_bem_secreta"


# -----------------------------
# Token de sessão no URL (sid)
# -----------------------------
def _b64url_encode(b: bytes) -> str:
    return base64.urlsafe_b64encode(b).decode().rstrip("=")


def _b64url_decode(s: str) -> bytes:
    pad = "=" * ((4 - len(s) % 4) % 4)
    return base64.urlsafe_b64decode(s + pad)


def _make_sid(username: str, role: str, name: str, ttl_seconds: int = 60 * 60 * 12) -> str:
    """Gera um token assinado com HMAC e expiração (colocado em ?sid=...)."""
    payload = {"u": username, "r": role, "n": name, "exp": int(time.time()) + ttl_seconds}
    data = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    key = _get_secret_key().encode("utf-8")
    sig = hmac.new(key, data, hashlib.sha256).digest()
    return _b64url_encode(data + sig)


def _parse_sid(sid: str):
    """Valida o sid do URL; retorna payload ou None."""
    try:
        raw = _b64url_decode(sid)
        if len(raw) < 33:
            return None
        data, sig = raw[:-32], raw[-32:]
        key = _get_secret_key().encode("utf-8")
        exp_sig = hmac.new(key, data, hashlib.sha256).digest()
        if not hmac.compare_digest(sig, exp_sig):
            return None
        payload = json.loads(data.decode("utf-8"))
        if payload.get("exp", 0) < time.time():
            return None
        return payload
    except Exception:
        return None


def _restore_from_sid_if_needed():
    """Se houver ?sid= válido e ainda não logado, restaura a sessão."""
    if st.session_state.get("_auth_ok"):
        return
    params = st.experimental_get_query_params()
    sid = (params.get("sid") or [None])[0]
    if not sid:
        return
    payload = _parse_sid(sid)
    if payload:
        st.session_state["_auth_ok"] = True
        st.session_state["_auth_user"] = payload.get("u")
        st.session_state["_auth_name"] = payload.get("n") or payload.get("u")
        st.session_state["_auth_role"] = payload.get("r", "atendente")
        if DEBUG_AUTH:
            st.sidebar.success(f"[DEBUG] sessão restaurada do URL: {payload}")


def _clear_sid_from_url():
    # remove query params
    st.experimental_set_query_params()


# -----------------------------
# Banner de bootstrap
# -----------------------------
def _show_bootstrap_banner(password: str):
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
    st.session_state["_bootstrap_admin_pwd"] = pwd
    try:
        os.makedirs("data", exist_ok=True)
        with open(os.path.join("data", "ADMIN_BOOTSTRAP.txt"), "w", encoding="utf-8") as f:
            f.write(f"usuario: admin\nsenha: {pwd}\n")
    except Exception:
        pass


# -----------------------------
# Carrega credenciais (SQLite)
# -----------------------------
def _load_auth_config() -> dict:
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

    raise RuntimeError("Sem usuários no banco. Use o bloco 'Setup rápido' para criar o admin.")


# -----------------------------
# Login compatibilidade (sem cookies)
# -----------------------------
def _fallback_manual_login(cfg: dict):
    """
    Formulário com st.form que valida usuário/senha (bcrypt)
    e mantém sessão em st.session_state. Além disso,
    grava um sid assinado no URL para restaurar a sessão após reconexões.
    """
    st.subheader("Login")
    users = cfg["credentials"].get("usernames", {})

    with st.form("compat_login", clear_on_submit=False):
        u = st.text_input("Username", key="fb_user")
        p = st.text_input("Password", type="password", key="fb_pass")
        submitted = st.form_submit_button("Entrar")

    if DEBUG_AUTH:
        st.sidebar.caption(
            f"[DEBUG] submitted={submitted} | users={len(users)} | example_keys={list(users.keys())[:3]}"
        )

    if submitted:
        u = (u or "").strip()
        p = (p or "").strip()

        if u in users:
            stored = (
                users[u].get("password")
                or users[u].get("hashed_password")
                or users[u].get("pass")
            )
            if stored is None:
                st.error("Credencial sem hash de senha no banco.")
                if DEBUG_AUTH:
                    st.sidebar.error("[DEBUG] stored hash ausente")
                return None, None, None, None

            try:
                stored_b = stored if isinstance(stored, (bytes, bytearray)) else str(stored).encode("utf-8")
                ok = bcrypt.checkpw(p.encode("utf-8"), stored_b)
            except Exception as e:
                ok = False
                if DEBUG_AUTH:
                    st.sidebar.error(f"[DEBUG] bcrypt.checkpw error: {e}")

            if ok:
                name = users[u].get("name", u)
                role = users[u].get("role", "atendente")
                # marca sessão
                st.session_state["_auth_ok"] = True
                st.session_state["_auth_user"] = u
                st.session_state["_auth_name"] = name
                st.session_state["_auth_role"] = role
                # grava token no URL
                sid = _make_sid(u, role, name)
                st.experimental_set_query_params(sid=sid)

                if DEBUG_AUTH:
                    st.sidebar.success(f"[DEBUG] login OK user={u}; sid emitido.")
                st.success("Login realizado!")
                return True, u, name, role
            else:
                st.error("Usuário/senha inválidos.")
                if DEBUG_AUTH:
                    st.sidebar.error(f"[DEBUG] senha inválida para '{u}'")
        else:
            st.error("Usuário não encontrado.")
            if DEBUG_AUTH:
                st.sidebar.error(f"[DEBUG] usuário '{u}' não encontrado")

    # caso já esteja logado de execuções anteriores
    if st.session_state.get("_auth_ok"):
        return True, st.session_state["_auth_user"], st.session_state["_auth_name"], st.session_state["_auth_role"]
    return None, None, None, None


class _DummyAuth:
    """Objeto com .logout() compatível com o app (aceita *args, **kwargs)."""

    def logout(self, *args, **kwargs):
        for k in ("_auth_ok", "_auth_user", "_auth_name", "_auth_role"):
            st.session_state.pop(k, None)
        _clear_sid_from_url()  # remove ?sid= da URL


# -----------------------------
# Função pública usada no app
# -----------------------------
def login():
    """
    Retorna: (authenticator, auth_status, username, name, role)

    Fluxo:
    1) Restaura de ?sid= se existir/for válido.
    2) Se ainda não logado, mostra login compatibilidade.
    """
    # 1) tenta restaurar sessão do URL
    _restore_from_sid_if_needed()

    # 2) carrega credenciais
    cfg = _load_auth_config()

    # 3) se já está ok por conta do sid
    if st.session_state.get("_auth_ok"):
        if DEBUG_AUTH:
            st.sidebar.caption("[DEBUG] sessão já ativa via sid/url")
        return _DummyAuth(), True, st.session_state["_auth_user"], st.session_state["_auth_name"], st.session_state["_auth_role"]

    # 4) exibe formulário
    ok, u, n, r = _fallback_manual_login(cfg)
    if ok:
        return _DummyAuth(), True, u, n, r

    return _DummyAuth(), None, None, None, None
