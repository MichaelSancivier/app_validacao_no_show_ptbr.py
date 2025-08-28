
import io
import re
import unicodedata
import pandas as pd
import streamlit as st

st.set_page_config(page_title="Validador de No-show (Regras Embutidas) — FINAL", layout="wide")
st.title("Validador de No-show — Regras Embutidas (PT-BR) — FINAL")

st.markdown("""
Esta aplicação lê **apenas a Exportação do sistema** (com muitas colunas), utiliza **somente uma coluna**
que contém o texto no formato `Causa. Motivo. Mascara...`, e **adiciona** ao final a coluna
**"Classificação No-show"** com os valores **"Máscara correta"** ou **"No-show Técnico"**.

As **regras padrão** estão **embutidas no código** (abaixo).  
Você pode **incluir regras adicionais** a qualquer momento **sem arquivo externo** usando o painel
**"➕ Regras extras (opcional)"** (colar texto no formato indicado). Essas regras **não são salvas**
entre execuções; para torná-las permanentes, edite a lista `REGRAS_EMBUTIDAS` no código.
""")

# ==============================
# 🔒 REGRAS EMBUTIDAS (padrão)
# Cada item é {"causa": "...", "motivo": "...", "mascara_modelo": "..."}
# Use '0' onde o prestador deve preencher.
# ==============================
REGRAS_EMBUTIDAS = [
    {
        "causa": "Agendamento cancelado.",
        "motivo": "Atendimento Improdutivo – Ponto Fixo",
        "mascara_modelo": "Veículo compareceu para atendimento, porém por 0, não foi possível realizar o serviço."
    },
    {
        "causa": "Agendamento cancelado.",
        "motivo": "Cancelada a Pedido do Cliente",
        "mascara_modelo": "Cliente 0 , contato via 0 em 0 - 0, informou indisponibilidade para o atendimento."
    },
    {
        "causa": "Agendamento cancelado.",
        "motivo": "No-show Cliente – Ponto Fixo/Móvel",
        "mascara_modelo": "Cliente não compareceu para atendimento até às 0."
    },
    {
        "causa": "Agendamento cancelado.",
        "motivo": "Erro de Agendamento – Cliente desconhecia",
        "mascara_modelo": "Em contato com o cliente o mesmo informou que desconhecia o agendamento. Nome: 0 / Data contato: 0 - 0"
    },
    {
        "causa": "Agendamento cancelado.",
        "motivo": "Erro de Agendamento – Endereço incorreto",
        "mascara_modelo": "Erro identificado no agendamento: 0 . Situação:0. Cliente 0 - informado em 0"
    },
    {
        "causa": "Agendamento cancelado.",
        "motivo": "Erro de Agendamento – Falta de informações na O.S.",
        "mascara_modelo": "OS agendada apresentou erro de 0 identificado via 0. Contato com cliente 0 -  em 0."
    },
    {
        "causa": "Agendamento cancelado.",
        "motivo": "Erro de Agendamento – O.S. agendada incorretamente (tipo/motivo/produto)",
        "mascara_modelo": "OS apresentou erro de 0 identificado via 0. Contato com cliente 0 -  em 0 - 0"
    },
    {
        "causa": "Agendamento cancelado.",
        "motivo": "Falta de Equipamento (Material/Principal/Reservado)",
        "mascara_modelo": "OS apresentou erro de 0 identificado via 0. Contato com cliente 0 -  em 0 - 0"
    },
    {
        "causa": "Agendamento cancelado.",
        "motivo": "Instabilidade de Equipamento/Sistema",
        "mascara_modelo": "Atendimento em 0 0 não concluído devido à instabilidade de 0. Registrado teste/reinstalação. ASM 0"
    },
    {
        "causa": "Agendamento cancelado.",
        "motivo": "Ocorrência com Técnico – Não foi possível realizar atendimento",
        "mascara_modelo": "Técnico 0 , em 0 - 0, não realizou o atendimento por motivo de 0"
    },
    {
        "causa": "Agendamento cancelado.",
        "motivo": "Ocorrência com Técnico – Sem tempo hábil",
        "mascara_modelo": "Motivo: 0 . Cliente 0 - informado do reagendamento."
    },
    {
        "causa": "Agendamento cancelado.",
        "motivo": "Perda/Extravio (Não devolução) – Mau uso",
        "mascara_modelo": "OS em 0 - 0 classificada como Perda/Extravio, equipamento - 0 não devolvido. Cliente recusou assinar termo."
    },
    {
        "causa": "Agendamento cancelado.",
        "motivo": "Cronograma de Instalação/Substituição de Placa",
        "mascara_modelo": "Realizado atendimento com substituição de placa. Alteração feita pela OS 0."
    },
    {
        "causa": "Agendamento cancelado.",
        "motivo": "No-show Técnico",
        "mascara_modelo": "Técnico 0 , em 0 - 0, não realizou o atendimento por motivo de 0"
    },
    {
        "causa": "Agendamento cancelado.",
        "motivo": "Cancelamento a pedido da RT",
        "mascara_modelo": "Acordado novo agendamento com o cliente  0 no dia  00, via  - 0, pelo motivo - 0"
    },
]

