import io
import re
import math
import unicodedata
import pandas as pd
import streamlit as st

# ------------------------------------------------------------
# CONFIG
# ------------------------------------------------------------
st.set_page_config(page_title="Validador de No-show — PT-BR", layout="wide")
st.title("Validador de No-show — PT-BR")

# ============================================================
# Regras embutidas (modelos oficiais de causa/motivo/máscara)
# -> Base normalizada a partir das regras enviadas
# ============================================================
REGRAS_EMBUTIDAS = [
    {
        "causa": "Agendamento cancelado",
        "motivo": "Alteração do tipo de serviço  – De assistência para reinstalação",
        "mascara_modelo": "Não foi possível realizar o atendimento devido 0 . Cliente  foi informado sobre a necessidade de reagendamento."
    },
    {
        "causa": "Agendamento cancelado",
        "motivo": "Atendimento Improdutivo – Ponto Fixo/Móvel",
        "mascara_modelo": "Veículo compareceu para atendimento, porém por 0, não foi possível realizar o serviço."
    },
    {
        "causa": "Agendamento cancelado",
        "motivo": "Cancelada a Pedido do Cliente",
        "mascara_modelo": "Cliente 0 , contato via  em  - , informou indisponibilidade para o atendimento."
    },
    {
        "causa": "Agendamento cancelado",
        "motivo": "Cancelada a Pedido do Cliente",
        "mascara_modelo": "Cliente 0 , contato via  em  - , informou indisponibilidade para o atendimento."
    },
    {
        "causa": "Agendamento cancelado",
        "motivo": "Cancelamento a pedido da RT",
        "mascara_modelo": "Não foi possível realizar o atendimento devido 0 . Cliente  o  -  foi informado sobre a necessidade de reagendamento."
    },
    {
        "causa": "Agendamento cancelado",
        "motivo": "Cronograma de Instalação/Substituição de Placa",
        "mascara_modelo": "Realizado atendimento com substituição de placa. Alteração feita pela OS 0."
    },
    {
        "causa": "Agendamento cancelado",
        "motivo": "Erro De Agendamento - Cliente desconhecia o agendamento",
        "mascara_modelo": "Em contato com o cliente o mesmo informou que desconhecia o agendamento. Nome cliente: 0 / Data contato:  - "
    },
    {
        "causa": "Agendamento cancelado",
        "motivo": "Erro de Agendamento – Endereço incorreto",
        "mascara_modelo": "Erro identificado no agendamento: 0 . Situação:. Cliente  - informado em "
    },
    {
        "causa": "Agendamento cancelado",
        "motivo": "Erro de Agendamento – Falta de informações na O.S.",
        "mascara_modelo": "OS agendada apresentou erro de 0  e foi identificado através de . Realizado o contato com o cliente  - no dia  - "
    },
    {
        "causa": "Agendamento cancelado",
        "motivo": "Erro de Agendamento – O.S. agendada incorretamente (tipo/motivo/produto)",
        "mascara_modelo": "OS agendada apresentou erro de 0  e foi identificado através de . Realizado o contato com o cliente  - no dia  - "
    },
    {
        "causa": "Agendamento cancelado",
        "motivo": "Erro de roteirização do agendamento - Atendimento móvel",
        "mascara_modelo": "Não foi possível concluir o atendimento devido 0 . Cliente ás  -  foi informado sobre a necessidade de reagendamento. Especialista  informado ás  - "
    },
    {
        "causa": "Agendamento cancelado",
        "motivo": "Erro de roteirização do agendamento - Atendimento móvel",
        "mascara_modelo": "Não foi possível concluir o atendimento devido 0 . Cliente ás  -  foi informado sobre a necessidade de reagendamento. Especialista  informado ás  - "
    },
    {
        "causa": "Agendamento cancelado",
        "motivo": "Falta De Equipamento - Acessórios Imobilizado",
        "mascara_modelo": "Atendimento não realizado por falta de  0 . Cliente  Informado em  - "
    },
    {
        "causa": "Agendamento cancelado",
        "motivo": "Falta De Equipamento - Item Reservado Não Compatível",
        "mascara_modelo": "Atendimento não realizado por falta de  0 . Cliente  Informado em  - "
    },
    {
        "causa": "Agendamento cancelado",
        "motivo": "Falta De Equipamento - Material",
        "mascara_modelo": "Atendimento não realizado por falta de  0 . Cliente  Informado em  - "
    },
    {
        "causa": "Agendamento cancelado",
        "motivo": "Falta De Equipamento - Principal",
        "mascara_modelo": "Atendimento não realizado por falta de  0 . Cliente  Informado em  - "
    },
    {
        "causa": "Agendamento cancelado",
        "motivo": "Instabilidade de Equipamento/Sistema",
        "mascara_modelo": "Atendimento finalizado em 0  não concluído devido à instabilidade de . Registrado teste/reinstalação em  - . Realizado contato com a central  -  e foi gerada a ASM "
    },
    {
        "causa": "Agendamento cancelado",
        "motivo": "No-show Cliente – Ponto Fixo/Móvel",
        "mascara_modelo": "Cliente não compareceu para atendimento até às 0."
    },
    {
        "causa": "Agendamento cancelado",
        "motivo": "No-show Técnico",
        "mascara_modelo": "Técnico 0 , em  - , não realizou o atendimento por motivo de "
    },
    {
        "causa": "Agendamento cancelado",
        "motivo": "Ocorrência com Técnico – Não foi possível realizar atendimento",
        "mascara_modelo": "Técnico 0 , em  - , não realizou o atendimento por motivo de "
    },
    {
        "causa": "Agendamento cancelado",
        "motivo": "Ocorrência Com Técnico - Sem Tempo Hábil Para Realizar O Serviço (Atendimento Parcial)",
        "mascara_modelo": "Não foi possível concluir o atendimento devido 0 . Cliente  às  -  foi informado sobre a necessidade de reagendamento."
    },
    {
        "causa": "Agendamento cancelado",
        "motivo": "Ocorrência Com Técnico - Sem Tempo Hábil Para Realizar O Serviço (Não iniciado)",
        "mascara_modelo": "Não foi possível realizar o atendimento devido 0 . Cliente  - informado do reagendamento."
    },
    {
        "causa": "Agendamento cancelado",
        "motivo": "Ocorrência Com Técnico - Sem Tempo Hábil Para Realizar O Serviço (Não iniciado)",
        "mascara_modelo": "Não foi possível realizar o atendimento devido 0 . Cliente  - informado do reagendamento."
    },
    {
        "causa": "Agendamento cancelado",
        "motivo": "Ocorrência Com Técnico - Técnico Sem Habilidade Para Realizar Serviço",
        "mascara_modelo": "Não foi possível realizar o atendimento devido 0 . Cliente  foi informado sobre a necessidade de reagendamento."
    },
    {
        "causa": "Agendamento cancelado",
        "motivo": "Perda/Extravio/Falta Do Equipamento/Equipamento Com Defeito",
        "mascara_modelo": "Não foi possível realizar o atendimento pois 0. Cliente recusou assinar termo."
    },
    {
        "causa": "Agendamento cancelado",
        "motivo": "Serviço incompatível com a OS aberta",
        "mascara_modelo": "Não foi possível realizar o atendimento devido 0 . Cliente  às  -  foi informado sobre a necessidade de reagendamento."
    }
]


