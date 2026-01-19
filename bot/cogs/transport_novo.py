"""
Cog: Sistema de Transporte com Fluxo Completo
Fluxo:
1. Perguntar nick do jogador
2. Coleta origem, prioridade, valor, print
3. Resumo e botão para confirmar (vai para pagamento)
4. Pagamento: Cliente faz PIX e envia comprovante
5. Validação: Staff aprova/rejeita
6. Liberação: Staff confirma acesso e envia local
7. Depósito: Cliente confirma que depositou items
8. Fila: Aguarda transporte
9. Transporte: Staff inicia e confirma
10. Entrega: Staff confirma e envia local
11. Retirada: Cliente confirma retirada (fim)
"""
import discord
from discord.ext import commands
from database import db
from config import PRECO_BASE, VALOR_MINIMO, TAXA_ALTA_PRIORIDADE, PIX_KEY, STATUS, ORIGENS
from utils.validators import calcular_taxa

class ModalNick(discord.ui.Modal):
    def __init__(self, callback):
        super().__init__(title="Seu Nick no Jogo", custom_id="modal_nick")
        self.callback_func = callback
        self.nick_input = discord.ui.TextInput(
            label="Digite seu nick exatamente como aparece no jogo",
            placeholder="Ex: Player#123",
            required=True,
            min_length=3,
            max_length=30
        )
        self.add_item(self.nick_input)
    
    async def on_submit(self, interaction: discord.Interaction):
        await self.callback_func(interaction, self.nick_input.value)

class TransporteCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.user_sessions = {}
        self.ticket_counter = 0
    
    @commands.Cog.listener()
    async def on_ready(self):
        print("✅ Cog Transport (novo fluxo) carregado")
        
        # Restaura contador
        conn = db.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM transportes")
        self.ticket_counter = cursor.fetchone()[0]
        conn.close()
    
    async def abrir_ticket(self, interaction: discord.Interaction):
        """Abre novo ticket e pergunta nick do jogador"""
        
        try:
            # Cria cliente
            cliente = db.get_or_create_cliente(
                str(interaction.user.id),
                interaction.user.name
            )
            
            # Gera número
            self.ticket_counter += 1
            numero_ticket = 1000 + self.ticket_counter
            
            # Cria canal privado
            guild = interaction.guild
            overwrites = {
                guild.default_role: discord.PermissionOverwrite(view_channel=False),
                interaction.user: discord.PermissionOverwrite(view_channel=True, send_messages=True),
            }
            
            # Adiciona staff
            for member in guild.members:
                if any(role.name.startswith("💼") or role.name.startswith("👑") for role in member.roles):
                    overwrites[member] = discord.PermissionOverwrite(view_channel=True, send_messages=True)
            
            canal_ticket = await guild.create_text_channel(
                name=f"ticket-transport-{numero_ticket:04d}",
                category=None,
                overwrites=overwrites,
                topic=f"Ticket #{numero_ticket:04d} | {interaction.user.name}"
            )
            
            # Inicializa sessão
            self.user_sessions[interaction.user.id] = {
                'numero_ticket': numero_ticket,
                'canal_ticket': canal_ticket.id,
                'cliente_id': cliente['id'],
                'nick_jogo': None,
                'origem': None,
                'prioridade': None,
                'valor': None,
                'obs': None,
                'status': 'COLETANDO_NICK'
            }
            
            # Responde ao usuário
            embed_welcome = discord.Embed(
                title=f"🎫 TICKET ABERTO - #{numero_ticket:04d}",
                description="Canal privado criado para seu transporte",
                color=0x3498DB
            )
            await interaction.response.send_message(embed=embed_welcome, ephemeral=True)
            
            # Envia no canal
            await canal_ticket.send(f"👋 Olá {interaction.user.mention}! Bem-vindo ao T.A.S Mania")
            
            # Pede nick
            await self.pedir_nick(interaction.user.id, canal_ticket)
            
        except Exception as e:
            print(f"❌ Erro ao abrir ticket: {e}")
            import traceback
            traceback.print_exc()
    
    async def pedir_nick(self, user_id, canal):
        """Pede o nick do jogador"""
        
        embed = discord.Embed(
            title="🎮 Qual é seu nick no jogo?",
            description="Digite exatamente como aparece no seu personagem",
            color=0x3498DB
        )
        
        modal = ModalNick(lambda inter, nick: self.processar_nick(inter, user_id, nick))
        
        # Cria um botão para abrir o modal
        view = discord.ui.View()
        
        async def abrir_modal(inter):
            await inter.response.send_modal(modal)
        
        btn = discord.ui.Button(
            label="Inserir Nick",
            style=discord.ButtonStyle.primary,
            custom_id="btn_nick"
        )
        btn.callback = abrir_modal
        view.add_item(btn)
        
        await canal.send(embed=embed, view=view)
    
    async def processar_nick(self, interaction: discord.Interaction, user_id, nick):
        """Processa o nick inserido"""
        
        await interaction.response.defer(ephemeral=True)
        
        session = self.user_sessions.get(user_id)
        if not session:
            return
        
        session['nick_jogo'] = nick
        session['status'] = 'COLETANDO_ORIGEM'
        
        embed_conf = discord.Embed(
            title="✅ Nick Confirmado",
            description=f"Nick em jogo: **{nick}**",
            color=0x2ECC71
        )
        await interaction.followup.send(embed=embed_conf, ephemeral=True)
        
        # Próxima pergunta
        canal = self.bot.get_channel(session['canal_ticket'])
        if canal:
            await self.pedir_origem(user_id, canal)
    
    async def pedir_origem(self, user_id, canal):
        """Pede a origem do transporte"""
        
        embed = discord.Embed(
            title="📍 Qual é a origem?",
            description="De qual cidade você quer transportar?",
            color=0x3498DB
        )
        
        class SelectOrigem(discord.ui.Select):
            def __init__(self, callback):
                options = [discord.SelectOption(label=o, value=o) for o in ORIGENS]
                super().__init__(
                    placeholder="Selecione a origem...",
                    min_values=1,
                    max_values=1,
                    options=options
                )
                self.cb = callback
            
            async def callback(self, inter: discord.Interaction):
                await self.cb(inter, self.values[0])
        
        view = discord.ui.View()
        view.add_item(SelectOrigem(lambda inter, orig: self.processar_origem(inter, user_id, orig)))
        
        await canal.send(embed=embed, view=view)
    
    async def processar_origem(self, interaction: discord.Interaction, user_id, origem):
        """Processa origem"""
        
        await interaction.response.defer(ephemeral=True)
        
        session = self.user_sessions.get(user_id)
        if session:
            session['origem'] = origem
            session['status'] = 'COLETANDO_PRIORIDADE'
            
            embed = discord.Embed(
                title="✅ Origem Confirmada",
                description=f"Saindo de: **{origem}**",
                color=0x2ECC71
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
            
            canal = self.bot.get_channel(session['canal_ticket'])
            if canal:
                await self.pedir_prioridade(user_id, canal)
    
    async def pedir_prioridade(self, user_id, canal):
        """Pede prioridade"""
        
        embed = discord.Embed(
            title="⚡ Qual é a prioridade?",
            description="Normal: até 2 horas\nAlta: +20% na taxa, máxima prioridade",
            color=0xF39C12
        )
        
        view = discord.ui.View()
        
        async def callback_normal(inter):
            await self.processar_prioridade(inter, user_id, "NORMAL")
        
        async def callback_alta(inter):
            await self.processar_prioridade(inter, user_id, "ALTA")
        
        btn_normal = discord.ui.Button(label="🕒 Normal", style=discord.ButtonStyle.gray)
        btn_alta = discord.ui.Button(label="⚡ Alta (+20%)", style=discord.ButtonStyle.danger)
        
        btn_normal.callback = callback_normal
        btn_alta.callback = callback_alta
        
        view.add_item(btn_normal)
        view.add_item(btn_alta)
        
        await canal.send(embed=embed, view=view)
    
    async def processar_prioridade(self, inter, user_id, prioridade):
        """Processa prioridade"""
        
        await inter.response.defer(ephemeral=True)
        
        session = self.user_sessions.get(user_id)
        if session:
            session['prioridade'] = prioridade
            session['status'] = 'COLETANDO_VALOR'
            
            await inter.followup.send(
                f"✅ Prioridade: **{prioridade}**",
                ephemeral=True
            )
            
            canal = self.bot.get_channel(session['canal_ticket'])
            if canal:
                await self.pedir_valor(user_id, canal)
    
    async def pedir_valor(self, user_id, canal):
        """Pede valor estimado"""
        
        embed = discord.Embed(
            title="💰 Valor Estimado",
            description=f"Qual é o valor aproximado em prata? (Mínimo: {VALOR_MINIMO:,})",
            color=0x3498DB
        )
        
        view = discord.ui.View()
        
        class ModalValor(discord.ui.Modal):
            def __init__(self, cog, user_id):
                super().__init__(title="Valor", custom_id="modal_valor_transport")
                self.cog = cog
                self.user_id = user_id
                self.valor = discord.ui.TextInput(
                    label="Valor em prata",
                    placeholder="Ex: 18500000",
                    required=True
                )
                self.add_item(self.valor)
            
            async def on_submit(self, inter: discord.Interaction):
                try:
                    valor = int(self.valor.value.replace(".", "").replace(",", ""))
                    if valor < VALOR_MINIMO:
                        await inter.response.send_message(
                            f"❌ Mínimo: {VALOR_MINIMO:,}",
                            ephemeral=True
                        )
                        return
                    await self.cog.processar_valor(inter, self.user_id, valor)
                except:
                    await inter.response.send_message(
                        "❌ Valor inválido",
                        ephemeral=True
                    )
        
        async def abrir_modal(inter):
            await inter.response.send_modal(ModalValor(self, user_id))
        
        btn = discord.ui.Button(label="Inserir Valor")
        btn.callback = abrir_modal
        view.add_item(btn)
        
        await canal.send(embed=embed, view=view)
    
    async def processar_valor(self, inter, user_id, valor):
        """Processa valor"""
        
        await inter.response.defer(ephemeral=True)
        
        session = self.user_sessions.get(user_id)
        if session:
            session['valor'] = valor
            session['status'] = 'COLETANDO_OBS'
            
            await inter.followup.send(
                f"✅ Valor: **{valor:,.0f} prata**",
                ephemeral=True
            )
            
            canal = self.bot.get_channel(session['canal_ticket'])
            if canal:
                await self.pedir_observacoes(user_id, canal)
    
    async def pedir_observacoes(self, user_id, canal):
        """Pede observações opcionais"""
        
        embed = discord.Embed(
            title="📝 Observações (opcional)",
            description="Algo especial que devemos saber?",
            color=0x3498DB
        )
        
        view = discord.ui.View()
        
        class ModalObs(discord.ui.Modal):
            def __init__(self, cog, user_id):
                super().__init__(title="Observações", custom_id="modal_obs_transport")
                self.cog = cog
                self.user_id = user_id
                self.obs = discord.ui.TextInput(
                    label="Observações",
                    required=False,
                    max_length=500,
                    style=discord.TextStyle.paragraph
                )
                self.add_item(self.obs)
            
            async def on_submit(self, inter: discord.Interaction):
                await self.cog.processar_observacoes(inter, self.user_id, self.obs.value or "Nenhuma")
        
        async def abrir_modal(inter):
            await inter.response.send_modal(ModalObs(self, user_id))
        
        btn = discord.ui.Button(label="Adicionar Observações")
        btn.callback = abrir_modal
        view.add_item(btn)
        
        await canal.send(embed=embed, view=view)
    
    async def processar_observacoes(self, inter, user_id, obs):
        """Processa observações e envia resumo final"""
        
        await inter.response.defer(ephemeral=True)
        
        session = self.user_sessions.get(user_id)
        if not session:
            return
        
        session['obs'] = obs
        session['status'] = 'AGUARDANDO_PAGAMENTO'
        
        # Calcula taxa
        taxa = calcular_taxa(
            session['valor'],
            session['prioridade'],
            PRECO_BASE,
            TAXA_ALTA_PRIORIDADE
        )
        
        # Cria transporte no banco
        transporte = db.create_transporte(
            cliente_id=session['cliente_id'],
            origem=session['origem'],
            valor_estimado=session['valor'],
            prioridade=session['prioridade'],
            taxa_final=taxa,
            ticket_channel_id=session['canal_ticket']
        )
        
        session['transporte_id'] = transporte['id']
        
        # Atualiza nick e obs no banco
        db.update_transporte(
            transporte['id'],
            notas=f"Nick: {session['nick_jogo']}\nObs: {obs}"
        )
        
        await inter.followup.send("✅ Resumo criado!", ephemeral=True)
        
        # Envia resumo no canal
        canal = self.bot.get_channel(session['canal_ticket'])
        if canal:
            embed_resumo = discord.Embed(
                title="✅ TRANSPORTE CRIADO",
                color=0x2ECC71
            )
            embed_resumo.add_field(name="🎫 Ticket", value=f"#{transporte['numero_ticket']:04d}")
            embed_resumo.add_field(name="🎮 Nick", value=session['nick_jogo'])
            embed_resumo.add_field(name="📍 Origem", value=session['origem'])
            embed_resumo.add_field(name="💰 Valor", value=f"{session['valor']:,.0f} prata")
            embed_resumo.add_field(name="⚡ Prioridade", value=session['prioridade'])
            embed_resumo.add_field(name="💵 Taxa", value=f"R$ {taxa:.2f}")
            
            if obs != "Nenhuma":
                embed_resumo.add_field(name="📝 Observações", value=obs, inline=False)
            
            embed_resumo.add_field(name="💳 PIX", value=PIX_KEY, inline=False)
            
            await canal.send(embed=embed_resumo)
            
            # Instruções de pagamento
            embed_pag = discord.Embed(
                title="💳 PAGAMENTO",
                color=0xF39C12
            )
            embed_pag.add_field(name="1️⃣", value="Faça o PIX conforme acima", inline=False)
            embed_pag.add_field(name="2️⃣", value="Envie a imagem do comprovante neste canal", inline=False)
            embed_pag.add_field(name="3️⃣", value="Clique no botão para confirmar", inline=False)
            
            view = discord.ui.View()
            btn_cancelar = discord.ui.Button(
                label="❌ Cancelar Transporte",
                style=discord.ButtonStyle.danger
            )
            
            async def cancelar(inter):
                await inter.response.send_message("❌ Transporte cancelado", ephemeral=True)
                db.update_transporte_status(transporte['id'], STATUS["CANCELADO"])
            
            btn_cancelar.callback = cancelar
            view.add_item(btn_cancelar)
            
            await canal.send(embed=embed_pag, view=view)

async def setup(bot):
    # Este cog será adicionado quando ativarmos
    # Por enquanto, deixa comentado
    pass
