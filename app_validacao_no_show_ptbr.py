import io
import re
import unicodedata
import pandas as pd
import streamlit as st

st.set_page_config(page_title="Validador de No-show — Uma Coluna (PT-BR) [FLEX + Regra Especial]", layout="wide")
st.title("Validador de No-show — Uma Coluna (PT-BR) [FLEX + Regra Especial]")

st.markdown("""
Selecione **apenas uma coluna** que contenha o texto completo no formato:

**`Causa. Motivo. Mascara (preenchida pelo prestador)...`**

E (opcional) selecione uma **coluna especial** onde, se o valor for **`Automático - PORTAL`**, a classificação será forçada para **`No-show Cliente`**.
Caso o valor seja diferente, a validação segue as regras normais (Causa + Motivo + Máscara).

Este modo é **tolerante** a pequenas variações de pontuação e espaços:
- vírgula opcional (ex.: `, via` ou ` via`),
- hífen/tipos de traço (`-`, `–`, `—`),
- espaços extras ou pontuação grudada nos valores dos `0`.

Os `0` do modelo são **placeholders** e aceitam qualquer conteúdo preenchido pelo prestador.
""")

# ==============================
# Regras embutidas (15)
# ==============================
REGRAS_EMBUTIDAS = [
    {"causa":"Agendamento cancelado.","motivo":"Atendimento Improdutivo – Ponto Fixo","mascara_modelo":"Veículo compareceu para atendimento, porém por 0, não foi possível realizar o serviço."},
    {"causa":"Agendamento cancelado.","motivo":"Cancelada a Pedido do Cliente","mascara_modelo":"Cliente 0 , contato via 0 em 0 - 0, informou indisponibilidade para o atendimento."},
    {"causa":"Agendamento cancelado.","motivo":"No-show Cliente – Ponto Fixo/Móvel","mascara_modelo":"Cliente não compareceu para atendimento até às 0."},
    {"causa":"Agendamento cancelado.","motivo":"Erro de Agendamento – Cliente desconhecia","mascara_modelo":"Em contato com o cliente o mesmo informou que desconhecia o agendamento. Nome: 0 / Data contato: 0 - 0"},
    {"causa":"Agendamento cancelado.","motivo":"Erro de Agendamento – Endereço incorreto","mascara_modelo":"Erro identificado no agendamento: 0 . Situação:0. Cliente 0 - informado em 0"},
    {"causa":"Agendamento cancelado.","motivo":"Erro de Agendamento – Falta de informações na O.S.","mascara_modelo":"OS agendada apresentou erro de 0 identificado via 0. Contato com cliente 0 -  em 0."},
    {"causa":"Agendamento cancelado.","motivo":"Erro de Agendamento – O.S. agendada incorretamente (tipo/motivo/produto)","mascara_modelo":"OS apresentou erro de 0 identificado via 0. Contato com cliente 0 -  em 0 - 0"},
    {"causa":"Agendamento cancelado.","motivo":"Falta de Equipamento (Material/Principal/Reservado)","mascara_modelo":"OS apresentou erro de 0 identificado via 0. Contato com cliente 0 -  em 0 - 0"},
    {"causa":"Agendamento cancelado.","motivo":"Instabilidade de Equipamento/Sistema","mascara_modelo":"Atendimento em 0 0 não concluído devido à instabilidade de 0. Registrado teste/reinstalação. ASM 0"},
    {"causa":"Agendamento cancelado.","motivo":"Ocorrência com Técnico – Não foi possível realizar atendimento","mascara_modelo":"Técnico 0 , em 0 - 0, não realizou o atendimento por motivo de 0"},
    {"causa":"Agendamento cancelado.","motivo":"Ocorrência com Técnico – Sem tempo hábil","mascara_modelo":"Motivo: 0 . Cliente 0 - informado do reagendamento."},
    {"causa":"Agendamento cancelado.","motivo":"Perda/Extravio (Não devolução) – Mau uso","mascara_modelo":"OS em 0 - 0 classificada como Perda/Extravio, equipamento - 0 não devolvido. Cliente recusou assinar termo."},
    {"causa":"Agendamento cancelado.","motivo":"Cronograma de Instalação/Substituição de Placa","mascara_modelo":"Realizado atendimento com substituição de placa. Alteração feita pela OS 0."},
    {"causa":"Agendamento cancelado.","motivo":"No-show Técnico","mascara_modelo":"Técnico 0 , em 0 - 0, não realizou o atendimento por motivo de 0"},
    {"causa":"Agendamento cancelado.","motivo":"Cancelamento a pedido da RT","mascara_modelo":"Acordado novo agendamento com o cliente  0 no dia  00, via  - 0, pelo motivo - 0"},
]

