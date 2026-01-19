"""
Cog: Histórico Público
"""
import discord
from discord.ext import commands
from bot.database import db
from bot.config import STATUS
from bot.utils.embeds import criar_embed_log_publico

class HistoryCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    @commands.Cog.listener()
    async def on_ready(self):
        print("✅ Cog History carregado")
    
    @commands.Cog.listener()
    async def on_app_command_error(self, interaction: discord.Interaction, error: discord.app_commands.AppCommandError):
        """Registra erros públicos no histórico"""
        
        db.create_log_transporte(
            0,
            "ERRO",
            f"Erro: {str(error)}"
        )
    
    async def registrar_entrega_publico(self, transporte_id: int):
        """Registra uma entrega no histórico público"""
        
        try:
            transporte = db.get_transporte(transporte_id)
            if not transporte:
                return
            
            guild_id = int(db.get_config("GUILD_ID") or 0)
            if not guild_id:
                return
            
            guild = self.bot.get_guild(guild_id)
            if not guild:
                return
            
            # Busca canal de histórico
            historico_channel_id = db.get_config("CANAL_HISTORICO")
            if not historico_channel_id:
                return
            
            historico_channel = guild.get_channel(int(historico_channel_id))
            if not historico_channel:
                return
            
            # Cria embed de log
            embed = criar_embed_log_publico(
                numero=transporte[1],
                origem=transporte[4],
                valor=transporte[7],
                prioridade=transporte[6]
            )
            
            # Envia para histórico público
            msg = await historico_channel.send(embed=embed)
            
            # Armazena no banco
            db.update_transporte(transporte_id, historico_message_id=msg.id)
            
            # Limpa mensagens antigas (mantém últimas 50)
            async for msg in historico_channel.history(limit=100):
                if msg.author == self.bot.user:
                    # Conta mensagens de bot neste canal
                    count = sum(1 for m in await historico_channel.history(limit=200) if m.author == self.bot.user)
                    if count > 50:
                        try:
                            await msg.delete()
                        except:
                            pass
        
        except Exception as e:
            print(f"Erro ao registrar entrega pública: {e}")
    
    @commands.command(name="log_entrega", hidden=True)
    @commands.is_owner()
    async def log_entrega(self, ctx, transporte_id: int):
        """Comando interno para registrar entrega"""
        
        await self.registrar_entrega_publico(transporte_id)
        await ctx.send(f"✅ Entrega #{transporte_id} registrada no histórico público", ephemeral=True)

async def setup(bot):
    await bot.add_cog(HistoryCog(bot))
