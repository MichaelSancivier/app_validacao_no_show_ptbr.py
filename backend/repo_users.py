# backend/repo_users.py
from __future__ import annotations
from typing import List, Dict, Any, Optional
import secrets
import bcrypt
from sqlalchemy import select, update, delete, func

from .db import get_session
from .models import User


def _hash(pwd: str) -> str:
    return bcrypt.hashpw(pwd.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def list_users(*, include_inactive: bool = True) -> List[Dict[str, Any]]:
    with get_session() as s:
        q = select(User)
        if not include_inactive:
            q = q.where(User.active == 1)
        rows = s.execute(q).scalars().all()
    out = []
    for u in rows:
        out.append(
            {
                "id": u.id,
                "username": u.username,
                "name": u.name,
                "role": u.role,
                "active": int(u.active or 0),
                "created_at": u.created_at,
            }
        )
    return out


def get_user(username: str) -> Optional[User]:
    with get_session() as s:
        return s.execute(select(User).where(User.username == username)).scalar_one_or_none()


def create_user(username: str, name: str, password: str, role: str = "atendente", active: int = 1) -> None:
    username = username.strip()
    if not username or not password:
        raise ValueError("Username e senha são obrigatórios.")
    if get_user(username):
        raise ValueError("Usuário já existe.")

    with get_session() as s:
        s.add(User(username=username, name=name.strip(), password=_hash(password), role=role, active=active))
        s.commit()


def set_password(username: str, new_password: str) -> None:
    if not new_password:
        raise ValueError("Nova senha vazia.")
    with get_session() as s:
        s.execute(
            update(User)
            .where(User.username == username)
            .values(password=_hash(new_password))
        )
        s.commit()


def set_active(username: str, active: int) -> None:
    with get_session() as s:
        s.execute(update(User).where(User.username == username).values(active=int(bool(active))))
        s.commit()


def ensure_bootstrap_admin() -> Optional[str]:
    """
    Cria admin 'admin' se a tabela estiver vazia. Retorna a senha criada (ou None se já existia).
    """
    with get_session() as s:
        cnt = s.execute(select(func.count(User.id))).scalar_one()
        if cnt and cnt > 0:
            return None

    first_pwd = secrets.token_urlsafe(8)
    create_user("admin", "Admin", first_pwd, role="admin", active=1)
    return first_pwd


def credentials_from_db() -> Dict[str, Any]:
    """
    Para o módulo de autenticação manual: devolve
    {"usernames": {username: {"name":..., "password": <bcrypt>, "role":..., "active": 0/1}}}
    """
    users = list_users(include_inactive=True)
    out = {"usernames": {}}
    # buscamos o hash diretamente do banco
    with get_session() as s:
        for u in s.execute(select(User)).scalars().all():
            out["usernames"][u.username] = {
                "name": u.name,
                "password": u.password,
                "role": u.role,
                "active": int(u.active or 0),
            }
    return out
