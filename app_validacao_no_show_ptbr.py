
import io
import re
import unicodedata
import pandas as pd
import streamlit as st

st.set_page_config(page_title="Validador de No-show — Uma Coluna (PT-BR)", layout="wide")
st.title("Validador de No-show — Uma Coluna (PT-BR)")

st.markdown("""
Selecione **apenas uma coluna** que contenha o texto completo no formato:

**`Causa. Motivo. Mascara (preenchida pelo prestador)...`**

O app identifica o **Motivo** baseado nas **regras embutidas** e valida a **Máscara** usando o modelo
(dos `0` como *placeholders*). Os dados preenchidos pelo prestador **não interferem** na validação,
pois os `0` aceitam qualquer conteúdo.
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
# Utilitários
# ==============================
def rm_acc(s: str) -> str:
    return ''.join(c for c in unicodedata.normalize('NFD', s) if unicodedata.category(c) != 'Mn')

def canon(s: str) -> str:
    """Normaliza texto para comparação robusta: sem acentos, minúsculas, normaliza traços e espaços."""
    if pd.isna(s):
        return ""
    s = str(s)
    s = s.replace("–", "-").replace("—", "-")
    s = rm_acc(s).lower()
    s = re.sub(r"[.;:\\s]+$", "", s)
    s = re.sub(r"\\s+", " ", s).strip()
    return s

def template_to_regex(template: str):
    if pd.isna(template):
        template = ""
    t = re.sub(r"\\s+", " ", str(template)).strip()
    parts = re.split(r"0+", t)
    fixed = [re.escape(p) for p in parts]
    body = r"(.+?)".join(fixed)
    body = re.sub(r"\\ ", r"\\s+", body)
    pat = r"^\\s*" + body + r"\\s*$"
    try:
        return re.compile(pat, flags=re.IGNORECASE | re.DOTALL)
    except re.error:
        return re.compile(r"^\\s*" + re.escape(t) + r"\\s*$", flags=re.IGNORECASE)

# Pré-compila regras: mapa {(causa_norm, motivo_norm): (motivo_original, regex)}
RULES_MAP = {}
for r in REGRAS_EMBUTIDAS:
    key = (canon(r["causa"]), canon(r["motivo"]))
    RULES_MAP[key] = (r["motivo"], template_to_regex(r["mascara_modelo"]))

def detect_motivo_and_mask(full_text: str):
    """
    Detecta qual 'motivo' das regras aparece no texto completo e retorna (causa, motivo, mascara).
    - Causa padrão: 'Agendamento cancelado.'
    - Mascara = sufixo após o motivo detectado (sem interferência dos dados do prestador)
    """
    if not full_text:
        return "", "", ""
    txt = re.sub(r"\\s+", " ", str(full_text)).strip()
    txt_c = canon(txt)
    causa_padrao = "Agendamento cancelado."
    causa_padrao_c = canon(causa_padrao)

    # tenta achar o primeiro motivo conhecido contido no texto
    for (c_norm, m_norm), (motivo_original, _regex) in RULES_MAP.items():
        if c_norm != causa_padrao_c:
            continue
        if m_norm in txt_c:
            # encontra índice aproximado do término do motivo na versão "canon"
            idx = txt_c.find(m_norm) + len(m_norm)
            # extrai máscara aproximando pelo comprimento; robusto o bastante pq validaremos por regex
            mascara = txt[idx:]
            mascara = mascara.strip(" .")
            return causa_padrao, motivo_original, mascara
    # fallback: não achou motivo -> tudo vira mascara
    return "", "", txt

# ==============================
# Entrada: só uma coluna
# ==============================
file = st.file_uploader("Exportação (xlsx/csv) — escolha uma coluna com 'Causa. Motivo. Mascara...'", type=["xlsx","csv"])

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

if file:
    df = read_any(file)
    col = st.selectbox("Selecione a coluna única (Causa. Motivo. Mascara...)", df.columns)

    resultados = []
    for _, row in df.iterrows():
        causa, motivo, mascara = detect_motivo_and_mask(row.get(col, ""))
        regex = RULES_MAP.get((canon(causa), canon(motivo)), (None, None))[1]
        mascara_norm = re.sub(r"\\s+", " ", str(mascara)).strip()
        resultados.append("Máscara correta" if (regex and regex.fullmatch(mascara_norm)) else "No-show Técnico")

    out = df.copy()
    out["Classificação No-show"] = resultados

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
    st.info("Envie a exportação e selecione a coluna única para iniciar.")
