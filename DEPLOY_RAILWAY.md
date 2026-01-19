# 🚀 Guia de Deploy no Railway

## Prerequisitos

- Conta no Railway (railway.app)
- GitHub com o código do bot
- Token do bot Discord
- Variáveis de ambiente configuradas

## Passo 1: Preparar o GitHub

```bash
# Inicializar repositório
git init
git add .
git commit -m "Bot T.A.S Mania - Pronto para produção"
git branch -M main
git remote add origin https://github.com/seu-usuario/tas-mania-bot.git
git push -u origin main
```

## Passo 2: Deploy no Railway

### Via Dashboard

1. Acesse [railway.app](https://railway.app)
2. Clique em "New Project"
3. Selecione "Deploy from GitHub"
4. Conecte sua conta GitHub
5. Selecione o repositório `tas-mania-bot`
6. Railway detectará automaticamente o `Dockerfile`

### Via CLI

```bash
# Instalar Railway CLI
npm i -g @railway/cli

# Fazer login
railway login

# Deploy
railway up
```

## Passo 3: Configurar Variáveis de Ambiente

No dashboard do Railway:

1. Vá para "Variables"
2. Adicione as variáveis necessárias:

```
BOT_TOKEN=seu_token_aqui
GUILD_ID=1462503692266766560
ADMIN_ROLE_ID=seu_admin_role_id
STAFF_ROLE_ID=seu_staff_role_id
TRANSPORTER_ROLE_ID=seu_transporter_role_id
PIX_KEY=sua_chave_pix
```

## Passo 4: Verificar Logs

```bash
# Via CLI
railway logs

# Via Dashboard
Vá em "Deployments" → "Logs"
```

## Passo 5: Persistência de Dados

O banco de dados SQLite é criado em `bot/data/tas_mania.db`

Para persistência entre restarts:

1. No Railway, crie um volume:
   - Vá para "Variables" → "Database"
   - Crie um PostgreSQL (opcional, mas recomendado)
   
2. Ou use o SQLite nativo (banco será recriado em cada deploy se não houver volume)

**Recomendação**: Use SQLite em produção com backup automático

## Monitoramento

### Logs do Bot

```bash
railway logs --tail
```

### Health Check

O bot exibe na inicialização:
```
✅ Bot conectado como: T.A.S Mania#2270
✅ 11 Cogs carregados
✅ 8+ comandos sincronizados
```

### Alertas

Configure no Railway:
- Alert on failed deployment
- Alert on high memory usage

## Troubleshooting

### Bot não inicia
```bash
# Verificar logs
railway logs

# Verificar variáveis
railway variables
```

### Erro de permissões do bot
- Verifique os escopos no Discord Developer Portal
- Scope necessários: `bot`, `applications.commands`

### Comando não aparece
- Aguarde 5-10 minutos para sincronização
- Faça refresh do Discord (Ctrl+R)

## Backup Automático

### Usando Railway Cron

Crie um job para fazer backup do banco de dados:

```bash
# railway.json adicional
{
  "backup": {
    "schedule": "0 0 * * *",
    "command": "python -c 'import shutil; shutil.copy(\"bot/data/tas_mania.db\", \"backups/tas_mania_$(date +%s).db\")'"
  }
}
```

### Ou use script externo

Script Python para backup:
```python
import shutil
import os
from datetime import datetime

def backup_database():
    source = "bot/data/tas_mania.db"
    backup_dir = "backups"
    
    if not os.path.exists(backup_dir):
        os.makedirs(backup_dir)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    destination = f"{backup_dir}/tas_mania_{timestamp}.db"
    
    shutil.copy(source, destination)
    print(f"✅ Backup criado: {destination}")

if __name__ == "__main__":
    backup_database()
```

## Atualizações

Para fazer update do código:

```bash
# Fazer mudanças localmente
git add .
git commit -m "Update: descrição das mudanças"
git push origin main

# Railway detectará e fará novo deploy automaticamente
```

## Performance em Produção

- Memory: ~100MB
- CPU: Minimal (< 1%)
- Uptime: 24/7
- Escalabilidade: Railway suporta auto-scaling

---

**Dúvidas?** Verifique os logs no Dashboard do Railway
