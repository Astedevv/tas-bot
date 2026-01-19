FROM python:3.11-slim

# Diretório de trabalho na raiz do app
WORKDIR /app

# Instala dependências de sistema necessárias
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copia requirements do bot e instala dependências
COPY bot/requirements.txt bot/requirements.txt
RUN pip install --no-cache-dir -r bot/requirements.txt

# Copia todo o repositório para /app (inclui a pasta bot)
COPY . .

# Cria diretório de dados dentro de bot
RUN mkdir -p bot/data/qr_codes
# Copia entrypoint de debug e garante permissão de execução
COPY bot/entrypoint.sh /app/bot/entrypoint.sh
RUN chmod +x /app/bot/entrypoint.sh

# Executa o entrypoint via shell para evitar problemas com line endings/shebang
CMD ["sh", "/app/bot/entrypoint.sh"]