# ==============================
# Utilitários (normalização + regex tolerante)
# ==============================
def rm_acc(s: str) -> str:
    return ''.join(c for c in unicodedata.normalize('NFD', s) if unicodedata.category(c) != 'Mn')

def canon(s: str) -> str:
    """Normaliza texto para comparação: sem acentos, minúsculas, normaliza traços e espaços."""
    if pd.isna(s):
        return ""
    s = str(s)
    s = s.replace("–", "-").replace("—", "-")
    s = rm_acc(s).lower()
    s = re.sub(r"[.;:\s]+$", "", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s

def _flexify_fixed_literal(escaped: str) -> str:
    """
    Torna o trecho fixo do modelo mais tolerante:
    - espaço -> \s+
    - vírgula -> [\s,]*
    - hífen -> aceita - – —
    - ponto -> [\.\s]*
    """
    escaped = escaped.replace(r"\ ", r"\s+")
    escaped = escaped.replace(r"\,", r"[\s,]*")
    escaped = escaped.replace(r"\-", r"[\-\–\—]\s*")
    escaped = escaped.replace(r"\.", r"[\.\s]*")
    return escaped

def template_to_regex_flex(template: str) -> re.Pattern:
    """Transforma o modelo em regex tolerante."""
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

# Pré-compila regras: {(causa_canon, motivo_canon): (motivo_original, regex, mascara_modelo)}
RULES_MAP = {}
for r in REGRAS_EMBUTIDAS:
    key = (canon(r["causa"]), canon(r["motivo"]))
    RULES_MAP[key] = (r["motivo"], template_to_regex_flex(r["mascara_modelo"]), r["mascara_modelo"])

def detect_motivo_and_mask(full_text: str):
    """Detecta o motivo dentro do texto completo comparando com as regras conhecidas."""
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

# ==============================
# Entrada: coluna única + coluna especial (opcional)
# ==============================
file = st.file_uploader("Exportação (xlsx/csv) — escolha 1 coluna com 'Causa. Motivo. Mascara...'", type=["xlsx","csv"])

if file:
    df = read_any(file)
    col_main = st.selectbox("Selecione a coluna única (Causa. Motivo. Mascara...)", df.columns)
    col_especial = st.selectbox("Coluna especial (opcional) — se for 'Automático - PORTAL' classifica como No-show Cliente", ["(Nenhuma)"] + list(df.columns))

    resultados, detalhes = [], []
    causas, motivos, mascaras = [], [], []
    combos = []                 # "Causa. Motivo. Máscara" (extra)
    mascaras_modelo = []        # Máscara prestador (modelo esperado)

    for _, row in df.iterrows():
        # Detecta sempre causa/motivo/máscara a partir da coluna principal
        causa, motivo, mascara = detect_motivo_and_mask(row.get(col_main, ""))
        causas.append(causa)
        motivos.append(motivo)
        mascaras.append(mascara)
        partes = [p for p in [str(causa).strip(), str(motivo).strip(), str(mascara).strip()] if p]
        combos.append(" ".join(partes))

        # por padrão, modelo vazio; será preenchido se reconhecermos o motivo
        mascara_modelo_val = ""

        # Regra especial: Automático - PORTAL
        if col_especial != "(Nenhuma)":
            valor_especial = row.get(col_especial, "")
            if canon(valor_especial) == canon("Automático - PORTAL"):
                resultados.append("No-show Cliente")
                detalhes.append("Regra especial aplicada: coluna especial = 'Automático - PORTAL'.")
                mascaras_modelo.append(mascara_modelo_val)  # fica vazio, pois não validamos pelo modelo
                continue  # não precisa validar regex

        # Fluxo normal: valida máscara pelo motivo detectado
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
    # 🔹 colunas separadas
    out["Causa detectada"] = causas
    out["Motivo detectado"] = motivos
    out["Máscara prestador (preenchida)"] = mascaras
    out["Máscara prestador"] = mascaras_modelo
    # 🔹 coluna combinada (pedido)
    out["Causa. Motivo. Máscara (extra)"] = combos
    # 🔹 colunas de status
    out["Classificação No-show"] = resultados
    out["Detalhe"] = detalhes
    # 🔹 nova coluna: Resultado No Show (mapeia 'Máscara correta' -> 'No-show Cliente')
    out["Resultado No Show"] = [
    "No-show Cliente" if r == "Máscara correta" else "No-show Técnico"
    for r in resultados
    ]

    st.success("Validação concluída.")
    st.dataframe(out, use_container_width=True)

    # Download
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as w:
        out.to_excel(w, index=False, sheet_name="Resultado")
    st.download_button("Baixar Excel com 'Classificação No-show'", data=buf.getvalue(),
                       file_name="resultado_no_show.xlsx",
                       mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
else:
    st.info("Envie a exportação; selecione a coluna única e (opcionalmente) a coluna especial.")

# =====================================================================
# MODO 2: Conferência (Dupla checagem) — múltiplas comparações
# =====================================================================

st.markdown("---")
st.header("Conferência (Dupla checagem) — múltiplas comparações")

st.markdown("""
Envie o **relatório conferido pelo atendente** (xlsx/csv).  
Mapeie **duplas de comparação** (coluna do **Robô** × coluna do **Atendente**).

**Status Geral da linha**
- **OK**: todas as duplas mapeadas estão OK
- **Pendência (vazio)**: alguma dupla tem valor do atendente vazio
- **Divergência**: pelo menos uma dupla diverge
""")

conf_file = st.file_uploader("Relatório conferido (xlsx/csv)", type=["xlsx", "csv"], key="conf-multi")

def read_any_loose(f):
    """Leitura resiliente: tenta detectar cabeçalho 'sujo' e pula 1 linha se necessário."""
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
        # heurística: se primeiro cabeçalho veio 'Unnamed', tenta pular 1 linha
        if str(df.columns[0]).lower().startswith("unnamed"):
            f.seek(0)
            df = pd.read_excel(f, engine="openpyxl", skiprows=1)
        return df
    except Exception:
        f.seek(0); return pd.read_excel(f)

# normalizador: mapeia rótulos comuns; devolve canônico para outros campos
def normalize_outcome(x: str) -> str:
    c = canon(x)  # usa a função canon já definida no app
    if "cliente" in c:
        return "no-show cliente"
    if "tecnico" in c or "técnico" in c:
        return "no-show tecnico"
    if "mascara correta" in c or "máscara correta" in c:
        # regra de negócio: máscara correta conta como cliente
        return "no-show cliente"
    return c

# controla qtde de duplas (pares) na sessão
if "pairs_n" not in st.session_state:
    st.session_state.pairs_n = 3   # 3 duplas por padrão

if conf_file:
    dfr = read_any_loose(conf_file)
    cols = list(dfr.columns)

    st.subheader("Duplas de comparação (Robô × Atendente)")
    cbtn1, cbtn2, _ = st.columns([1,1,6])
    if cbtn1.button("➕ Adicionar dupla"):
        st.session_state.pairs_n += 1
    if st.session_state.pairs_n > 1 and cbtn2.button("➖ Remover última"):
        st.session_state.pairs_n -= 1

    # mapeamento de duplas
    pair_defs = []
    for i in range(st.session_state.pairs_n):
        st.markdown("---" if i == 0 else "")
        c1, c2 = st.columns(2)
        robo_col = c1.selectbox(f"Robô — coluna #{i+1}", cols, key=f"robot_col_{i}")
        att_col  = c2.selectbox(f"Atendente — coluna #{i+1}", cols, key=f"att_col_{i}")
        pair_defs.append((robo_col, att_col))

    # rótulos amigáveis por dupla (Robô × Atendente)
    pair_labels = [f"{rc} × {ac}" for rc, ac in pair_defs]

    # util: nome seguro para aba Excel (<=31 chars; sem caracteres inválidos)
    def safe_sheet_name(name: str) -> str:
        bad = r'[]:*?/\\'
        for ch in bad:
            name = name.replace(ch, "_")
        name = name.strip()
        return name[:31] if len(name) > 31 else name

    # computa comparações por linha/dupla
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

    # monta dataframe de auditoria
    dfo = dfr.copy()
    for i in range(st.session_state.pairs_n):
        dfo[f"{pair_labels[i]} — Robô (norm)"] = pair_robo_norm_cols[i]
        dfo[f"{pair_labels[i]} — Atendente (norm)"] = pair_att_norm_cols[i]
        dfo[f"{pair_labels[i]} — Status"] = pair_status_cols[i]
    dfo["Conferência — Status geral"] = linhas_status_geral

    # métricas gerais (com base no status geral)
    total = len(dfo)
    ok   = int((dfo["Conferência — Status geral"] == "OK").sum())
    pend = int((dfo["Conferência — Status geral"] == "Pendência (vazio)").sum())
    div  = int((dfo["Conferência — Status geral"] == "Divergência").sum())
    acc  = (ok / total * 100.0) if total else 0.0

    st.subheader("Resumo")
    st.write(f"**Total:** {total}  |  **OK:** {ok}  |  **Divergência:** {div}  |  **Pendência:** {pend}  |  **Acurácia:** {acc:.1f}%")

    # --- KPIs (com explicação) ---
    desvio_rt    = (div / total * 100.0) if total else 0.0            # Robô divergiu do atendente
    desvio_att   = (pend / total * 100.0) if total else 0.0           # Pendências do atendente
    perc_rpa     = (ok / total * 100.0) if total else 0.0             # Casos resolvidos pelo robô (OK)
    perc_humano  = ((div + pend) / total * 100.0) if total else 0.0   # Precisou intervenção humana

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

    # --- Indicadores POR DUPLA ---
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

    # --- Matrizes por dupla ---
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

    # --- Exporta Excel multi-aba ---
    st.subheader("Prévia da planilha de auditoria")
    st.dataframe(dfo, use_container_width=True)

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

    outbuf = io.BytesIO()
    with pd.ExcelWriter(outbuf, engine="openpyxl") as w:
        dfo.to_excel(w, index=False, sheet_name="Conferencia")
        indicadores.to_excel(w, index=False, sheet_name="Indicadores")
        df_ind_duplas.to_excel(w, index=False, sheet_name="Indicadores_por_dupla")
        # uma aba de matriz por dupla com nome seguro
        for i, cm in matrizes.items():
            sheet = safe_sheet_name(f"Matriz_{pair_labels[i]}")
            cm.to_excel(w, sheet_name=sheet)

    st.download_button(
        "Baixar Excel da conferência (multi-duplas)",
        data=outbuf.getvalue(),
        file_name="conferencia_no_show.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
else:
    st.info("Para rodar a conferência, envie o relatório e mapeie as duplas (Robô × Atendente).")
