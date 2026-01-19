"""
Cog: Sistema de Transporte - Novo Fluxo
Fluxo Completo: Nick → Origem → Prioridade → Valor → Obs → Pagamento → Validação → Acesso → Depósito → Fila → Transporte → Entrega → Retirada
"""
import discord
from discord.ext import commands
from database import db
from config import (
    PRECO_POR_MILHAO, PRECO_ALTA_PRIORIDADE, VALOR_MINIMO, 
    TAXA_ALTA_PRIORIDADE, PIX_KEY, STATUS, ORIGENS, DESTINO_PADRAO, PIX_QRCODE_PATH
)
from pathlib import Path

def calcular_taxa_novo(valor, prioridade):
    """Calcula taxa com novo sistema"""
    if prioridade == "ALTA":
        taxa = (valor / 1_000_000) * PRECO_ALTA_PRIORIDADE
    else:
        taxa = (valor / 1_000_000) * PRECO_POR_MILHAO
    return taxa

class ViewAbrirTransporte(discord.ui.View):
    def __init__(self, cog):
        super().__init__()
        self.cog = cog
    
    @discord.ui.button(label="🎫 Abrir Transporte", style=discord.ButtonStyle.success)
    async def abrir(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.cog.abrir_ticket(interaction)

class ModalNick(discord.ui.Modal):
    def __init__(self, callback):
        super().__init__(title="🎮 Qual é seu Nick?", custom_id="modal_nick_transport")
        self.callback_func = callback
        self.nick = discord.ui.TextInput(
            label="Nick exatamente como no jogo",
            placeholder="Ex: Player#123",
            required=True,
            min_length=3,
            max_length=30
        )
        self.add_item(self.nick)
    
    async def on_submit(self, interaction: discord.Interaction):
        print(f"\n🎮 [MODAL_NICK] Enviado por {interaction.user.name}")
        print(f"   Nick: {self.nick.value}")
        
        try:
            await interaction.response.defer(ephemeral=True)
            print(f"   ✅ Defer feito no modal")
            
            await self.callback_func(interaction, self.nick.value)
            print(f"   ✅ Callback executado")
            
        except Exception as e:
            print(f"   ❌ Erro no modal: {e}")
            import traceback
            traceback.print_exc()

class ModalValor(discord.ui.Modal):
    def __init__(self, callback):
        super().__init__(title="💰 Valor em Prata", custom_id="modal_valor_novo")
        self.callback_func = callback
        self.valor = discord.ui.TextInput(
            label=f"Mínimo {VALOR_MINIMO:,} prata",
            placeholder="Ex: 50000000",
            required=True
        )
        self.add_item(self.valor)
    
    async def on_submit(self, interaction: discord.Interaction):
        try:
            valor = int(self.valor.value.replace(".", "").replace(",", ""))
            await self.callback_func(interaction, valor)
        except:
            await interaction.response.send_message("❌ Valor inválido", ephemeral=True)

class ModalObs(discord.ui.Modal):
    def __init__(self, callback):
        super().__init__(title="📝 Observações", custom_id="modal_obs_novo")
        self.callback_func = callback
        self.obs = discord.ui.TextInput(
            label="Algo especial?",
            placeholder="Ex: Peso alto, Black Market, etc",
            required=False,
            max_length=500,
            style=discord.TextStyle.paragraph
        )
        self.add_item(self.obs)
    
    async def on_submit(self, interaction: discord.Interaction):
        await self.callback_func(interaction, self.obs.value or "Nenhuma")

class TransportFlowCog(commands.Cog):
    """Sistema de transporte com fluxo completo"""
    
    def __init__(self, bot):
        self.bot = bot
        self.sessions = {}  # user_id → session
        self.ticket_counter = 0
    
    @commands.Cog.listener()
    async def on_ready(self):
        print("✅ Cog Transport Flow carregado")
        
        # Restaura contador
        conn = db.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM transportes")
        self.ticket_counter = cursor.fetchone()[0]
        conn.close()
    
    async def abrir_ticket(self, interaction: discord.Interaction):
        """Abre novo ticket - FASE 1"""
        
        print(f"\n🔄 [ABRIR_TICKET] Iniciado por {interaction.user.name}")
        
        try:
            # Defer imediatamente
            print(f"   ⏳ Fazendo defer da interação...")
            await interaction.response.defer(ephemeral=True)
            print(f"   ✅ Defer feito")
            
            # Cria cliente
            print(f"   ⏳ Criando cliente...")
            cliente = db.get_or_create_cliente(
                str(interaction.user.id),
                interaction.user.name
            )
            print(f"   ✅ Cliente criado: {cliente['id']}")
            
            # Gera número
            self.ticket_counter += 1
            numero_ticket = 1000 + self.ticket_counter
            print(f"   ✅ Ticket gerado: #{numero_ticket:04d}")
            
            # Cria canal privado
            print(f"   ⏳ Criando canal privado...")
            guild = interaction.guild
            user_role = interaction.user
            
            overwrites = {
                guild.default_role: discord.PermissionOverwrite(view_channel=False),
                user_role: discord.PermissionOverwrite(view_channel=True, send_messages=True),
            }
            
            # Adiciona staff
            for member in guild.members:
                if any(r.name.startswith("💼") or r.name.startswith("👑") for r in member.roles):
                    overwrites[member] = discord.PermissionOverwrite(view_channel=True, send_messages=True)
            
            canal = await guild.create_text_channel(
                name=f"ticket-{numero_ticket:04d}",
                category=None,
                overwrites=overwrites,
                topic=f"Ticket #{numero_ticket:04d} | {interaction.user.name}"
            )
            print(f"   ✅ Canal criado: {canal.mention}")
            
            # Inicializa sessão
            self.sessions[interaction.user.id] = {
                'numero_ticket': numero_ticket,
                'canal_id': canal.id,
                'cliente_id': cliente['id'],
                'status': 'COLETANDO_NICK',
                'nick_jogo': None,
                'origem': None,
                'prioridade': None,
                'valor': None,
                'obs': None,
                'transporte_id': None,
                'comprovante_url': None
            }
            print(f"   ✅ Sessão inicializada")
            
            # Responde ao usuário
            print(f"   ⏳ Enviando resposta...")
            embed = discord.Embed(
                title=f"🎫 TICKET #{numero_ticket:04d} ABERTO",
                description="Seu canal privado foi criado!",
                color=0x2ECC71
            )
            embed.set_footer(text=f"Ticket criado | Próximo passo: Seu nick no jogo")
            
            await interaction.followup.send(embed=embed, ephemeral=True)
            print(f"   ✅ Resposta enviada")
            
            # Envia no canal
            print(f"   ⏳ Enviando mensagem de boas-vindas...")
            embed_welcome = discord.Embed(
                title="🎉 Bem-vindo ao T.A.S Mania!",
                description="Vamos processar seu transporte passo a passo\n\n🎯 **WHADAWEL** aqui garantindo segurança!",
                color=0x3498DB
            )
            embed_welcome.add_field(
                name="📋 Processo",
                value="1️⃣ Nick\n2️⃣ Origem\n3️⃣ Prioridade\n4️⃣ Valor\n5️⃣ Observações\n6️⃣ Pagamento",
                inline=False
            )
            embed_welcome.set_footer(text="WHADAWEL Transportes™")
            await canal.send(f"{interaction.user.mention}", embed=embed_welcome)
            print(f"   ✅ Mensagem de boas-vindas enviada")
            
            # Pede nick
            print(f"   ⏳ Iniciando fase de coleta de nick...")
            await self.pedir_nick(interaction.user.id, canal)
            print(f"   ✅ Fase de nick iniciada")
            
            print(f"\n✅ [ABRIR_TICKET] Concluído com sucesso para {interaction.user.name}\n")
            
        except Exception as e:
            print(f"\n❌ [ABRIR_TICKET] Erro: {e}")
            import traceback
            traceback.print_exc()
            
            # Tenta enviar mensagem de erro
            try:
                await interaction.followup.send(
                    f"❌ Erro ao criar ticket: {str(e)}",
                    ephemeral=True
                )
            except:
                try:
                    await interaction.response.send_message(
                        f"❌ Erro ao criar ticket",
                        ephemeral=True
                    )
                except:
                    pass
    
    async def pedir_nick(self, user_id, canal):
        """FASE 1: Pergunta Nick do Jogador"""
        
        print(f"\n📝 [PEDIR_NICK] Abrindo para user_id={user_id}")
        
        embed = discord.Embed(
            title="🎮 Qual é seu Nick no Jogo?",
            description="Digite exatamente como aparece no seu personagem",
            color=0x3498DB
        )
        embed.add_field(
            name="💡 Dica",
            value="Isso será usado para liberar acesso à island",
            inline=False
        )
        embed.set_footer(text="✅ WHADAWEL: Vamos cuidar bem dos seus itens!")
        
        view = discord.ui.View()
        
        async def abrir_modal(inter):
            print(f"   ✅ Botão clicado por {inter.user.name}")
            print(f"   Abrindo modal com user_id={user_id}")
            await inter.response.send_modal(ModalNick(lambda i, n: self.processar_nick(i, user_id, n)))
        
        btn = discord.ui.Button(
            label="📝 Inserir Nick",
            style=discord.ButtonStyle.primary
        )
        btn.callback = abrir_modal
        view.add_item(btn)
        
        await canal.send(embed=embed, view=view)
        print(f"✅ [PEDIR_NICK] Mensagem enviada\n")
    
    async def processar_nick(self, interaction, user_id, nick):
        """Processa nick e vai para FASE 2"""
        
        print(f"\n📝 [PROCESSAR_NICK] Iniciado por {interaction.user.name}")
        print(f"   Nick inserido: {nick}")
        
        try:
            # Já foi feito defer no on_submit, apenas usar followup
            print(f"   ✅ Usando followup (defer já foi feito no modal)")
            
            session = self.sessions.get(user_id)
            if not session:
                print(f"   ❌ Sessão não encontrada!")
                await interaction.followup.send("❌ Sessão expirou", ephemeral=True)
                return
            
            session['nick_jogo'] = nick
            session['status'] = 'COLETANDO_ORIGEM'
            print(f"   ✅ Nick salvo na sessão: {nick}")
            
            embed = discord.Embed(
                title="✅ Nick Confirmado",
                description=f"🎮 **{nick}**",
                color=0x2ECC71
            )
            embed.set_footer(text="✅ WHADAWEL aprova!")
            await interaction.followup.send(embed=embed, ephemeral=True)
            print(f"   ✅ Resposta enviada")
            
            canal = self.bot.get_channel(session['canal_id'])
            if canal:
                await self.pedir_origem(user_id, canal)
                print(f"   ✅ Origem solicitada")
            else:
                print(f"   ❌ Canal não encontrado!")
            
            print(f"✅ [PROCESSAR_NICK] Concluído\n")
            
        except Exception as e:
            print(f"\n❌ [PROCESSAR_NICK] Erro: {e}")
            import traceback
            traceback.print_exc()
            
            try:
                await interaction.followup.send(
                    f"❌ Erro ao processar nick: {str(e)}",
                    ephemeral=True
                )
            except:
                pass
    
    async def pedir_origem(self, user_id, canal):
        """FASE 2: Pergunta Origem"""
        
        print(f"\n📍 [PEDIR_ORIGEM] Iniciando para user_id={user_id}")
        
        embed = discord.Embed(
            title="📍 De Qual Cidade Você Quer Transportar?",
            description="Escolha a origem do seu transporte\n\n✅ WHADAWEL aprova! Agora escolha a origem...",
            color=0x3498DB
        )
        
        class SelectOrigem(discord.ui.Select):
            def __init__(self, callback):
                options = [discord.SelectOption(label=o, value=o, emoji="📍") for o in ORIGENS]
                super().__init__(
                    placeholder="Selecione...",
                    min_values=1,
                    max_values=1,
                    options=options
                )
                self.cb = callback
            
            async def callback(self, inter: discord.Interaction):
                print(f"   ✅ Select clicado: {self.values[0]}")
                await self.cb(inter, self.values[0])
        
        view = discord.ui.View()
        view.add_item(SelectOrigem(lambda i, o: self.processar_origem(i, user_id, o)))
        
        await canal.send(embed=embed, view=view)
        print(f"✅ [PEDIR_ORIGEM] Enviado\n")
    
    async def processar_origem(self, interaction, user_id, origem):
        """Processa origem e vai para FASE 3"""
        
        print(f"\n🌍 [PROCESSAR_ORIGEM] Iniciado")
        print(f"   Origem: {origem}")
        print(f"   User: {interaction.user.name}")
        
        try:
            await interaction.response.defer(ephemeral=True)
            print(f"   ✅ Defer feito")
            
            session = self.sessions.get(user_id)
            if not session:
                print(f"   ❌ Sessão não encontrada!")
                await interaction.followup.send("❌ Sessão expirou", ephemeral=True)
                return
            
            session['origem'] = origem
            session['status'] = 'COLETANDO_PRIORIDADE'
            print(f"   ✅ Origem salva: {origem}")
            
            # Resposta ao cliente
            embed = discord.Embed(
                title="✅ Origem Confirmada",
                description=f"📍 **{origem}** → Caerleon",
                color=0x2ECC71
            )
            embed.set_footer(text="✅ WHADAWEL aprova!")
            await interaction.followup.send(embed=embed, ephemeral=True)
            print(f"   ✅ Resposta enviada ao cliente")
            
            # Próxima fase
            canal = self.bot.get_channel(session['canal_id'])
            if canal:
                await self.pedir_prioridade(user_id, canal)
                print(f"   ✅ Prioridade solicitada")
            else:
                print(f"   ❌ Canal não encontrado!")
            
            print(f"✅ [PROCESSAR_ORIGEM] Concluído\n")
            
        except Exception as e:
            print(f"\n❌ [PROCESSAR_ORIGEM] Erro: {e}")
            import traceback
            traceback.print_exc()
            
            try:
                await interaction.followup.send(
                    f"❌ Erro ao processar origem: {str(e)}",
                    ephemeral=True
                )
            except:
                pass
            session['origem'] = origem
            session['status'] = 'COLETANDO_PRIORIDADE'
            
            embed = discord.Embed(
                title="✅ Origem Confirmada",
                description=f"📍 **{origem} → {DESTINO_PADRAO}**",
                color=0x2ECC71
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
            
            canal = self.bot.get_channel(session['canal_id'])
            if canal:
                await self.pedir_prioridade(user_id, canal)
    
    async def pedir_prioridade(self, user_id, canal):
        """FASE 3: Pergunta Prioridade"""
        
        print(f"\n⚡ [PEDIR_PRIORIDADE] Iniciando para user_id={user_id}")
        
        embed = discord.Embed(
            title="⚡ Qual é a Prioridade?",
            color=0xF39C12
        )
        embed.add_field(
            name="🕒 Normal",
            value="Entrega até 2 horas\nValor: Base",
            inline=True
        )
        embed.add_field(
            name="⚡ Alta",
            value="Entrega rápida (1-2h)\nValor: +20%",
            inline=True
        )
        embed.set_footer(text="✅ WHADAWEL garante agilidade!")
        
        view = discord.ui.View()
        
        async def callback_normal(inter):
            print(f"   ✅ Botão NORMAL clicado")
            await self.processar_prioridade(inter, user_id, "NORMAL")
        
        async def callback_alta(inter):
            print(f"   ✅ Botão ALTA clicado")
            await self.processar_prioridade(inter, user_id, "ALTA")
        
        btn_normal = discord.ui.Button(label="🕒 Normal", style=discord.ButtonStyle.gray)
        btn_alta = discord.ui.Button(label="⚡ Alta (+20%)", style=discord.ButtonStyle.danger)
        
        btn_normal.callback = callback_normal
        btn_alta.callback = callback_alta
        
        view.add_item(btn_normal)
        view.add_item(btn_alta)
        
        await canal.send(embed=embed, view=view)
        print(f"✅ [PEDIR_PRIORIDADE] Enviado\n")
    
    async def processar_prioridade(self, inter, user_id, prioridade):
        """Processa prioridade e vai para FASE 4"""
        
        print(f"\n⚡ [PROCESSAR_PRIORIDADE] Iniciado")
        print(f"   Prioridade: {prioridade}")
        
        try:
            await inter.response.defer(ephemeral=True)
            print(f"   ✅ Defer feito")
            
            session = self.sessions.get(user_id)
            if not session:
                print(f"   ❌ Sessão não encontrada!")
                await inter.followup.send("❌ Sessão expirou", ephemeral=True)
                return
            
            session['prioridade'] = prioridade
            session['status'] = 'COLETANDO_VALOR'
            print(f"   ✅ Prioridade salva: {prioridade}")
            
            embed = discord.Embed(
                title="✅ Prioridade Confirmada",
                description=f"⚡ **{prioridade}**",
                color=0x2ECC71
            )
            embed.set_footer(text="✅ WHADAWEL aprova!")
            await inter.followup.send(embed=embed, ephemeral=True)
            print(f"   ✅ Resposta enviada ao cliente")
            
            canal = self.bot.get_channel(session['canal_id'])
            if canal:
                await self.pedir_valor(user_id, canal)
                print(f"   ✅ Valor solicitado")
            else:
                print(f"   ❌ Canal não encontrado!")
            
            print(f"✅ [PROCESSAR_PRIORIDADE] Concluído\n")
            
        except Exception as e:
            print(f"\n❌ [PROCESSAR_PRIORIDADE] Erro: {e}")
            import traceback
            traceback.print_exc()
            
            try:
                await inter.followup.send(
                    f"❌ Erro ao processar prioridade: {str(e)}",
                    ephemeral=True
                )
            except:
                pass
    
    async def pedir_valor(self, user_id, canal):
        """FASE 4: Pergunta Valor"""
        
        embed = discord.Embed(
            title="💰 Qual é o Valor em Prata?",
            color=0x3498DB
        )
        embed.add_field(
            name="📊 Cálculo",
            value=f"R$ 0,60 por 1 milhão (normal)\nR$ 0,72 por 1 milhão (alta +20%)",
            inline=False
        )
        embed.add_field(
            name="📝 Exemplos",
            value=f"10M = R$ 6,00 | 50M = R$ 30,00 | 350M = R$ 210,00",
            inline=False
        )
        embed.add_field(
            name="⚠️ Mínimo",
            value=f"{VALOR_MINIMO:,} prata",
            inline=False
        )
        
        view = discord.ui.View()
        
        async def abrir_modal(inter):
            await inter.response.send_modal(ModalValor(lambda i, v: self.processar_valor(i, user_id, v)))
        
        btn = discord.ui.Button(label="💵 Inserir Valor")
        btn.callback = abrir_modal
        view.add_item(btn)
        
        await canal.send(embed=embed, view=view)
    
    async def processar_valor(self, inter, user_id, valor):
        """Processa valor e vai para FASE 5"""
        
        await inter.response.defer(ephemeral=True)
        
        session = self.sessions.get(user_id)
        if not session:
            return
        
        if valor < VALOR_MINIMO:
            await inter.followup.send(
                f"❌ Mínimo: {VALOR_MINIMO:,} prata\nVocê inseriu: {valor:,}",
                ephemeral=True
            )
            return
        
        session['valor'] = valor
        session['status'] = 'COLETANDO_OBS'
        
        taxa = calcular_taxa_novo(valor, session['prioridade'])
        
        embed = discord.Embed(
            title="✅ Valor Confirmado",
            description=f"💰 {valor:,} prata",
            color=0x2ECC71
        )
        embed.add_field(
            name="💵 Taxa",
            value=f"R$ {taxa:.2f}",
            inline=False
        )
        
        await inter.followup.send(embed=embed, ephemeral=True)
        
        canal = self.bot.get_channel(session['canal_id'])
        if canal:
            await self.pedir_observacoes(user_id, canal)
    
    async def pedir_observacoes(self, user_id, canal):
        """FASE 5: Pergunta Observações"""
        
        embed = discord.Embed(
            title="📝 Observações (Opcional)",
            description="Algo especial que devemos saber?",
            color=0x3498DB
        )
        embed.add_field(
            name="💡 Exemplos",
            value="Peso alto, itens raros, Black Market, urgente, etc",
            inline=False
        )
        
        view = discord.ui.View()
        
        async def abrir_modal(inter):
            await inter.response.send_modal(ModalObs(lambda i, o: self.processar_observacoes(i, user_id, o)))
        
        btn = discord.ui.Button(label="📝 Adicionar Observações")
        btn.callback = abrir_modal
        view.add_item(btn)
        
        await canal.send(embed=embed, view=view)
    
    async def processar_observacoes(self, inter, user_id, obs):
        """Processa observações e envia resumo + pagamento - FASE 6"""
        
        print(f"\n📝 [PROCESSAR_OBSERVACOES] Iniciado")
        print(f"   Observações: {obs}")
        
        try:
            await inter.response.defer(ephemeral=True)
            print(f"   ✅ Defer feito")
            
            session = self.sessions.get(user_id)
            if not session:
                print(f"   ❌ Sessão não encontrada!")
                await inter.followup.send("❌ Sessão expirou", ephemeral=True)
                return
            
            print(f"   ✅ Sessão encontrada")
            
            session['obs'] = obs
            session['status'] = 'AGUARDANDO_PAGAMENTO'
            print(f"   ✅ Status alterado para AGUARDANDO_PAGAMENTO")
            
            # Calcula taxa final
            taxa_final = calcular_taxa_novo(session['valor'], session['prioridade'])
            print(f"   ✅ Taxa calculada: R$ {taxa_final:.2f}")
            
            # Cria transporte no banco
            transporte = db.create_transporte(
                cliente_id=session['cliente_id'],
                origem=session['origem'],
                valor_estimado=session['valor'],
                prioridade=session['prioridade'],
                taxa_final=taxa_final,
                ticket_channel_id=session['canal_id']
            )
            print(f"   ✅ Transporte criado: #{transporte['numero_ticket']:04d}")
            
            session['transporte_id'] = transporte['id']
            
            # Salva nick e obs
            db.update_transporte(
                transporte['id'],
                notas=f"🎮 Nick: {session['nick_jogo']}\n📝 Obs: {obs}"
            )
            print(f"   ✅ Dados salvos no banco")
            
            await inter.followup.send("✅ Resumo criado!", ephemeral=True)
            print(f"   ✅ Resposta enviada ao cliente")
            
            # Envia para o canal
            canal = self.bot.get_channel(session['canal_id'])
            if canal:
                print(f"   ✅ Enviando resumo e pagamento...")
                
                # Resumo bonito
                embed_resumo = discord.Embed(
                    title="✅ TRANSPORTE CRIADO - WHADAWEL GARANTE!",
                    description="Verifique os dados abaixo e confirme o pagamento",
                    color=0x2ECC71
                )
                embed_resumo.add_field(name="🎫 Ticket", value=f"#{transporte['numero_ticket']:04d}", inline=True)
                embed_resumo.add_field(name="🎮 Nick", value=session['nick_jogo'], inline=True)
                embed_resumo.add_field(name="📍 Rota", value=f"{session['origem']} → Caerleon", inline=True)
                embed_resumo.add_field(name="💰 Prata", value=f"{session['valor']:,}", inline=True)
                embed_resumo.add_field(name="⚡ Prioridade", value=session['prioridade'], inline=True)
                embed_resumo.add_field(name="💵 Valor BR", value=f"R$ {taxa_final:.2f}", inline=True)
                
                if obs != "Nenhuma":
                    embed_resumo.add_field(name="📝 Observações", value=obs, inline=False)
                
                embed_resumo.set_footer(text="🎯 WHADAWEL™ | Transportes Seguros")
                
                await canal.send(embed=embed_resumo)
                print(f"   ✅ Resumo enviado")
                
                # Instruções de pagamento
                embed_pag = discord.Embed(
                    title="💳 PAGAMENTO - FAÇA O PIX",
                    description="Escaneie o QR Code ou copie a chave PIX abaixo\n\n🎯 **WHADAWEL:** Pagamento confirmado = Itens saindo em minutos! ⚡",
                    color=0xF39C12
                )
                embed_pag.add_field(
                    name="💵 Valor a Pagar",
                    value=f"```R$ {taxa_final:.2f}```",
                    inline=False
                )
                embed_pag.add_field(
                    name="🔑 Chave PIX (CPF/Email/Telefone/Aleatória)",
                    value=f"```{PIX_KEY}```",
                    inline=False
                )
                embed_pag.add_field(
                    name="📋 Como Fazer o Pagamento",
                    value="1️⃣ Abra seu app de banco ou PIX\n2️⃣ Escaneie o QR Code abaixo\n   OU\n   Copie a chave PIX e faça a transferência\n3️⃣ Digite o valor exatamente: **R$ " + f"{taxa_final:.2f}" + "**\n4️⃣ Confirme a transação",
                    inline=False
                )
                
                view = discord.ui.View(timeout=None)
                
                # Botão para copiar chave PIX
                btn_copiar = discord.ui.Button(
                    label="📋 Copiar Chave PIX",
                    style=discord.ButtonStyle.blurple
                )
                
                async def copiar_callback(i):
                    await i.response.send_message(
                        f"```{PIX_KEY}```\n✅ Chave PIX copiada! Cole no seu banco",
                        ephemeral=True
                    )
                
                btn_copiar.callback = copiar_callback
                view.add_item(btn_copiar)
                
                # Botão para cancelar
                btn_cancelar = discord.ui.Button(
                    label="❌ Cancelar Transporte",
                    style=discord.ButtonStyle.danger
                )
                
                async def cancelar(i):
                    await i.response.defer(ephemeral=True)
                    db.update_transporte_status(transporte['id'], STATUS["CANCELADO"])
                    await i.followup.send("❌ Transporte cancelado", ephemeral=True)
                    await canal.send("❌ Transporte foi cancelado pelo cliente")
                
                btn_cancelar.callback = cancelar
                view.add_item(btn_cancelar)
                
                # Envia embed de pagamento
                await canal.send(embed=embed_pag, view=view)
                print(f"   ✅ Pagamento enviado")
                
                # Envia QR Code se existir
                qr_path = Path(PIX_QRCODE_PATH)
                if qr_path.exists():
                    await canal.send(
                        "📱 **QR Code PIX:**",
                        file=discord.File(qr_path)
                    )
                    print(f"   ✅ QR Code enviado")
                
                print(f"   ✅ Resumo e pagamento completos")
            else:
                print(f"   ❌ Canal não encontrado!")
            
            print(f"✅ [PROCESSAR_OBSERVACOES] Concluído\n")
            
        except Exception as e:
            print(f"\n❌ [PROCESSAR_OBSERVACOES] Erro: {e}")
            import traceback
            traceback.print_exc()
            
            try:
                await inter.followup.send(
                    f"❌ Erro ao processar observações: {str(e)}",
                    ephemeral=True
                )
            except:
                pass

        if not canal:
            return
        
        # Resumo bonito
        embed_resumo = discord.Embed(
            title="✅ TRANSPORTE CRIADO - WHADAWEL GARANTE!",
            description="Verifique os dados abaixo e confirme o pagamento",
            color=0x2ECC71
        )
        embed_resumo.add_field(name="🎫 Ticket", value=f"#{transporte['numero_ticket']:04d}", inline=True)
        embed_resumo.add_field(name="🎮 Nick", value=session['nick_jogo'], inline=True)
        embed_resumo.add_field(name="📍 Rota", value=f"{session['origem']} → Caerleon", inline=True)
        embed_resumo.add_field(name="💰 Prata", value=f"{session['valor']:,}", inline=True)
        embed_resumo.add_field(name="⚡ Prioridade", value=session['prioridade'], inline=True)
        embed_resumo.add_field(name="💵 Valor BR", value=f"R$ {taxa_final:.2f}", inline=True)
        
        if obs != "Nenhuma":
            embed_resumo.add_field(name="📝 Observações", value=obs, inline=False)
        
        embed_resumo.set_footer(text="🎯 WHADAWEL™ | Transportes Seguros")
        
        await canal.send(embed=embed_resumo)
        
        # Instruções de pagamento
        embed_pag = discord.Embed(
            title="💳 PAGAMENTO - FAÇA O PIX",
            description="Escaneie o QR Code ou copie a chave PIX abaixo\n\n🎯 **WHADAWEL:** Pagamento confirmado = Itens saindo em minutos! ⚡",
            color=0xF39C12
        )
        embed_pag.add_field(
            name="💵 Valor a Pagar",
            value=f"```R$ {taxa_final:.2f}```",
            inline=False
        )
        embed_pag.add_field(
            name="🔑 Chave PIX (CPF/Email/Telefone/Aleatória)",
            value=f"```{PIX_KEY}```",
            inline=False
        )
        embed_pag.add_field(
            name="📋 Como Fazer o Pagamento",
            value="1️⃣ Abra seu app de banco ou PIX\n2️⃣ Escaneie o QR Code abaixo\n   OU\n   Copie a chave PIX e faça a transferência\n3️⃣ Digite o valor exatamente: **R$ " + f"{taxa_final:.2f}" + "**\n4️⃣ Confirme a transação",
            inline=False
        )
        
        view = discord.ui.View(timeout=None)
        
        # Botão para copiar chave PIX
        btn_copiar = discord.ui.Button(
            label="Copiar Chave PIX",
            style=discord.ButtonStyle.blurple,
            emoji="📋"
        )
        
        async def copiar_callback(i):
            await i.response.send_message(
                f"```{PIX_KEY}```\n✅ Chave PIX copiada! Cole no seu banco",
                ephemeral=True
            )
        
        btn_copiar.callback = copiar_callback
        view.add_item(btn_copiar)
        
        # Botão para cancelar
        btn_cancelar = discord.ui.Button(
            label="❌ Cancelar Transporte",
            style=discord.ButtonStyle.danger
        )
        
        async def cancelar(i):
            await i.response.defer(ephemeral=True)
            db.update_transporte_status(transporte['id'], STATUS["CANCELADO"])
            await i.followup.send("❌ Transporte cancelado", ephemeral=True)
            await canal.send("❌ Transporte foi cancelado pelo cliente")
        
        btn_cancelar.callback = cancelar
        view.add_item(btn_cancelar)
        
        # Envia embed de pagamento
        await canal.send(embed=embed_pag, view=view)
        
        # Envia QR Code se existir
        qr_path = Path(PIX_QRCODE_PATH)
        if qr_path.exists():
            await canal.send(
                "📱 **QR Code PIX:**",
                file=discord.File(qr_path)
            )
        
        # Instruções finais
        embed_final = discord.Embed(
            title="✅ Próximas Etapas",
            description="Após fazer o PIX:",
            color=discord.Color.green()
        )
        embed_final.add_field(
            name="1️⃣ Envie o Comprovante",
            value="Faça um print/screenshot do seu comprovante de PIX",
            inline=False
        )
        embed_final.add_field(
            name="2️⃣ Cole a Imagem",
            value="Cole a imagem neste canal",
            inline=False
        )
        embed_final.add_field(
            name="3️⃣ Clique em Confirmar",
            value="Clique no botão abaixo quando enviar a imagem",
            inline=False
        )
        embed_final.add_field(
            name="4️⃣ Validação",
            value="Staff validará seu pagamento rapidamente",
            inline=False
        )
        embed_final.set_footer(text="Não compartilhe seu comprovante com ninguém além de staff!")
        
        await canal.send(embed=embed_final)

async def setup(bot):
    await bot.add_cog(TransportFlowCog(bot))
