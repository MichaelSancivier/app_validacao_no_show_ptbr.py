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
st.header("Módulo 2 — Conferência (Dupla checagem) — múltiplas comparações")
st.markdown("""
Envie o **relatório conferido pelo atendente** (xlsx/csv).  
Mapeie **duplas de comparação** (coluna do **Robô** × coluna do **Atendente**).

**Status Geral da linha**
- **OK**: todas as duplas mapeadas estão OK  
- **Pendência (vazio)**: alguma dupla tem valor do atendente vazio  
- **Divergência**: pelo menos uma dupla diverge
""")

def read_any_loose(f):
    if f is None:
        return None
    name = f.name.lower()
    if name.endswith(".csv"):
        try:
            return pd.read_csv(f, sep=None, engine="python", skip_blank_lines=True)
        except Exception:
            f.seek(0); return pd.read_csv(f)
    try:
        df = pd.read_excel(f, engine="openpyxl")
        if str(df.columns[0]).lower().startswith("unnamed"):
            f.seek(0)
            df = pd.read_excel(f, engine="openpyxl", skiprows=1)
        return df
    except Exception:
        f.seek(0); return pd.read_excel(f)

# normalizador (cobre 4 categorias)
def normalize_outcome(x: str) -> str:
    c = canon(x)
    if "erro agendamento" in c or ("erro" in c and "agendamento" in c):
        return "erro agendamento"
    if "falta de equipamento" in c or "perda/extravio" in c or "equipamento com defeito" in c:
        return "falta de equipamentos"
    if "cliente" in c:
        return "no-show cliente"
    if "tecnico" in c or "técnico" in c:
        return "no-show tecnico"
    if "mascara correta" in c or "máscara correta" in c:
        return "no-show cliente"
    return c

conf_file = st.file_uploader("Relatório conferido (xlsx/csv)", type=["xlsx", "csv"], key="conf-multi")

if "pairs_n" not in st.session_state:
    st.session_state.pairs_n = 3

