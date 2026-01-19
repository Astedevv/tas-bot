# 📝 Guia de Uso do Git e GitHub

## Configuração Inicial

```bash
# Configurar identidade
git config --global user.name "Seu Nome"
git config --global user.email "seu@email.com"

# Ou localmente para este projeto
git config user.name "Seu Nome"
git config user.email "seu@email.com"
```

## Inicializar Repositório

```bash
cd d:\SoluTi\TAS mania

# Se ainda não inicializou
git init

# Verificar status
git status
```

## Adicionar Arquivos

```bash
# Adicionar todos os arquivos
git add .

# Ou adicionar específico
git add bot/main.py
git add README.md
```

## Fazer Commit

```bash
# Commit simples
git commit -m "Descrição das mudanças"

# Commit com descrição detalhada
git commit -m "Título" -m "Descrição detalhada das mudanças"
```

## Conectar ao GitHub

```bash
# Criar repositório no GitHub (via site)
# Depois conectar:

git remote add origin https://github.com/seu-usuario/tas-mania-bot.git

# Verificar conexão
git remote -v
```

## Fazer Push

```bash
# First push
git push -u origin main

# Próximos pushes
git push
```

## Estrutura de Commits

Use mensagens claras e descritivas:

```
feat: Adicionar dashboard de finanças
fix: Corrigir erro de sincronização de comandos
docs: Atualizar README
refactor: Reorganizar código de validação
chore: Atualizar dependências
```

## Branches

```bash
# Ver branches
git branch

# Criar nova branch
git branch feature/nova-feature

# Mudar de branch
git checkout feature/nova-feature

# Ou criar e mudar ao mesmo tempo
git checkout -b feature/nova-feature

# Fazer merge
git checkout main
git merge feature/nova-feature

# Deletar branch
git branch -d feature/nova-feature
```

## .gitignore

O arquivo `.gitignore` já está configurado para ignorar:
- `.env` (variáveis de ambiente)
- `__pycache__/` (cache Python)
- `*.db` (banco de dados local)
- `.venv/` (ambientes virtuais)

**NÃO faça commit de:**
- `.env` - TOKEN DO BOT!
- `*.db` - dados sensíveis
- `__pycache__/` - arquivos compilados
- `.vscode/` - configurações locais

## Workflow Recomendado

```bash
# 1. Criar branch para feature
git checkout -b feature/minha-feature

# 2. Fazer mudanças
# ... editar arquivos ...

# 3. Verificar mudanças
git status
git diff

# 4. Adicionar mudanças
git add .

# 5. Commit
git commit -m "feat: Descrição clara da feature"

# 6. Push
git push origin feature/minha-feature

# 7. Criar Pull Request no GitHub
# (via interface GitHub.com)

# 8. Após aprovação, merge para main
git checkout main
git pull origin main
git merge feature/minha-feature
git push origin main
```

## Verificar Histórico

```bash
# Ver últimos commits
git log

# Ver commits de um arquivo
git log bot/main.py

# Ver mudanças de um commit específico
git show <commit-hash>
```

## Desfazer Mudanças

```bash
# Desfazer mudanças não commitadas
git checkout -- bot/main.py

# Desfazer último commit (mantém mudanças)
git reset --soft HEAD~1

# Desfazer último commit (remove mudanças)
git reset --hard HEAD~1

# Desfazer commit específico
git revert <commit-hash>
```

## Clonar Repositório

```bash
# Para outro computador
git clone https://github.com/seu-usuario/tas-mania-bot.git
cd tas-mania-bot

# Instalar dependências
cd bot
pip install -r requirements.txt

# Configurar .env
# Adicionar variáveis de ambiente

# Rodar bot
python main.py
```

## GitHub Actions (CI/CD Automático)

Criar arquivo `.github/workflows/deploy.yml`:

```yaml
name: Deploy to Railway

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Deploy to Railway
        uses: ./.github/actions/railway-deploy
        with:
          railway-token: ${{ secrets.RAILWAY_TOKEN }}
```

---

**Checklist antes de fazer push:**

- [ ] Código testado localmente
- [ ] Sem arquivos `.env` ou `.db`
- [ ] Commits com mensagens claras
- [ ] `git status` vazio (tudo commitado)
- [ ] `.gitignore` configurado corretamente
