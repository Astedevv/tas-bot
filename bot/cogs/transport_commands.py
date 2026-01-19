"""
Cog: Comando de Abrir Transporte
"""
import discord
from discord.ext import commands

class ViewAbrir(discord.ui.View):
    """View para o botão de abrir transporte"""
    
    def __init__(self, commands_cog):
        super().__init__(timeout=None)
        self.commands_cog = commands_cog
    
    @discord.ui.button(
        label="Abrir Transporte Agora",
        style=discord.ButtonStyle.success,
        emoji="🚚"
    )
    async def btn_abrir(self, inter: discord.Interaction, button: discord.ui.Button):
        """Botão para abrir novo transporte"""
        print(f"\n🔘 Botão clicado por {inter.user.name}")
        await self.commands_cog.abrir_ticket(inter)

class TransportCommandsCog(commands.Cog):
    """Comandos principais de transporte"""
    
    def __init__(self, bot):
        self.bot = bot
    
    @commands.Cog.listener()
    async def on_ready(self):
        print("✅ Transport Commands carregado")
    
    @commands.command(name="start_transport_menu")
    @commands.has_permissions(administrator=True)
    async def start_menu(self, ctx):
        """Admin: Coloca menu de transportes no canal"""
        
        # Encontra o cog de transporte
        transport_cog = self.bot.get_cog("TransportFlowCog")
        if not transport_cog:
            return await ctx.send("❌ Cog de transporte não carregado!", ephemeral=True)
        
        embed = discord.Embed(
            title="🎫 ABRIR NOVO TRANSPORTE",
            description="Clique no botão verde abaixo para iniciar seu transporte seguro!",
            color=discord.Color.blue()
        )
        
        embed.add_field(
            name="✨ O que você vai fazer:",
            value="1️⃣ Digite seu nick exatamente como no jogo\n2️⃣ Escolha a origem\n3️⃣ Selecione prioridade\n4️⃣ Digite a quantidade de prata\n5️⃣ Adicione observações (opcional)\n6️⃣ Confirme e pague via PIX\n7️⃣ Aguarde a entrega",
            inline=False
        )
        
        embed.add_field(
            name="💰 Tabela de Preços:",
            value="**Normal:** R$ 0,60 por 1M\n**Alta Prioridade:** R$ 0,72 por 1M\n**Mínimo:** 10M (R$ 6,00)",
            inline=False
        )
        
        embed.add_field(
            name="⏱️ Tempo de Entrega:",
            value="**Normal:** até 2 horas\n**Alta Prioridade:** 1-2 horas",
            inline=False
        )
        
        embed.add_field(
            name="📍 Informações:",
            value="Destino padrão: **Caerleon**\nSeus dados são 100% privados\nStaff confiável",
            inline=False
        )
        
        embed.set_footer(text="T.A.S Mania | Transporte Seguro desde 2024")
        embed.set_thumbnail(url="https://cdn.discordapp.com/emojis/1462502345991520613.png")
        
        # View com o botão
        view = ViewAbrir(self)
        
        await ctx.send(embed=embed, view=view)
        await ctx.send("✅ Menu postado com sucesso!")
    
    @discord.app_commands.command(
        name="abrir",
        description="🚚 Abrir novo transporte agora!"
    )
    async def abrir_transporte(self, interaction: discord.Interaction):
        """Comando slash para abrir transporte - FUNCIONA GARANTIDO"""
        print(f"\n🚀 Comando slash /abrir executado por {interaction.user.name}")
        
        transport_cog = self.bot.get_cog("TransportFlowCog")
        if transport_cog:
            await transport_cog.abrir_ticket(interaction)
        else:
            await interaction.response.send_message(
                "❌ Sistema de transporte não está pronto",
                ephemeral=True
            )
    
    async def abrir_ticket(self, interaction: discord.Interaction):
        """Delega para o cog de transporte"""
        transport_cog = self.bot.get_cog("TransportFlowCog")
        if transport_cog:
            await transport_cog.abrir_ticket(interaction)

async def setup(bot):
    await bot.add_cog(TransportCommandsCog(bot))
