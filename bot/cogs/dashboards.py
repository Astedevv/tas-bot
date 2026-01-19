"""
Dashboards - Relatórios e Configurações
Sistema de visualização de dados de transportes e configurações do bot
"""
import discord
from discord.ext import commands
from discord import app_commands
import sqlite3
from datetime import datetime
import asyncio
from bot.config import GUILD_ID
import sys
import os

# Adiciona o caminho do bot ao sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Importa config para valores
import config

class Dashboards(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.guild_id = GUILD_ID
        self.dashboard_relatorios_enviado = False
        self.dashboard_config_enviado = False
        self._init_tabelas()
    
    def _init_tabelas(self):
        """Inicializa tabelas se não existirem"""
        try:
            # Como a tabela de configurações pode ter conflito, vamos usar arquivo de config
            print("✅ Dashboards inicializados")
        except Exception as e:
            print(f"❌ Erro ao inicializar dashboards: {e}")
    
    def _get_stats_transporte(self):
        """Retorna estatísticas de transportes por status"""
        try:
            conn = db.get_connection()
            cursor = db.get_wrapped_cursor(conn)
            
            # Conta transportes por status
            # Assumindo que existe uma tabela de transportes com status
            
            # Concluídos
            cursor.execute("""
                SELECT COUNT(*) FROM transportes 
                WHERE status = 'concluido' OR status = 'CONCLUIDO'
            """)
            concluidos = cursor.fetchone()[0] or 0
            
            # Fila (criados/aguardando)
            cursor.execute("""
                SELECT COUNT(*) FROM transportes 
                WHERE status IN ('criado', 'CRIADO', 'fila', 'FILA')
            """)
            fila = cursor.fetchone()[0] or 0
            
            # Aguardando Pagamento
            cursor.execute("""
                SELECT COUNT(*) FROM transportes 
                WHERE status IN ('aguardando_pagamento', 'AGUARDANDO_PAGAMENTO', 'aguardando_pag')
            """)
            aguardando_pagamento = cursor.fetchone()[0] or 0
            
            # Pagos Esperando Transportar
            cursor.execute("""
                SELECT COUNT(*) FROM transportes 
                WHERE status IN ('pago', 'PAGO', 'em_transporte', 'EM_TRANSPORTE', 'aguardando_transporte')
            """)
            pagos_esperando = cursor.fetchone()[0] or 0
            
            conn.close()
            
            return {
                'concluidos': concluidos,
                'fila': fila,
                'aguardando_pagamento': aguardando_pagamento,
                'pagos_esperando': pagos_esperando,
                'total': concluidos + fila + aguardando_pagamento + pagos_esperando
            }
        except Exception as e:
            print(f"❌ Erro ao buscar stats: {e}")
            return {
                'concluidos': 0,
                'fila': 0,
                'aguardando_pagamento': 0,
                'pagos_esperando': 0,
                'total': 0
            }
    
    def _get_preco_por_milhao(self):
        """Retorna preço por milhão de prata configurado"""
        # Lê do arquivo config ou retorna valor padrão
        try:
            return getattr(config, 'PRECO_POR_MILHAO', 0.60)
        except:
            return 0.60
    
    def _set_preco_por_milhao(self, preco):
        """Atualiza preço por milhão de prata no config"""
        try:
            # Atualiza o config.py dinamicamente
            config_path = os.path.join(os.path.dirname(__file__), '../config.py')
            
            with open(config_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Encontra e substitui o valor
            import re
            content = re.sub(
                r'PRECO_POR_MILHAO = [\d.]+',
                f'PRECO_POR_MILHAO = {preco}',
                content
            )
            
            with open(config_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            # Recarrega o módulo config
            import importlib
            importlib.reload(config)
            
            return True
        except Exception as e:
            print(f"❌ Erro ao atualizar preço: {e}")
            return False
    
    async def _enviar_dashboard_relatorios(self, canal):
        """Envia dashboard de relatórios para o canal"""
        try:
            stats = self._get_stats_transporte()
            
            # Cores por status
            cores_status = {
                'concluidos': 0x2ECC71,  # Verde
                'fila': 0x3498DB,         # Azul
                'aguardando_pagamento': 0xF39C12,  # Laranja
                'pagos_esperando': 0x9B59B6        # Roxo
            }
            
            # Embed principal
            embed = discord.Embed(
                title="📊 DASHBOARD DE TRANSPORTES",
                description="Sistema de Análise de Operações de Transporte",
                color=0x1ABC9C  # Turquesa
            )
            
            # Estatísticas em grande destaque
            embed.add_field(
                name="✅ CONCLUÍDOS",
                value=f"```\n{stats['concluidos']}\n```",
                inline=True
            )
            
            embed.add_field(
                name="📋 FILA",
                value=f"```\n{stats['fila']}\n```",
                inline=True
            )
            
            embed.add_field(
                name="💰 AGUARDANDO PAGAMENTO",
                value=f"```\n{stats['aguardando_pagamento']}\n```",
                inline=True
            )
            
            embed.add_field(
                name="🚚 PAGO - AGUARDANDO TRANSPORTE",
                value=f"```\n{stats['pagos_esperando']}\n```",
                inline=True
            )
            
            # Total de operações
            embed.add_field(
                name="📈 TOTAL DE TRANSPORTES",
                value=f"```\n{stats['total']}\n```",
                inline=False
            )
            
            # Barra visual de progresso
            if stats['total'] > 0:
                percentual_concluidos = (stats['concluidos'] / stats['total']) * 100
                barra_tamanho = int(percentual_concluidos / 5)  # 20 caracteres max
                barra = "█" * barra_tamanho + "░" * (20 - barra_tamanho)
                embed.add_field(
                    name="📊 PROGRESSO DE CONCLUSÃO",
                    value=f"```{barra} {percentual_concluidos:.1f}%```",
                    inline=False
                )
            
            # Resumo operacional
            resumo = f"""
🟢 **Concluídos**: {stats['concluidos']} operações finalizadas
🔵 **Fila**: {stats['fila']} aguardando processamento
🟠 **Pagamento**: {stats['aguardando_pagamento']} aguardando confirmação
🟣 **Pronto**: {stats['pagos_esperando']} pronto para transportar
"""
            embed.add_field(
                name="📋 RESUMO OPERACIONAL",
                value=resumo,
                inline=False
            )
            
            embed.set_footer(text=f"Última atualização: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
            embed.set_thumbnail(url="https://cdn-icons-png.flaticon.com/512/2633/2633509.png")
            
            # Botões
            view = discord.ui.View(timeout=None)
            
            # Botão Atualizar
            btn_atualizar = discord.ui.Button(
                label="🔄 Atualizar",
                style=discord.ButtonStyle.secondary,
                custom_id="btn_atualizar_relatorios",
                emoji="🔄"
            )
            
            async def atualizar_callback(interaction: discord.Interaction):
                await interaction.response.defer()
                await self._enviar_dashboard_relatorios(canal)
            
            btn_atualizar.callback = atualizar_callback
            view.add_item(btn_atualizar)
            
            # Botão Detalhes
            btn_detalhes = discord.ui.Button(
                label="📋 Detalhes",
                style=discord.ButtonStyle.primary,
                custom_id="btn_detalhes_relatorios",
                emoji="📋"
            )
            
            async def detalhes_callback(interaction: discord.Interaction):
                stats_atualizadas = self._get_stats_transporte()
                
                embed_detalhes = discord.Embed(
                    title="📋 DETALHES DOS TRANSPORTES",
                    color=0x1ABC9C
                )
                
                embed_detalhes.add_field(
                    name="✅ CONCLUÍDOS",
                    value=f"{stats_atualizadas['concluidos']} operações finalizadas com sucesso",
                    inline=False
                )
                
                embed_detalhes.add_field(
                    name="📋 EM FILA",
                    value=f"{stats_atualizadas['fila']} transportes aguardando processamento",
                    inline=False
                )
                
                embed_detalhes.add_field(
                    name="💰 AGUARDANDO PAGAMENTO",
                    value=f"{stats_atualizadas['aguardando_pagamento']} transportes com pagamento pendente",
                    inline=False
                )
                
                embed_detalhes.add_field(
                    name="🚚 PAGOS - ESPERANDO TRANSPORTAR",
                    value=f"{stats_atualizadas['pagos_esperando']} transportes pagos e prontos",
                    inline=False
                )
                
                await interaction.response.send_message(embed=embed_detalhes, ephemeral=True)
            
            btn_detalhes.callback = detalhes_callback
            view.add_item(btn_detalhes)
            
            # Envia para o canal
            await canal.send(embed=embed, view=view)
            print("✅ Dashboard de relatórios enviado para o canal")
        except Exception as e:
            print(f"❌ Erro ao enviar dashboard de relatórios: {e}")
    
    async def _enviar_dashboard_config(self, canal):
        """Envia dashboard de configurações para o canal"""
        try:
            preco_atual = self._get_preco_por_milhao()
            taxa_alta_prioridade = preco_atual * (1 + 0.20)  # +20%
            
            # Embed de configuração
            embed = discord.Embed(
                title="⚙️ CONFIGURAÇÕES DO SISTEMA",
                description="Painel de Controle - Configuração Rápida de Preços",
                color=0xE74C3C  # Vermelho
            )
            
            embed.add_field(
                name="💵 PREÇO POR 1 MILHÃO DE PRATA",
                value=f"```\nR$ {preco_atual:.2f}\n```",
                inline=False
            )
            
            embed.add_field(
                name="⭐ TAXA ALTA PRIORIDADE (+20%)",
                value=f"```\nR$ {taxa_alta_prioridade:.2f}\n```",
                inline=False
            )
            
            # Exemplos de cálculo
            valor_minimo = 10_000_000
            exemplos = f"""
**Exemplos de taxa com R$ {preco_atual:.2f} por milhão:**
├─ 10M = R$ {(valor_minimo / 1_000_000) * preco_atual:.2f}
├─ 50M = R$ {(50_000_000 / 1_000_000) * preco_atual:.2f}
├─ 100M = R$ {(100_000_000 / 1_000_000) * preco_atual:.2f}
└─ 500M = R$ {(500_000_000 / 1_000_000) * preco_atual:.2f}

**Com Alta Prioridade (+20%):**
├─ 10M = R$ {(valor_minimo / 1_000_000) * taxa_alta_prioridade:.2f}
├─ 50M = R$ {(50_000_000 / 1_000_000) * taxa_alta_prioridade:.2f}
├─ 100M = R$ {(100_000_000 / 1_000_000) * taxa_alta_prioridade:.2f}
└─ 500M = R$ {(500_000_000 / 1_000_000) * taxa_alta_prioridade:.2f}
"""
            embed.add_field(
                name="📐 TABELA DE EXEMPLOS",
                value=exemplos,
                inline=False
            )
            
            embed.add_field(
                name="📝 INSTRUÇÕES",
                value="Clique nos botões abaixo para ajustar o preço por milhão\nSem necessidade de editar código!",
                inline=False
            )
            
            embed.set_footer(text=f"Última atualização: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
            embed.set_thumbnail(url="https://cdn-icons-png.flaticon.com/512/3050/3050159.png")
            
            # Botões
            view = discord.ui.View(timeout=None)
            
            # Botão Aumentar 0.05
            btn_aumentar = discord.ui.Button(
                label="➕ +R$ 0.05",
                style=discord.ButtonStyle.success,
                custom_id="btn_aumentar_milhao",
                emoji="➕"
            )
            
            async def aumentar_callback(interaction: discord.Interaction):
                novo_preco = preco_atual + 0.05
                if self._set_preco_por_milhao(novo_preco):
                    await interaction.response.send_message(
                        f"✅ Preço atualizado para **R$ {novo_preco:.2f}/milhão**",
                        ephemeral=True
                    )
                    await self._enviar_dashboard_config(canal)
                else:
                    await interaction.response.send_message("❌ Erro ao atualizar preço", ephemeral=True)
            
            btn_aumentar.callback = aumentar_callback
            view.add_item(btn_aumentar)
            
            # Botão Diminuir 0.05
            btn_diminuir = discord.ui.Button(
                label="➖ -R$ 0.05",
                style=discord.ButtonStyle.danger,
                custom_id="btn_diminuir_milhao",
                emoji="➖"
            )
            
            async def diminuir_callback(interaction: discord.Interaction):
                novo_preco = max(0.05, preco_atual - 0.05)  # Mínimo R$ 0.05
                if self._set_preco_por_milhao(novo_preco):
                    await interaction.response.send_message(
                        f"✅ Preço atualizado para **R$ {novo_preco:.2f}/milhão**",
                        ephemeral=True
                    )
                    await self._enviar_dashboard_config(canal)
                else:
                    await interaction.response.send_message("❌ Erro ao atualizar preço", ephemeral=True)
            
            btn_diminuir.callback = diminuir_callback
            view.add_item(btn_diminuir)
            
            # Botão Editar Customizado
            btn_editar = discord.ui.Button(
                label="✏️ Editar Valor",
                style=discord.ButtonStyle.primary,
                custom_id="btn_editar_milhao",
                emoji="✏️"
            )
            
            async def editar_callback(interaction: discord.Interaction):
                await self._modal_editar_preco(interaction)
            
            btn_editar.callback = editar_callback
            view.add_item(btn_editar)
            
            # Envia para o canal
            await canal.send(embed=embed, view=view)
            print("✅ Dashboard de configurações enviado para o canal")
        except Exception as e:
            print(f"❌ Erro ao enviar dashboard de config: {e}")
    
    async def _modal_editar_preco(self, interaction: discord.Interaction):
        """Modal para editar preço customizado"""
        
        class PrecoModal(discord.ui.Modal):
            preco_input = discord.ui.TextInput(
                label="Novo Preço por Milhão (R$)",
                placeholder="Ex: 0.75",
                max_length=10
            )
            
            async def on_submit(modal_self, modal_interaction: discord.Interaction):
                try:
                    novo_preco = float(modal_self.preco_input)
                    
                    if novo_preco < 0.05:
                        await modal_interaction.response.send_message(
                            "❌ Preço mínimo é R$ 0.05",
                            ephemeral=True
                        )
                        return
                    
                    if novo_preco > 10:
                        await modal_interaction.response.send_message(
                            "❌ Preço máximo é R$ 10.00",
                            ephemeral=True
                        )
                        return
                    
                    # Atualiza preço
                    if self._set_preco_por_milhao(novo_preco):
                        embed_conf = discord.Embed(
                            title="✅ PREÇO ATUALIZADO",
                            color=0x2ECC71
                        )
                        embed_conf.add_field(
                            name="💵 Novo Valor",
                            value=f"R$ {novo_preco:.2f}/milhão",
                            inline=False
                        )
                        
                        taxa_alta = novo_preco * 1.20
                        embed_conf.add_field(
                            name="⭐ Alta Prioridade (+20%)",
                            value=f"R$ {taxa_alta:.2f}/milhão",
                            inline=False
                        )
                        
                        await modal_interaction.response.send_message(embed=embed_conf, ephemeral=True)
                        
                        # Reenvia o dashboard atualizado
                        guild = modal_interaction.guild
                        for ch in guild.channels:
                            if "config" in ch.name.lower() and isinstance(ch, discord.TextChannel):
                                await self._enviar_dashboard_config(ch)
                                break
                    else:
                        await modal_interaction.response.send_message(
                            "❌ Erro ao atualizar preço",
                            ephemeral=True
                        )
                except ValueError:
                    await modal_interaction.response.send_message(
                        "❌ Valor inválido! Use formato: 0.75",
                        ephemeral=True
                    )
        
        modal = PrecoModal(title="💵 EDITAR PREÇO POR MILHÃO")
        await interaction.response.send_modal(modal)
    
    @commands.Cog.listener()
    async def on_ready(self):
        """Envia dashboards quando bot inicia"""
        # Dashboard de Relatórios
        if not self.dashboard_relatorios_enviado:
            await asyncio.sleep(3)
            try:
                guild = self.bot.get_guild(self.guild_id)
                if guild:
                    for ch in guild.channels:
                        if "relatorio" in ch.name.lower() and isinstance(ch, discord.TextChannel):
                            await self._enviar_dashboard_relatorios(ch)
                            self.dashboard_relatorios_enviado = True
                            break
            except Exception as e:
                print(f"❌ Erro ao enviar dashboard de relatórios: {e}")
        
        # Dashboard de Configurações
        if not self.dashboard_config_enviado:
            await asyncio.sleep(3)
            try:
                guild = self.bot.get_guild(self.guild_id)
                if guild:
                    for ch in guild.channels:
                        if "config" in ch.name.lower() and isinstance(ch, discord.TextChannel):
                            await self._enviar_dashboard_config(ch)
                            self.dashboard_config_enviado = True
                            break
            except Exception as e:
                print(f"❌ Erro ao enviar dashboard de config: {e}")
    
    @app_commands.command(name="enviar_relatorios", description="Envia dashboard de relatórios")
    @app_commands.guild_only()
    async def enviar_relatorios(self, interaction: discord.Interaction):
        """Envia dashboard de relatórios para o canal"""
        try:
            guild = interaction.guild
            
            for ch in guild.channels:
                if "relatorio" in ch.name.lower() and isinstance(ch, discord.TextChannel):
                    await self._enviar_dashboard_relatorios(ch)
                    await interaction.response.send_message("✅ Dashboard de relatórios enviado!", ephemeral=True)
                    return
            
            await interaction.response.send_message("❌ Canal de relatórios não encontrado!", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ Erro: {e}", ephemeral=True)
    
    @app_commands.command(name="enviar_config", description="Envia dashboard de configurações")
    @app_commands.guild_only()
    async def enviar_config(self, interaction: discord.Interaction):
        """Envia dashboard de configurações para o canal"""
        try:
            guild = interaction.guild
            
            for ch in guild.channels:
                if "config" in ch.name.lower() and isinstance(ch, discord.TextChannel):
                    await self._enviar_dashboard_config(ch)
                    await interaction.response.send_message("✅ Dashboard de config enviado!", ephemeral=True)
                    return
            
            await interaction.response.send_message("❌ Canal de config não encontrado!", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ Erro: {e}", ephemeral=True)

async def setup(bot):
    await bot.add_cog(Dashboards(bot))
