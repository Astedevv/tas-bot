"""
Validadores e utilitários gerais
"""
from PIL import Image
import io
import discord

async def validar_imagem(attachment: discord.Attachment, max_size_mb=10) -> bool:
    """Valida se um attachment é uma imagem válida"""
    if not attachment:
        return False
    
    # Verifica tipo
    if not attachment.content_type or not attachment.content_type.startswith('image/'):
        return False
    
    # Verifica tamanho (em MB)
    if attachment.size > max_size_mb * 1024 * 1024:
        return False
    
    try:
        # Tenta abrir como imagem
        data = await attachment.read()
        img = Image.open(io.BytesIO(data))
        img.verify()
        return True
    except Exception:
        return False

def validar_valor_prata(valor_text: str, minimo: int = 10_000_000) -> tuple[bool, int]:
    """
    Valida um valor em prata
    Retorna: (é_válido, valor_convertido)
    """
    try:
        # Remove pontuação comum
        valor_limpo = valor_text.strip().replace(".", "").replace(",", "")
        valor = int(valor_limpo)
        
        if valor < minimo:
            return False, valor
        
        return True, valor
    except ValueError:
        return False, 0

def formatar_valor_prata(valor: int) -> str:
    """Formata um valor em prata com separadores"""
    return f"{valor:,}".replace(",", ".")

def calcular_taxa(valor_prata: int, prioridade: str, preco_base: float, taxa_alta: float) -> float:
    """Calcula a taxa baseado em valor e prioridade"""
    taxa = preco_base
    
    if prioridade == "ALTA":
        taxa *= (1 + taxa_alta)
    
    return taxa

def gerar_valor_aproximado(valor_prata: int) -> str:
    """Gera representação aproximada (ex: ~18M)"""
    milhoes = valor_prata / 1_000_000
    return f"~{milhoes:.1f}M"

async def enviar_dm(usuario: discord.User, embed: discord.Embed = None, content: str = None):
    """Envia uma mensagem direta para o usuário"""
    try:
        await usuario.send(embed=embed, content=content)
        return True
    except discord.Forbidden:
        return False
    except Exception:
        return False

def garantir_numero_ticket_unico(numero: int, db_check_func) -> int:
    """Garante um número de ticket único"""
    numero_base = numero
    counter = 0
    
    while db_check_func(numero) and counter < 1000:
        numero += 1
        counter += 1
    
    return numero if counter < 1000 else None
