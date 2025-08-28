import io
import re
import unicodedata
import pandas as pd
import streamlit as st

st.set_page_config(page_title="Validador de No-show (PT-BR)", layout="wide")
st.title("Validador de No-show — PT-BR")

# ===== Funções auxiliares (mesmas do final) =====
def remove_acentos(s: str) -> str:
    import unicodedata
    return ''.join(c for c in unicodedata.normalize('NFD', s) if unicodedata.category(c) != 'Mn')

def norm(s: str) -> str:
    if pd.isna(s):
        return ""
    s = str(s)
    s = remove_acentos(s).lower()
    s = re.sub(r"[.;:\\s]+$", "", s)
    s = re.sub(r"\\s+", " ", s).strip()
    return s

def dividir_texto_uma_coluna(value: str):
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
    if pd.isna(template):
        template = ""
    t = re.sub(r"\\s+", " ", str(template)).strip()
    partes = re.split(r"0+", t)
    fixos = [re.escape(p) for p in partes]
    corpo = r"(.+?)".join(fixos)
    corpo = re.sub(r"\\ ", r"\\s+", corpo)
    padrao = r"^\\s*" + corpo + r"\\s*$"
    import re as _re
    try:
        return _re.compile(padrao, flags=_re.IGNORECASE | _re.DOTALL)
    except _re.error:
        return _re.compile(r"^\\s*" + _re.escape(t) + r"\\s*$", flags=_re.IGNORECASE)

def construir_mapa_regras(regras):
    mapa = {}
    for item in regras:
        causa = norm(item.get("causa", ""))
        motivo = norm(item.get("motivo", ""))
        modelo = item.get("mascara_modelo", "")
        mapa[(causa, motivo)] = modelo_para_regex(modelo)
    return mapa

# Regras: importamos do arquivo final já gerado
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

with st.sidebar:
    st.header("➕ Regras extras (opcional)")
    st.caption("Cole novas regras no formato:\\n\\nCAUSA: ...\\nMOTIVO: ...\\nMASCARA_MODELO: ...\\n---")
    texto = st.text_area("Cole aqui (uma ou mais, separadas por '---')", height=220)
    import re as _re
    def parse(texto):
        if not texto:
            return []
        blocos = _re.split(r"^---\\s*$", texto, flags=_re.MULTILINE)
        items = []
        for b in blocos:
            b = b.strip()
            if not b: 
                continue
            c = _re.search(r"(?mi)^\\s*CAUSA\\s*:\\s*(.+)$", b)
            m = _re.search(r"(?mi)^\\s*MOTIVO\\s*:\\s*(.+)$", b)
            mm = _re.search(r"(?mi)^\\s*MASCARA_MODELO\\s*:\\s*(.+)$", b)
            if c and m and mm:
                items.append({"causa": c.group(1).strip(), "motivo": m.group(1).strip(), "mascara_modelo": mm.group(1).strip()})
        return items
    regras_extras = parse(texto)

# Uploader apenas da exportação
arq_exp = st.file_uploader("Exportação (xlsx/csv) — contém muitas colunas", type=["xlsx","csv"])

def ler_arquivo(f):
    if f is None:
        return None
    nome = f.name.lower()
    if nome.endswith(".csv"):
        try:
            return pd.read_csv(f, sep=None, engine="python")
        except Exception:
            f.seek(0); return pd.read_csv(f)
    # Excel: tenta usar openpyxl e dá mensagem amigável se faltar
    try:
        return pd.read_excel(f, engine="openpyxl")
    except ImportError as e:
        st.error("Faltou a dependência **openpyxl** para ler arquivos Excel (.xlsx). "
                 "Confirme que o `requirements.txt` do repositório contém a linha `openpyxl` "
                 "e faça o *Rebuild* da aplicação. Como alternativa, exporte seu arquivo como **CSV** e reenvie.")
        raise
    except Exception:
        # tenta sem especificar engine
        f.seek(0)
        return pd.read_excel(f)

if arq_exp:
    df_exp = ler_arquivo(arq_exp)
    col_exp = st.selectbox("Escolha a coluna que contém 'Causa. Motivo. Mascara...':", df_exp.columns, index=0)

    regras_ativas = list(REGRAS_EMBUTIDAS)
    if regras_extras:
        regras_ativas.extend(regras_extras)
    mapa = construir_mapa_regras(regras_ativas)

    resultados = []
    for _, row in df_exp.iterrows():
        texto = row.get(col_exp, "")
        causa, motivo, mascara = dividir_texto_uma_coluna(texto)
        regex = mapa.get((norm(causa), norm(motivo)))
        mascara_norm = re.sub(r"\\s+", " ", str(mascara)).strip()
        resultados.append("Máscara correta" if (regex and regex.fullmatch(mascara_norm)) else "No-show Técnico")

    saida = df_exp.copy()
    saida["Classificação No-show"] = resultados
    st.dataframe(saida, use_container_width=True)

    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as w:
        saida.to_excel(w, index=False, sheet_name="Resultado")
    st.download_button("Baixar Excel com 'Classificação No-show'", data=buf.getvalue(),
                       file_name="resultado_no_show.xlsx",
                       mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
else:
    st.info("Envie a exportação para iniciar a validação.")
