# Validador de No-show — PT-BR (resumo)

App **Streamlit** para:
- **Módulo 1 (Pré-análise):** validar “Causa. Motivo. Máscara…”, aplicar regra especial **Automático - PORTAL**, e gerar colunas de resultado.
- **Módulo 2 (Conferência):** comparar **Robô × Atendente** em múltiplas duplas, ver KPIs com explicação, indicadores por dupla e matrizes.

---

## Formatos de entrada
- Aceita **Excel (.xlsx)** e **CSV (.csv)** em ambos os módulos.  
- O app detecta automaticamente o tipo e, no caso de CSV, tenta identificar o separador.  
- Se o arquivo tiver cabeçalhos “sujos” (ex.: linha “TABELA …”), o app pula automaticamente ou basta limpar antes de subir.

---

## Novidades de Exportação

### Módulo 1 — Pré-análise
- **Selecionar colunas**: marque **“Exportar todas as colunas”** ou escolha manualmente *quais* colunas vão para o Excel.
- A ordem padrão mantém **Atendente designado → Causa detectada** (antes das demais colunas geradas).
- O arquivo baixado é **resultado_no_show.xlsx** com a planilha **Resultado**.

### Módulo 2 — Conferência
- **Escolher abas (sheets)** para exportar:
  - `Conferencia` (dados + status por dupla + status geral)
  - `Indicadores` (KPIs gerais)
  - `Indicadores_por_dupla`
  - `Matriz_<Dupla>` (uma por dupla)
- **Selecionar colunas da aba Conferencia**: exportar todas ou escolher manualmente.
- O arquivo baixado é **conferencia_no_show.xlsx**.

---

## Como rodar localmente

```bash
pip install -r requirements.txt
streamlit run app_validacao_no_show_ptbr.py
