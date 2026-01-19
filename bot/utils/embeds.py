"""
Utilitários para criar embeds padronizados
"""
import discord
from datetime import datetime
from config import get_cor_status

def criar_embed_transporte(transporte, status_para_mostrar=None):
    """Cria um embed padrão para um transporte"""
    status = status_para_mostrar or transporte[2]  # transporte[2] é o status
    cor = get_cor_status(status)
    
    embed = discord.Embed(
        title=f"📦 TRANSPORTE #{transporte[1]:04d}",
        description=f"**Status:** {status}",
        color=cor,
        timestamp=datetime.now()
    )
    
    embed.add_field(
        name="🏘️ Origem",
        value=transporte[3],  # origem
        inline=False
    )
    
    embed.add_field(
        name="📍 Destino",
        value=transporte[4],  # destino
        inline=False
    )
    
    valor_em_milhoes = transporte[5] / 1_000_000 if transporte[5] else 0
    embed.add_field(
        name="💰 Valor Estimado",
        value=f"~{valor_em_milhoes:.1f}M prata",
        inline=True
    )
    
    prioridade_emoji = "⚡" if transporte[6] == "ALTA" else "🕒"
    embed.add_field(
        name="⚡ Prioridade",
        value=f"{prioridade_emoji} {transporte[6]}",
        inline=True
    )
    
    embed.add_field(
        name="💳 Taxa",
        value=f"R$ {transporte[7]:.2f}",
        inline=True
    )
    
    embed.set_footer(text="T.A.S Mania | Sistema de Transporte")
    
    return embed

def criar_embed_resumo_transporte(numero_ticket, origem, valor_estimado, prioridade, taxa_final, pix_key):
    """Cria embed com resumo de transporte criado"""
    valor_em_milhoes = valor_estimado / 1_000_000
    prioridade_emoji = "⚡" if prioridade == "ALTA" else "🕒"
    
    embed = discord.Embed(
        title=f"✅ TRANSPORTE CRIADO - #{numero_ticket:04d}",
        description="Resumo do seu transporte",
        color=0x2ECC71,
        timestamp=datetime.now()
    )
    
    embed.add_field(name="🏘️ Origem", value=origem, inline=False)
    embed.add_field(name="📍 Destino", value="Caerleon", inline=False)
    embed.add_field(name="💰 Valor Estimado", value=f"~{valor_em_milhoes:.1f}M prata", inline=True)
    embed.add_field(name="⚡ Prioridade", value=f"{prioridade_emoji} {prioridade}", inline=True)
    embed.add_field(name="💳 Taxa Final", value=f"R$ {taxa_final:.2f}", inline=True)
    
    embed.add_field(
        name="📲 Chave PIX",
        value=f"```\n{pix_key}\n```",
        inline=False
    )
    
    embed.add_field(
        name="⏳ Status",
        value="**AGUARDANDO PAGAMENTO**",
        inline=False
    )
    
    embed.set_footer(text="T.A.S Mania | Envie o comprovante para continuar")
    
    return embed

def criar_embed_fila(transporte):
    """Cria embed para fila de transportes"""
    numero = transporte[1]
    origem = transporte[3]
    valor_em_milhoes = transporte[5] / 1_000_000 if transporte[5] else 0
    prioridade = transporte[6]
    status = transporte[2]
    
    prioridade_emoji = "⚡" if prioridade == "ALTA" else "🕒"
    
    texto = f"**#{numero:04d}** | {prioridade_emoji} {prioridade}\n"
    texto += f"**Origem:** {origem}\n"
    texto += f"**Valor:** ~{valor_em_milhoes:.1f}M\n"
    
    if status == "DEPOSITADO":
        texto += "**Status:** ✅ Pronto para Transporte"
    elif status == "EM_TRANSPORTE":
        texto += "**Status:** 🚀 Em Transporte"
    else:
        texto += f"**Status:** {status}"
    
    embed = discord.Embed(
        description=texto,
        color=0x3498DB
    )
    
    return embed

def criar_embed_alerta_pagamento(numero_ticket, cliente_id, valor):
    """Cria embed de alerta de pagamento"""
    embed = discord.Embed(
        title="💳 NOVO PAGAMENTO AGUARDANDO",
        description=f"Ticket #{numero_ticket:04d}",
        color=0xF39C12
    )
    
    embed.add_field(name="Cliente", value=f"<@{cliente_id}>", inline=False)
    embed.add_field(name="Valor", value=f"R$ {valor:.2f}", inline=False)
    embed.add_field(name="Ação", value="Valide o comprovante no ticket", inline=False)
    
    embed.set_footer(text="T.A.S Mania | Validação Manual")
    
    return embed

def criar_embed_log_publico(numero_ticket, origem, destino, valor_aproximado, prioridade):
    """Cria embed para log público"""
    prioridade_emoji = "⚡" if prioridade == "ALTA" else "🕒"
    
    embed = discord.Embed(
        title=f"✔ TRANSPORTE #{numero_ticket:04d} CONCLUÍDO",
        description="Serviço finalizado com sucesso",
        color=0x27AE60
    )
    
    embed.add_field(name="🏘️ Origem", value=origem, inline=True)
    embed.add_field(name="📍 Destino", value=destino, inline=True)
    embed.add_field(name="💰 Valor", value=valor_aproximado, inline=True)
    embed.add_field(name="⚡ Prioridade", value=f"{prioridade_emoji} {prioridade}", inline=False)
    
    embed.set_footer(text="T.A.S Mania | Histórico Público")
    embed.timestamp = datetime.now()
    
    return embed
