"""
Sistema de Relatórios de Transportes - T.A.S Mania
Dashboard inteligente de estatísticas de transportes
"""
import discord
from discord.ext import commands
from discord import app_commands
import sqlite3
from datetime import datetime
import asyncio
from database import db
from config import GUILD_ID, STATUS

class RelatorioTransportes(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.guild_id = GUILD_ID
        self.dashboard_enviado = False
    
    def _get_estatisticas(self):
        """Retorna estatísticas de transportes"""
        try:
            # Concluídos (CONCLUIDO ou ENTREGUE)
            concluidos = len(db.get_transportes_by_status(STATUS["CONCLUIDO"])) + \
                         len(db.get_transportes_by_status(STATUS["ENTREGUE"]))
            
            # Em fila (ABERTO)
            fila = len(db.get_transportes_by_status(STATUS["ABERTO"]))
            
            # Aguardando pagamento
            aguardando_pagamento = len(db.get_transportes_by_status(STATUS["AGUARDANDO_PAGAMENTO"]))
            
            # Pagos aguardando transporte (PAGO ou DEPOSITADO)
            pagos = len(db.get_transportes_by_status(STATUS["PAGO"])) + \
                    len(db.get_transportes_by_status(STATUS["DEPOSITADO"]))
            
            # Em transporte
            em_transporte = len(db.get_transportes_by_status(STATUS["EM_TRANSPORTE"]))
            
            # Cancelados
            cancelados = len(db.get_transportes_by_status(STATUS["CANCELADO"])) + \
                         len(db.get_transportes_by_status(STATUS["REJEITADO"]))
            
            total = concluidos + fila + aguardando_pagamento + pagos + em_transporte + cancelados
            
            return {
                'concluidos': concluidos,
                'fila': fila,
                'aguardando_pagamento': aguardando_pagamento,
                'pagos': pagos,
                'em_transporte': em_transporte,
                'cancelados': cancelados,
                'total': total
            }
        except Exception as e:
            print(f"❌ Erro ao buscar estatísticas: {e}")
            return {
                'concluidos': 0,
                'fila': 0,
                'aguardando_pagamento': 0,
                'pagos': 0,
                'em_transporte': 0,
                'cancelados': 0,
                'total': 0
            }
    
    async def _enviar_dashboard(self, canal):
        """Envia dashboard com botões para o canal de relatórios"""
        
        stats = self._get_estatisticas()
        
        # Embed principal - Dashboard
        embed_main = discord.Embed(
            title="📊 RELATÓRIO DE TRANSPORTES - T.A.S MANIA",
            description="Dashboard em Tempo Real de Estatísticas",
            color=0x3498DB  # Azul
        )
        
        # Estatísticas principais
        embed_main.add_field(
            name="✅ CONCLUÍDOS",
            value=f"```\n  {stats['concluidos']}\n```",
            inline=True
        )
        embed_main.add_field(
            name="⏳ AGUARDANDO PAGAMENTO",
            value=f"```\n  {stats['aguardando_pagamento']}\n```",
            inline=True
        )
        embed_main.add_field(
            name="💰 PAGOS - TRANSPORTAR",
            value=f"```\n  {stats['pagos']}\n```",
            inline=True
        )
        
        # Segunda linha
        embed_main.add_field(
            name="📋 EM FILA",
            value=f"```\n  {stats['fila']}\n```",
            inline=True
        )
        embed_main.add_field(
            name="🚚 EM TRANSPORTE",
            value=f"```\n  {stats['em_transporte']}\n```",
            inline=True
        )
        embed_main.add_field(
            name="❌ CANCELADOS",
            value=f"```\n  {stats['cancelados']}\n```",
            inline=True
        )
        
        # Total geral
        embed_main.add_field(
            name="📈 TOTAL",
            value=f"```\n  {stats['total']}\n```",
            inline=False
        )
        
        # Barra de progresso visual
        if stats['total'] > 0:
            percentual_concluido = (stats['concluidos'] / stats['total']) * 100
            barra_tamanho = int(percentual_concluido / 5)  # 20 caracteres max
            barra = "█" * barra_tamanho + "░" * (20 - barra_tamanho)
            
            embed_main.add_field(
                name="📊 PROGRESSO GERAL",
                value=f"```{barra} {percentual_concluido:.1f}%```",
                inline=False
            )
        
        # Resumo com emojis
        resumo = f"""
🎯 **RESUMO EXECUTIVO**
• ✅ Concluídos: **{stats['concluidos']}** transportes
• 📋 Em Fila: **{stats['fila']}** aguardando pagamento
• 💰 Pagos: **{stats['pagos']}** aguardando transporte
• 🚚 Em Transporte: **{stats['em_transporte']}** em andamento
• ⏳ Pendência de Pagamento: **{stats['aguardando_pagamento']}** pendentes
        """
        
        embed_main.add_field(
            name="📌 SUMÁRIO",
            value=resumo,
            inline=False
        )
        
        embed_main.set_footer(text=f"Atualizado em: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
        embed_main.set_thumbnail(url="https://cdn-icons-png.flaticon.com/512/924/924514.png")
        
        # View com botões
        view = discord.ui.View(timeout=None)
        
        # Botão Detalhes Concluídos
        btn_concluidos = discord.ui.Button(
            label=f"✅ Concluídos ({stats['concluidos']})",
            style=discord.ButtonStyle.success,
            custom_id="btn_concluidos",
            emoji="✅"
        )
        
        async def concluidos_callback(interaction: discord.Interaction):
            await self._mostrar_detalhes(interaction, "CONCLUIDOS")
        
        btn_concluidos.callback = concluidos_callback
        view.add_item(btn_concluidos)
        
        # Botão Detalhes Em Fila
        btn_fila = discord.ui.Button(
            label=f"📋 Fila ({stats['fila']})",
            style=discord.ButtonStyle.primary,
            custom_id="btn_fila",
            emoji="📋"
        )
        
        async def fila_callback(interaction: discord.Interaction):
            await self._mostrar_detalhes(interaction, "FILA")
        
        btn_fila.callback = fila_callback
        view.add_item(btn_fila)
        
        # Botão Detalhes Aguardando Pagamento
        btn_aguardando = discord.ui.Button(
            label=f"⏳ Pendência ({stats['aguardando_pagamento']})",
            style=discord.ButtonStyle.secondary,
            custom_id="btn_aguardando",
            emoji="⏳"
        )
        
        async def aguardando_callback(interaction: discord.Interaction):
            await self._mostrar_detalhes(interaction, "AGUARDANDO_PAGAMENTO")
        
        btn_aguardando.callback = aguardando_callback
        view.add_item(btn_aguardando)
        
        # Botão Detalhes Pagos
        btn_pagos = discord.ui.Button(
            label=f"💰 Pagos ({stats['pagos']})",
            style=discord.ButtonStyle.success,
            custom_id="btn_pagos",
            emoji="💰"
        )
        
        async def pagos_callback(interaction: discord.Interaction):
            await self._mostrar_detalhes(interaction, "PAGOS")
        
        btn_pagos.callback = pagos_callback
        view.add_item(btn_pagos)
        
        # Botão Em Transporte
        btn_transportando = discord.ui.Button(
            label=f"🚚 Transportando ({stats['em_transporte']})",
            style=discord.ButtonStyle.primary,
            custom_id="btn_transportando",
            emoji="🚚"
        )
        
        async def transportando_callback(interaction: discord.Interaction):
            await self._mostrar_detalhes(interaction, "EM_TRANSPORTE")
        
        btn_transportando.callback = transportando_callback
        view.add_item(btn_transportando)
        
        # Botão Atualizar
        btn_atualizar = discord.ui.Button(
            label="🔄 Atualizar",
            style=discord.ButtonStyle.secondary,
            custom_id="btn_atualizar_relatorio",
            emoji="🔄"
        )
        
        async def atualizar_callback(interaction: discord.Interaction):
            await interaction.response.defer()
            await self._enviar_dashboard(canal)
        
        btn_atualizar.callback = atualizar_callback
        view.add_item(btn_atualizar)
        
        # Envia para o canal
        try:
            await canal.send(embed=embed_main, view=view)
            print("✅ Dashboard de relatórios enviado para o canal")
        except Exception as e:
            print(f"❌ Erro ao enviar dashboard: {e}")
    
    async def _mostrar_detalhes(self, interaction: discord.Interaction, tipo: str):
        """Mostra detalhes de um tipo de transporte"""
        
        try:
            await interaction.response.defer(ephemeral=True)
            
            # Busca transportes do tipo solicitado
            if tipo == "CONCLUIDOS":
                transportes1 = db.get_transportes_by_status(STATUS["CONCLUIDO"])
                transportes2 = db.get_transportes_by_status(STATUS["ENTREGUE"])
                transportes = transportes1 + transportes2
                titulo = "✅ TRANSPORTES CONCLUÍDOS"
                cor = 0x27AE60
            
            elif tipo == "FILA":
                transportes = db.get_transportes_by_status(STATUS["ABERTO"])
                titulo = "📋 TRANSPORTES EM FILA"
                cor = 0x3498DB
            
            elif tipo == "AGUARDANDO_PAGAMENTO":
                transportes = db.get_transportes_by_status(STATUS["AGUARDANDO_PAGAMENTO"])
                titulo = "⏳ AGUARDANDO PAGAMENTO"
                cor = 0xF39C12
            
            elif tipo == "PAGOS":
                transportes1 = db.get_transportes_by_status(STATUS["PAGO"])
                transportes2 = db.get_transportes_by_status(STATUS["DEPOSITADO"])
                transportes = transportes1 + transportes2
                titulo = "💰 PAGOS - AGUARDANDO TRANSPORTE"
                cor = 0x2ECC71
            
            elif tipo == "EM_TRANSPORTE":
                transportes = db.get_transportes_by_status(STATUS["EM_TRANSPORTE"])
                titulo = "🚚 EM TRANSPORTE"
                cor = 0x9B59B6
            
            else:
                transportes = []
                titulo = "❓ DETALHES"
                cor = 0x95A5A6
            
            if not transportes:
                embed = discord.Embed(
                    title=titulo,
                    description="Nenhum transporte nesta categoria",
                    color=cor
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
                return
            
            # Cria embed com detalhes
            embed = discord.Embed(
                title=f"{titulo} ({len(transportes)})",
                description=f"Detalhes dos {len(transportes)} transportes",
                color=cor
            )
            
            # Mostra até 25 transportes
            for trans in transportes[:25]:
                numero = trans[11] if len(trans) > 11 else "N/A"
                status = trans[2]
                cliente_id = trans[1]
                data = trans[7] if len(trans) > 7 else "N/A"
                
                embed.add_field(
                    name=f"🎫 Ticket #{numero}",
                    value=f"**Status:** {status}\n**Cliente:** <@{cliente_id}>\n**Data:** {data}",
                    inline=False
                )
            
            if len(transportes) > 25:
                embed.set_footer(text=f"Mostrando 25 de {len(transportes)} transportes")
            
            await interaction.followup.send(embed=embed, ephemeral=True)
            
        except Exception as e:
            print(f"❌ Erro ao mostrar detalhes: {e}")
            await interaction.followup.send(f"❌ Erro: {e}", ephemeral=True)
    
    @app_commands.command(name="enviar_relatorio", description="Envia dashboard de relatórios ao canal")
    @app_commands.guild_only()
    async def enviar_relatorio(self, interaction: discord.Interaction):
        """Envia o dashboard de relatórios para o canal de relatórios"""
        try:
            guild = interaction.guild
            
            # Encontra o canal de relatórios
            canal_relatorio = None
            for ch in guild.channels:
                if "relatorio" in ch.name.lower() and isinstance(ch, discord.TextChannel):
                    canal_relatorio = ch
                    break
            
            if not canal_relatorio:
                await interaction.response.send_message("❌ Canal de relatórios não encontrado!", ephemeral=True)
                return
            
            # Envia o dashboard
            await self._enviar_dashboard(canal_relatorio)
            await interaction.response.send_message("✅ Dashboard de relatórios enviado!", ephemeral=True)
            
        except Exception as e:
            print(f"❌ Erro ao enviar relatório: {e}")
            await interaction.response.send_message(f"❌ Erro: {e}", ephemeral=True)
    
    @commands.Cog.listener()
    async def on_ready(self):
        """Envia dashboard ao canal de relatórios quando o bot inicia"""
        print(f"🔍 Listener on_ready (RelatorioTransportes) chamado")
        
        if not self.dashboard_enviado:
            await asyncio.sleep(3)  # Aguarda 3 segundos
            
            try:
                print(f"📡 Procurando guild {self.guild_id}...")
                guild = self.bot.get_guild(self.guild_id)
                
                if not guild:
                    print(f"❌ Guild não encontrada!")
                    return
                
                print(f"✅ Guild encontrada: {guild.name}")
                
                for ch in guild.channels:
                    if "relatorio" in ch.name.lower() and isinstance(ch, discord.TextChannel):
                        print(f"📨 Enviando dashboard para {ch.name}...")
                        await self._enviar_dashboard(ch)
                        self.dashboard_enviado = True
                        print("✅ Dashboard de relatórios enviado com sucesso!")
                        break
                        
            except Exception as e:
                print(f"❌ Erro ao enviar dashboard: {e}")
                import traceback
                traceback.print_exc()

async def setup(bot):
    await bot.add_cog(RelatorioTransportes(bot))
