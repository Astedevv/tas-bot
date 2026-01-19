FROM python:3.11-slim

WORKDIR /app

# Instala dependências do sistema
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copia arquivos de requisitos
COPY bot/requirements.txt .

# Instala dependências Python
RUN pip install --no-cache-dir -r requirements.txt

# Copia o código
COPY bot/ .

# Cria diretório de dados
RUN mkdir -p data/qr_codes

# Executa o bot
CMD ["python", "main.py"]
