# Validador de No-show (PT-BR)

Aplicação **Streamlit** para validar **Máscaras de No-show** em ordens de serviço.

- Lê apenas a **Exportação do sistema** (Excel/CSV com muitas colunas).
- Você escolhe qual coluna contém `Causa. Motivo. Mascara...`.
- Compara com as **regras embutidas** (15 regras já cadastradas).
- Permite incluir **regras extras** na barra lateral durante a execução.
- Mantém todas as colunas originais e adiciona apenas uma nova: **Classificação No-show**.

## 🚀 Rodar localmente

```bash
pip install -r requirements.txt
streamlit run app_validacao_no_show_ptbr.py
```

## ☁️ Deploy no Streamlit Cloud

1. Suba este repositório no GitHub.
2. Vá até [Streamlit Cloud](https://share.streamlit.io).
3. Conecte sua conta GitHub e selecione este repositório.
4. Configure:
   - **Branch:** `main`
   - **Main file path:** `app_validacao_no_show_ptbr.py`
5. Clique em **Deploy** 🚀

Pronto! Sua aplicação ficará disponível em uma URL pública para compartilhar com a equipe.

---
