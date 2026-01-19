#!/bin/bash
# Script para testar o bot com PostgreSQL no Docker

set -e

echo "🚀 Iniciando teste com PostgreSQL..."

# Verificar se Docker está rodando
if ! command -v docker &> /dev/null; then
    echo "❌ Docker não encontrado"
    exit 1
fi

# Iniciar PostgreSQL em background
echo "📦 Iniciando PostgreSQL..."
docker run --rm -d \
  --name test-postgres \
  -e POSTGRES_PASSWORD=postgres \
  -e POSTGRES_DB=tas_db \
  -p 5432:5432 \
  postgres:15-alpine

# Aguardar PostgreSQL ficar pronto
echo "⏳ Aguardando PostgreSQL iniciar..."
sleep 5

# Rodar o bot
echo "🤖 Iniciando bot..."
docker run --rm \
  --link test-postgres:postgres \
  -e BOT_TOKEN=test_token \
  -e GUILD_ID=123456789 \
  -e DATABASE_URL=postgresql://postgres:postgres@postgres:5432/tas_db \
  -e AUTO_PROVISION=false \
  -e PIX_KEY=test_key \
  --name test-bot \
  tas-bot:latest \
  python bot/main.py &

BOT_PID=$!

# Aguardar 10 segundos para ver a saída
sleep 10

# Parar o bot
kill $BOT_PID 2>/dev/null || true

# Parar PostgreSQL
echo "🛑 Parando containers de teste..."
docker stop test-postgres 2>/dev/null || true

echo "✅ Teste completo!"
