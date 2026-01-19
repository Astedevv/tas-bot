"""
Cog: Comandos do Staff
DESABILITADO: Requer banco de dados legado não disponível
"""
import discord
from discord.ext import commands
from discord.app_commands import checks
from bot.config import STATUS, PRECO_BASE
from bot.utils.embeds import criar_embed_transporte
from datetime import datetime, timedelta

class StaffCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    @commands.Cog.listener()
    async def on_ready(self):
        print("✅ Cog Staff carregado (desabilitado)")
    
    staff_group = discord.app_commands.Group(name="staff", description="Comandos de staff [DESABILITADO]")
    
    # Todos os comandos removidos por requererem db legado
    # Funcionalidade de staff será implementada no futuro com novo sistema de banco de dados

async def setup(bot):
    await bot.add_cog(StaffCog(bot))