# ==============================
# Utilitários
# ==============================
def remove_acentos(s: str) -> str:
    return ''.join(c for c in unicodedata.normalize('NFD', s) if unicodedata.category(c) != 'Mn')

def norm(s: str) -> str:
    """Normalização robusta para comparar Causa/Motivo (casefold + sem acentos + espaços colapsados)."""
    if pd.isna(s):
        return ""
    s = str(s)
    s = remove_acentos(s).lower()
    s = re.sub(r"[.;:\\s]+$", "", s)  # remove pontuação final
    s = re.sub(r"\\s+", " ", s).strip()
    return s

def dividir_texto_uma_coluna(value: str):
    """
    Divide 'Causa. Motivo. Mascara...' em (causa, motivo, mascara).
    Se não conseguir segmentar, devolve tudo em 'mascara'.
    """
    txt = re.sub(r"\\s+", " ", str(value)).strip()
    m = re.match(r"^(.*?\\.)\\s+(.*?\\.)\\s+(.*)$", txt)
    if m:
        return m.group(1).strip(), m.group(2).strip(), m.group(3).strip()
    partes = [p.strip() for p in txt.split(".")]
    if len(partes) >= 3:
        causa = partes[0] + "."
        motivo = partes[1] + "."
        mascara = ".".join(partes[2:]).strip()
        return causa, motivo, mascara
    return "", "", txt

def modelo_para_regex(template: str):
    """
    Converte a máscara modelo (com '0' como placeholder) em regex.
    - Cada sequência de '0' vira '(.+?)' (não guloso).
    - Partes fixas exigidas literalmente, com tolerância a variação de espaços.
    """
    if pd.isna(template):
        template = ""
    t = re.sub(r"\\s+", " ", str(template)).strip()
    partes = re.split(r"0+", t)
    fixos = [re.escape(p) for p in partes]
    corpo = r"(.+?)".join(fixos)
    corpo = re.sub(r"\\ ", r"\\s+", corpo)
    padrao = r"^\\s*" + corpo + r"\\s*$"
    try:
        return re.compile(padrao, flags=re.IGNORECASE | re.DOTALL)
    except re.error:
        return re.compile(r"^\\s*" + re.escape(t) + r"\\s*$", flags=re.IGNORECASE)

def construir_mapa_regras(regras):
    """Retorna {(causa_norm, motivo_norm): regex(mascara_modelo)}."""
    mapa = {}
    for item in regras:
        causa = norm(item.get("causa", ""))
        motivo = norm(item.get("motivo", ""))
        modelo = item.get("mascara_modelo", "")
        mapa[(causa, motivo)] = modelo_para_regex(modelo)
    return mapa

