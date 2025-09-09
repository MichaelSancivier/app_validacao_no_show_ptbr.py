# backend/repo_users.py
from __future__ import annotations
import secrets
from typing import Optional, Dict, Any, List
import bcrypt
from sqlalchemy import select
from .db import get_session
from .models import User

# ---------- util ----------
def _hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

# ---------- CRUD ----------
def add_user(username: str, name: str, role: str, password_plain: str) -> None:
    username = username.strip()
    with get_session() as s:
        exists = s.execute(select(User).where(User.username == username)).scalar()
        if exists:
            raise ValueError("Username já existe.")
        s.add(User(
            username=username,
            name=name.strip(),
            role=role.strip(),
            password_hash=_hash_password(password_plain),
            active=1,
        ))
        s.commit()

def list_users(include_inactive: bool = True) -> List[User]:
    with get_session() as s:
        if include_inactive:
            return s.execute(select(User)).scalars().all()
        return s.execute(select(User).where(User.active == 1)).scalars().all()

def set_password(username: str, new_password_plain: str) -> None:
    with get_session() as s:
        u = s.execute(select(User).where(User.username == username)).scalar_one()
        u.password_hash = _hash_password(new_password_plain)
        s.commit()

def set_role(username: str, role: str) -> None:
    with get_session() as s:
        u = s.execute(select(User).where(User.username == username)).scalar_one()
        u.role = role
        s.commit()

def set_active(username: str, active: bool) -> None:
    with get_session() as s:
        u = s.execute(select(User).where(User.username == username)).scalar_one()
        u.active = 1 if active else 0
        s.commit()

# ---------- Auth helper ----------
def credentials_from_db() -> Optional[Dict[str, Any]]:
    """Formata para o streamlit-authenticator."""
    users = list_users(include_inactive=False)
    if not users:
        return None
    return {
        "usernames": {
            u.username: {
                "name": u.name,
                "password": u.password_hash,
                "role": u.role,
            }
            for u in users
        }
    }

def ensure_bootstrap_admin() -> Optional[str]:
    """
    Se não existir NENHUM usuário, cria um admin inicial com senha aleatória
    e retorna a senha em texto para mostrar 1x na tela.
    """
    with get_session() as s:
        any_user = s.execute(select(User)).scalar()
        if any_user:
            return None
        # cria admin
        tmp_password = secrets.token_urlsafe(10)
        s.add(User(
            username="admin",
            name="Admin",
            role="admin",
            password_hash=_hash_password(tmp_password),
            active=1,
        ))
        s.commit()
        return tmp_password
