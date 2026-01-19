"""
Cog: Gerenciamento de Transportes (Transportadores)
"""
import discord
from discord.ext import commands
from database import db
from config import STATUS
from utils.embeds import criar_embed_transporte

class TransportCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    @commands.Cog.listener()
    async def on_ready(self):
        print("✅ Cog Transport carregado")
    
    transportador_group = discord.app_commands.Group(name="transporter", description="Comandos de transportador")
    
    @transportador_group.command(name="start", description="Iniciar um transporte")
    @discord.app_commands.describe(numero_ticket="Número do ticket a transportar")
    async def iniciar_transporte(self, interaction: discord.Interaction, numero_ticket: int):
        """Inicia um transporte"""
        
        await interaction.response.defer(ephemeral=True)
        
        # Verifica se é transportador
        guild = interaction.guild
        transportador_role = discord.utils.get(guild.roles, name="Transporter")
        
        if transportador_role not in interaction.user.roles:
            await interaction.followup.send(
                "❌ Apenas transportadores podem iniciar transportes!",
                ephemeral=True
            )
            return
        
        # Busca transporte
        transporte = db.get_transporte_by_numero(numero_ticket)
        if not transporte:
            await interaction.followup.send(
                f"❌ Ticket #{numero_ticket:04d} não encontrado!",
                ephemeral=True
            )
            return
        
        # Verifica status
        if transporte[2] != STATUS["PAGO"]:
            await interaction.followup.send(
                f"❌ Ticket deve estar com status PAGO (Status atual: {transporte[2]})",
                ephemeral=True
            )
            return
        
        # Atualiza status
        db.update_transporte_status(transporte[0], STATUS["EM_TRANSPORTE"])
        db.update_transporte(transporte[0], transportador_id=str(interaction.user.id))
        db.create_auditoria(
            str(interaction.user.id),
            "INICIAR_TRANSPORTE",
            transporte[0],
            f"Transporte iniciado por {interaction.user.name}"
        )
        
        # Notifica cliente
        cliente_id = transporte[1]
        cliente = self.bot.get_user(cliente_id) or await self.bot.fetch_user(cliente_id)
        
        if cliente:
            await cliente.send(
                f"🚚 **Transporte Iniciado!**\n"
                f"Ticket: #{numero_ticket:04d}\n"
                f"Transportador: {interaction.user.mention}\n"
                f"Dirija-se a Caerleon para retirar seus items!"
            )
        
        await interaction.followup.send(
            f"✅ Transporte #{numero_ticket:04d} iniciado com sucesso!",
            ephemeral=True
        )
    
    @transportador_group.command(name="confirm", description="Confirmar entrega de um transporte")
    @discord.app_commands.describe(numero_ticket="Número do ticket a confirmar")
    async def confirmar_transporte(self, interaction: discord.Interaction, numero_ticket: int):
        """Confirma a entrega de um transporte"""
        
        await interaction.response.defer(ephemeral=True)
        
        # Verifica se é transportador
        guild = interaction.guild
        transportador_role = discord.utils.get(guild.roles, name="Transporter")
        
        if transportador_role not in interaction.user.roles:
            await interaction.followup.send(
                "❌ Apenas transportadores podem confirmar transportes!",
                ephemeral=True
            )
            return
        
        # Busca transporte
        transporte = db.get_transporte_by_numero(numero_ticket)
        if not transporte:
            await interaction.followup.send(
                f"❌ Ticket #{numero_ticket:04d} não encontrado!",
                ephemeral=True
            )
            return
        
        # Verifica status
        if transporte[2] != STATUS["EM_TRANSPORTE"]:
            await interaction.followup.send(
                f"❌ Ticket deve estar com status EM_TRANSPORTE (Status atual: {transporte[2]})",
                ephemeral=True
            )
            return
        
        # Atualiza status
        db.update_transporte_status(transporte[0], STATUS["ENTREGUE"])
        db.create_auditoria(
            str(interaction.user.id),
            "CONFIRMAR_ENTREGA",
            transporte[0],
            f"Entrega confirmada por {interaction.user.name}"
        )
        
        # Notifica cliente
        cliente_id = transporte[1]
        cliente = self.bot.get_user(cliente_id) or await self.bot.fetch_user(cliente_id)
        
        if cliente:
            embed_entrega = discord.Embed(
                title="🎉 TRANSPORTE ENTREGUE!",
                description="Seus itens chegaram com segurança em Caerleon!",
                color=discord.Color.gold()
            )
            embed_entrega.add_field(
                name="🎫 Ticket",
                value=f"#{numero_ticket:04d}",
                inline=False
            )
            embed_entrega.add_field(
                name="📍 Localização",
                value="Tavern (ao lado do Portal em Caerleon)",
                inline=False
            )
            embed_entrega.add_field(
                name="✨ Mensagem Especial",
                value="**WHADAWHADAWEL VOLTE SEMPRE!** 🎯\n\nSeus itens estão esperando! Retire-os com segurança.\n\nFoi um prazer transportar seus bens! 💙\nEstaremos aqui se precisar novamente!",
                inline=False
            )
            embed_entrega.set_footer(text="T.A.S Mania | Transportes Seguros desde 2024 | WHADAWEL™")
            
            await cliente.send(embed=embed_entrega)
        
        await interaction.followup.send(
            f"✅ Transporte #{numero_ticket:04d} entregue com sucesso!",
            ephemeral=True
        )

async def setup(bot):
    await bot.add_cog(TransportCog(bot))
