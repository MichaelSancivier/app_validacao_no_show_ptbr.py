# backend/repo_users.py
from __future__ import annotations

import secrets
import string
import bcrypt
from typing import List, Dict, Any

from sqlalchemy import select, func

from .db import get_session
from .models import User


def list_users(include_inactive: bool = False) -> List[User]:
    with get_session() as s:
        stmt = select(User)
        if not include_inactive:
            stmt = stmt.where(User.active == 1)
        return s.execute(stmt).scalars().all()


def credentials_from_db() -> Dict[str, Any] | None:
    """Formata credenciais no shape esperado pelo auth."""
    users = list_users(include_inactive=True)
    if not users:
        return None
    creds = {"usernames": {}}
    for u in users:
        creds["usernames"][u.username] = {
            "name": u.name or u.username,
            "password": u.password,  # HASH BCRYPT
            "role": u.role or "atendente",
            "active": u.active,
        }
    return creds


def ensure_bootstrap_admin() -> str | None:
    """
    Garante um admin inicial se a tabela estiver vazia (ou se 'admin' não existir).
    Retorna a senha em texto claro (uma vez) quando criar; senão, None.
    """
    with get_session() as s:
        # já existe algum user?
        total = s.execute(select(func.count()).select_from(User)).scalar_one()
        if total and total > 0:
            # Se já existe admin, não mexe
            exists_admin = s.execute(
                select(func.count()).select_from(User).where(User.username == "admin")
            ).scalar_one()
            if exists_admin:
                return None

        # cria admin com senha aleatória
        raw_pwd = "".join(secrets.choice(string.ascii_letters + string.digits) for _ in range(10))
        hashed = bcrypt.hashpw(raw_pwd.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

        s.add(User(
            username="admin",
            name="Admin",
            password=hashed,
            role="admin",
            active=1,
        ))
        s.commit()
        return raw_pwd
