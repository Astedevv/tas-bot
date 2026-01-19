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

# Executa o bot a partir de /app com o caminho para bot/main.py
CMD ["python", "bot/main.py"]
