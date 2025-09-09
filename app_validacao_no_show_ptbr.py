# -*- coding: utf-8 -*-
# App Streamlit — Validador No-show (Pré-análise + Conferência, sem dupla checagem)
from __future__ import annotations

import io
import re
import uuid
from datetime import datetime

import numpy as np
import pandas as pd
import streamlit as st
import unicodedata

# ===== infra: banco + auth + repos =====
from backend.db import init_db
from utils.auth import sticky_sid_bootstrap, login
from backend.repo_reviews import upsert_reviews_from_df, list_all_reviews_df
from backend.repo_users import list_users, create_user, set_password, set_active

# ------------------------------------------------------------
# Boot: banco + SID + login
# ------------------------------------------------------------
init_db()                 # cria tabelas se não existirem
sticky_sid_bootstrap()    # fixa/restaura ?sid= e estabiliza a sessão
authenticator, ok, username, name, role = login()
if not ok:
    st.stop()

with st.sidebar:
    st.markdown(f"**{role or 'Usuário'} — {name or username or '—'}**")
    if st.button("Sair"):
        authenticator.logout()
        st.stop()

# ============================================================
# Utils de normalização e regex tolerante
# ============================================================
def _rm_acc(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")

def canon(s: str) -> str:
    if s is None or (isinstance(s, float) and pd.isna(s)):
        return ""
    s = str(s)
    s = s.replace("–", "-").replace("—", "-")
    s = _rm_acc(s).lower()
    s = re.sub(r"[.;:\s]+$", "", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s

def _flexify_fixed_literal(escaped: str) -> str:
    escaped = escaped.replace(r"\ ", r"\s+")
    escaped = escaped.replace(r"\,", r"[\s,]*")
    escaped = escaped.replace(r"\-", r"[\-\–\—]\s*")
    escaped = escaped.replace(r"\.", r"[\.\s]*")
    return escaped

def template_to_regex_flex(template: str):
    if template is None:
        template = ""
    t = re.sub(r"\s+", " ", str(template)).strip()
    parts = re.split(r"0+", t)
    fixed = [_flexify_fixed_literal(re.escape(p)) for p in parts]
    between = r"[\s\.,;:\-\–\—]*" + r"(.+?)" + r"[\s\.,;:\-\–\—]*"
    body = between.join(fixed)
    pattern = r"^\s*" + body + r"\s*[.,;:\-–—]*\s*$"
    try:
        return re.compile(pattern, flags=re.IGNORECASE | re.DOTALL)
    except re.error:
        return re.compile(r"^\s*" + re.escape(t) + r"\s*$", flags=re.IGNORECASE)

# ============================================================
# Catálogo de regras embutidas + índice RULES_MAP
# ============================================================
REGRAS_EMBUTIDAS = [
    {"causa": "Agendamento cancelado.", "motivo": "Alteração do tipo de serviço  – De assistência para reinstalação", "mascara_modelo": "Não foi possível realizar o atendimento devido 0 . Cliente  foi informado sobre a necessidade de reagendamento."},
    {"causa": "Agendamento cancelado.", "motivo": "Atendimento Improdutivo – Ponto Fixo/Móvel", "mascara_modelo": "Veículo compareceu para atendimento, porém por 0, não foi possível realizar o serviço."},
    {"causa": "Agendamento cancelado.", "motivo": "Cancelada a Pedido do Cliente", "mascara_modelo": "Cliente 0 , contato via  em  - , informou indisponibilidade para o atendimento."},
    {"causa": "Agendamento cancelado.", "motivo": "Cancelamento a pedido da RT", "mascara_modelo": "Não foi possível realizar o atendimento devido 0 . Cliente  o  -  foi informado sobre a necessidade de reagendamento."},
    {"causa": "Agendamento cancelado.", "motivo": "Cronograma de Instalação/Substituição de Placa", "mascara_modelo": "Realizado atendimento com substituição de placa. Alteração feita pela OS 0."},
    {"causa": "Agendamento cancelado.", "motivo": "Erro De Agendamento - Cliente desconhecia o agendamento", "mascara_modelo": "Em contato com o cliente o mesmo informou que desconhecia o agendamento. Nome cliente: 0 / Data contato:  - "},
    {"causa": "Agendamento cancelado.", "motivo": "Erro de Agendamento – Endereço incorreto", "mascara_modelo": "Erro identificado no agendamento: 0 . Situação:. Cliente  - informado em "},
    {"causa": "Agendamento cancelado.", "motivo": "Erro de Agendamento – Falta de informações na O.S.", "mascara_modelo": "OS agendada apresentou erro de 0  e foi identificado através de . Realizado o contato com o cliente  - no dia  - "},
    {"causa": "Agendamento cancelado.", "motivo": "Erro de Agendamento – O.S. agendada incorretamente (tipo/motivo/produto)", "mascara_modelo": "OS agendada apresentou erro de 0  e foi identificado através de . Realizado o contato com o cliente  - no dia  - "},
    {"causa": "Agendamento cancelado.", "motivo": "Erro de roteirização do agendamento - Atendimento móvel", "mascara_modelo": "Não foi possível concluir o atendimento devido 0 . Cliente ás  -  foi informado sobre a necessidade de reagendamento. Especialista  informado ás  - "},
    {"causa": "Agendamento cancelado.", "motivo": "Falta De Equipamento - Acessórios Imobilizado", "mascara_modelo": "Atendimento não realizado por falta de  0 . Cliente  Informado em  - "},
    {"causa": "Agendamento cancelado.", "motivo": "Falta De Equipamento - Item Reservado Não Compatível", "mascara_modelo": "Atendimento não realizado por falta de  0 . Cliente  Informado em  - "},
    {"causa": "Agendamento cancelado.", "motivo": "Falta De Equipamento - Material", "mascara_modelo": "Atendimento não realizado por falta de  0 . Cliente  Informado em  - "},
    {"causa": "Agendamento cancelado.", "motivo": "Falta De Equipamento - Principal", "mascara_modelo": "Atendimento não realizado por falta de  0 . Cliente  Informado em  - "},
    {"causa": "Agendamento cancelado.", "motivo": "Instabilidade de Equipamento/Sistema", "mascara_modelo": "Atendimento finalizado em 0  não concluído devido à instabilidade de . Registrado teste/reinstalação em  - . Realizado contato com a central  -  e foi gerada a ASM "},
    {"causa": "Agendamento cancelado.", "motivo": "No-show Cliente – Ponto Fixo/Móvel", "mascara_modelo": "Cliente não compareceu para atendimento até às 0."},
    {"causa": "Agendamento cancelado.", "motivo": "No-show Técnico", "mascara_modelo": "Técnico 0 , em  - , não realizou o atendimento por motivo de "},
    {"causa": "Agendamento cancelado.", "motivo": "Ocorrência com Técnico – Não foi possível realizar atendimento", "mascara_modelo": "Técnico 0 , em  - , não realizou o atendimento por motivo de "},
    {"causa": "Agendamento cancelado.", "motivo": "Ocorrência Com Técnico - Sem Tempo Hábil Para Realizar O Serviço (Atendimento Parcial)", "mascara_modelo": "Não foi possível concluir o atendimento devido 0 . Cliente  às  -  foi informado sobre a necessidade de reagendamento."},
    {"causa": "Agendamento cancelado.", "motivo": "Ocorrência Com Técnico - Sem Tempo Hábil Para Realizar O Serviço (Não iniciado)", "mascara_modelo": "Não foi possível realizar o atendimento devido 0 . Cliente  - informado do reagendamento."},
    {"causa": "Agendamento cancelado.", "motivo": "Ocorrência Com Técnico - Técnico Sem Habilidade Para Realizar Serviço", "mascara_modelo": "Não foi possível realizar o atendimento devido 0 . Cliente  foi informado sobre a necessidade de reagendamento."},
    {"causa": "Agendamento cancelado.", "motivo": "Perda/Extravio/Falta Do Equipamento/Equipamento Com Defeito", "mascara_modelo": "Não foi possível realizar o atendimento pois 0. Cliente recusou assinar termo."},
    {"causa": "Agendamento cancelado.", "motivo": "Serviço incompatível com a OS aberta", "mascara_modelo": "Não foi possível realizar o atendimento devido 0 . Cliente  às  -  foi informado sobre a necessidade de reagendamento."},
]

ESPECIAIS_NO_SHOW_CLIENTE = ["Automático - PORTAL", "Michelin", "OUTRO"]

def eh_especial_no_show_cliente(valor: str) -> bool:
    v = canon(valor)
    return any(canon(g) in v for g in ESPECIAIS_NO_SHOW_CLIENTE if g.strip())

def _build_rules_map():
    rules = {}
    for r in REGRAS_EMBUTIDAS:
        key = (canon(r["causa"]), canon(r["motivo"]))
        rules[key] = (r["motivo"], template_to_regex_flex(r["mascara_modelo"]), r["mascara_modelo"])
    return rules

RULES_MAP = _build_rules_map()

def recarregar_regras():
    global RULES_MAP
    RULES_MAP = _build_rules_map()

# ============================================================
# Parser simples: "Causa. Motivo. Máscara ..."
# ============================================================
def detect_motivo_and_mask(full_text: str):
    if not full_text:
        return "", "", ""
    txt = re.sub(r"\s+", " ", str(full_text)).strip()
    txt_c = canon(txt)
    causa_padrao = "Agendamento cancelado."
    causa_padrao_c = canon(causa_padrao)

    for (c_norm, m_norm), (motivo_original, _regex, _modelo) in RULES_MAP.items():
        if c_norm != causa_padrao_c:
            continue
        if m_norm in txt_c:
            idx = txt_c.find(m_norm) + len(m_norm)
            mascara = txt[idx:].strip(" .")
            return causa_padrao, motivo_original, mascara
    return "", "", txt

# ============================================================
# Streamlit (UI)
# ============================================================
st.set_page_config(page_title="Validador de No-show — v1.2.1", layout="wide")
st.title("Validador de No-show — PT-BR (v1.2.1) — Sem dupla checagem")
st.caption(
    "Módulo 1: pré-análise com regras embutidas + regra especial. "
    "Módulo 2: conferência no app (máscara conferida com validação automática)."
)

def read_any(f):
    if f is None:
        return None
    name = f.name.lower()
    if name.endswith(".csv"):
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

def categoria_por_motivo(motivo: str) -> str:
    m = canon(motivo)
    if not m:
        return ""
    if m.startswith("erro de agendamento") or "erro de roteirizacao do agendamento" in m:
        return "Erro Agendamento"
    if m.startswith("falta de equipamento") or "perda/extravio" in m or "equipamento com defeito" in m:
        return "Falta de equipamentos"
    return ""

# ============================================================
# MÓDULO 1 — Pré-análise
# ============================================================
st.header("Módulo 1 — Validador (Pré-análise)")

file = st.file_uploader(
    "Exportação (xlsx/csv) — coluna principal com 'Causa. Motivo. Máscara ...' e, opcionalmente, uma coluna especial",
    type=["xlsx", "csv"],
    help="A coluna especial é usada para a 'regra especial' (ex.: Automático - PORTAL, Michelin, OUTRO).",
)

out = None

with st.expander("Adicionar regras rápidas (runtime)", expanded=False):
    st.caption("Formato: `causa ; motivo ; mascara_modelo` — uma regra por linha.")
    exemplo = "Agendamento cancelado.; Erro de Agendamento – Documento inválido; OS apresentou erro de 0 identificado via 0. Cliente 0 informado em 0."
    regras_txt = st.text_area("Cole aqui as regras", value="", placeholder=exemplo, height=120)
    c1, c2 = st.columns(2)
    aplicar = c1.button("Aplicar regras")
    limpar = c2.button("Limpar")
    if limpar:
        st.session_state.pop("ultimas_regras_aplicadas", None)
        st.experimental_rerun()
    if aplicar:
        erros = []
        for ln, linha in enumerate(regras_txt.splitlines(), start=1):
            linha = linha.strip()
            if not linha:
                continue
            parts = [p.strip() for p in linha.split(";", 2)]
            if len(parts) != 3:
                erros.append(f"Linha {ln}: use 2 ';' (causa ; motivo ; mascara_modelo)")
                continue
            causa, motivo, mascara = parts
            if not causa or not motivo or not mascara:
                erros.append(f"Linha {ln}: campos vazios")
                continue
            REGRAS_EMBUTIDAS.append({"causa": causa, "motivo": motivo, "mascara_modelo": mascara})
        if erros:
            for e in erros:
                st.warning(e)
        else:
            recarregar_regras()
            st.success("✅ Regras aplicadas e ativas nesta sessão.")

if file:
    df = read_any(file)

    col_main = st.selectbox(
        "Coluna principal (Causa. Motivo. Máscara ...)",
        df.columns,
        help="Texto completo enviado pelo prestador: 'Causa. Motivo. Máscara ...'",
    )
    col_especial = st.selectbox(
        "Coluna especial (opcional) — gatilhos: Automático - PORTAL / Michelin / OUTRO",
        ["(Nenhuma)"] + list(df.columns),
        help="Se esta coluna contiver qualquer um dos gatilhos, a linha vira 'No-show Cliente' por regra especial.",
    )

    # --- cálculo dos resultados por linha ---
    resultados, detalhes = [], []
    causas, motivos, mascaras_preenchidas = [], [], []
    combos, mascaras_modelo = [], []

    for _, row in df.iterrows():
        causa, motivo, mascara = detect_motivo_and_mask(row.get(col_main, ""))
        causas.append(causa)
        motivos.append(motivo)
        mascaras_preenchidas.append(mascara)
        partes = [p for p in [str(causa).strip(), str(motivo).strip(), str(mascara).strip()] if p]
        combos.append(" ".join(partes))

        mascara_modelo_val = ""
        if col_especial != "(Nenhuma)":
            valor_especial = row.get(col_especial, "")
            if eh_especial_no_show_cliente(valor_especial):
                resultados.append("No-show Cliente")
                detalhes.append(
                    f"Regra especial aplicada: coluna especial = '{valor_especial}'. "
                    f"Gatilhos ativos: {', '.join(ESPECIAIS_NO_SHOW_CLIENTE)}"
                )
                mascaras_modelo.append(mascara_modelo_val)
                continue

        key = (canon(causa), canon(motivo))
        found = RULES_MAP.get(key)
        if not found:
            resultados.append("No-show Técnico")
            detalhes.append("Motivo não reconhecido nas regras embutidas.")
            mascaras_modelo.append(mascara_modelo_val)
            continue

        _motivo_oficial, regex, modelo = found
        mascara_modelo_val = modelo or ""
        mascara_norm = re.sub(r"\s+", " ", str(mascara)).strip()
        if regex.fullmatch(mascara_norm):
            resultados.append("Máscara correta")
            detalhes.append("")
        else:
            resultados.append("No-show Técnico")
            detalhes.append("Não casa com o modelo (modo tolerante).")
        mascaras_modelo.append(mascara_modelo_val)

    out = df.copy()

    # preserva/garante O.S.
    if "O.S." not in out.columns and "OS" in out.columns:
        out = out.rename(columns={"OS": "O.S."})
    if "O.S." not in out.columns:
        out["O.S."] = ""

    out["Causa detectada"] = causas
    out["Motivo detectado"] = motivos
    out["Máscara prestador (preenchida)"] = mascaras_preenchidas
    out["Máscara prestador"] = mascaras_modelo
    out["Causa. Motivo. Máscara (extra)"] = combos
    out["Classificação No-show"] = resultados
    out["Detalhe"] = detalhes

    # Resultado No Show derivado
    resultado_no_show = []
    for r_cls, mot in zip(resultados, motivos):
        cat = categoria_por_motivo(mot)
        if cat:
            resultado_no_show.append(cat)
        elif r_cls in ("Máscara correta", "No-show Cliente"):
            resultado_no_show.append("No-show Cliente")
        else:
            resultado_no_show.append("No-show Técnico")
    out["Resultado No Show"] = resultado_no_show

    # -------------------- Alocação por LOGIN (com fallback por nome) --------------------
    st.markdown("#### Alocação de atendentes")

    usuarios_ativos = [
        u for u in list_users(include_inactive=False)
        if u.get("role") == "atendente" and int(u.get("active", 0)) == 1
    ]
    logins_disponiveis = sorted({u["username"] for u in usuarios_ativos})
    nome_por_login = {u["username"]: u["name"] for u in usuarios_ativos}

    logins_escolhidos = st.multiselect(
        "Logins que participarão da conferência",
        options=logins_disponiveis,
        default=logins_disponiveis,
        help="As O.S. serão distribuídas ciclicamente entre os logins selecionados.",
    )

    st.caption("Fallback por **nome** (apenas se você não quiser distribuir por login).")
    qtd = st.number_input("Número de atendentes (fallback por nome)", 1, 200, 3)
    nomes_raw = st.text_area(
        "Nomes (1 por linha ou separados por , ; ) — usado apenas no fallback",
        value="",
    )

    if "Login atendente" not in out.columns and logins_escolhidos:
        import numpy as _np
        bloco = int(_np.ceil(len(out) / max(1, len(logins_escolhidos))))
        logins_alocados = (logins_escolhidos * bloco)[: len(out)]
        out.insert(0, "Login atendente", logins_alocados)
        out.insert(1, "Atendente designado", [nome_por_login.get(l, l) for l in logins_alocados])

    if "Atendente designado" not in out.columns:
        import re as _re, numpy as _np
        nomes = [n.strip() for n in _re.split(r"[,;\n]+", nomes_raw) if n.strip()]
        if not nomes:
            nomes = [f"Atendente {i+1}" for i in range(int(qtd))]
        else:
            while len(nomes) < int(qtd):
                nomes.append(f"Atendente {len(nomes)+1}")
        bloco = int(_np.ceil(len(out) / len(nomes)))
        out.insert(0, "Atendente designado", (nomes * bloco)[: len(out)])

    if "Login atendente" not in out.columns:
        rev_login_por_nome = {v: k for k, v in nome_por_login.items()}
        out.insert(0, "Login atendente", [rev_login_por_nome.get(str(n), "") for n in out["Atendente designado"]])
    # ------------------------------------------------------------------------------------

    # guarda OUT na sessão para permitir reatribuições no Módulo 2
    st.session_state["out_df"] = out

    st.success("Pré-análise concluída.")
    st.dataframe(out, use_container_width=True)

    # Exportar planilha da pré-análise
    buf_pre = io.BytesIO()
    with pd.ExcelWriter(buf_pre, engine="openpyxl") as w:
        out.to_excel(w, index=False, sheet_name="Resultado")
    st.download_button(
        "⬇️ Baixar Excel — Pré-análise",
        data=buf_pre.getvalue(),
        file_name="resultado_no_show.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )

# ============================================================
# MÓDULO 2 — Conferência (sem dupla checagem)
# ============================================================
st.markdown("---")
st.header("Módulo 2 — Conferência (sem dupla checagem)")

# carrega o OUT mais recente da sessão (se houver)
if "out_df" in st.session_state:
    out = st.session_state["out_df"]

if "out" in locals() and out is not None:

    # ================== Bulk reassignment (ADMIN) ==================
    if role == "admin" and "Login atendente" in out.columns:
        with st.expander("🔁 Reatribuir O.S. (Admin)", expanded=False):
            # logins atuais na planilha + logins ativos no banco
            current_logins = sorted(out["Login atendente"].astype(str).unique())
            ativos = [u for u in list_users(include_inactive=False) if int(u.get("active", 0)) == 1]
            known_logins = sorted(set(current_logins) | {u["username"] for u in ativos})
            nome_por_login_all = {u["username"]: u["name"] for u in ativos}

            src = st.selectbox("Reatribuir de (login origem)", current_logins, key="re_src")
            dst = st.selectbox("Para (login destino)", [l for l in known_logins if l != src], key="re_dst")
            only_pend = st.checkbox("Apenas O.S. com status '⏳ Pendente'", value=True, key="re_pend")
            qtd_max = st.number_input("Qtde a mover (0 = todas elegíveis)", min_value=0, max_value=len(out), value=0, step=1, key="re_qtd")

            if st.button("🔁 Reatribuir O.S. para outro login", key="btn_reassign"):
                mask = out["Login atendente"].astype(str) == str(src)
                if only_pend:
                    if "Status da conferência" in out.columns:
                        pend_mask = out["Status da conferência"].astype(str).fillna("").str.contains("Pendente")
                        mask = mask & pend_mask
                    else:
                        st.warning("Coluna 'Status da conferência' ainda não existe; reatribuindo **sem** filtrar pendentes.")
                idx = out[mask].index.tolist()
                if qtd_max and qtd_max > 0:
                    idx = idx[:qtd_max]
                if not idx:
                    st.info("Nada para reatribuir.")
                else:
                    out.loc[idx, "Login atendente"] = dst
                    out.loc[idx, "Atendente designado"] = [nome_por_login_all.get(dst, dst)] * len(idx)
                    st.session_state["out_df"] = out
                    st.success(f"Reatribuídas {len(idx)} O.S. de **{src}** → **{dst}**.")
    # ===============================================================

    st.markdown("### Conferência por atendente")

    chave = "Login atendente" if "Login atendente" in out.columns else "Atendente designado"

    if role == "admin":
        valor_sel = st.selectbox(
            f"Selecione { 'o login' if chave=='Login atendente' else 'o nome' }",
            options=sorted(out[chave].astype(str).unique()),
            help="Admin pode escolher qualquer atendente para conferir."
        )
    else:
        if chave == "Login atendente":
            valor_sel = (username or st.session_state.get("_auth_user", "") or "").strip()
            st.info(f"Você está conferindo as O.S. de **{valor_sel or '—'}**.")
        else:
            valor_sel = st.selectbox(
                "Selecione seu nome",
                options=sorted(out[chave].astype(str).unique()),
                help="Selecione o atendente para carregar apenas os registros designados."
            )

    df_atendente = out[out[chave].astype(str) == str(valor_sel)].copy()
    st.markdown(f"**Total de registros para {valor_sel or '—'}:** {len(df_atendente)}")

    # Garante colunas de conferência
    for col in [
        "Máscara conferida",
        "Classificação ajustada",
        "Status da conferência",
        "Observações",
        "Validação automática (conferida)",
        "Detalhe (app)",
    ]:
        if col not in df_atendente.columns:
            df_atendente[col] = ""

    # Opções
    classificacoes = [
        "No-show Cliente",
        "No-show Técnico",
        "Erro Agendamento",
        "Falta de equipamentos",
    ]
    status_opcoes = [
        "⏳ Pendente",
        "✅ App acertou",
        "❌ App errou, atendente corrigiu",
        "⚠️ Atendente errou",
    ]

    # ===== Edição linha a linha =====
    for i, row in df_atendente.iterrows():
        st.markdown("---")
        st.markdown(f"**O.S.:** {row.get('O.S.', '')}")
        st.markdown(f"**Texto original:** {row.get('Causa. Motivo. Máscara (extra)', '')}")
        st.markdown(f"**Classificação pré-análise:** {row.get('Classificação No-show', '')}")
        st.markdown(f"**Resultado No Show (app):** {row.get('Resultado No Show', '')}")

        # --- Detalhe / regra especial
        detalhe_app = str(row.get("Detalhe", "")).strip()
        df_atendente.at[i, "Detalhe (app)"] = detalhe_app
        is_regra_especial = "regra especial aplicada" in detalhe_app.lower()

        if detalhe_app:
            if is_regra_especial:
                st.warning(f"**Detalhe (regra especial):**\n\n{detalhe_app}", icon="⚠️")
            else:
                st.info(f"**Detalhe do app:** {detalhe_app}")

        # Modelo oficial
        modelo_oficial = "No-show Cliente" if is_regra_especial else str(row.get("Máscara prestador", "")).strip()
        st.markdown(f"**Máscara modelo (oficial):** `{modelo_oficial}`")

        # Máscara conferida (select + opção texto)
        opcoes_mask = ([modelo_oficial] if modelo_oficial else []) + ["(Outro texto)"]
        escolha = st.selectbox(
            f"Máscara conferida — escolha (linha {i})",
            options=opcoes_mask,
            key=f"mask_sel_{i}",
            help=(
                "Escolha a máscara oficial OU selecione '(Outro texto)' para digitar a máscara conferida no sistema. "
                "Em caso de regra especial, a máscara esperada é 'No-show Cliente'."
            ),
        )
        if escolha == "(Outro texto)":
            mask_conf = st.text_area(
                f"Digite a máscara conferida (linha {i})",
                value=str(row.get("Máscara conferida", "")),
                key=f"mask_txt_{i}",
                help="Se escolheu '(Outro texto)', digite aqui a máscara exata registrada na O.S.",
            )
        else:
            mask_conf = escolha

        # Validação automática
        if is_regra_especial:
            validacao = "✅ Máscara correta" if canon(mask_conf) == canon("No-show Cliente") else "❌ Máscara incorreta"
        else:
            causa = row.get("Causa detectada", "")
            motivo = row.get("Motivo detectado", "")
            key_rm = (canon(causa), canon(motivo))
            found = RULES_MAP.get(key_rm)
            if found:
                _, regex, _ = found
                mask_norm = re.sub(r"\s+", " ", str(mask_conf)).strip()
                validacao = "✅ Máscara correta" if regex.fullmatch(mask_norm) else "❌ Máscara incorreta"
            else:
                validacao = "⚠️ Motivo não reconhecido"

        st.caption(f"**Validação automática (conferida):** {validacao}")

        # Atualiza DF com edição
        df_atendente.at[i, "Máscara conferida"] = mask_conf
        df_atendente.at[i, "Validação automática (conferida)"] = validacao

        # Classificação ajustada
        if is_regra_especial and "No-show Cliente" in classificacoes:
            idx_default = classificacoes.index("No-show Cliente")
        else:
            idx_default = (
                classificacoes.index(row.get("Resultado No Show", ""))
                if row.get("Resultado No Show", "") in classificacoes
                else 0
            )
        df_atendente.at[i, "Classificação ajustada"] = st.selectbox(
            f"Classificação ajustada (linha {i})",
            options=classificacoes,
            index=idx_default,
            key=f"class_{i}",
            help="Ajuste a classificação final conforme a conferência no sistema.",
        )

        # Status da conferência (default Pendente; se existir valor, usa-o)
        status_atual = str(row.get("Status da conferência", "")).strip()
        idx_status = status_opcoes.index(status_atual) if status_atual in status_opcoes else 0
        df_atendente.at[i, "Status da conferência"] = st.selectbox(
            f"Status da conferência (linha {i})",
            options=status_opcoes,
            index=idx_status,
            key=f"status_{i}",
            help="Registre o desfecho ou mantenha pendente.",
        )

        # Observações
        df_atendente.at[i, "Observações"] = st.text_area(
            f"Observações (linha {i})",
            value=str(row.get("Observações", "")),
            key=f"obs_{i}",
            help="Observações complementares (evidências, contato, RT, etc.).",
        )

    # ==== Persistência da conferência no servidor ====
    st.markdown("#### Salvar no servidor")
    if st.button("💾 Salvar conferência deste atendente", type="primary", key="save_att"):
        batch_id = str(uuid.uuid4())[:8]
        gravados = upsert_reviews_from_df(
            df_atendente.copy(),
            username=(username or st.session_state.get("_auth_user", "")),
            batch_id=batch_id,
        )
        if gravados:
            st.success(f"✅ {gravados} linha(s) salva(s) (lote {batch_id}).")
        else:
            st.info("Nada novo para salvar.")

    # ==== Consolidação geral (somente Admin) ====
    if role == "admin":
        with st.expander("Consolidação geral (Admin)", expanded=False):
            if st.button("📥 Exportar consolidação (XLSX)", key="export_all"):
                df_all = list_all_reviews_df()
                if df_all.empty:
                    st.warning("Nenhum dado salvo ainda.")
                else:
                    buf = io.BytesIO()
                    with pd.ExcelWriter(buf, engine="openpyxl") as w:
                        df_all.to_excel(w, index=False, sheet_name="Consolidado")
                    st.download_button(
                        "⬇️ Baixar consolidado.xlsx",
                        data=buf.getvalue(),
                        file_name=f"consolidado_{datetime.now():%Y%m%d-%H%M}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        key="dl_all",
                    )

    # Tabela final + export do atendente
    st.markdown("### Tabela final da conferência")
    st.dataframe(df_atendente, use_container_width=True)

    buf_conf = io.BytesIO()
    with pd.ExcelWriter(buf_conf, engine="openpyxl") as w:
        df_atendente.to_excel(w, index=False, sheet_name="Conferencia")

    st.download_button(
        "⬇️ Baixar Excel — Conferência do atendente",
        data=buf_conf.getvalue(),
        file_name=f"conferencia_{valor_sel or 'atendente'}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        help="Exporta a conferência do atendente com a máscara conferida e a validação automática.",
    )
else:
    st.info("Realize a **Pré-análise** no Módulo 1 para habilitar a Conferência.")

# =========================
# Admin — Usuários (isolado em função)
# =========================
from backend.repo_users import (
    list_users, create_user, set_password, set_active,
)

def render_admin_users():
    st.markdown("---")
    st.header("Admin — Usuários")

    # Cria os tabs apenas aqui, dentro da função
    tab_listar, tab_criar, tab_senha, tab_status = st.tabs(
        ["👥 Listar", "➕ Criar", "🔑 Trocar senha", "🚦 Ativar/Desativar"]
    )

    # ------------ Listar ------------
    with tab_listar:
        include_inactive = st.checkbox("Mostrar inativos", value=True, key="adm_list_inativos")
        users_df = pd.DataFrame(list_users(include_inactive=include_inactive))
        if not users_df.empty:
            users_df = users_df.sort_values(["active", "username"], ascending=[False, True])
        st.dataframe(users_df, use_container_width=True)

    # ------------ Criar ------------
    with tab_criar:
        st.caption("Crie logins de atendentes (ou outro admin). A senha será mostrada uma única vez.")
        c1, c2 = st.columns(2)
        username_new = c1.text_input("Login (sem espaços)", key="adm_user_new")
        name_new = c2.text_input("Nome", key="adm_name_new")
        role_new = st.selectbox("Papel", ["atendente", "admin"], index=0, key="adm_role_new")

        if st.button("Criar usuário", key="adm_btn_criar"):
            import secrets
            pwd = secrets.token_urlsafe(8)
            try:
                create_user(username_new.strip(), name_new.strip(), pwd, role=role_new, active=1)
            except Exception as e:
                st.error(f"Não foi possível criar: {e}")
            else:
                st.success(f"Usuário criado: **{username_new}**")
                cred = f"login: {username_new}\nsenha: {pwd}\n"
                st.code(cred, language="bash")
                st.download_button(
                    "Baixar credenciais",
                    data=cred,
                    file_name=f"credenciais_{username_new}.txt",
                    mime="text/plain",
                    key="adm_dl_creds",
                )

    # ------------ Trocar senha ------------
    with tab_senha:
        ulist = [u["username"] for u in list_users()]
        if not ulist:
            st.info("Sem usuários.")
        else:
            u_sel = st.selectbox("Usuário", ulist, key="adm_sel_user_pwd")
            new_pwd = st.text_input("Nova senha", type="password", key="adm_new_pwd")
            if st.button("Alterar senha", key="adm_btn_pwd"):
                try:
                    set_password(u_sel, new_pwd)
                except Exception as e:
                    st.error(f"Erro: {e}")
                else:
                    st.success("Senha atualizada.")

    # ------------ Ativar / Desativar ------------
    with tab_status:
        users_all = list_users(include_inactive=True)
        if not users_all:
            st.info("Sem usuários.")
        else:
            u_sel = st.selectbox("Usuário", [u["username"] for u in users_all], key="adm_sel_user_status")
            ativo_atual = next((int(u["active"]) for u in users_all if u["username"] == u_sel), 1)
            novo_status = st.selectbox(
                "Status", ["Ativo", "Inativo"], index=0 if ativo_atual else 1, key="adm_sel_status"
            )
            if st.button("Aplicar status", key="adm_btn_status"):
                try:
                    set_active(u_sel, 1 if novo_status == "Ativo" else 0)
                except Exception as e:
                    st.error(f"Erro: {e}")
                else:
                    st.success("Status atualizado.")

# ===== chamada protegida por papel =====
st.markdown("---")
st.header("Admin — Usuários")
if role == "admin":
    render_admin_users()
else:
    st.info("Área restrita ao administrador.")
