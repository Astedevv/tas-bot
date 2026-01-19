"""
Cog: Fila de Transportes em Real-time
"""
import discord
from discord.ext import commands, tasks
from database import db
from config import STATUS
from utils.embeds import criar_embed_fila
import asyncio

class QueueCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.fila_task = None
        self.ultima_mensagem_fila = None
        self.transportes_cache = []
    
    @commands.Cog.listener()
    async def on_ready(self):
        print("✅ Cog Queue carregado")
        
        # Inicia task de atualização
        if not self.fila_task or not self.fila_task.is_running():
            self.atualizar_fila.start()
    
    @tasks.loop(seconds=30)
    async def atualizar_fila(self):
        """Atualiza a fila de transportes a cada 30 segundos"""
        
        try:
            guild_id = int(db.get_config("GUILD_ID") or 0)
            if not guild_id:
                return
            
            guild = self.bot.get_guild(guild_id)
            if not guild:
                return
            
            # Busca canal de fila
            fila_channel_id = db.get_config("CANAL_FILA")
            if not fila_channel_id:
                return
            
            fila_channel = guild.get_channel(int(fila_channel_id))
            if not fila_channel:
                return
            
            # Busca transportes com status PAGO ou DEPOSITADO
            transportes = db.get_transportes_por_status([STATUS["PAGO"], STATUS["DEPOSITADO"]])
            
            # Ordena por prioridade (ALTA primeiro) depois por data
            transportes_ordenados = sorted(
                transportes,
                key=lambda x: (
                    0 if x[6] == "ALTA" else 1 if x[6] == "NORMAL" else 2,
                    x[8]  # data_criacao
                )
            )
            
            if not transportes_ordenados:
                # Nenhum transporte na fila
                embed = discord.Embed(
                    title="📭 Fila de Transportes",
                    description="Nenhum transporte aguardando transportador",
                    color=discord.Color.greyple()
                )
                embed.set_footer(text="Atualizado a cada 30 segundos")
                
                if self.ultima_mensagem_fila:
                    try:
                        await self.ultima_mensagem_fila.edit(embed=embed)
                    except:
                        self.ultima_mensagem_fila = await fila_channel.send(embed=embed)
                else:
                    self.ultima_mensagem_fila = await fila_channel.send(embed=embed)
                return
            
            # Cria embeds para cada transporte
            embeds = []
            for idx, transporte in enumerate(transportes_ordenados[:10], 1):  # Máx 10 na fila
                embed = criar_embed_fila(
                    numero=transporte[1],
                    origem=transporte[4],
                    valor=transporte[7],
                    prioridade=transporte[6],
                    cliente_id=transporte[1]
                )
                embeds.append(embed)
            
            # Envia/atualiza mensagem de fila
            view = discord.ui.View()
            
            if self.ultima_mensagem_fila:
                try:
                    # Tenta editar mensagem existente
                    await self.ultima_mensagem_fila.edit(embeds=embeds)
                except discord.errors.NotFound:
                    # Se foi deletada, cria nova
                    self.ultima_mensagem_fila = await fila_channel.send(embeds=embeds)
            else:
                self.ultima_mensagem_fila = await fila_channel.send(embeds=embeds)
            
        except Exception as e:
            print(f"Erro ao atualizar fila: {e}")
    
    def cog_unload(self):
        """Limpa ao descarregar o cog"""
        if self.fila_task.is_running():
            self.fila_task.cancel()

async def setup(bot):
    await bot.add_cog(QueueCog(bot))
