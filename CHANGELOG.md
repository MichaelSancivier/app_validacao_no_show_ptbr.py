

---

### `CHANGELOG.md`

```markdown
# CHANGELOG

Todas as mudanças relevantes deste projeto.

## [1.2.0] - 2025-09-09
### Adicionado
- Distribuição por **login** (coluna “Login atendente”) com fallback por nome.
- Ação de **Reatribuição em massa** (Admin) no Módulo 2.
- Área **Admin — Usuários**: criar usuário, trocar senha, ativar/desativar.
- Exportação de **Consolidação geral** (Admin).

### Alterado
- **“⏳ Pendente”** como status padrão da conferência.
- Restrição por papel: **Atendente** não vê o Módulo 1; **Admin** controla tudo.

### Corrigido
- Conflitos de widgets (`StreamlitDuplicateElementId`) usando chaves (`key=`) únicas.
- Casos de validação de máscara com pontuação/acentos variáveis (regex tolerante).

### Removido
- — (n/a)

---

## [1.1.0] - 2025-09-08
### Adicionado
- Versão base com Módulo 1 (pré-análise) e Módulo 2 (conferência).
- Leitura `.xlsx`/`.csv`, regras embutidas e validação de máscara.
- Exportações em Excel por módulo.


## [v1.0.0] - 2025-08-28
### Inicial
- Versão inicial do app com classificação de no-show para 17 regras mapeadas, permitindo padronisar a classificação.
