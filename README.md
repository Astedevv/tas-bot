# T.A.S Mania - Bot Discord

Sistema de gerenciamento de transportes para Albion Online com integração Discord completa.

## 🚀 Funcionalidades

### 💰 Sistema Financeiro
- Dashboard de saldo com visualização em tempo real
- Registro de entradas e saídas de fundos
- Histórico completo de transações
- Interface com botões interativos

### 📊 Dashboard de Relatórios
- Estatísticas de transportes concluídos
- Fila de transportes aguardando processamento
- Transportes aguardando pagamento
- Transportes pagos aguardando envio
- Progresso visual em percentual

### ⚙️ Configurações Dinâmicas
- Ajuste de preço por milhão em tempo real
- Cálculo automático com taxa de alta prioridade (+20%)
- Exemplos dinâmicos de valores
- Sem necessidade de editar código

### 🎫 Sistema de Tickets
- Criação automática de tickets de transporte
- Coleta de dados: origem, destino, valor, prioridade
- Geração de código QR para PIX
- Status em tempo real

### 🚚 Gerenciamento de Transporte
- Fila de espera inteligente
- Confirmação de entrega
- Integração com sistema de pagamento PIX
- Histórico completo de operações

## 📋 Requisitos

- Python 3.10+
- discord.py 2.0+
- SQLite3
- Variáveis de ambiente configuradas

## ⚙️ Configuração

### 1. Variáveis de Ambiente (.env)

```env
BOT_TOKEN=seu_token_aqui
GUILD_ID=seu_guild_id
ADMIN_ROLE_ID=seu_admin_role_id
STAFF_ROLE_ID=seu_staff_role_id
TRANSPORTER_ROLE_ID=seu_transporter_role_id
PIX_KEY=sua_chave_pix
```

### 2. Instalação de Dependências

```bash
cd bot
pip install -r requirements.txt
```

### 3. Inicialização do Bot

```bash
python main.py
```

## 📁 Estrutura do Projeto

```
bot/
├── main.py                 # Arquivo principal
├── config.py              # Configurações centralizadas
├── database.py            # Gerenciamento de banco de dados
├── requirements.txt       # Dependências Python
├── cogs/                  # Módulos do bot
│   ├── financeiro.py      # Sistema financeiro
│   ├── dashboards.py      # Relatórios e configurações
│   ├── tickets.py         # Sistema de tickets
│   ├── transport.py       # Transporte base
│   ├── transport_flow.py  # Fluxo de transporte
│   ├── payment_verification.py  # Verificação de pagamento
│   ├── staff.py           # Comandos de staff
│   ├── history.py         # Histórico
│   └── queue_cog.py       # Fila de espera
├── utils/                 # Utilitários
│   ├── buttons.py         # Componentes de botões
│   ├── embeds.py          # Templates de embeds
│   └── validators.py      # Validações
└── data/                  # Arquivos de dados
    └── qr_codes/          # QR codes gerados
```

## 🔧 Configurações Principais (config.py)

- **PRECO_POR_MILHAO**: Preço base por 1 milhão de prata (padrão: 0.60)
- **VALOR_MINIMO**: Valor mínimo de transporte (padrão: 10M)
- **TAXA_ALTA_PRIORIDADE**: Taxa para alta prioridade (padrão: 20%)
- **PIX_KEY**: Chave PIX para recebimento

## 🔌 Comandos Disponíveis

### Financeiro
- `/banco` - Exibe dashboard financeiro
- `/depositar [valor] [motivo]` - Registra depósito
- `/retirada [valor]` - Inicia retirada (abre modal)
- `/historico_financeiro [limite]` - Mostra histórico
- `/enviar_banco` - Envia dashboard ao canal

### Relatórios
- `/enviar_relatorios` - Envia dashboard de relatórios

### Configurações
- `/enviar_config` - Envia dashboard de configurações

## 📊 Canais Esperados

O bot procura automaticamente por canais com os seguintes nomes:
- `💰-financeiro` - Painel de finanças
- `📊-relatorios` - Painel de relatórios
- `🔧-config` - Painel de configurações

## 🔒 Segurança em Produção

1. **Variáveis de Ambiente**: Nunca commit `.env` ao repositório
2. **Banco de Dados**: Fazer backup regular de `data/tas_mania.db`
3. **Logs**: Monitorar saída do bot para erros
4. **Token do Bot**: Manter privado em ambiente seguro

## 📈 Monitoramento

O bot exibe logs detalhados de:
- Carregamento de cogs
- Sincronização de comandos
- Operações de dashboard
- Erros e exceções

---

**Versão**: 1.0.0  
**Status**: Pronto para produção ✅
