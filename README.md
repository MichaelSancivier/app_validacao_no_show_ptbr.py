# Validador de No-show — PT-BR (v1.2.0)

Aplicação **Streamlit** para validar **Máscaras de No-show** em ordens de serviço, com:
- **Módulo 1 (Admin):** Pré-análise com regras embutidas + regra especial.
- **Módulo 2 (Admin/Atendente):** Conferência no app (sem dupla checagem), validação automática da máscara, salvamento no servidor e exportação.

> **Novidades v1.2.1**
> - **Distribuição por login** (coluna **Login atendente**) com fallback por nome.  
> - **Reatribuição em massa** (“🔁 Reatribuir O.S. para outro login”) para Admin.  
> - **Gestão de usuários** no app: criar usuário, trocar senha, ativar/desativar.  
> - Correções de UX: “Pendente” como padrão, filtros por papel, etc.

---

## Sumário
- [Estrutura do projeto](#estrutura-do-projeto)
- [Papéis e acesso](#papéis-e-acesso)
- [Fluxo de uso](#fluxo-de-uso)
- [Colunas esperadas (entrada)](#colunas-esperadas-entrada)
- [Regra especial (gatilhos)](#regra-especial-gatilhos)
- [Persistência & arquivos](#persistência--arquivos)
- [Reset de senha do admin](#reset-de-senha-do-admin)
- [Solução de problemas](#solução-de-problemas)
- [Como rodar localmente](#como-rodar-localmente)
- [Licença](#licença)

---

## Estrutura do projeto

├─ app_validacao_no_show_ptbr.py # App principal
├─ backend/
│ ├─ db.py # Engine SQLite + Session + init_db()
│ ├─ models.py # Tabelas (Users, Reviews, etc.)
│ ├─ repo_users.py # CRUD de usuários
│ └─ repo_reviews.py # Persistência das conferências
├─ utils/
│ └─ auth.py # Login + sessão estável (SID)
├─ data/
│ └─ .gitkeep # Pasta de runtime (não versionar .db)
├─ requirements.txt
├─ README.md
└─ CHANGELOG.md


> **Importante:** mantenha a pasta `data/` versionada **vazia** (apenas com `.gitkeep`).  
> Arquivos gerados em runtime (`.db`) **não** devem ser enviados ao Git.

Sugestão de `.gitignore`:

pycache/
.py[cod]
.venv/
venv/
data/.db
data/*.sqlite
!data/.gitkeep
.streamlit/secrets.toml


---

## Papéis e acesso

- **admin**
  - Acessa **Módulo 1 (Pré-análise)**.
  - Acessa **Módulo 2** e pode escolher qualquer atendente.
  - Pode **reatribuir** O.S. em massa (origem/destino) e **exportar** a consolidação geral.
  - Acessa a área **Admin — Usuários** (criar usuário, trocar senha, ativar/desativar).

- **atendente**
  - **Não** vê o Módulo 1.
  - No **Módulo 2**, vê **somente** suas O.S. (filtradas por **Login atendente**; se ausente, por **Atendente designado**).

---

## Fluxo de uso

1. **Admin → Módulo 1 (Pré-análise)**
   - Carregar `.xlsx` ou `.csv`.
   - Selecionar a coluna **“Causa. Motivo. Máscara …”**.
   - (Opcional) Selecionar a **coluna especial** (para a Regra Especial).
   - O app detecta **Motivo** e valida a **Máscara** (regex tolerante).
   - Definir a **distribuição por Login atendente** (recomendado).  
     Se ainda não houver logins cadastrados, usar **Atendente designado** (nomes).
   - (Opcional) exportar planilha de pré-análise.

2. **Admin/Atendente → Módulo 2 (Conferência)**
   - **Admin** escolhe o login/nome a conferir; **Atendente** entra direto no seu.
   - Para cada O.S.: informar **Máscara conferida**, visualizar **validação automática**, ajustar **Classificação**, marcar **Status** e preencher **Observações**.
   - **Salvar no servidor**: grava no banco (`reviews`) com o usuário e um `batch_id`.
   - **Admin** pode **reatribuir** O.S. (filtro por pendentes e limite de quantidade) e **exportar consolidação geral (XLSX)**.

---

## Colunas esperadas (entrada)

- **Obrigatória**
  - `Causa. Motivo. Máscara ...` — texto único com *Causa. Motivo. Máscara*.

- **Opcionais**
  - `O.S.` (se ausente, o app cria vazia).
  - **Coluna especial** — usada pela Regra Especial.
  - `Atendente designado` e/ou `Login atendente` — se vierem do seu sistema, o app usará diretamente.

---

## Regra especial (gatilhos)

Se a **coluna especial** contiver qualquer um dos termos abaixo (case/acentos indiferentes), a linha vira **No-show Cliente** automaticamente: Automático - PORTAL, Michelin, OUTRO.


A lista pode ser alterada no código (`ESPECIAIS_NO_SHOW_CLIENTE`).

---

## Persistência & arquivos

- **Banco SQLite**: arquivo definido em `backend/db.py` (`DB_FILE`), padrão **`data/no_show_vs.db`**.  
- **Conferências** ficam na tabela (ex.: `reviews`), exportáveis em **Admin → Consolidação geral**.

> **Não** versione o `.db`. Mantenha somente `data/.gitkeep` no Git.

---

## Reset de senha do admin

**Padrão:** use **Admin — Usuários → 🔑 Trocar senha**.

**Emergência (sem conseguir logar):**
1. Abra `app_validacao_no_show_ptbr.py`.
2. Logo após `init_db()` e `sticky_sid_bootstrap()`, adicione **temporariamente**:


```python
from backend.repo_users import set_password, create_user
# Força redefinição/garantia do admin
try:
    set_password("admin", "SenhaNova123!")
except Exception:
    create_user("admin", "Administrador", "SenhaNova123!", role="admin", active=1)


3. Faça o deploy/execução, copie a senha, logue como admin e REMOVA o bloco do código.


#Solução de problemas

“Usuário não encontrado” ao logar admin

Use o bloco de emergência acima ou troque a senha localmente na aba Admin.

“StreamlitDuplicateElementId” na área Admin

Garanta key= únicos nos widgets e crie os st.tabs() apenas dentro do bloco if role == "admin":.

Banco “locked” / erro de escrita

Tente novamente em alguns segundos; se persistir, pare e reinicie o app.

Atendente enxerga Módulo 1

Confira se o Módulo 1 está protegido por if role != "admin": st.info(...); out = None.

Atendente não vê O.S.

Confirme a coluna Login atendente ou o mapeamento de Atendente designado para login; verifique se o usuário está ativo.

# 1) Criar venv e instalar deps
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# 2) Rodar o app
streamlit run app_validacao_no_show_ptbr.py
A base SQLite será criada automaticamente em data/ na primeira execução.
