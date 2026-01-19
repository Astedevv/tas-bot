# 🚀 GUIA DE EXECUÇÃO - T.A.S MANIA BOT

## 📋 Pré-requisitos

- Python 3.9+
- pip (gerenciador de pacotes Python)
- Token do bot Discord configurado
- IDs de Server e Roles

---

## 🔧 INSTALAÇÃO INICIAL

### 1️⃣ Instalar Dependências

```bash
cd "d:\SoluTi\TAS mania\bot"
pip install -r requirements.txt
```

**Esperado:** Todas as bibliotecas instaladas sem erros

---

### 2️⃣ Configurar .env

O arquivo `.env` já está na pasta raiz com as credenciais. Verifique se está completo:

```env
BOT_TOKEN=<seu_token_aqui>
GUILD_ID=<seu_guild_id>
ADMIN_ROLE_ID=<será auto-criado>
STAFF_ROLE_ID=<será auto-criado>
TRANSPORTER_ROLE_ID=<será auto-criado>
AUTO_PROVISION=true
PIX_KEY=<sua_chave_pix>
```

---

## 🚀 PRIMEIRA EXECUÇÃO

### 1️⃣ Inicie o Bot

```bash
cd "d:\SoluTi\TAS mania\bot"
python main.py
```

**Esperado:**
```
==================================================
✅ Bot conectado como: T.A.S Mania Bot#1234
   ID: 1462502345991520613
   Guild: 1462503692266766560
==================================================

✅ Cog carregado: rebuild
✅ Cog carregado: tickets
✅ Cog carregado: payments
✅ Cog carregado: transport
✅ Cog carregado: queue
✅ Cog carregado: history
✅ Cog carregado: staff
✅ 0 comandos sincronizados
```

---

### 2️⃣ Executar Rebuild do Servidor

No Discord, em qualquer canal, como **OWNER do bot**:

```
/rebuild
```

**Processo:**
1. ⚠️ Bot pedirá confirmação
2. Digite: `confirmo`
3. Bot vai:
   - 🗑️ Deletar todos os canais
   - 🗑️ Deletar todos os cargos
   - ✅ Criar canais públicos, staff, tickets
   - ✅ Criar cargos (Admin, Staff, Transporter, Cliente)
   - ✅ Configurar permissões
   - ✅ Enviar mensagens iniciais

**Tempo estimado:** 2-3 minutos

**Resultado esperado:**
```
✅ REBUILD CONCLUÍDO! 100%

✅ Servidor Configurado com Sucesso!
Canais Criados:
📢 PÚBLICO
🛠️ STAFF

Cargos Criados:
👑 Admin
💼 Staff
🚚 Transporter
📱 Cliente
```

---

## 🎮 USANDO O BOT

### Cliente Abrindo um Transporte

1. Vá para canal `#abrir-transporte`
2. Clique no botão: **"🚚 Abrir Transporte"**
3. Siga as instruções (botões visuais):
   - Escolha origem
   - Escolha prioridade
   - Insira valor
   - Envie print dos items
   - Adicione observações (opcional)
4. Bot gera resumo com valor e PIX
5. Cliente envia comprovante
6. Staff valida manualmente
7. Cliente confirma depósito na island
8. Transporte inicia
9. Entrega é feita
10. Cliente retira items

---

## 📊 ESTRUTURA DE ARQUIVOS CRIADOS

```
d:\SoluTi\TAS mania\
├── bot/
│   ├── main.py                 ✅ Entry point
│   ├── config.py               ✅ Configurações
│   ├── database.py             ✅ SQLite
│   ├── requirements.txt        ✅ Dependências
│   │
│   ├── cogs/
│   │   ├── __init__.py         ✅
│   │   ├── rebuild.py          ✅ Setup servidor
│   │   ├── tickets.py          ✅ Sistema tickets
│   │   ├── payments.py         ⏳ Em desenvolvimento
│   │   ├── transport.py        ⏳ Em desenvolvimento
│   │   ├── queue.py            ⏳ Em desenvolvimento
│   │   ├── history.py          ⏳ Em desenvolvimento
│   │   └── staff.py            ⏳ Em desenvolvimento
│   │
│   ├── utils/
│   │   ├── __init__.py         ✅
│   │   ├── embeds.py           ✅ Embeds
│   │   ├── buttons.py          ✅ Botões/Modais
│   │   └── validators.py       ✅ Validações
│   │
│   └── data/
│       └── tas_mania.db        ✅ SQLite (criado auto)
│
├── .env                        ✅ Credenciais
├── PLANO_EXECUCAO.md          ✅ Documentação completa
└── README.md                   ✅ Este arquivo
```

---

## ⚠️ TROUBLESHOOTING

### Bot não conecta
```
❌ Erro: 401 Unauthorized
```
**Solução:** Verifique se BOT_TOKEN está correto em `.env`

---

### Rebuild falha
```
❌ Erro: Invalid GUILD_ID
```
**Solução:** Copie o ID correto do servidor em `.env`

---

### Dependências não instalam
```
❌ Erro: No module named 'discord'
```
**Solução:**
```bash
pip install --upgrade pip
pip install -r requirements.txt --force-reinstall
```

---

## 📈 PRÓXIMAS FASES

### Fase 1 (AGORA):
- ✅ Estrutura base
- ✅ Sistema de tickets
- ⏳ Sistema de pagamentos (manual)
- ⏳ Fluxos de depósito/entrega

### Fase 2:
- [ ] OCR para análise de prints
- [ ] Dashboard web
- [ ] API REST

### Fase 3:
- [ ] Múltiplos transportadores
- [ ] PostgreSQL
- [ ] Sistema de rating

---

## 🆘 SUPORTE

Se algo não funcionar:

1. ✅ Verifique se o bot tem permissões de `Administrator`
2. ✅ Verifique se `.env` está com credenciais corretas
3. ✅ Veja os logs do terminal para mais detalhes
4. ✅ Tente deletar `tas_mania.db` e rodar novamente

---

## 📝 COMANDOS DISPONÍVEIS

### Agora:
```
/rebuild    → Configurar servidor (Admin only)
```

### Em breve:
```
/status [ticket]              → Ver status
/validar_pagamento [ticket]   → Staff validar
/iniciar_transporte [ticket]  → Iniciar transporte
/concluir_transporte [ticket] → Concluir entrega
```

---

**Versão:** 1.0  
**Data:** 18/01/2026  
**Status:** ✅ Pronto para testes