if conf_file:
    dfr = read_any_loose(conf_file)
    cols = list(dfr.columns)

    st.subheader("Duplas de comparação (Robô × Atendente)")
    cbtn1, cbtn2, _ = st.columns([1,1,6])
    if cbtn1.button("➕ Adicionar dupla"):
        st.session_state.pairs_n += 1
    if st.session_state.pairs_n > 1 and cbtn2.button("➖ Remover última"):
        st.session_state.pairs_n -= 1

    pair_defs = []
    for i in range(st.session_state.pairs_n):
        c1, c2 = st.columns(2)
        robo_col = c1.selectbox(f"Robô — coluna #{i+1}", cols, key=f"robot_col_{i}")
        att_col  = c2.selectbox(f"Atendente — coluna #{i+1}", cols, key=f"att_col_{i}")
        pair_defs.append((robo_col, att_col))

    pair_labels = [f"{rc} × {ac}" for rc, ac in pair_defs]

    def safe_sheet_name(name: str) -> str:
        bad = r']:*?/\\['
        for ch in bad:
            name = name.replace(ch, "_")
        name = name.strip()
        return name[:31] if len(name) > 31 else name

    linhas_status_geral = []
    pair_status_cols = {i: [] for i in range(st.session_state.pairs_n)}
    pair_robo_norm_cols = {i: [] for i in range(st.session_state.pairs_n)}
    pair_att_norm_cols  = {i: [] for i in range(st.session_state.pairs_n)}

    for _, r in dfr.iterrows():
        tem_pendencia = False
        tem_div = False
        for i, (rc, ac) in enumerate(pair_defs):
            robo_val = r.get(rc, "")
            att_val  = r.get(ac, "")

            rn = normalize_outcome(robo_val)
            an = normalize_outcome(att_val)

            pair_robo_norm_cols[i].append(rn)
            pair_att_norm_cols[i].append(an)

            if not str(att_val).strip():
                pair_status_cols[i].append("Pendência (vazio)")
                tem_pendencia = True
            else:
                if rn == an:
                    pair_status_cols[i].append("OK")
                else:
                    pair_status_cols[i].append("Divergência")
                    tem_div = True

        if tem_pendencia:
            linhas_status_geral.append("Pendência (vazio)")
        else:
            linhas_status_geral.append("Divergência" if tem_div else "OK")

    dfo = dfr.copy()
    for i in range(st.session_state.pairs_n):
        dfo[f"{pair_labels[i]} — Robô (norm)"] = pair_robo_norm_cols[i]
        dfo[f"{pair_labels[i]} — Atendente (norm)"] = pair_att_norm_cols[i]
        dfo[f"{pair_labels[i]} — Status"] = pair_status_cols[i]
    dfo["Conferência — Status geral"] = linhas_status_geral

    total = len(dfo)
    ok   = int((dfo["Conferência — Status geral"] == "OK").sum())
    pend = int((dfo["Conferência — Status geral"] == "Pendência (vazio)").sum())
    div  = int((dfo["Conferência — Status geral"] == "Divergência").sum())
    acc  = (ok / total * 100.0) if total else 0.0

    st.subheader("Resumo")
    st.write(f"**Total:** {total}  |  **OK:** {ok}  |  **Divergência:** {div}  |  **Pendência:** {pend}  |  **Acurácia:** {acc:.1f}%")

    desvio_rt    = (div / total * 100.0) if total else 0.0
    desvio_att   = (pend / total * 100.0) if total else 0.0
    perc_rpa     = (ok / total * 100.0) if total else 0.0
    perc_humano  = ((div + pend) / total * 100.0) if total else 0.0

    st.subheader("Indicadores")
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("% Desvios RT", f"{desvio_rt:.1f}%")
    k2.metric("% Desvios atendente", f"{desvio_att:.1f}%")
    k3.metric("% RPA", f"{perc_rpa:.1f}%")
    k4.metric("% Atendimento Humano", f"{perc_humano:.1f}%")

    st.markdown(
        f"""
**Como interpretar estes indicadores:**

- **{desvio_rt:.1f}% Desvios RT** = {desvio_rt:.1f}% das linhas deram **divergência** Robô × Atendente.  
- **{desvio_att:.1f}% Desvios atendente** = {desvio_att:.1f}% das linhas ficaram **pendentes** (campo do atendente vazio).  
- **{perc_rpa:.1f}% RPA** = {perc_rpa:.1f}% das linhas **bateram 100%** entre Robô e Atendente (sem intervenção).  
- **{perc_humano:.1f}% Atendimento Humano** = {perc_humano:.1f}% das linhas **exigiram revisão humana** (divergência ou pendência).
"""
    )

    st.subheader("Indicadores por dupla de comparação")
    st.caption("Cada dupla é nomeada como **Robô × Atendente** usando os nomes de coluna selecionados.")

    indicadores_duplas = []
    for i in range(st.session_state.pairs_n):
        serie_status = pd.Series(pair_status_cols[i])
        tot_p = int(serie_status.size)
        ok_p  = int((serie_status == "OK").sum())
        div_p = int((serie_status == "Divergência").sum())
        pen_p = int((serie_status == "Pendência (vazio)").sum())

        pct_ok  = (ok_p  / tot_p * 100.0) if tot_p else 0.0
        pct_div = (div_p / tot_p * 100.0) if tot_p else 0.0
        pct_pen = (pen_p / tot_p * 100.0) if tot_p else 0.0

        indicadores_duplas.append({
            "Dupla": pair_labels[i],
            "Total": tot_p,
            "OK": ok_p,           "% OK": round(pct_ok, 1),
            "Divergência": div_p, "% Divergência": round(pct_div, 1),
            "Pendência": pen_p,   "% Pendência": round(pct_pen, 1),
        })

    df_ind_duplas = pd.DataFrame(indicadores_duplas)
    st.dataframe(df_ind_duplas, use_container_width=True)

    with st.expander("Como ler os indicadores por dupla"):
        st.markdown("""
- **% OK**: proporção de linhas em que Robô e Atendente coincidiram **nesta dupla**.  
- **% Divergência**: proporção de linhas com **diferença** nesta dupla.  
- **% Pendência**: proporção de linhas que ficaram **sem preenchimento do atendente** nesta dupla.  
> O **Status geral** da linha é OK apenas se **todas** as duplas mapeadas estiverem OK.
""")

    st.subheader("Matrizes de concordância (por dupla)")
    matrizes = {}
    for i in range(st.session_state.pairs_n):
        try:
            cm = pd.crosstab(
                pd.Series(pair_robo_norm_cols[i], name="Robô (norm)"),
                pd.Series(pair_att_norm_cols[i],  name="Atendente (norm)")
            )
            matrizes[i] = cm
            st.markdown(f"**{pair_labels[i]}**")
            st.dataframe(cm, use_container_width=True)
        except Exception:
            st.info(f"Não foi possível montar a matriz para a dupla **{pair_labels[i]}**.")

    st.markdown("### Exportação — seleção de conteúdo")
    exp_conf   = st.checkbox("Incluir aba **Conferencia**", value=True)
    exp_kpis   = st.checkbox("Incluir aba **Indicadores**", value=True)
    exp_duplas = st.checkbox("Incluir aba **Indicadores_por_dupla**", value=True)
    exp_mats   = st.checkbox("Incluir **Matriz_<Dupla>**", value=True)

    export_all_conf = st.checkbox(
        "Conferencia: exportar **todas** as colunas",
        value=True,
        help="Desmarque para escolher manualmente as colunas da aba Conferencia."
    )

    if export_all_conf:
        cols_export_conf = list(dfo.columns)
    else:
        st.caption("Escolha as colunas da aba **Conferencia** (ordem respeitada):")
        favs = [c for c in dfo.columns if any(k in c for k in ["Status geral", "Status", "Robô (norm)", "Atendente (norm)"])]
        base_defaults = [c for c in dfr.columns if c in dfo.columns][:5]
        default_conf = list(dict.fromkeys(base_defaults + favs))[:20] or list(dfo.columns)[:20]
        cols_export_conf = st.multiselect("Colunas para a aba Conferencia", options=list(dfo.columns), default=default_conf)
        if not cols_export_conf:
            st.warning("Sem colunas selecionadas para a aba Conferencia — exportarei todas.")
            cols_export_conf = list(dfo.columns)

    outbuf = io.BytesIO()
    with pd.ExcelWriter(outbuf, engine="openpyxl") as w:
        if exp_conf:
            dfo[cols_export_conf].to_excel(w, index=False, sheet_name="Conferencia")
        if exp_kpis:
            indicadores = pd.DataFrame([
                {"Métrica": "Total", "Valor": total},
                {"Métrica": "OK", "Valor": ok},
                {"Métrica": "Divergência", "Valor": div},
                {"Métrica": "Pendência", "Valor": pend},
                {"Métrica": "% Desvios RT", "Valor": round(desvio_rt, 1)},
                {"Métrica": "% Desvios atendente", "Valor": round(desvio_att, 1)},
                {"Métrica": "% RPA", "Valor": round(perc_rpa, 1)},
                {"Métrica": "% Atendimento Humano", "Valor": round(perc_humano, 1)},
                {"Métrica": "Acurácia (%)", "Valor": round(acc, 1)},
            ])
            indicadores.to_excel(w, index=False, sheet_name="Indicadores")
        if exp_duplas:
            df_ind_duplas.to_excel(w, index=False, sheet_name="Indicadores_por_dupla")
        if exp_mats and matrizes:
            for i, cm in matrizes.items():
                sheet = safe_sheet_name(f"Matriz_{pair_labels[i]}")
                cm.to_excel(w, sheet_name=sheet)

    st.download_button(
        "Baixar Excel da conferência (seleção aplicada)",
        data=outbuf.getvalue(),
        file_name="conferencia_no_show.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
else:
    st.info("Para rodar a conferência, envie o relatório e mapeie as duplas (Robô × Atendente).")


# ------------------------------------------------------------
# MÓDULO 2 — CONFERÊNCIA INDIVIDUAL POR ATENDENTE
# ------------------------------------------------------------
st.markdown("---")

st.markdown("### Validação automática das máscaras preenchidas")

if 'out' in locals():
    df_validado = out.copy()
    validacoes = []
    for i, row in df_validado.iterrows():
        causa = canon(row.get("Causa detectada", ""))
        motivo = canon(row.get("Motivo detectado", ""))
        mascara = str(row.get("Máscara prestador (preenchida)", "")).strip()
        key = (causa, motivo)
        found = RULES_MAP.get(key)
        if found:
            _, regex, _ = found
            if regex.fullmatch(mascara):
                validacoes.append("✅ Máscara correta")
            else:
                validacoes.append("❌ Máscara incorreta")
        else:
            validacoes.append("⚠️ Motivo não reconhecido")
    df_validado["Validação automática"] = validacoes
    st.dataframe(df_validado, use_container_width=True)
else:
    st.info("Realize a pré-análise no Módulo 1 para habilitar a validação automática.")

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

