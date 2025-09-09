# app.py
from __future__ import annotations

import io
import re
import unicodedata
from datetime import datetime

import numpy as np
import pandas as pd
import streamlit as st

# --- infraestrutura (banco + login) ---
from backend.db import init_db
from backend.repo import (
    create_dataset,
    list_datasets,
    load_rows_for_user,
    save_conferencia,
)
from utils.auth import login

# =========================================
# Utilidades de normalização/regex
# =========================================
def _rm_acc(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")

def canon(s: str) -> str:
    if s is None or (isinstance(s, float) and pd.isna(s)):
        return ""
    s = str(s).replace("–", "-").replace("—", "-")
    s = _rm_acc(s).lower()
    s = re.sub(r"[.;:\s]+$", "", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s

def _flex(escaped: str) -> str:
    return (
        escaped.replace(r"\ ", r"\s+")
        .replace(r"\,", r"[\s,]*")
        .replace(r"\-", r"[\-\–\—]\s*")
        .replace(r"\.", r"[\.\s]*")
    )

def template_to_regex_flex(t: str):
    if t is None:
        t = ""
    t = re.sub(r"\s+", " ", str(t)).strip()
    parts = re.split(r"0+", t)
    fixed = [_flex(re.escape(p)) for p in parts]
    between = r"[\s\.,;:\-\–\—]*" + r"(.+?)" + r"[\s\.,;:\-\–\—]*"
    body = between.join(fixed)
    pattern = r"^\s*" + body + r"\s*[.,;:\-–—]*\s*$"
    try:
        return re.compile(pattern, flags=re.IGNORECASE | re.DOTALL)
    except re.error:
        return re.compile(r"^\s*" + re.escape(t) + r"\s*$", re.I)

# =========================================
# Regras embutidas + "Regra especial"
# =========================================
REGRAS_EMBUTIDAS = [
    {
        "causa": "Agendamento cancelado.",
        "motivo": "Erro De Agendamento - Cliente desconhecia o agendamento",
        "mascara_modelo": "Em contato com o cliente o mesmo informou que desconhecia o agendamento. Nome cliente: 0 / Data contato:  - ",
    },
    {
        "causa": "Agendamento cancelado.",
        "motivo": "Erro de Agendamento – Endereço incorreto",
        "mascara_modelo": "Erro identificado no agendamento: 0 . Situação:. Cliente  - informado em ",
    },
    {
        "causa": "Agendamento cancelado.",
        "motivo": "No-show Cliente – Ponto Fixo/Móvel",
        "mascara_modelo": "Cliente não compareceu para atendimento até às 0.",
    },
    {
        "causa": "Agendamento cancelado.",
        "motivo": "No-show Técnico",
        "mascara_modelo": "Técnico 0 , em  - , não realizou o atendimento por motivo de ",
    },
]

# valores que disparam a “regra especial” => vira No-show Cliente
ESPECIAIS_NO_SHOW_CLIENTE = ["Automático - PORTAL", "Michelin", "OUTRO"]

def _build_rules_map():
    return {
        (canon(r["causa"]), canon(r["motivo"])): (
            r["motivo"],
            template_to_regex_flex(r["mascara_modelo"]),
            r["mascara_modelo"],
        )
        for r in REGRAS_EMBUTIDAS
    }

RULES_MAP = _build_rules_map()

def recarregar_regras():
    global RULES_MAP
    RULES_MAP = _build_rules_map()

def eh_especial(valor: str) -> bool:
    v = canon(valor)
    return any(canon(g) in v for g in ESPECIAIS_NO_SHOW_CLIENTE if g.strip())

def read_any(f):
    if f is None:
        return None
    n = f.name.lower()
    if n.endswith(".csv"):
        try:
            return pd.read_csv(f, sep=None, engine="python")
        except Exception:
            f.seek(0)
            return pd.read_csv(f)
    try:
        return pd.read_excel(f, engine="openpyxl")
    except Exception:
        f.seek(0)
        return pd.read_excel(f)

def detect(full_text: str):
    """tenta extrair (causa, motivo, máscara) a partir do texto cheio."""
    if not full_text:
        return "", "", ""
    txt = re.sub(r"\s+", " ", str(full_text)).strip()
    txt_c = canon(txt)
    causa_c = canon("Agendamento cancelado.")
    for (c_norm, m_norm), (motivo_oficial, _rx, _mod) in RULES_MAP.items():
        if c_norm != causa_c:
            continue
        if m_norm in txt_c:
            idx = txt_c.find(m_norm) + len(m_norm)
            mascara = txt[idx:].strip(" .")
            return "Agendamento cancelado.", motivo_oficial, mascara
    return "", "", txt

def categoria(motivo: str) -> str:
    m = canon(motivo)
    if not m:
        return ""
    if m.startswith("erro de agendamento") or "erro de roteirizacao do agendamento" in m:
        return "Erro Agendamento"
    if m.startswith("falta de equipamento") or "perda/extravio" in m or "equipamento com defeito" in m:
        return "Falta de equipamentos"
    return ""

# =========================================
# STREAMLIT APP
# =========================================
st.set_page_config(page_title="Validador de No-show", layout="wide")
st.title("Validador de No-show — um app só")

# Inicializa o banco (cria tabelas)
init_db()
from backend.repo_users import ensure_bootstrap_admin
_boot = ensure_bootstrap_admin()
if _boot:
    st.warning(f"👑 Admin inicial criado: usuário 'admin' / senha '{_boot}'. "
               "Entre e troque em Admin → Usuários.")

# ---- Login (SQLite via utils/auth.py) ----
authenticator, ok, username, name, role = login()
if ok is False:
    st.error("Usuário/senha inválidos.")
    st.stop()
elif ok is None:
    st.info("Faça login para continuar.")
    st.stop()

# Logout (compatibilidade com versões)
try:
    authenticator.logout(location="sidebar")
except TypeError:
    authenticator.logout("Sair", "sidebar")

st.sidebar.write(f"👋 {name} — **{role}**")

# =========================================
# MÓDULO 1 — Pré-análise (ADMIN)
# =========================================
if role == "admin":
    st.header("Módulo 1 — Pré-análise e publicação")

    file = st.file_uploader("Arquivo de entrada (xlsx/csv)", type=["xlsx", "csv"])
    out = None

    with st.expander("Adicionar regras rápidas (opcional)", expanded=False):
        ex = "Agendamento cancelado.; Erro de Agendamento – Documento inválido; OS apresentou erro de 0 identificado via 0. Cliente 0 informado em 0."
        txt = st.text_area(
            "Cole aqui linhas no formato: causa ; motivo ; mascara_modelo",
            value="",
            placeholder=ex,
            help="Cada linha vira uma regra nova. O dígito 0 indica os pontos onde o texto pode variar (número, nome, data...).",
        )
        c1, c2 = st.columns(2)
        if c1.button("Aplicar regras"):
            for linha in txt.splitlines():
                linha = linha.strip()
                if not linha:
                    continue
                p = [p.strip() for p in linha.split(";", 2)]
                if len(p) != 3:
                    continue
                REGRAS_EMBUTIDAS.append({"causa": p[0], "motivo": p[1], "mascara_modelo": p[2]})
            recarregar_regras()
            st.success("Regras aplicadas.")
        if c2.button("Limpar texto"):
            st.experimental_rerun()

    if file:
        df = read_any(file)
        col_main = st.selectbox("Coluna principal (texto cheio)", df.columns)
        col_especial = st.selectbox("Coluna 'especial' para regra No-show Cliente (opcional)", ["(Nenhuma)"] + list(df.columns))

        st.markdown("**Distribuição por atendentes (opcional)**")
        qtd = st.number_input("Qtd. atendentes", 1, 200, 3)
        nomes_raw = st.text_area("Nomes (1 por linha, ou separados por , ; )", value="")

        causas, motivos, mascaras, combos, modelos = [], [], [], [], []
        resultados, detalhes = [], []

        for _, r in df.iterrows():
            c, m, ms = detect(r.get(col_main, ""))
            causas.append(c)
            motivos.append(m)
            mascaras.append(ms)
            partes = [p for p in [str(c).strip(), str(m).strip(), str(ms).strip()] if p]
            combos.append(" ".join(partes))

            modelo = ""
            if col_especial != "(Nenhuma)" and eh_especial(r.get(col_especial, "")):
                resultados.append("No-show Cliente")
                detalhes.append("Regra especial aplicada: virou No-show Cliente.")
                modelos.append(modelo)
                continue

            key = (canon(c), canon(m))
            found = RULES_MAP.get(key)
            if not found:
                resultados.append("No-show Técnico")
                detalhes.append("Motivo não reconhecido.")
                modelos.append(modelo)
                continue

            _, rx, mod = found
            modelo = mod or ""
            if rx.fullmatch(re.sub(r"\s+", " ", str(ms)).strip()):
                resultados.append("Máscara correta")
                detalhes.append("")
            else:
                resultados.append("No-show Técnico")
                detalhes.append("Não casa com o modelo.")
            modelos.append(modelo)

        out = df.copy()
        # Garante coluna O.S.
        if "O.S." not in out.columns and "OS" in out.columns:
            out = out.rename(columns={"OS": "O.S."})
        if "O.S." not in out.columns:
            out["O.S."] = ""

        out["Causa detectada"] = causas
        out["Motivo detectado"] = motivos
        out["Máscara prestador (preenchida)"] = mascaras
        out["Máscara prestador"] = modelos
        out["Causa. Motivo. Máscara (extra)"] = combos
        out["Classificação No-show"] = resultados
        out["Detalhe"] = detalhes

        # Resultado No Show agregado
        res = []
        for r_cls, mot in zip(resultados, motivos):
            cat = categoria(mot)
            if cat:
                res.append(cat)
            elif r_cls in ("Máscara correta", "No-show Cliente"):
                res.append("No-show Cliente")
            else:
                res.append("No-show Técnico")
        out["Resultado No Show"] = res

        # Distribuição por atendente (se não existir a coluna)
        if "Atendente designado" not in out.columns:
            import re as _re

            nomes = [n.strip() for n in _re.split(r"[,;\n]+", nomes_raw) if n.strip()]
            if not nomes:
                nomes = [f"Atendente {i+1}" for i in range(int(qtd))]
            else:
                while len(nomes) < int(qtd):
                    nomes.append(f"Atendente {len(nomes)+1}")
            bloco = int(np.ceil(len(out) / len(nomes)))
            out.insert(0, "Atendente designado", (nomes * bloco)[: len(out)])

        st.success("Pré-análise concluída!")
        st.dataframe(out, use_container_width=True)

        if st.button("📡 Publicar para conferência (salvar no banco)"):
            ds_id = create_dataset(f"Dataset {datetime.now():%Y-%m-%d %H:%M}", name, out)
            st.success(f"Publicado! Dataset #{ds_id}.")

        buf = io.BytesIO()
        with pd.ExcelWriter(buf, engine="openpyxl") as w:
            out.to_excel(w, index=False, sheet_name="Resultado")
        st.download_button(
            "⬇️ Baixar Excel (pré-análise)",
            data=buf.getvalue(),
            file_name="resultado_no_show.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

# =========================================
# MÓDULO 2 — Conferência (TODOS)
# =========================================
st.header("Módulo 2 — Conferência (no app)")

datasets = list_datasets()
if not datasets:
    st.info("Nenhum dataset publicado.")
else:
    def _fmt_ds(d):
        # suporta Row/tuple/obj
        did = getattr(d, "id", d[0] if isinstance(d, (list, tuple)) else None)
        nm = getattr(d, "name", d[1] if isinstance(d, (list, tuple)) and len(d) > 1 else str(d))
        return f"#{did} — {nm}"

    ds = st.selectbox("Escolha o dataset", options=datasets, format_func=_fmt_ds)
    if ds:
        ds_id = getattr(ds, "id", ds[0] if isinstance(ds, (list, tuple)) else None)

        df = load_rows_for_user(ds_id, role, name)

        classificacoes = ["No-show Cliente", "No-show Técnico", "Erro Agendamento", "Falta de equipamentos"]
        status_ops = ["✅ App acertou", "❌ App errou, atendente corrigiu", "⚠️ Atendente errou", "⏳ Pendente"]

        for i, r in df.iterrows():
            st.markdown("---")
            st.markdown(f"**O.S.:** {r.get('O.S.', '')}")
            st.markdown(f"**Texto original:** {r.get('Causa. Motivo. Máscara (extra)', '')}")
            st.markdown(f"**Classificação pré-análise:** {r.get('Classificação No-show','')}")
            st.markdown(f"**Resultado No Show (app):** {r.get('Resultado No Show','')}")

            detalhe = str(r.get("Detalhe", "")).strip()
            is_especial = "regra especial aplicada" in detalhe.lower()
            if detalhe:
                msg = f"**Detalhe (regra especial):** {detalhe}" if is_especial else f"**Detalhe do app:** {detalhe}"
                (st.warning if is_especial else st.info)(msg)

            # Modelo esperado para conferência:
            modelo = "No-show Cliente" if is_especial else str(r.get("Máscara prestador", "")).strip()
            st.markdown(f"**Máscara modelo (oficial):** `{modelo or '—'}`")

            # Campo “Máscara conferida”
            opcoes = ([modelo] if modelo else []) + ["(Outro texto)"]
            escolha = st.selectbox(
                f"Máscara conferida — escolha (linha {i})",
                options=opcoes,
                key=f"mask_sel_{i}",
                help="Escolha a máscara oficial OU '(Outro texto)'. Em regra especial, a esperada é 'No-show Cliente'.",
            )
            if escolha == "(Outro texto)":
                mask = st.text_input(
                    f"Digite a máscara conferida (linha {i})",
                    value=str(r.get("Máscara conferida", "")),
                    key=f"mask_txt_{i}",
                    help="Texto exato que constará na O.S.",
                )
            else:
                mask = escolha

            # Validação automática das máscaras conferidas
            if is_especial:
                valid = "✅ Máscara correta" if canon(mask) == canon("No-show Cliente") else "❌ Máscara incorreta"
            else:
                key = (canon(r.get("Causa detectada", "")), canon(r.get("Motivo detectado", "")))
                found = RULES_MAP.get(key)
                if found:
                    _, rx, _ = found
                    valid = (
                        "✅ Máscara correta"
                        if rx.fullmatch(re.sub(r"\s+", " ", str(mask)).strip())
                        else "❌ Máscara incorreta"
                    )
                else:
                    valid = "⚠️ Motivo não reconhecido"
            st.caption(f"**Validação automática (conferida):** {valid}")

            # persiste no DF editável
            df.at[i, "Máscara conferida"] = mask
            df.at[i, "Validação automática (conferida)"] = valid

            # Classificação ajustada (sem a opção 'Correta')
            if is_especial and "No-show Cliente" in classificacoes:
                idx = classificacoes.index("No-show Cliente")
            else:
                base = r.get("Resultado No Show", "")
                idx = classificacoes.index(base) if base in classificacoes else 0
            df.at[i, "Classificação ajustada"] = st.selectbox(
                f"Classificação ajustada (linha {i})", options=classificacoes, index=idx, key=f"class_{i}"
            )
            df.at[i, "Status da conferência"] = st.selectbox(
                f"Status da conferência (linha {i})", options=status_ops, key=f"status_{i}"
            )
            df.at[i, "Observações"] = st.text_input(
                f"Observações (linha {i})",
                value=str(r.get("Observações", "")),
                key=f"obs_{i}",
            )

        if st.button("💾 Salvar conferência no banco"):
            save_conferencia(
                df[
                    [
                        "row_id",
                        "Máscara conferida",
                        "Validação automática (conferida)",
                        "Classificação ajustada",
                        "Status da conferência",
                        "Observações",
                    ]
                ]
            )
            st.success("Conferência salva!")

        st.markdown("### Visualização/Exportação")
        st.dataframe(df, use_container_width=True)
        buf2 = io.BytesIO()
        with pd.ExcelWriter(buf2, engine="openpyxl") as w:
            df.to_excel(w, index=False, sheet_name="Conferencia")
        st.download_button(
            "⬇️ Baixar Excel — minha visão",
            data=buf2.getvalue(),
            file_name=f"conferencia_{name}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

# =========================================
# ADMIN — Painel de Usuários (SQLite)
# =========================================
if role == "admin":
    from backend.repo_users import add_user, list_users, set_password, set_role, set_active

    st.header("Admin — Usuários")

    colA, colB = st.columns(2, gap="large")

    with colA:
        st.subheader("Criar usuário")
        u = st.text_input("Username (ex.: joao)")
        n = st.text_input("Nome exibido")
        r = st.selectbox("Função (role)", ["atendente", "admin"])
        p = st.text_input("Senha inicial", type="password")
        if st.button("Criar usuário"):
            try:
                if not (u and n and p):
                    st.error("Preencha username, nome e senha.")
                else:
                    add_user(u, n, r, p)
                    st.success(f"Usuário `{u}` criado!")
            except Exception as e:
                st.error(f"Erro: {e}")

        st.divider()
        st.subheader("Alterar função")
        usuarios = list_users(include_inactive=True)
        if usuarios:
            sel1 = st.selectbox("Escolha o usuário", [x.username for x in usuarios])
            nova = st.selectbox("Nova função", ["atendente", "admin"])
            if st.button("Salvar função"):
                try:
                    set_role(sel1, nova)
                    st.success("Função atualizada.")
                except Exception as e:
                    st.error(f"Erro: {e}")

    with colB:
        st.subheader("Resetar senha")
        usuarios = list_users(include_inactive=True)
        if usuarios:
            sel2 = st.selectbox("Usuário", [x.username for x in usuarios], key="reset_user")
            nova_senha = st.text_input("Nova senha", type="password")
            if st.button("Resetar senha"):
                try:
                    if not nova_senha:
                        st.error("Digite a nova senha.")
                    else:
                        set_password(sel2, nova_senha)
                        st.success("Senha atualizada.")
                except Exception as e:
                    st.error(f"Erro: {e}")

        st.divider()
        st.subheader("Ativar / Desativar")
        if usuarios:
            sel3 = st.selectbox("Usuário", [x.username for x in usuarios], key="act_user")
            alvo = next((x for x in usuarios if x.username == sel3), None)
            if alvo:
                acao = "Desativar" if alvo.active else "Ativar"
                if st.button(acao):
                    try:
                        set_active(sel3, not bool(alvo.active))
                        st.success(f"{acao} ok.")
                    except Exception as e:
                        st.error(f"Erro: {e}")

    st.divider()
    st.subheader("Lista de usuários")
    try:
        users_df = pd.DataFrame(
            [
                {
                    "username": u.username,
                    "nome": u.name,
                    "role": u.role,
                    "ativo": "Sim" if u.active else "Não",
                    "criado_em": u.created_at,
                }
                for u in list_users(include_inactive=True)
            ]
        )
        if users_df.empty:
            st.info("Nenhum usuário cadastrado ainda.")
        else:
            st.dataframe(users_df, use_container_width=True)
    except Exception:
        st.info("Nenhum usuário cadastrado ainda.")