def parse_bloco_regras(texto: str):
    """
    Parser de regras extras coladas no formato:
    CAUSA: ...
    MOTIVO: ...
    MASCARA_MODELO: ...
    ---
    Retorna lista de itens no mesmo formato de REGRAS_EMBUTIDAS.
    """
    if not texto:
        return []
    itens = []
    # divide por linhas '---'
    blocos = re.split(r"^---\\s*$", texto, flags=re.MULTILINE)
    for b in blocos:
        b = b.strip()
        if not b:
            continue
        # captura campos
        causa = re.search(r"(?mi)^\\s*CAUSA\\s*:\\s*(.+)$", b)
        motivo = re.search(r"(?mi)^\\s*MOTIVO\\s*:\\s*(.+)$", b)
        mascara = re.search(r"(?mi)^\\s*MASCARA_MODELO\\s*:\\s*(.+)$", b)
        if causa and motivo and mascara:
            itens.append({
                "causa": causa.group(1).strip(),
                "motivo": motivo.group(1).strip(),
                "mascara_modelo": mascara.group(1).strip(),
            })
    return itens

# ==============================
# Sidebar: Regras extras (opcional)
# ==============================
with st.sidebar:
    st.header("➕ Regras extras (opcional)")
    st.caption("Cole novas regras no formato:\n\nCAUSA: ...\nMOTIVO: ...\nMASCARA_MODELO: ...\n---")
    texto_regras_extras = st.text_area("Cole aqui (uma ou mais, separadas por '---')", height=220, key="ta_regras")
    regras_extras = parse_bloco_regras(texto_regras_extras)
    if regras_extras:
        st.success(f"{len(regras_extras)} regra(s) extra(s) carregada(s) para esta sessão.")
    with st.expander("Ver regras padrões embutidas"):
        st.code(REGRAS_EMBUTIDAS, language="python")
    if regras_extras:
        with st.expander("Ver regras extras parseadas"):
            st.code(regras_extras, language="python")

# ==============================
# Entrada (somente exportação)
# ==============================
arq_exp = st.file_uploader("Exportação (xlsx/csv) — contém muitas colunas", type=["xlsx","csv"], key="exp")

def ler_arquivo(f):
    if f is None:
        return None
    nome = f.name.lower()
    if nome.endswith(".csv"):
        # Detectar separador automaticamente quando possível
        try:
            return pd.read_csv(f, sep=None, engine="python")
        except Exception:
            f.seek(0)
            return pd.read_csv(f)
    return pd.read_excel(f)

if arq_exp:
    df_exp = ler_arquivo(arq_exp)
    col_exp = st.selectbox("Escolha a coluna que contém 'Causa. Motivo. Mascara...':",
                           df_exp.columns, index=0, key="col_exp")

    # Constrói mapa de regras: embutidas + extras (se houver)
    regras_ativas = list(REGRAS_EMBUTIDAS)
    if regras_extras:
        regras_ativas.extend(regras_extras)
    mapa = construir_mapa_regras(regras_ativas)

    resultados = []
    for _, row in df_exp.iterrows():
        texto = row.get(col_exp, "")
        causa, motivo, mascara_preenchida = dividir_texto_uma_coluna(texto)
        chave = (norm(causa), norm(motivo))
        regex = mapa.get(chave)
        mascara_norm = re.sub(r"\\s+", " ", str(mascara_preenchida)).strip()
        if regex and regex.fullmatch(mascara_norm):
            resultados.append("Máscara correta")
        else:
            resultados.append("No-show Técnico")

    # Saída: mantém todas as colunas originais + 1 nova
    df_saida = df_exp.copy()
    df_saida["Classificação No-show"] = resultados

    st.success("Validação concluída!")
    st.dataframe(df_saida, use_container_width=True)

    # Download Excel
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        df_saida.to_excel(writer, index=False, sheet_name="Resultado")
    st.download_button("Baixar Excel com 'Classificação No-show'",
                       data=buffer.getvalue(),
                       file_name="resultado_no_show.xlsx",
                       mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                       key="dl_excel")
else:
    st.info("Envie a exportação para iniciar a validação.")