# ------------------------------------------------------------
# UTILITÁRIOS (normalização + regex tolerante)
# ------------------------------------------------------------
def rm_acc(s: str) -> str:
    return ''.join(c for c in unicodedata.normalize('NFD', s) if unicodedata.category(c) != 'Mn')

def canon(s: str) -> str:
    if pd.isna(s):
        return ""
    s = str(s)
    s = s.replace("–", "-").replace("—", "-")
    s = rm_acc(s).lower()
    s = re.sub(r"[.;:\s]+$", "", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s

def _flexify_fixed_literal(escaped: str) -> str:
    escaped = escaped.replace(r"\ ", r"\s+")
    escaped = escaped.replace(r"\,", r"[\s,]*")
    escaped = escaped.replace(r"\-", r"[\-\–\—]\s*")
    escaped = escaped.replace(r"\.", r"[\.\s]*")
    return escaped

def template_to_regex_flex(template: str) -> re.Pattern:
    if pd.isna(template):
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

# Mapa pré-compilado das regras
RULES_MAP = {}
for r in REGRAS_EMBUTIDAS:
    key = (canon(r["causa"]), canon(r["motivo"]))
    RULES_MAP[key] = (r["motivo"], template_to_regex_flex(r["mascara_modelo"]), r["mascara_modelo"])

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

def read_any(f):
    if f is None:
        return None
    name = f.name.lower()
    if name.endswith(".csv"):
        try:
            return pd.read_csv(f, sep=None, engine="python")
        except Exception:
            f.seek(0); return pd.read_csv(f)
    try:
        return pd.read_excel(f, engine="openpyxl")
    except Exception:
        f.seek(0); return pd.read_excel(f)

# ------------------------------------------------------------
# Gatilhos da REGRA ESPECIAL → viram "No-show Cliente"
# ------------------------------------------------------------
ESPECIAIS_NO_SHOW_CLIENTE = [
    "Automático - PORTAL",
    "Michelin",
    "OUTRO",
]

def eh_especial_no_show_cliente(valor: str) -> bool:
    v = canon(valor)
    return any(canon(g) in v for g in ESPECIAIS_NO_SHOW_CLIENTE if g.strip())

# ============================================================
# (Opcional) Adicionar regras rápidas (runtime)
# ============================================================
st.markdown("#### (Opcional) Adicionar regras rápidas (runtime)")
with st.expander("Adicionar novas regras **sem editar** o código"):
    st.caption("Formato: **uma regra por linha**, separando por ponto e vírgula: `causa ; motivo ; mascara_modelo`")
    exemplo = "Agendamento cancelado.; Erro de Agendamento – Documento inválido; OS apresentou erro de 0 identificado via 0. Cliente 0 informado em 0."
    regras_txt = st.text_area("Cole aqui as regras", value="", placeholder=exemplo, height=140)

    col_apply, col_clear = st.columns([1, 1])
    aplicar = col_apply.button("Aplicar regras rápidas")
    limpar  = col_clear.button("Limpar caixa")

    if limpar:
        st.session_state.pop("ultimas_regras_aplicadas", None)
        st.experimental_rerun()

    if aplicar:
        extras, erros = [], []
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
                erros.append(f"Linha {ln}: 'causa', 'motivo' e 'mascara_modelo' não podem estar vazios")
                continue
            extras.append({"causa": causa, "motivo": motivo, "mascara_modelo": mascara})

        if erros:
            for e in erros:
                st.warning(e)

        if extras:
            base_by_key = {(canon(r["causa"]), canon(r["motivo"])): r for r in REGRAS_EMBUTIDAS}
            for r in extras:
                key = (canon(r["causa"]), canon(r["motivo"]))
                base_by_key[key] = r
            REGRAS_EMBUTIDAS[:] = list(base_by_key.values())

            RULES_MAP.clear()
            for r in REGRAS_EMBUTIDAS:
                key = (canon(r["causa"]), canon(r["motivo"]))
                RULES_MAP[key] = (r["motivo"], template_to_regex_flex(r["mascara_modelo"]), r["mascara_modelo"])

            st.session_state["ultimas_regras_aplicadas"] = extras
            st.success(f"✅ {len(extras)} regra(s) adicionada(s)/atualizada(s). Já estão ativas nesta sessão.")

if "ultimas_regras_aplicadas" in st.session_state and st.session_state["ultimas_regras_aplicadas"]:
    st.markdown("#### Últimas regras aplicadas")
    st.dataframe(pd.DataFrame(st.session_state["ultimas_regras_aplicadas"]), use_container_width=True)

# ============================================================
# Exportar regras (JSON)
# ============================================================
import json
from datetime import datetime

st.markdown("#### Exportar regras (JSON)")

def _sort_key(r):
    return (str(r.get("causa", "")).lower(), str(r.get("motivo", "")).lower())

regras_atuais = sorted(REGRAS_EMBUTIDAS, key=_sort_key)
json_str = json.dumps(regras_atuais, ensure_ascii=False, indent=2)
fname = f"regras_no_show_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

st.download_button(
    label="📥 Baixar regras atuais (JSON)",
    data=json_str.encode("utf-8"),
    file_name=fname,
    mime="application/json",
    help="Exporta todas as regras ativas neste momento (inclui as adicionadas em runtime)."
)

with st.expander("Pré-visualizar regras (tabela)"):
    st.dataframe(pd.DataFrame(regras_atuais), use_container_width=True)

# ------------------------------------------------------------
# MÓDULO 1 — PRÉ-ANÁLISE (VALIDADOR)
# ------------------------------------------------------------
st.header("Módulo 1 — Validador (Pré-análise)")
st.markdown("""
Selecione **uma coluna** com o texto completo no formato:

**`Causa. Motivo. Máscara (preenchida pelo prestador)...`**

E (opcional) selecione uma **coluna especial**: se o valor bater em **qualquer gatilho** (ex.: `Automático - PORTAL`, `Michelin`, `OUTRO`), a linha será classificada como **No-show Cliente**.
""")

# Helper p/ 4 categorias
def categoria_por_motivo(motivo: str) -> str:
    m = canon(motivo)
    if not m:
        return ""
    if m.startswith("erro de agendamento") or "erro de roteirizacao do agendamento" in m:
        return "Erro Agendamento"
    if m.startswith("falta de equipamento") or "perda/extravio" in m or "equipamento com defeito" in m:
        return "Falta de equipamentos"
    return ""

file = st.file_uploader("Exportação (xlsx/csv) — coluna única + (opcional) coluna especial", type=["xlsx","csv"])

if file:
    df = read_any(file)
    col_main = st.selectbox("Coluna principal (Causa. Motivo. Máscara...)", df.columns)
    col_especial = st.selectbox(
        "Coluna especial (opcional) — gatilhos forçam No-show Cliente",
        ["(Nenhuma)"] + list(df.columns)
    )

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
            detalhes.append("Não casa com o modelo (mesmo no modo tolerante).")
        mascaras_modelo.append(mascara_modelo_val)

    out = df.copy()
    out["Causa detectada"] = causas
    out["Motivo detectado"] = motivos
    out["Máscara prestador (preenchida)"] = mascaras_preenchidas
    out["Máscara prestador"] = mascaras_modelo
    out["Causa. Motivo. Máscara (extra)"] = combos
    out["Classificação No-show"] = resultados
    out["Detalhe"] = detalhes

    # Resultado No Show (4 categorias)
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

    # Alocação de atendentes
    st.markdown("### Alocação de atendentes (opcional)")
    qtd_atend = st.number_input("Número de atendentes", min_value=1, max_value=200, value=3, step=1)
    nomes_raw = st.text_area(
        "Nomes dos atendentes (um por linha ou separados por vírgula/;)",
        value="",
        placeholder="Ex.: Ana\nBruno\nCarla  (ou)  Ana, Bruno, Carla"
    )

    nomes_list = [n.strip() for n in re.split(r"[,;\n]+", nomes_raw) if n.strip()]
    if not nomes_list:
        nomes_list = [f"Atendente {i+1}" for i in range(int(qtd_atend))]
    else:
        while len(nomes_list) < int(qtd_atend):
            nomes_list.append(f"Atendente {len(nomes_list)+1}")
    n_final = len(nomes_list)

    total_linhas = len(out)
    bloco = math.ceil(total_linhas / n_final) if n_final else total_linhas
    designados = (nomes_list * bloco)[:total_linhas]

    try:
        pos = out.columns.get_loc("Causa detectada")
        out.insert(pos, "Atendente designado", designados)
    except Exception:
        out["Atendente designado"] = designados

    # Exportação (Pré-análise)
    st.markdown("### Exportação — seleção de colunas")
    export_all_pre = st.checkbox(
        "Exportar **todas** as colunas (originais + geradas)",
        value=True,
        help="Desmarque para escolher manualmente quais colunas vão para o Excel."
    )

    geradas_order = [
        "Atendente designado",
        "Causa detectada",
        "Motivo detectado",
        "Máscara prestador (preenchida)",
        "Máscara prestador",
        "Causa. Motivo. Máscara (extra)",
        "Classificação No-show",
        "Detalhe",
        "Resultado No Show",
    ]
    originais = [c for c in df.columns if c in out.columns]
    geradas   = [c for c in geradas_order if c in out.columns]
    todas_cols_pre = originais + geradas

    if export_all_pre:
        cols_export_pre = todas_cols_pre
    else:
        st.caption("Escolha as colunas que irão para o arquivo (ordem respeitada):")
        default_pre = [c for c in ["O.S.", "MOTIVO CANCELAMENTO", "Atendente designado",
                                   "Causa detectada", "Motivo detectado",
                                   "Classificação No-show", "Resultado No Show"] if c in todas_cols_pre]
        cols_export_pre = st.multiselect("Colunas para exportar", options=todas_cols_pre, default=default_pre)
        if not cols_export_pre:
            st.warning("Nenhuma coluna selecionada. Exportarei todas as colunas.")
            cols_export_pre = todas_cols_pre

    st.success("Validação concluída.")
    st.dataframe(out[cols_export_pre], use_container_width=True)

    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as w:
        out[cols_export_pre].to_excel(w, index=False, sheet_name="Resultado")
    st.download_button(
        "Baixar Excel — Pré-análise (com seleção de colunas)",
        data=buf.getvalue(),
        file_name="resultado_no_show.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
else:
    st.info("Envie a exportação; selecione a coluna única e (opcionalmente) a coluna especial.")

# ------------------------------------------------------------
# MÓDULO 2 — CONFERÊNCIA (multi-duplas Robô × Atendente)
# (ÚNICO BLOCO — evita DuplicateWidgetID)
# ------------------------------------------------------------
st.markdown("---")
st.markdown("---")
st.header("Módulo 2 — Conferência dos atendentes")

if 'out' in locals():
    st.markdown("### Conferência por atendente")
    nome_atendente = st.selectbox("Selecione seu nome", options=sorted(out["Atendente designado"].unique()))
    df_atendente = out[out["Atendente designado"] == nome_atendente].copy()

    st.markdown(f"**Total de registros para {nome_atendente}:** {len(df_atendente)}")

    # Campos de conferência
    df_atendente["Máscara conferida"] = ""
    df_atendente["Classificação ajustada"] = ""
    df_atendente["Status da conferência"] = ""
    df_atendente["Observações"] = ""

    classificacoes = ["No-show Cliente", "No-show Técnico", "Erro Agendamento", "Falta de equipamentos", "Correta"]
    status_opcoes = ["✅ App acertou", "❌ App errou, atendente corrigiu", "⚠️ Atendente errou", "⏳ Pendente"]

    for i, row in df_atendente.iterrows():
        st.markdown("---")
        st.markdown(f"**O.S.:** {row.get('O.S.', '')}")
        st.markdown(f"**Texto original:** {row.get('Causa. Motivo. Máscara (extra)', '')}")
        st.markdown(f"**Classificação pré-análise:** {row.get('Classificação No-show', '')}")
        st.markdown(f"**Resultado No Show:** {row.get('Resultado No Show', '')}")
        st.markdown(f"**Máscara modelo:** {row.get('Máscara prestador', '')}")

        df_atendente.at[i, "Máscara conferida"] = st.text_input(f"Máscara conferida (linha {i})", value="", key=f"mask_{i}")
        df_atendente.at[i, "Classificação ajustada"] = st.selectbox(f"Classificação ajustada (linha {i})", options=classificacoes, key=f"class_{i}")
        df_atendente.at[i, "Status da conferência"] = st.selectbox(f"Status da conferência (linha {i})", options=status_opcoes, key=f"status_{i}")
        df_atendente.at[i, "Observações"] = st.text_area(f"Observações (linha {i})", value="", key=f"obs_{i}")

    st.markdown("### Tabela final da conferência")
    st.dataframe(df_atendente, use_container_width=True)

    # Exportação
    buf_conf = io.BytesIO()
    with pd.ExcelWriter(buf_conf, engine="openpyxl") as w:
        df_atendente.to_excel(w, index=False, sheet_name="Conferencia")

    st.download_button(
        "Baixar Excel — Conferência do atendente",
        data=buf_conf.getvalue(),
        file_name=f"conferencia_{nome_atendente}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
else:
    st.info("Realize a pré-análise no Módulo 1 para habilitar a conferência.")


