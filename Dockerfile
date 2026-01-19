FROM python:3.11-slim

# Coloca o diretório de trabalho diretamente em /app/bot
WORKDIR /app/bot

# Instala dependências do sistema necessárias para algumas wheels
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copia apenas o requirements do diretório bot e instala as dependências
COPY bot/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copia apenas o código da pasta bot para o WORKDIR (/app/bot)
COPY bot/ .

# Cria diretório de dados
RUN mkdir -p data/qr_codes

# Executa o bot a partir de /app/bot
CMD ["python", "main.py"]
