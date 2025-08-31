# Validador de No-show (PT-BR)

Aplicação **Streamlit** para validar **Máscaras de No-show** em ordens de serviço e permitir
a **conferência manual dos atendentes** contra o sistema.

## ✨ Funcionalidades

### 1. Pré-Análise (Robô)
- Lê exportação do sistema (Excel/CSV).
- Valida a coluna de **Causa. Motivo. Máscara** contra as **15 regras embutidas**.
- Considera também a regra especial: se a coluna de origem contiver `"Automático - PORTAL"`, 
  classifica direto como **No-show Cliente**.
- Gera novas colunas:
  - **Máscara prestador (preenchida)** → texto exato usado pelo prestador.
  - **Máscara prestador** → apenas a parte da máscara, sem dados variáveis.
  - **Causa. Motivo. Máscara** → campo extra com o padrão reconhecido.
  - **Classificação No-show** → “Máscara correta”, “No-show Cliente” ou “No-show Técnico”.
  - **Detalhe** → explicação em caso de erro ou regra especial aplicada.
  - **Resultado No Show** → padronizado em **No-show Cliente** ou **No-show Técnico**.

### 2. Conferência (Dupla checagem)
- Atendentes sobem um relatório conferido.
- É possível mapear **várias duplas de comparação** (Robô × Atendente).  
  - Ex.: Resultado No Show × Resultado validado, Motivo × Motivo validado etc.
- Status geral da linha:
  - **OK** → todas as duplas estão OK  
  - **Pendência (vazio)** → alguma dupla sem preenchimento do atendente  
  - **Divergência** → pelo menos uma dupla diverge
- Indicadores (KPIs):
  - **% Desvios RT** → divergências Robô × Atendente  
  - **% Desvios atendente** → campos vazios do atendente  
  - **% RPA** → casos totalmente automáticos (OK)  
  - **% Atendimento Humano** → casos que precisaram intervenção
- Explicação textual para cada KPI.
- **Indicadores por dupla** → mostra % OK, % Divergência e % Pendência de cada par.
- **Matrizes de concordância** (uma por dupla).
- Exportação para Excel com múltiplas abas:
  - `Conferencia` → dados originais + colunas de comparação
  - `Indicadores` → KPIs gerais
  - `Indicadores_por_dupla` → estatísticas detalhadas
  - `Matriz_<Dupla>` → matriz de concordância de cada par

## 🛠 Rodar localmente

```bash
pip install -r requirements.txt
streamlit run app_validacao_no_show_ptbr.py



