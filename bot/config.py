"""
Configurações centralizadas do bot
"""
import os
from dotenv import load_dotenv

# Load .env from parent directory (project root)
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

# Discord
BOT_TOKEN = os.getenv("BOT_TOKEN")
GUILD_ID = int(os.getenv("GUILD_ID", 0))
ADMIN_ROLE_ID = os.getenv("ADMIN_ROLE_ID")
STAFF_ROLE_ID = os.getenv("STAFF_ROLE_ID")
TRANSPORTER_ROLE_ID = os.getenv("TRANSPORTER_ROLE_ID")

# Database
DATABASE_PATH = "./data/tas_mania.db"
# Prefer DATABASE_URL from environment (Postgres). If not present, fall back to sqlite URL.
DATABASE_URL = os.getenv("DATABASE_URL") or f"sqlite:///{DATABASE_PATH}"

# Preços (novo sistema)
PRECO_POR_MILHAO = 0.6  # R$ 0,60 por 1 milhão de prata
VALOR_MINIMO = 10_000_000  # 10M prata mínimo
TAXA_ALTA_PRIORIDADE = 0.20  # +20% para alta prioridade (0,60 → 0,72)
PRECO_ALTA_PRIORIDADE = PRECO_POR_MILHAO * (1 + TAXA_ALTA_PRIORIDADE)  # 0,72

# Mantém para compatibilidade
PRECO_BASE = VALOR_MINIMO * PRECO_POR_MILHAO  # R$ 6.00

# PIX
PIX_KEY = os.getenv("PIX_KEY", "fc22c002-961c-43fa-8177-c86ef47f33a0")
PIX_QRCODE_PATH = "./data/qr_codes/pix_qrcode.png"

# Origens disponíveis
ORIGENS = [
    "Bridgewatch",
    "Martlock",
    "Lymhurst",
    "Fort Sterling",
    "Thetford",
    "Brecilien"
]

# Destino padrão
DESTINO_PADRAO = "Caerleon"

# Timeouts e limites
TIMEOUT_PAGAMENTO = 1800  # 30 min em segundos
TIMEOUT_DEPOSITO = 3600  # 1 hora
AUTO_DELETE_TICKET = 604800  # 7 dias

# IDs dos canais (serão setados após rebuild)
CANAIS = {
    "anuncios": None,
    "regras": None,
    "abrir_transporte": None,
    "feedbacks": None,
    "status_transportes": None,
    "historico_publico": None,
    "painel_staff": None,
    "fila_transportes": None,
    "alertas": None,
    "configuracoes": None
}

# Status possíveis
STATUS = {
    "ABERTO": "ABERTO",
    "AGUARDANDO_PAGAMENTO": "AGUARDANDO_PAGAMENTO",
    "PAGO": "PAGO",
    "DEPOSITADO": "DEPOSITADO",
    "EM_TRANSPORTE": "EM_TRANSPORTE",
    "ENTREGUE": "ENTREGUE",
    "CONCLUIDO": "CONCLUIDO",
    "CANCELADO": "CANCELADO",
    "REJEITADO": "REJEITADO"
}

# Cores para embeds
CORES = {
    "ABERTO": 0x3498DB,  # Blue
    "AGUARDANDO_PAGAMENTO": 0xF39C12,  # Yellow
    "PAGO": 0x2ECC71,  # Green
    "DEPOSITADO": 0x2ECC71,  # Green
    "EM_TRANSPORTE": 0x9B59B6,  # Purple
    "ENTREGUE": 0x27AE60,  # Green
    "CONCLUIDO": 0x27AE60,  # Green
    "CANCELADO": 0xE74C3C,  # Red
    "REJEITADO": 0xC0392B  # Dark Red
}

def get_cor_status(status):
    """Retorna a cor para um determinado status"""
    return CORES.get(status, 0x95A5A6)  # Gray default
