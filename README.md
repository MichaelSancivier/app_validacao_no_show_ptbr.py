# Validador de No-show (PT-BR) — Uma Coluna FLEX + Regra Especial

Aplicação **Streamlit** para validar **agendamentos cancelados** e classificar corretamente casos de **No-show** com base em **15 regras oficiais embutidas**.

---

## 🚀 Como funciona

1. O app lê uma planilha **Excel (.xlsx)** ou **CSV (.csv)** exportada do sistema.  
2. Você escolhe:
   - **Coluna principal**: contém o texto completo no formato  
     `Causa. Motivo. Máscara (preenchida pelo prestador)...`  
   - **Coluna especial (opcional)**: se o valor for exatamente **`Automático - PORTAL`**, a linha é classificada direto como **No-show Cliente**.  
3. O app valida se o texto bate com o modelo oficial de cada motivo.  
4. A regex é **tolerante**:
   - aceita vírgulas opcionais, espaços extras e pontuação,  
   - diferentes tipos de traço (`-`, `–`, `—`),  
   - os `0` no modelo aceitam qualquer conteúdo digitado pelo prestador.  

---

## 📊 Colunas adicionadas na exportação

- **Causa detectada** → extraída do texto (ex.: `Agendamento cancelado.`)  
- **Motivo detectado** → um dos 15 motivos oficiais  
- **Máscara prestador (preenchida)** → o que o prestador digitou  
- **Máscara prestador** → o **modelo oficial esperado** (com `0`)  
- **Causa. Motivo. Máscara (extra)** → concatenação das três partes detectadas  
- **Classificação No-show** → resultado da validação (`Máscara correta`, `No-show Cliente` pela regra especial ou `No-show Técnico`)  
- **Detalhe** → explica falhas (ex.: motivo não reconhecido, máscara não bateu)  
- **Resultado No Show** → regra de negócio final:  
  - se **Classificação = Máscara correta** → `No-show Cliente`  
  - caso contrário → `No-show Técnico`

---

## ▶️ Rodar localmente

1. Instale as dependências:
   ```bash
   pip install -r requirements.txt


