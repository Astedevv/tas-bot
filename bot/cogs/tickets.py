"""
Cog: Sistema de Tickets
"""
import discord
from discord.ext import commands
from bot.database import db
from bot.config import (
    PRECO_BASE, VALOR_MINIMO, TAXA_ALTA_PRIORIDADE, PIX_KEY, 
    STATUS, ORIGENS, DESTINO_PADRAO
)
from bot.utils.embeds import (
    criar_embed_resumo_transporte, criar_embed_transporte
)
from bot.utils.buttons import (
    BotaoOrigem, BotaoPrioridade, ModalValor, ModalObservacoes,
    ViewConfirmarDeposito, ModalConfirmarDeposito
)
from bot.utils.validators import validar_valor_prata, calcular_taxa

class TicketsCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.ticket_counter = 0
        self.user_sessions = {}  # Armazena estado de cada usuário
    
    @commands.Cog.listener()
    async def on_ready(self):
        """Evento quando bot conecta"""
        print(f"✅ Cog Tickets carregado")
        
        # Restaura o contador do banco
        conn = db.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM transportes")
        self.ticket_counter = cursor.fetchone()[0]
        conn.close()
    
    @commands.Cog.listener()
    async def on_button_click(self, interaction: discord.Interaction):
        """Listener para cliques em botões"""
        
        # Abrir novo ticket
        if interaction.data.get('custom_id') == 'btn_abrir_ticket':
            await self.abrir_ticket(interaction)
        
        # Confirmar depósito
        elif interaction.data.get('custom_id') == 'btn_confirmar_dep':
            await self.modal_confirmar_deposito(interaction)
        
        # Cancelar depósito
        elif interaction.data.get('custom_id') == 'btn_cancelar_dep':
            await interaction.response.send_message(
                "❌ Operação cancelada.",
                ephemeral=True
            )
    
    async def abrir_ticket(self, interaction: discord.Interaction):
        """Abre um novo ticket para o usuário"""
        
        # Cria canal privado para o ticket
        try:
            # Cria cliente se não existir
            cliente = db.get_or_create_cliente(
                str(interaction.user.id),
                interaction.user.name
            )
            
            # Gera próximo número de ticket
            self.ticket_counter += 1
            numero_ticket = 1000 + self.ticket_counter
            
            # Cria canal privado
            guild = interaction.guild
            overwrites = {
                guild.default_role: discord.PermissionOverwrite(view_channel=False),
                interaction.user: discord.PermissionOverwrite(view_channel=True, send_messages=True),
            }
            
            # Adiciona staff se tiver permissão
            for member in guild.members:
                if any(role.name.startswith("💼") or role.name.startswith("👑") for role in member.roles):
                    overwrites[member] = discord.PermissionOverwrite(view_channel=True, send_messages=True)
            
            canal_ticket = await guild.create_text_channel(
                name=f"ticket-transport-{numero_ticket:04d}",
                category=None,  # Root level
                overwrites=overwrites,
                topic=f"Ticket de transporte #{numero_ticket:04d} | Cliente: {interaction.user.name}"
            )
            
            # Salva sessão do usuário
            self.user_sessions[interaction.user.id] = {
                'numero_ticket': numero_ticket,
                'canal_ticket': canal_ticket.id,
                'cliente_id': cliente['id'],
                'origem': None,
                'prioridade': None,
                'valor': None,
                'print_item': None,
                'obs': None,
                'transporte_id': None
            }
            
            # Responde ao usuário
            embed_welcome = discord.Embed(
                title=f"🎫 TICKET ABERTO - #{numero_ticket:04d}",
                description="Bem-vindo! Vamos preencher as informações do seu transporte.",
                color=0x3498DB
            )
            embed_welcome.add_field(
                name="⏳ Próximo passo",
                value="Escolha a cidade de origem",
                inline=False
            )
            
            await interaction.response.send_message(
                embed=embed_welcome,
                ephemeral=True
            )
            
            # Envia primeira mensagem no canal
            await canal_ticket.send(f"👋 Olá {interaction.user.mention}! Vamos começar...")
            
            # Pergunta 1: Origem
            await self.pedir_origem(interaction, numero_ticket, canal_ticket)
            
        except Exception as e:
            await interaction.response.send_message(
                f"❌ Erro ao criar ticket: {str(e)}",
                ephemeral=True
            )
    
    async def pedir_origem(self, interaction: discord.Interaction, numero_ticket: int, canal_ticket):
        """Pede a origem do transporte"""
        
        embed = discord.Embed(
            title="📍 Escolha a Origem",
            description="De qual cidade você quer transportar?",
            color=0x3498DB
        )
        
        # Create select menu
        class SelectOrigem(discord.ui.Select):
            def __init__(self, callback):
                options = [
                    discord.SelectOption(label=origem, value=origem)
                    for origem in ORIGENS
                ]
                super().__init__(
                    placeholder="Selecione a origem...",
                    min_values=1,
                    max_values=1,
                    options=options,
                    custom_id=f"select_origem_{numero_ticket}"
                )
                self.callback_func = callback
            
            async def callback(self, inter: discord.Interaction):
                await self.callback_func(inter, self.values[0])
        
        view = discord.ui.View()
        view.add_item(SelectOrigem(self.processar_origem))
        
        await canal_ticket.send(embed=embed, view=view)
    
    async def processar_origem(self, interaction: discord.Interaction, origem: str):
        """Processa a origem escolhida"""
        
        await interaction.response.defer(ephemeral=True)
        
        # Atualiza sessão
        session = self.user_sessions.get(interaction.user.id)
        if session:
            session['origem'] = origem
            
            # Envia confirmação
            embed_conf = discord.Embed(
                title="✅ Origem Confirmada",
                description=f"Saindo de: **{origem}**",
                color=0x2ECC71
            )
            await interaction.followup.send(embed=embed_conf, ephemeral=True)
            
            # Próxima pergunta
            await self.pedir_prioridade(interaction)
    
    async def pedir_prioridade(self, interaction: discord.Interaction):
        """Pede a prioridade do transporte"""
        
        canal_id = self.user_sessions[interaction.user.id]['canal_ticket']
        canal = self.bot.get_channel(canal_id)
        
        embed = discord.Embed(
            title="⚡ Qual é a Prioridade?",
            description="Normal: Entrega em até 2 horas\nAlta: +20% na taxa, prioridade máxima",
            color=0xF39C12
        )
        
        view = discord.ui.View()
        
        async def callback_normal(inter):
            await self.processar_prioridade(inter, "NORMAL")
        
        async def callback_alta(inter):
            await self.processar_prioridade(inter, "ALTA")
        
        btn_normal = discord.ui.Button(
            label="🕒 Normal",
            style=discord.ButtonStyle.gray,
            custom_id="btn_normal"
        )
        btn_normal.callback = callback_normal
        
        btn_alta = discord.ui.Button(
            label="⚡ Alta (+20%)",
            style=discord.ButtonStyle.danger,
            custom_id="btn_alta"
        )
        btn_alta.callback = callback_alta
        
        view.add_item(btn_normal)
        view.add_item(btn_alta)
        
        await canal.send(embed=embed, view=view)
    
    async def processar_prioridade(self, interaction: discord.Interaction, prioridade: str):
        """Processa a prioridade escolhida"""
        
        await interaction.response.defer(ephemeral=True)
        
        session = self.user_sessions.get(interaction.user.id)
        if session:
            session['prioridade'] = prioridade
            
            emoji = "⚡" if prioridade == "ALTA" else "🕒"
            embed_conf = discord.Embed(
                title="✅ Prioridade Confirmada",
                description=f"Prioridade: **{emoji} {prioridade}**",
                color=0x2ECC71
            )
            await interaction.followup.send(embed=embed_conf, ephemeral=True)
            
            # Próxima pergunta
            await self.pedir_valor(interaction)
    
    async def pedir_valor(self, interaction: discord.Interaction):
        """Pede o valor estimado"""
        
        canal_id = self.user_sessions[interaction.user.id]['canal_ticket']
        canal = self.bot.get_channel(canal_id)
        
        embed = discord.Embed(
            title="💰 Valor Estimado",
            description=f"Qual é o valor aproximado da carga em prata? (Mínimo: {VALOR_MINIMO:,})",
            color=0x3498DB
        )
        
        class ModalValor(discord.ui.Modal):
            def __init__(self, cog):
                super().__init__(title="Valor da Carga", custom_id="modal_valor_ticket")
                self.cog = cog
                self.valor_input = discord.ui.TextInput(
                    label="Valor em prata (ex: 18500000)",
                    placeholder="Apenas números",
                    required=True,
                    min_length=2,
                    max_length=20
                )
                self.add_item(self.valor_input)
            
            async def on_submit(self, inter: discord.Interaction):
                await self.cog.processar_valor(inter, self.valor_input.value)
        
        view = discord.ui.View()
        
        async def open_modal(inter):
            await inter.response.send_modal(ModalValor(self))
        
        btn = discord.ui.Button(
            label="Inserir Valor",
            style=discord.ButtonStyle.primary,
            custom_id="btn_valor"
        )
        btn.callback = open_modal
        view.add_item(btn)
        
        await canal.send(embed=embed, view=view)
    
    async def processar_valor(self, interaction: discord.Interaction, valor_text: str):
        """Processa o valor inserido"""
        
        valido, valor = validar_valor_prata(valor_text, VALOR_MINIMO)
        
        if not valido:
            await interaction.response.send_message(
                f"❌ Valor inválido! Mínimo: {VALOR_MINIMO:,}",
                ephemeral=True
            )
            return
        
        await interaction.response.defer(ephemeral=True)
        
        session = self.user_sessions.get(interaction.user.id)
        if session:
            session['valor'] = valor
            
            valor_em_milhoes = valor / 1_000_000
            embed_conf = discord.Embed(
                title="✅ Valor Confirmado",
                description=f"Valor: **~{valor_em_milhoes:.1f}M prata**",
                color=0x2ECC71
            )
            await interaction.followup.send(embed=embed_conf, ephemeral=True)
            
            # Próxima pergunta
            await self.pedir_print(interaction)
    
    async def pedir_print(self, interaction: discord.Interaction):
        """Pede o print dos items"""
        
        canal_id = self.user_sessions[interaction.user.id]['canal_ticket']
        canal = self.bot.get_channel(canal_id)
        
        embed = discord.Embed(
            title="📸 Print dos Items",
            description="Por segurança, envie um print do seu inventário/baú mostrando os items a transportar.",
            color=0x3498DB
        )
        
        await canal.send(embed=embed)
        await canal.send(
            "⏳ Aguardando upload de imagem... (máx 10MB, formatos: PNG, JPG, GIF)"
        )
    
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        """Listener para mensagens (detecta imagens nos tickets)"""
        
        if message.author.bot:
            return
        
        # Verifica se é um ticket
        if not message.channel.name.startswith("ticket-transport-"):
            return
        
        session = self.user_sessions.get(message.author.id)
        if not session:
            return
        
        # Se aguardando print
        if session['print_item'] is None and message.attachments:
            from bot.utils.validators import validar_imagem
            
            attachment = message.attachments[0]
            
            # Valida imagem
            if await validar_imagem(attachment):
                session['print_item'] = attachment.url
                
                embed_conf = discord.Embed(
                    title="✅ Print Recebido",
                    description="Imagem validada com sucesso!",
                    color=0x2ECC71
                )
                await message.reply(embed=embed_conf)
                
                # Próxima pergunta
                await self.pedir_observacoes(message)
            else:
                embed_erro = discord.Embed(
                    title="❌ Print Inválido",
                    description="A imagem deve ser válida e ter até 10MB",
                    color=0xE74C3C
                )
                await message.reply(embed=embed_erro)
    
    async def pedir_observacoes(self, message: discord.Message):
        """Pede observações opcionais"""
        
        embed = discord.Embed(
            title="📝 Observações (Opcional)",
            description="Tem algo especial que devemos saber?\n"
                       "Ex: Peso alto, itens refinados, Black Market, etc",
            color=0x3498DB
        )
        
        view = discord.ui.View()
        
        class ModalObs(discord.ui.Modal):
            def __init__(self, cog):
                super().__init__(title="Observações", custom_id="modal_obs")
                self.cog = cog
                self.obs_input = discord.ui.TextInput(
                    label="Observações",
                    placeholder="Digite aqui... (opcional)",
                    required=False,
                    max_length=500,
                    style=discord.TextStyle.paragraph
                )
                self.add_item(self.obs_input)
            
            async def on_submit(self, inter: discord.Interaction):
                await self.cog.processar_observacoes(inter, self.obs_input.value or "Nenhuma")
        
        async def open_modal(inter):
            await inter.response.send_modal(ModalObs(self))
        
        btn = discord.ui.Button(
            label="Adicionar Observações",
            style=discord.ButtonStyle.primary,
            custom_id="btn_obs"
        )
        btn.callback = open_modal
        view.add_item(btn)
        
        await message.channel.send(embed=embed, view=view)
    
    async def processar_observacoes(self, interaction: discord.Interaction, obs: str):
        """Processa observações e gera resumo"""
        
        await interaction.response.defer(ephemeral=True)
        
        session = self.user_sessions.get(interaction.user.id)
        if not session:
            return
        
        session['obs'] = obs
        
        # Calcula taxa
        prioridade = session['prioridade']
        taxa = calcular_taxa(
            session['valor'],
            prioridade,
            PRECO_BASE,
            TAXA_ALTA_PRIORIDADE
        )
        
        # Cria transporte no banco
        transporte = db.create_transporte(
            cliente_id=session['cliente_id'],
            origem=session['origem'],
            valor_estimado=session['valor'],
            prioridade=prioridade,
            taxa_final=taxa,
            ticket_channel_id=session['canal_ticket']
        )
        
        session['transporte_id'] = transporte['id']
        
        # Envia resumo
        canal_id = session['canal_ticket']
        canal = self.bot.get_channel(canal_id)
        
        embed_resumo = criar_embed_resumo_transporte(
            numero_ticket=transporte['numero_ticket'],
            origem=session['origem'],
            valor_estimado=session['valor'],
            prioridade=prioridade,
            taxa_final=taxa,
            pix_key=PIX_KEY
        )
        
        if obs != "Nenhuma":
            embed_resumo.add_field(
                name="📝 Observações",
                value=obs,
                inline=False
            )
        
        # Botões de ação
        view = ViewConfirmarDeposito(self.callback_confirmar_deposito)
        
        await canal.send(embed=embed_resumo, view=view)
        
        embed_prox = discord.Embed(
            title="📋 Próximos Passos",
            description="1️⃣ Faça o PIX conforme acima\n"
                       "2️⃣ Envie o comprovante neste canal\n"
                       "3️⃣ Nós validaremos manualmente\n"
                       "4️⃣ Você confirmará o depósito dos items na island",
            color=0x3498DB
        )
        await canal.send(embed=embed_prox)
    
    async def callback_confirmar_deposito(self, interaction: discord.Interaction, confirmado: bool):
        """Callback do botão de confirmar depósito"""
        
        if not confirmado:
            await interaction.response.send_message(
                "❌ Operação cancelada.",
                ephemeral=True
            )
            return
        
        # Pede para enviar comprovante de PIX
        embed = discord.Embed(
            title="💳 Envie o Comprovante de PIX",
            description="Faça um print do seu comprovante de PIX e envie neste canal.\n\n"
                       "Será necessário para validarmos o pagamento.",
            color=0x3498DB
        )
        
        await interaction.response.send_message(
            embed=embed,
            ephemeral=True
        )

async def setup(bot):
    await bot.add_cog(TicketsCog(bot))
