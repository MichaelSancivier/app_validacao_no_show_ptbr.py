# Validador de No-show (PT-BR) — Uma Coluna Flexível

Aplicação **Streamlit** para validar **Máscaras de No-show** em ordens de serviço.

- Lê apenas a **exportação do sistema** (Excel/CSV).
- Você escolhe **uma coluna** que contém `Causa. Motivo. Mascara (preenchida pelo prestador)...`.
- Compara com as **15 regras embutidas**.
- Considera os `0` das máscaras como **placeholders**, aceitando qualquer texto preenchido pelo prestador.
- Regex **tolerante**: aceita vírgula opcional, espaços extras, pontuação ou tipos de traço diferentes.
- Mantém todas as colunas originais e adiciona:
  - **Classificação No-show** → `Máscara correta` ou `No-show Técnico`
  - **Detalhe** → explicação em caso de `No-show Técnico`.

## 🚀 Rodar localmente

```bash
pip install -r requirements.txt
streamlit run app_validacao_no_show_ptbr.py

