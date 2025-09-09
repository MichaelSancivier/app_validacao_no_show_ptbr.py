# Validador de No-show — PT-BR

Aplicação **Streamlit** para validar **Máscaras de No-show** em ordens de serviço.

---

## Funcionalidades principais
- Lê arquivos de entrada em **Excel (.xlsx)** e **CSV (.csv)**.
- Você escolhe **qual coluna** contém `Causa. Motivo. Máscara...` (preenchida pelo prestador).
- Compara com as **23 regras embutidas**:
  - 21 regras oficiais de negócio.
  - +2 regras novas adicionadas:
    - **Alteração do tipo de serviço**
    - **Ocorrência Com Técnico - Técnico Sem Habilidade Para Realizar Serviço**
- Suporta **inclusão dinâmica de regras rápidas** (na tela do app) ou via **importação de JSON**.
- Aplica regra especial para **Automático - PORTAL** (classifica direto como *No-show Cliente*).
- Gera colunas adicionais no resultado:
  - **Máscara prestador (preenchida)**
  - **Máscara prestador**
  - **Causa. Motivo. Máscara**
  - **Classificação No-show**
  - **Detalhe**
  - **Resultado No Show**
  - **Atendente designado** (pode dividir registros entre atendentes).

---

## Exportação
- **Pré-análise**: escolha exportar todas as colunas ou apenas algumas.  
- **Conferência**: permite exportar múltiplas abas (`Conferencia`, `Indicadores`, `Indicadores_por_dupla`, `Matriz_<Dupla>`).

---

## Rodar localmente

```bash
pip install -r requirements.txt
streamlit run app_validacao_no_show_ptbr.py

