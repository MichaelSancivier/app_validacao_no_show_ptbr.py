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
    mascaras_modelo = []        # << NOVA: Máscara prestador (modelo esperado)

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
    out["Máscara prestador (preenchida)"] = mascaras   # renomeada
    out["Máscara prestador"] = mascaras_modelo         # NOVA: o modelo esperado (com 0)
    # 🔹 coluna combinada (pedido)
    out["Causa. Motivo. Máscara (extra)"] = combos
    # 🔹 colunas de status
    out["Classificação No-show"] = resultados
    out["Detalhe"] = detalhes

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
