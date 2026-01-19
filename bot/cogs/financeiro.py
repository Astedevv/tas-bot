"""
Sistema de Banco Financeiro - T.A.S Mania
Gerenciador de saldo, receitas e despesas
"""
import discord
from discord.ext import commands
from discord import app_commands
import sqlite3
from datetime import datetime
import asyncio
from bot.database import db
from bot.config import GUILD_ID

class Financeiro(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.guild_id = GUILD_ID
        self.dashboard_enviado = False
        self._init_tabelas()
    
    def _init_tabelas(self):
        """Inicializa tabelas de financeiro se não existirem"""
        try:
            conn = sqlite3.connect("./data/tas_mania.db")
            cursor = conn.cursor()
            
            # Tabela de transações financeiras
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS financeiro_transacoes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    tipo TEXT,
                    descricao TEXT,
                    valor REAL,
                    motivo TEXT,
                    autor_id INTEGER,
                    data_criacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Tabela de saldo
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS financeiro_saldo (
                    id INTEGER PRIMARY KEY,
                    saldo_total REAL DEFAULT 0,
                    saldo_entrada REAL DEFAULT 0,
                    saldo_saida REAL DEFAULT 0,
                    ultima_atualizacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Inicializa saldo se não existir
            cursor.execute("SELECT * FROM financeiro_saldo WHERE id = 1")
            if not cursor.fetchone():
                cursor.execute("""
                    INSERT INTO financeiro_saldo (id, saldo_total, saldo_entrada, saldo_saida)
                    VALUES (1, 0, 0, 0)
                """)
            
            conn.commit()
            conn.close()
            print("✅ Tabelas de financeiro inicializadas")
        except Exception as e:
            print(f"❌ Erro ao inicializar tabelas: {e}")
    
    def _adicionar_transacao(self, tipo, valor, descricao="", motivo="", autor_id=0):
        """Adiciona uma transação e atualiza saldo"""
        try:
            conn = sqlite3.connect("./data/tas_mania.db")
            cursor = conn.cursor()
            
            # Adiciona transação
            cursor.execute("""
                INSERT INTO financeiro_transacoes 
                (tipo, valor, descricao, motivo, autor_id)
                VALUES (?, ?, ?, ?, ?)
            """, (tipo, valor, descricao, motivo, autor_id))
            
            # Busca saldo atual
            cursor.execute("SELECT * FROM financeiro_saldo WHERE id = 1")
            saldo_data = cursor.fetchone()
            saldo_total = saldo_data[1] if saldo_data else 0
            entrada = saldo_data[2] if saldo_data else 0
            saida = saldo_data[3] if saldo_data else 0
            
            # Atualiza saldo
            if tipo == "ENTRADA":
                novo_total = saldo_total + valor
                nova_entrada = entrada + valor
                nova_saida = saida
            else:  # SAIDA
                novo_total = saldo_total - valor
                nova_entrada = entrada
                nova_saida = saida + valor
            
            cursor.execute("""
                UPDATE financeiro_saldo 
                SET saldo_total = ?, saldo_entrada = ?, saldo_saida = ?,
                    ultima_atualizacao = CURRENT_TIMESTAMP
                WHERE id = 1
            """, (novo_total, nova_entrada, nova_saida))
            
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"❌ Erro ao adicionar transação: {e}")
            return False
    
    def _get_saldo(self):
        """Retorna saldo atual"""
        try:
            conn = sqlite3.connect("./data/tas_mania.db")
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM financeiro_saldo WHERE id = 1")
            dados = cursor.fetchone()
            conn.close()
            
            if dados:
                return {
                    'total': dados[1],
                    'entrada': dados[2],
                    'saida': dados[3],
                    'ultima_atualizacao': dados[4]
                }
            return {'total': 0, 'entrada': 0, 'saida': 0}
        except Exception as e:
            print(f"❌ Erro ao buscar saldo: {e}")
            return {'total': 0, 'entrada': 0, 'saida': 0}
    
    def _get_historico(self, limite=10):
        """Retorna histórico de transações"""
        try:
            conn = sqlite3.connect("./data/tas_mania.db")
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT * FROM financeiro_transacoes 
                ORDER BY id DESC LIMIT ?
            """, (limite,))
            
            transacoes = cursor.fetchall()
            conn.close()
            return transacoes
        except Exception as e:
            print(f"❌ Erro ao buscar histórico: {e}")
            return []
    
    @app_commands.command(name="banco", description="Exibe dashboard financeiro")
    @app_commands.guild_only()
    async def banco_dashboard(self, interaction: discord.Interaction):
        """Exibe dashboard financeiro"""
        
        saldo = self._get_saldo()
        historico = self._get_historico(5)
        
        # Embed principal - Dashboard
        embed_main = discord.Embed(
            title="💰 BANCO FINANCEIRO - T.A.S MANIA",
            description="Sistema de Gerenciamento Monetário",
            color=0xFFD700  # Ouro
        )
        
        # Saldo Total (grande destaque)
        saldo_total = saldo['total']
        if saldo_total >= 0:
            cor_saldo = "🟢"
            emoji_saldo = "💚"
        else:
            cor_saldo = "🔴"
            emoji_saldo = "❌"
        
        embed_main.add_field(
            name=f"{emoji_saldo} SALDO TOTAL",
            value=f"```\n  R$ {saldo_total:,.2f}\n```",
            inline=False
        )
        
        # Entradas e Saídas lado a lado
        embed_main.add_field(
            name="📈 ENTRADAS",
            value=f"```\nR$ {saldo['entrada']:,.2f}\n```",
            inline=True
        )
        embed_main.add_field(
            name="📉 SAÍDAS",
            value=f"```\nR$ {saldo['saida']:,.2f}\n```",
            inline=True
        )
        
        # Barra visual de saldo
        if saldo_total > 0:
            barra_tamanho = min(int(saldo_total / 1000), 20)  # Max 20
            barra = "█" * barra_tamanho + "░" * (20 - barra_tamanho)
        else:
            barra = "░" * 20
        
        embed_main.add_field(
            name="📊 VISUALIZAÇÃO",
            value=f"```{barra}```",
            inline=False
        )
        
        # Histórico de transações
        if historico:
            historico_text = ""
            for trans in historico:
                tipo_emoji = "🟢" if trans['tipo'] == "ENTRADA" else "🔴"
                valor = trans['valor']
                desc = trans['descricao'][:20]
                motivo = f" ({trans['motivo'][:15]})" if trans['motivo'] else ""
                
                historico_text += f"{tipo_emoji} R$ {valor:,.2f} - {desc}{motivo}\n"
            
            embed_main.add_field(
                name="📜 ÚLTIMAS TRANSAÇÕES",
                value=historico_text,
                inline=False
            )
        
        embed_main.add_field(
            name="⚙️ AÇÕES",
            value="Use `/retirada` para sacar fundos\nUse `/depositar` para registrar entrada",
            inline=False
        )
        
        embed_main.set_footer(text=f"Última atualização: {saldo.get('ultima_atualizacao', 'N/A')}")
        embed_main.set_thumbnail(url="https://cdn-icons-png.flaticon.com/512/3090/3090329.png")
        
        await interaction.response.send_message(embed=embed_main)
    
    @app_commands.command(name="retirada", description="Faz retirada do banco")
    @app_commands.describe(valor="Valor da retirada")
    @app_commands.guild_only()
    async def retirada(self, interaction: discord.Interaction, valor: float):
        """Faz retirada do banco com motivo"""
        
        if valor <= 0:
            await interaction.response.send_message("❌ Valor deve ser maior que zero!", ephemeral=True)
            return
        
        saldo = self._get_saldo()
        
        if saldo['total'] < valor:
            await interaction.response.send_message(f"❌ Saldo insuficiente! Você tem R$ {saldo['total']:,.2f}", ephemeral=True)
            return
        
        # Cria modal com referência ao cog
        cog_ref = self
        
        # Modal para motivo
        class MotivModal(discord.ui.Modal):
            motivo_input = discord.ui.TextInput(
                label="Motivo da Retirada",
                placeholder="Ex: Pagamento de transportador",
                max_length=100
            )
            
            async def on_submit(modal_self, modal_interaction: discord.Interaction):
                motivo = str(modal_self.motivo_input)
                
                # Adiciona transação
                cog_ref._adicionar_transacao(
                    tipo="SAIDA",
                    valor=valor,
                    descricao=f"Retirada de R$ {valor:,.2f}",
                    motivo=motivo,
                    autor_id=modal_interaction.user.id
                )
                
                # Novo saldo
                novo_saldo = cog_ref._get_saldo()
                
                # Embed de confirmação
                embed_conf = discord.Embed(
                    title="✅ RETIRADA CONFIRMADA",
                    color=0x2ECC71
                )
                embed_conf.add_field(name="💵 Valor Retirado", value=f"R$ {valor:,.2f}", inline=True)
                embed_conf.add_field(name="🎯 Motivo", value=motivo, inline=True)
                embed_conf.add_field(name="💰 Novo Saldo", value=f"R$ {novo_saldo['total']:,.2f}", inline=False)
                embed_conf.add_field(name="👤 Autorizado por", value=modal_interaction.user.mention, inline=False)
                embed_conf.set_footer(text=datetime.now().strftime("%d/%m/%Y %H:%M:%S"))
                
                await modal_interaction.response.send_message(embed=embed_conf, ephemeral=False)
                
                # Envia para canal financeiro
                guild = cog_ref.bot.get_guild(cog_ref.guild_id)
                for ch in guild.channels:
                    if ch.name == "financeiro":
                        embed_log = discord.Embed(
                            title="📊 RETIRADA REGISTRADA",
                            description=f"Retirada de **R$ {valor:,.2f}**",
                            color=0xE74C3C
                        )
                        embed_log.add_field(name="🎯 Motivo", value=motivo, inline=False)
                        embed_log.add_field(name="👤 Por", value=modal_interaction.user.mention, inline=False)
                        embed_log.add_field(name="💰 Saldo Atual", value=f"R$ {novo_saldo['total']:,.2f}", inline=False)
                        await ch.send(embed=embed_log)
                        break
        
        modal = MotivModal()
        await interaction.response.send_modal(modal)
    
    @app_commands.command(name="depositar", description="Adiciona valor ao banco")
    @app_commands.describe(valor="Valor do depósito", motivo="Motivo do depósito")
    @app_commands.guild_only()
    async def depositar(self, interaction: discord.Interaction, valor: float, motivo: str = "Depósito manual"):
        """Adiciona valor ao banco"""
        
        if valor <= 0:
            await interaction.response.send_message("❌ Valor deve ser maior que zero!", ephemeral=True)
            return
        
        self._adicionar_transacao(
            tipo="ENTRADA",
            valor=valor,
            descricao=f"Depósito de R$ {valor:,.2f}",
            motivo=motivo,
            autor_id=interaction.user.id
        )
        
        novo_saldo = self._get_saldo()
        
        # Embed de confirmação
        embed_conf = discord.Embed(
            title="✅ DEPÓSITO CONFIRMADO",
            color=0x2ECC71
        )
        embed_conf.add_field(name="💵 Valor Depositado", value=f"R$ {valor:,.2f}", inline=True)
        embed_conf.add_field(name="🎯 Motivo", value=motivo, inline=True)
        embed_conf.add_field(name="💰 Novo Saldo", value=f"R$ {novo_saldo['total']:,.2f}", inline=False)
        embed_conf.add_field(name="👤 Autorizado por", value=interaction.user.mention, inline=False)
        embed_conf.set_footer(text=datetime.now().strftime("%d/%m/%Y %H:%M:%S"))
        
        await interaction.response.send_message(embed=embed_conf)
        
        # Envia para canal financeiro
        guild = self.bot.get_guild(self.guild_id)
        for ch in guild.channels:
            if ch.name == "financeiro":
                embed_log = discord.Embed(
                    title="📊 DEPÓSITO REGISTRADO",
                    description=f"Depósito de **R$ {valor:,.2f}**",
                    color=0x2ECC71
                )
                embed_log.add_field(name="🎯 Motivo", value=motivo, inline=False)
                embed_log.add_field(name="👤 Por", value=interaction.user.mention, inline=False)
                embed_log.add_field(name="💰 Saldo Atual", value=f"R$ {novo_saldo['total']:,.2f}", inline=False)
                await ch.send(embed=embed_log)
                break
    
    @app_commands.command(name="historico_financeiro", description="Mostra histórico de transações")
    @app_commands.describe(limite="Número de transações a mostrar")
    @app_commands.guild_only()
    async def historico_financeiro(self, interaction: discord.Interaction, limite: int = 20):
        """Mostra histórico completo de transações"""
        
        historico = self._get_historico(limite)
        
        if not historico:
            await interaction.response.send_message("📭 Nenhuma transação registrada", ephemeral=True)
            return
        
        # Cria embeds pagináveis
        embed = discord.Embed(
            title="📜 HISTÓRICO FINANCEIRO COMPLETO",
            description=f"Últimas {len(historico)} transações",
            color=0x9B59B6
        )
        
        for trans in historico:
            tipo_emoji = "🟢 ENTRADA" if trans['tipo'] == "ENTRADA" else "🔴 SAÍDA"
            valor = trans['valor']
            desc = trans['descricao']
            motivo = trans['motivo'] if trans['motivo'] else "N/A"
            data = trans['data_criacao']
            
            embed.add_field(
                name=f"{tipo_emoji} - R$ {valor:,.2f}",
                value=f"**Descrição:** {desc}\n**Motivo:** {motivo}\n**Data:** {data}",
                inline=False
            )
        
        saldo = self._get_saldo()
        embed.set_footer(text=f"💰 Saldo Atual: R$ {saldo['total']:,.2f}")
        
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="enviar_banco", description="Envia dashboard do banco ao canal financeiro")
    @app_commands.guild_only()
    async def enviar_banco(self, interaction: discord.Interaction):
        """Envia o dashboard do banco para o canal financeiro"""
        try:
            guild = interaction.guild
            
            # Encontra o canal financeiro (com qualquer nome que contenha financeiro)
            canal_financeiro = None
            for ch in guild.channels:
                if "financeiro" in ch.name.lower() and isinstance(ch, discord.TextChannel):
                    canal_financeiro = ch
                    break
            
            if not canal_financeiro:
                await interaction.response.send_message("❌ Canal 'financeiro' não encontrado!", ephemeral=True)
                return
            
            # Envia o dashboard
            await self._enviar_dashboard(canal_financeiro)
            await interaction.response.send_message("✅ Dashboard enviado ao canal de financeiro!", ephemeral=True)
            
        except Exception as e:
            print(f"❌ Erro ao enviar dashboard: {e}")
            await interaction.response.send_message(f"❌ Erro: {e}", ephemeral=True)
    
    @commands.Cog.listener()
    async def on_ready(self):
        """Envia dashboard ao canal financeiro quando o bot inicia"""
        print(f"🔍 Listener on_ready chamado - dashboard_enviado: {self.dashboard_enviado}")
        
        if not self.dashboard_enviado:
            await asyncio.sleep(2)  # Aguarda 2 segundos para garantir que tudo está pronto
            
            try:
                print(f"📡 Procurando guild {self.guild_id}...")
                guild = self.bot.get_guild(self.guild_id)
                
                if not guild:
                    print(f"❌ Guild {self.guild_id} não encontrada!")
                    return
                
                print(f"✅ Guild encontrada: {guild.name}")
                print(f"📋 Canais disponíveis: {[ch.name for ch in guild.channels]}")
                
                for ch in guild.channels:
                    # Procura por qualquer canal que contenha "financeiro"
                    if "financeiro" in ch.name.lower() and isinstance(ch, discord.TextChannel):
                        print(f"📨 Enviando dashboard para {ch.name}...")
                        await self._enviar_dashboard(ch)
                        self.dashboard_enviado = True
                        print("✅ Dashboard financeiro enviado com sucesso!")
                        break
                else:
                    print("❌ Canal financeiro não encontrado!")
                    
            except Exception as e:
                print(f"❌ Erro ao enviar dashboard: {e}")
                import traceback
                traceback.print_exc()
    
    
    async def _enviar_dashboard(self, canal):
        """Envia dashboard com botões para o canal de financeiro"""
        
        saldo = self._get_saldo()
        historico = self._get_historico(5)
        
        # Embed principal - Dashboard
        embed_main = discord.Embed(
            title="💰 BANCO FINANCEIRO - T.A.S MANIA",
            description="Sistema de Gerenciamento Monetário",
            color=0xFFD700  # Ouro
        )
        
        # Saldo Total (grande destaque)
        saldo_total = saldo['total']
        if saldo_total >= 0:
            emoji_saldo = "💚"
        else:
            emoji_saldo = "❌"
        
        embed_main.add_field(
            name=f"{emoji_saldo} SALDO TOTAL",
            value=f"```\n  R$ {saldo_total:,.2f}\n```",
            inline=False
        )
        
        # Entradas e Saídas lado a lado
        embed_main.add_field(
            name="📈 ENTRADAS",
            value=f"```\nR$ {saldo['entrada']:,.2f}\n```",
            inline=True
        )
        embed_main.add_field(
            name="📉 SAÍDAS",
            value=f"```\nR$ {saldo['saida']:,.2f}\n```",
            inline=True
        )
        
        # Barra visual de saldo
        if saldo_total > 0:
            barra_tamanho = min(int(saldo_total / 1000), 20)
            barra = "█" * barra_tamanho + "░" * (20 - barra_tamanho)
        else:
            barra = "░" * 20
        
        embed_main.add_field(
            name="📊 VISUALIZAÇÃO",
            value=f"```{barra}```",
            inline=False
        )
        
        # Histórico de transações
        if historico:
            historico_text = ""
            for trans in historico:
                tipo_emoji = "🟢" if trans['tipo'] == "ENTRADA" else "🔴"
                valor = trans['valor']
                desc = trans['descricao'][:20]
                motivo = f" ({trans['motivo'][:15]})" if trans['motivo'] else ""
                
                historico_text += f"{tipo_emoji} R$ {valor:,.2f} - {desc}{motivo}\n"
            
            embed_main.add_field(
                name="📜 ÚLTIMAS TRANSAÇÕES",
                value=historico_text,
                inline=False
            )
        
        embed_main.set_footer(text="Sistema automático de financeiro")
        embed_main.set_thumbnail(url="https://cdn-icons-png.flaticon.com/512/3090/3090329.png")
        
        # View com botões
        view = discord.ui.View(timeout=None)
        
        # Botão Depositar
        btn_depositar = discord.ui.Button(
            label="💵 Depositar",
            style=discord.ButtonStyle.success,
            custom_id="btn_depositar_banco",
            emoji="💵"
        )
        
        async def depositar_callback(interaction: discord.Interaction):
            await self._modal_depositar(interaction)
        
        btn_depositar.callback = depositar_callback
        view.add_item(btn_depositar)
        
        # Botão Retirada
        btn_retirada = discord.ui.Button(
            label="💸 Retirada",
            style=discord.ButtonStyle.danger,
            custom_id="btn_retirada_banco",
            emoji="💸"
        )
        
        async def retirada_callback(interaction: discord.Interaction):
            await self._modal_retirada(interaction)
        
        btn_retirada.callback = retirada_callback
        view.add_item(btn_retirada)
        
        # Botão Histórico
        btn_historico = discord.ui.Button(
            label="📜 Histórico",
            style=discord.ButtonStyle.primary,
            custom_id="btn_historico_banco",
            emoji="📜"
        )
        
        async def historico_callback(interaction: discord.Interaction):
            historico = self._get_historico(20)
            saldo = self._get_saldo()
            
            embed = discord.Embed(
                title="📜 HISTÓRICO FINANCEIRO",
                description=f"Últimas {len(historico)} transações",
                color=0x9B59B6
            )
            
            for trans in historico:
                tipo_emoji = "🟢 ENTRADA" if trans['tipo'] == "ENTRADA" else "🔴 SAÍDA"
                valor = trans['valor']
                desc = trans['descricao']
                motivo = trans['motivo'] if trans['motivo'] else "N/A"
                data = trans['data_criacao']
                
                embed.add_field(
                    name=f"{tipo_emoji} - R$ {valor:,.2f}",
                    value=f"**Descrição:** {desc}\n**Motivo:** {motivo}\n**Data:** {data}",
                    inline=False
                )
            
            embed.set_footer(text=f"💰 Saldo Atual: R$ {saldo['total']:,.2f}")
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
        
        btn_historico.callback = historico_callback
        view.add_item(btn_historico)
        
        # Botão Atualizar
        btn_atualizar = discord.ui.Button(
            label="🔄 Atualizar",
            style=discord.ButtonStyle.secondary,
            custom_id="btn_atualizar_banco",
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
            print("✅ Dashboard financeiro enviado para o canal")
        except Exception as e:
            print(f"❌ Erro ao enviar dashboard: {e}")
    
    async def _modal_depositar(self, interaction: discord.Interaction):
        """Modal para depositar"""
        
        class DepositoModal(discord.ui.Modal):
            valor_input = discord.ui.TextInput(
                label="Valor do Depósito",
                placeholder="Ex: 1000.00",
                max_length=20
            )
            motivo_input = discord.ui.TextInput(
                label="Motivo do Depósito",
                placeholder="Ex: Venda de items",
                max_length=100
            )
            
            async def on_submit(modal_self, modal_interaction: discord.Interaction):
                try:
                    valor = float(modal_self.valor_input)
                    motivo = str(modal_self.motivo_input)
                    
                    if valor <= 0:
                        await modal_interaction.response.send_message("❌ Valor deve ser maior que zero!", ephemeral=True)
                        return
                    
                    # Adiciona transação
                    self._adicionar_transacao(
                        tipo="ENTRADA",
                        valor=valor,
                        descricao=f"Depósito de R$ {valor:,.2f}",
                        motivo=motivo,
                        autor_id=modal_interaction.user.id
                    )
                    
                    novo_saldo = self._get_saldo()
                    
                    # Embed de confirmação
                    embed_conf = discord.Embed(
                        title="✅ DEPÓSITO CONFIRMADO",
                        color=0x2ECC71
                    )
                    embed_conf.add_field(name="💵 Valor", value=f"R$ {valor:,.2f}", inline=True)
                    embed_conf.add_field(name="🎯 Motivo", value=motivo, inline=True)
                    embed_conf.add_field(name="💰 Novo Saldo", value=f"R$ {novo_saldo['total']:,.2f}", inline=False)
                    embed_conf.add_field(name="👤 Por", value=modal_interaction.user.mention, inline=False)
                    embed_conf.set_footer(text=datetime.now().strftime("%d/%m/%Y %H:%M:%S"))
                    
                    await modal_interaction.response.send_message(embed=embed_conf)
                except ValueError:
                    await modal_interaction.response.send_message("❌ Valor inválido!", ephemeral=True)
        
        modal = DepositoModal(title="💵 DEPOSITAR")
        await interaction.response.send_modal(modal)
    
    async def _modal_retirada(self, interaction: discord.Interaction):
        """Modal para retirada"""
        
        class RetiradaModal(discord.ui.Modal):
            valor_input = discord.ui.TextInput(
                label="Valor da Retirada",
                placeholder="Ex: 500.00",
                max_length=20
            )
            motivo_input = discord.ui.TextInput(
                label="Motivo da Retirada",
                placeholder="Ex: Pagamento de transportador",
                max_length=100
            )
            
            async def on_submit(modal_self, modal_interaction: discord.Interaction):
                try:
                    valor = float(modal_self.valor_input)
                    motivo = str(modal_self.motivo_input)
                    
                    if valor <= 0:
                        await modal_interaction.response.send_message("❌ Valor deve ser maior que zero!", ephemeral=True)
                        return
                    
                    saldo = self._get_saldo()
                    if saldo['total'] < valor:
                        await modal_interaction.response.send_message(f"❌ Saldo insuficiente! Você tem R$ {saldo['total']:,.2f}", ephemeral=True)
                        return
                    
                    # Adiciona transação
                    self._adicionar_transacao(
                        tipo="SAIDA",
                        valor=valor,
                        descricao=f"Retirada de R$ {valor:,.2f}",
                        motivo=motivo,
                        autor_id=modal_interaction.user.id
                    )
                    
                    novo_saldo = self._get_saldo()
                    
                    # Embed de confirmação
                    embed_conf = discord.Embed(
                        title="✅ RETIRADA CONFIRMADA",
                        color=0xE74C3C
                    )
                    embed_conf.add_field(name="💵 Valor", value=f"R$ {valor:,.2f}", inline=True)
                    embed_conf.add_field(name="🎯 Motivo", value=motivo, inline=True)
                    embed_conf.add_field(name="💰 Novo Saldo", value=f"R$ {novo_saldo['total']:,.2f}", inline=False)
                    embed_conf.add_field(name="👤 Por", value=modal_interaction.user.mention, inline=False)
                    embed_conf.set_footer(text=datetime.now().strftime("%d/%m/%Y %H:%M:%S"))
                    
                    await modal_interaction.response.send_message(embed=embed_conf)
                except ValueError:
                    await modal_interaction.response.send_message("❌ Valor inválido!", ephemeral=True)
        
        modal = RetiradaModal(title="💸 RETIRADA")
        await interaction.response.send_modal(modal)

async def setup(bot):
    await bot.add_cog(Financeiro(bot))
