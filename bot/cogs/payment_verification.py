"""
Sistema de Verificação de Pagamento
Analisa comprovantes de PIX enviados pelos clientes
"""
import discord
from discord.ext import commands
from pathlib import Path
import sqlite3
from datetime import datetime
from bot.database import db
from bot.config import GUILD_ID, STATUS, PIX_KEY, PIX_QRCODE_PATH

class PaymentVerification(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.guild_id = GUILD_ID
        self.aguardando_foto_deposito = {}
        
    @commands.Cog.listener()
    async def on_message(self, message):
        """Escuta mensagens nos canais de ticket para comprovantes de PIX e fotos de depósito"""
        
        print(f"\n[LISTENER] Mensagem recebida")
        print(f"   Canal: {message.channel.name}")
        print(f"   Autor: {message.author.name}")
        print(f"   Bot? {message.author == self.bot.user}")
        print(f"   Anexos: {len(message.attachments) if message.attachments else 0}")
        
        # Ignora mensagens do bot
        if message.author == self.bot.user:
            print(f"   ↩️ Ignorando (é o bot)")
            return
        
        # Verifica se é um canal de ticket
        if not message.channel.name.startswith("ticket-"):
            print(f"   ↩️ Ignorando (não é canal ticket)")
            return
        
        print(f"   ✅ É canal ticket")
        
        # Verifica se tem anexos (imagens)
        if not message.attachments:
            print(f"   ↩️ Ignorando (sem anexos)")
            return
        
        print(f"   ✅ Tem {len(message.attachments)} anexo(s)")
        
        # Extrai número do ticket
        try:
            numero_ticket = int(message.channel.name.split("-")[1])
            print(f"   ✅ Número ticket extraído: {numero_ticket}")
        except (IndexError, ValueError) as e:
            print(f"   ❌ Erro ao extrair número: {e}")
            return
        
        # VERIFICA SE ESTÁ AGUARDANDO FOTO DE DEPÓSITO
        if numero_ticket in self.aguardando_foto_deposito:
            print(f"   📸 [FOTO_DEPOSITO] Detectada foto de depósito!")
            await self._processar_foto_deposito(message, numero_ticket)
            return
        
        # CASO CONTRÁRIO, PROCESSA COMPROVANTE DE PAGAMENTO
        print(f"\n📸 [COMPROVANTE] Iniciando processamento ticket-{numero_ticket}")
        print(f"   Autor: {message.author.name} (ID: {message.author.id})")
        print(f"   Anexos: {len(message.attachments)}")
        
        # Busca o transporte
        try:
            print(f"   ⏳ Buscando transporte no banco...")
            conn = db.get_connection()
            conn.row_factory = sqlite3.Row
            cursor = db.get_wrapped_cursor(conn)
            
            cursor.execute("""
                SELECT * FROM transportes 
                WHERE numero_ticket = ? 
                ORDER BY id DESC LIMIT 1
            """, (numero_ticket,))
            
            transporte = cursor.fetchone()
            conn.close()
            
            if not transporte:
                print(f"   ❌ Transporte NÃO encontrado no banco")
                await message.reply(
                    "❌ Ticket não encontrado no sistema",
                    mention_author=False
                )
                return
            
            print(f"   ✅ Transporte encontrado:")
            print(f"      ID: {transporte['id']}")
            print(f"      Status: {transporte['status']}")
            print(f"      Cliente ID: {transporte['cliente_id']}")
            
        except Exception as e:
            print(f"   ❌ Erro ao buscar no banco: {e}")
            import traceback
            traceback.print_exc()
            return
        
        # Valida se está aguardando pagamento
        if transporte['status'] != STATUS["AGUARDANDO_PAGAMENTO"]:
            print(f"   ⏭️ Status não é AGUARDANDO_PAGAMENTO (é: {transporte['status']})")
            await message.reply(
                f"⏭️ Este transporte não está aguardando pagamento (Status: {transporte['status']})",
                mention_author=False
            )
            return
        
        print(f"   ✅ Status é AGUARDANDO_PAGAMENTO")
        
        # Processa cada anexo
        for anexo in message.attachments:
            print(f"\n   📎 Processando anexo: {anexo.filename}")
            await self._processar_comprovante(
                message, 
                anexo, 
                transporte, 
                numero_ticket
            )
        
        print(f"✅ [COMPROVANTE] Processamento iniciado para {len(message.attachments)} anexo(s)\n")
    
    async def _processar_comprovante(self, message, anexo, transporte, numero_ticket):
        """Processa um comprovante de pagamento"""
        
        print(f"      📎 [VERIFICAÇÃO] Processando: {anexo.filename}")
        
        try:
            # Valida se é imagem
            if not anexo.content_type or not anexo.content_type.startswith('image/'):
                print(f"         ❌ Não é imagem: {anexo.content_type}")
                await message.reply(
                    "❌ **Erro:** Envie uma imagem do comprovante de PIX",
                    mention_author=False
                )
                return
            
            print(f"         ✅ Imagem válida: {anexo.content_type}")
            
            # Busca canal de análise de pagamentos
            guild = self.bot.get_guild(self.guild_id)
            if not guild:
                print(f"         ❌ Guild não encontrada")
                return
            
            print(f"         ✅ Guild encontrada")
            
            # Procura canal "analise-pagamentos" (pode ter emoji)
            canal_analise = None
            for ch in guild.channels:
                if "analise-pagamentos" in ch.name:
                    canal_analise = ch
                    break
            
            if not canal_analise:
                print(f"         ⚠️ Canal 'analise-pagamentos' não encontrado")
                await message.reply(
                    "⚠️ Canal de análise não configurado. Contate o staff!",
                    mention_author=False
                )
                return
            
            print(f"         ✅ Canal de análise encontrado: {canal_analise.name}")
            
            # Cria embed para análise
            embed_analise = discord.Embed(
                title="📸 COMPROVANTE PARA ANÁLISE",
                description="Comprovante de PIX enviado para verificação",
                color=0xFFD700
            )
            embed_analise.add_field(
                name="🎫 Ticket",
                value=f"#{transporte['numero_ticket']:04d}",
                inline=True
            )
            embed_analise.add_field(
                name="👤 Cliente",
                value=f"<@{message.author.id}>",
                inline=True
            )
            valor_prata = transporte['valor_estimado'] or 0
            taxa_br = transporte['taxa_final'] or 0
            embed_analise.add_field(
                name="💰 Valor",
                value=f"R$ {float(taxa_br):.2f} (ou {valor_prata:,.0f} prata)",
                inline=True
            )
            notas = transporte['notas'] or ''
            nick_jogo = 'Não informado'
            if notas and 'Nick:' in notas:
                nick_jogo = notas.split('Nick:')[1].split('\n')[0].strip()
            embed_analise.add_field(
                name="🎮 Nick",
                value=nick_jogo,
                inline=True
            )
            embed_analise.add_field(
                name="⏱️ Horário",
                value=datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
                inline=True
            )
            embed_analise.add_field(
                name="📎 Arquivo",
                value=f"```{anexo.filename}```",
                inline=False
            )
            embed_analise.set_footer(text="⏳ Aguardando análise do Staff")
            
            print(f"         ✅ Embed criado")
            
            # Cria view com botões de ação
            view = discord.ui.View(timeout=None)
            
            # Botão APROVAR
            btn_aprovar = discord.ui.Button(
                label="✅ Aprovar Pagamento",
                style=discord.ButtonStyle.success,
                custom_id=f"aprovar_pag_{transporte['id']}"
            )
            
            async def aprovar_callback(interaction):
                await self._aprovar_pagamento(interaction, transporte, numero_ticket, message)
            
            btn_aprovar.callback = aprovar_callback
            view.add_item(btn_aprovar)
            
            # Botão REJEITAR
            btn_rejeitar = discord.ui.Button(
                label="❌ Rejeitar (Enviar foto novamente)",
                style=discord.ButtonStyle.danger,
                custom_id=f"rejeitar_pag_{transporte['id']}"
            )
            
            async def rejeitar_callback(interaction):
                await self._rejeitar_pagamento(interaction, numero_ticket, message)
            
            btn_rejeitar.callback = rejeitar_callback
            view.add_item(btn_rejeitar)
            
            # Botão CORRIGIR (valor diferente)
            btn_corrigir = discord.ui.Button(
                label="🔧 Corrigir (Valor Diferente)",
                style=discord.ButtonStyle.secondary,
                custom_id=f"corrigir_pag_{transporte['id']}"
            )
            
            async def corrigir_callback(interaction):
                await self._corrigir_pagamento(interaction, numero_ticket, message)
            
            btn_corrigir.callback = corrigir_callback
            view.add_item(btn_corrigir)
            
            print(f"         ✅ Botões criados")
            
            # Envia para canal de análise com a imagem
            print(f"         ✅ Enviando para análise...")
            msg_analise = await canal_analise.send(embed=embed_analise, view=view)
            print(f"         ✅ Embed enviado")
            
            # Também envia a imagem do comprovante
            await canal_analise.send(file=await anexo.to_file())
            print(f"         ✅ Imagem enviada")
            
            # Responde ao cliente que recebeu
            embed_ok = discord.Embed(
                title="✅ Comprovante Recebido!",
                description="Sua imagem foi enviada para análise",
                color=0x2ECC71
            )
            embed_ok.add_field(
                name="🎯 O que acontece agora?",
                value="1️⃣ O Staff analisa seu comprovante\n2️⃣ Pode levar alguns minutos\n3️⃣ Você receberá uma mensagem quando for aprovado",
                inline=False
            )
            embed_ok.set_footer(text="⏳ Status: Aguardando análise")
            
            await message.reply(embed=embed_ok, mention_author=False)
            print(f"         ✅ Cliente notificado")
            
            print(f"✅ [VERIFICAÇÃO] Comprovante enviado para análise\n")
            
        except Exception as e:
            print(f"         ❌ Erro: {e}")
            import traceback
            traceback.print_exc()
            
            try:
                await message.reply(
                    f"❌ Erro ao processar comprovante: {str(e)}",
                    mention_author=False
                )
            except:
                pass
            return
    
    async def _aprovar_pagamento(self, interaction, transporte, numero_ticket, msg_original):
        """Aprova o pagamento e inicia fluxo de acesso"""
        
        print(f"\n✅ [APROVAR] Pagamento do ticket-{numero_ticket}")
        
        await interaction.response.defer()
        
        # Atualiza status para PAGO
        db.update_transporte_status(transporte['id'], STATUS["PAGO"])
        
        print(f"   Status atualizado para: {STATUS['PAGO']}")
        
        # ===== ADICIONAR AO BANCO FINANCEIRO =====
        try:
            conn = db.get_connection()
            cursor = db.get_wrapped_cursor(conn)
            
            # Adiciona transação de entrada
            taxa_final = float(transporte['taxa_final'])
            cursor.execute("""
                INSERT INTO financeiro_transacoes 
                (tipo, valor, descricao, motivo, autor_id)
                VALUES (?, ?, ?, ?, ?)
            """, ("ENTRADA", taxa_final, f"Transporte Ticket #{numero_ticket:04d}", f"Cliente: {transporte['cliente_id']}", 0))
            
            # Atualiza saldo
            cursor.execute("SELECT * FROM financeiro_saldo WHERE id = 1")
            saldo_data = cursor.fetchone()
            saldo_total = (saldo_data[1] if saldo_data else 0) + taxa_final
            entrada = (saldo_data[2] if saldo_data else 0) + taxa_final
            saida = saldo_data[3] if saldo_data else 0
            
            cursor.execute("""
                UPDATE financeiro_saldo 
                SET saldo_total = ?, saldo_entrada = ?, 
                    ultima_atualizacao = CURRENT_TIMESTAMP
                WHERE id = 1
            """, (saldo_total, entrada))
            
            conn.commit()
            conn.close()
            print(f"   💰 Entrada registrada no banco: R$ {taxa_final:.2f}")
        except Exception as e:
            print(f"   ⚠️ Erro ao registrar no banco: {e}")
        
        # Busca dados do cliente
        notas = transporte['notas'] or ''
        nick_jogo = 'Não informado'
        if notas and 'Nick:' in notas:
            nick_jogo = notas.split('Nick:')[1].split('\n')[0].strip()
        
        origem = transporte['origem'] or 'Desconhecida'
        
        # ===== PASSO 1: Enviar para Staff liberar acesso =====
        guild = self.bot.get_guild(self.guild_id)
        
        # Busca canal do ticket
        canal_ticket = None
        for ch in guild.channels:
            if ch.name == f"ticket-{numero_ticket}":
                canal_ticket = ch
                break
        
        # Notifica cliente que foi aprovado
        if canal_ticket:
            embed_aprovado = discord.Embed(
                title="✅ PAGAMENTO APROVADO!",
                description="Seu pagamento foi verificado e aprovado",
                color=0x2ECC71
            )
            embed_aprovado.add_field(
                name="⏳ Próxima Etapa",
                value="Aguardando staff liberar acesso à ilha...",
                inline=False
            )
            embed_aprovado.set_footer(text="🎯 WHADAWEL™ | Transportes Seguros")
            
            try:
                conn = db.get_connection()
                conn.row_factory = sqlite3.Row
                cursor = db.get_wrapped_cursor(conn)
                cursor.execute("SELECT discord_id FROM clientes WHERE id = ?", (transporte['cliente_id'],))
                cliente_row = cursor.fetchone()
                conn.close()
                discord_id = int(cliente_row['discord_id']) if cliente_row else transporte['cliente_id']
            except:
                discord_id = transporte['cliente_id']
            
            await canal_ticket.send(
                content=f"<@{discord_id}>",
                embed=embed_aprovado
            )
        
        # ===== Enviar para Staff liberar acesso =====
        embed_acesso = discord.Embed(
            title="🔓 LIBERAR ACESSO À ILHA",
            description="Realize os passos abaixo no jogo",
            color=0x3498DB
        )
        embed_acesso.add_field(
            name="👤 Cliente",
            value=nick_jogo,
            inline=True
        )
        embed_acesso.add_field(
            name="🏘️ Cidade",
            value=origem,
            inline=True
        )
        embed_acesso.add_field(
            name="📝 Passos a fazer:",
            value="1️⃣ Vá até a ilha do cliente\n2️⃣ Prepare um baú para receber items\n3️⃣ Dê acesso ao cliente\n4️⃣ Clique em 'Acesso Liberado' com a opção de foto",
            inline=False
        )
        embed_acesso.set_footer(text="Ticket #{:04d}".format(numero_ticket))
        
        # View com botão para liberar acesso
        view_acesso = discord.ui.View(timeout=None)
        
        btn_liberar = discord.ui.Button(
            label="✅ Acesso Liberado",
            style=discord.ButtonStyle.success,
            custom_id=f"liberar_acesso_{transporte['id']}"
        )
        
        async def liberar_callback(inter):
            await self._liberar_acesso_ilha(inter, transporte, numero_ticket, canal_ticket)
        
        btn_liberar.callback = liberar_callback
        view_acesso.add_item(btn_liberar)
        
        # Procura canal staff
        canal_staff = None
        for ch in guild.channels:
            if "painel-staff" in ch.name:
                canal_staff = ch
                break
        
        if canal_staff:
            await canal_staff.send(embed=embed_acesso, view=view_acesso)
            print(f"   ✅ Enviado para staff liberar acesso")
        
        # Confirma para o staff que aprovou
        embed_conf = discord.Embed(
            title="✅ Pagamento Aprovado",
            description=f"Ticket #{transporte['numero_ticket']:04d} - Aguardando staff liberar acesso",
            color=0x2ECC71
        )
        
        await interaction.followup.send(embed=embed_conf, ephemeral=True)
        
        # Edita mensagem original no canal de análise
        try:
            msg_analise = await interaction.channel.fetch_message(
                interaction.message.id
            )
            embed_editado = msg_analise.embeds[0]
            embed_editado.color = 0x2ECC71
            embed_editado.set_footer(text="✅ APROVADO - Aguardando acesso à ilha")
            await msg_analise.edit(embed=embed_editado, view=None)
        except:
            pass
        
        print(f"✅ [APROVAR] Concluído\n")
    
    async def _liberar_acesso_ilha(self, interaction, transporte, numero_ticket, canal_ticket):
        """Staff libera acesso à ilha - foto OPCIONAL no canal"""
        
        print(f"\n🔓 [LIBERAR_ACESSO] Ticket-{numero_ticket}")
        
        await interaction.response.defer()
        
        # Busca dados do cliente
        try:
            conn = db.get_connection()
            conn.row_factory = sqlite3.Row
            cursor = db.get_wrapped_cursor(conn)
            cursor.execute("SELECT discord_id FROM clientes WHERE id = ?", (transporte['cliente_id'],))
            cliente_row = cursor.fetchone()
            conn.close()
            discord_id = int(cliente_row['discord_id']) if cliente_row else transporte['cliente_id']
        except:
            discord_id = transporte['cliente_id']
        
        # Envia para cliente
        embed_acesso_liberado = discord.Embed(
            title="🔓 ACESSO LIBERADO!",
            description="Seu acesso à ilha foi liberado pelo staff",
            color=0x2ECC71
        )
        embed_acesso_liberado.add_field(
            name="📝 Próximos Passos:",
            value="1️⃣ Vá até a ilha indicada\n2️⃣ Localize o baú preparado\n3️⃣ Deposite todos os items\n4️⃣ Clique em 'Confirmar Depósito'",
            inline=False
        )
        embed_acesso_liberado.set_footer(text="🎯 WHADAWEL™ | Transporte em progresso")
        
        # Cria view com botão de confirmar depósito
        view_deposito = discord.ui.View(timeout=None)
        
        btn_deposito = discord.ui.Button(
            label="✅ Confirmar Depósito de Items",
            style=discord.ButtonStyle.success,
            custom_id=f"confirmar_deposito_{transporte['id']}"
        )
        
        async def deposito_callback(dep_inter):
            await self._confirmar_deposito(dep_inter, transporte, numero_ticket)
        
        btn_deposito.callback = deposito_callback
        view_deposito.add_item(btn_deposito)
        
        # Envia para o cliente
        if canal_ticket:
            await canal_ticket.send(
                content=f"<@{discord_id}>",
                embed=embed_acesso_liberado,
                view=view_deposito
            )
        
        # Confirma para staff
        embed_confirmado = discord.Embed(
            title="✅ Acesso Liberado",
            description=f"Cliente informado - Aguardando depósito de items",
            color=0x2ECC71
        )
        
        await interaction.followup.send(embed=embed_confirmado, ephemeral=True)
        print(f"   ✅ Acesso liberado e cliente notificado\n")
    
    
    async def _processar_foto_deposito(self, message, numero_ticket):
        """Processa foto de depósito enviada no canal"""
        
        print(f"\n📸 [FOTO_DEPOSITO] Recebida em ticket-{numero_ticket}")
        
        # Valida se tem anexo
        if not message.attachments:
            print(f"   ❌ Nenhum anexo encontrado")
            return
        
        anexo = message.attachments[0]
        print(f"   Arquivo: {anexo.filename}")
        
        # Valida se é imagem
        if not anexo.content_type or not anexo.content_type.startswith('image/'):
            print(f"   ❌ Não é imagem: {anexo.content_type}")
            await message.reply(
                "❌ Arquivo inválido! Envie uma imagem (PNG, JPG, etc)",
                mention_author=False
            )
            return
        
        print(f"   ✅ Imagem válida: {anexo.content_type}")
        
        # Pega dados salvos
        dados = self.aguardando_foto_deposito[numero_ticket]
        transporte_id = dados['transporte_id']
        taxa_final = dados['taxa_final']
        prioridade = dados['prioridade']
        
        # Atualiza status
        db.update_transporte_status(transporte_id, STATUS["DEPOSITADO"])
        db.update_transporte(transporte_id, print_items_origem=anexo.url)
        
        print(f"   ✅ Status atualizado para DEPOSITADO")
        print(f"   ✅ Foto salva: {anexo.url[:50]}...")
        
        # Confirma para cliente
        embed_confirmado = discord.Embed(
            title="✅ DEPÓSITO CONFIRMADO!",
            description="Foto recebida e validada",
            color=0x2ECC71
        )
        embed_confirmado.add_field(
            name="📸 Evidência",
            value="Foto armazenada para segurança",
            inline=False
        )
        embed_confirmado.set_image(url=anexo.url)
        embed_confirmado.add_field(
            name="⏳ Próxima Etapa",
            value="Seu item está na fila de transporte!\nAguardando transportador iniciar...",
            inline=False
        )
        embed_confirmado.set_footer(text="🎯 WHADAWEL™")
        
        await message.reply(embed=embed_confirmado, mention_author=False)
        
        # ===== Enviar para fila de transporte =====
        guild = self.bot.get_guild(self.guild_id)
        canal_fila = None
        for ch in guild.channels:
            if "historico" in ch.name:
                canal_fila = ch
                break
        
        if canal_fila:
            embed_fila = discord.Embed(
                title="📦 NOVO ITEM NA FILA",
                description=f"Ticket #{numero_ticket:04d} - Pronto para transporte",
                color=0xFF9800
            )
            embed_fila.add_field(name="Prioridade", value=prioridade, inline=True)
            embed_fila.add_field(name="Valor", value=f"R$ {float(taxa_final):.2f}", inline=True)
            embed_fila.set_image(url=anexo.url)
            
            # View com botão para iniciar transporte
            view_transporte = discord.ui.View(timeout=None)
            
            btn_iniciar = discord.ui.Button(
                label="🚚 Iniciar Transporte",
                style=discord.ButtonStyle.primary,
                custom_id=f"iniciar_transporte_{transporte_id}"
            )
            
            # Busca canal ticket
            canal_ticket = message.channel
            
            async def iniciar_callback(init_inter):
                # Busca dados completos do transporte
                try:
                    conn = db.get_connection()
                    conn.row_factory = sqlite3.Row
                    cursor = db.get_wrapped_cursor(conn)
                    cursor.execute("SELECT * FROM transportes WHERE id = ?", (transporte_id,))
                    transporte_completo = cursor.fetchone()
                    conn.close()
                    
                    if transporte_completo:
                        await self._iniciar_transporte(init_inter, transporte_completo, numero_ticket, canal_ticket)
                    else:
                        await init_inter.response.defer()
                        await init_inter.followup.send("❌ Transporte não encontrado", ephemeral=True)
                except Exception as e:
                    print(f"   ❌ Erro ao buscar transporte: {e}")
                    await init_inter.response.defer()
                    await init_inter.followup.send(f"❌ Erro: {e}", ephemeral=True)
            
            btn_iniciar.callback = iniciar_callback
            view_transporte.add_item(btn_iniciar)
            
            await canal_fila.send(embed=embed_fila, view=view_transporte)
            print(f"   ✅ Enviado para fila com foto")
        
        # Remove do dicionário aguardando
        del self.aguardando_foto_deposito[numero_ticket]
        print(f"✅ [FOTO_DEPOSITO] Processamento concluído\n")

    async def _confirmar_deposito(self, interaction, transporte, numero_ticket):
        """Cliente confirma depósito de items - deve enviar FOTO no canal"""
        
        print(f"\n📦 [CONFIRMAR_DEPOSITO] Ticket-{numero_ticket}")
        
        await interaction.response.defer()
        
        # Busca canal ticket
        guild = self.bot.get_guild(self.guild_id)
        canal_ticket = None
        for ch in guild.channels:
            if ch.name == f"ticket-{numero_ticket}":
                canal_ticket = ch
                break
        
        if not canal_ticket:
            await interaction.followup.send("❌ Canal do ticket não encontrado", ephemeral=True)
            return
        
        # Envia mensagem pedindo foto
        embed_pedir_foto = discord.Embed(
            title="📸 ENVIE FOTO DO DEPÓSITO",
            description="Para confirmar o depósito, você deve enviar UMA ou MAIS fotos dos items já no baú",
            color=0xFF9800
        )
        embed_pedir_foto.add_field(
            name="📝 Próximo Passo:",
            value="1️⃣ Tire uma foto dos items no baú\n2️⃣ Envie a imagem **NESTE CANAL**\n3️⃣ Aguarde a confirmação automática",
            inline=False
        )
        embed_pedir_foto.add_field(
            name="✅ Depois que enviar a foto:",
            value="O bot confirmará automaticamente e seu transporte entrará na fila",
            inline=False
        )
        embed_pedir_foto.set_footer(text="🎯 WHADAWEL™ | Enviando arquivo...")
        
        await canal_ticket.send(embed=embed_pedir_foto)
        
        # Salva estado temporário
        self.aguardando_foto_deposito = getattr(self, 'aguardando_foto_deposito', {})
        self.aguardando_foto_deposito[numero_ticket] = {
            'transporte_id': transporte['id'],
            'cliente_id': transporte['cliente_id'],
            'taxa_final': transporte['taxa_final'],
            'prioridade': transporte['prioridade']
        }
        
        await interaction.followup.send(
            "✅ Aguardando sua foto no canal...\nEnvie a imagem que será confirmada automaticamente",
            ephemeral=True
        )
        print(f"   ⏳ Aguardando foto do cliente\n")

    
    async def _iniciar_transporte(self, interaction, transporte, numero_ticket, canal_ticket):
        """Transportador inicia o transporte"""
        
        print(f"\n🚚 [INICIAR_TRANSPORTE] Ticket-{numero_ticket}")
        
        await interaction.response.defer()
        
        # Atualiza status
        db.update_transporte_status(transporte['id'], STATUS["EM_TRANSPORTE"])
        
        # Notifica cliente
        embed_iniciado = discord.Embed(
            title="🚚 TRANSPORTE INICIADO!",
            description="Seu transporte foi iniciado e está a caminho",
            color=0xFF9800
        )
        embed_iniciado.add_field(
            name="📍 Status",
            value="Transportando items para Caerleon...",
            inline=False
        )
        embed_iniciado.set_footer(text="🎯 WHADAWEL™")
        
        guild = self.bot.get_guild(self.guild_id)
        try:
            conn = db.get_connection()
            conn.row_factory = sqlite3.Row
            cursor = db.get_wrapped_cursor(conn)
            cursor.execute("SELECT discord_id FROM clientes WHERE id = ?", (transporte['cliente_id'],))
            cliente_row = cursor.fetchone()
            conn.close()
            discord_id = int(cliente_row['discord_id']) if cliente_row else transporte['cliente_id']
        except:
            discord_id = transporte['cliente_id']
        
        if canal_ticket:
            await canal_ticket.send(
                content=f"<@{discord_id}>",
                embed=embed_iniciado
            )
        
        # Enviar para staff confirmar transporte
        embed_confirma = discord.Embed(
            title="✅ Confirmar Transporte",
            description=f"Transporte #{numero_ticket:04d} - Items entregues em Caerleon",
            color=0x3498DB
        )
        embed_confirma.add_field(
            name="📝 Passos:",
            value="1️⃣ Verifique se os items estão em Caerleon\n2️⃣ Tire uma foto (opcional)\n3️⃣ Clique em 'Transporte Confirmado'",
            inline=False
        )
        
        view_confirma = discord.ui.View(timeout=None)
        
        btn_confirmar = discord.ui.Button(
            label="✅ Transporte Confirmado",
            style=discord.ButtonStyle.success,
            custom_id=f"confirmar_transporte_{transporte['id']}"
        )
        
        async def confirmar_callback(conf_inter):
            await self._confirmar_transporte(conf_inter, transporte, numero_ticket, canal_ticket)
        
        btn_confirmar.callback = confirmar_callback
        view_confirma.add_item(btn_confirmar)
        
        # Procura canal staff
        canal_staff = None
        for ch in guild.channels:
            if "painel-staff" in ch.name:
                canal_staff = ch
                break
        
        if canal_staff:
            await canal_staff.send(embed=embed_confirma, view=view_confirma)
        
        # Confirma para quem iniciou
        await interaction.followup.send(
            "✅ Transporte iniciado! Aguardando confirmação da entrega...",
            ephemeral=True
        )
        print(f"   ✅ Transporte iniciado\n")
    
    async def _confirmar_transporte(self, interaction, transporte, numero_ticket, canal_ticket):
        """Staff confirma transporte entregue - foto OPCIONAL no canal"""
        
        print(f"\n✅ [CONFIRMAR_TRANSPORTE] Ticket-{numero_ticket}")
        
        await interaction.response.defer()
        
        # Busca cliente
        try:
            conn = db.get_connection()
            conn.row_factory = sqlite3.Row
            cursor = db.get_wrapped_cursor(conn)
            cursor.execute("SELECT discord_id FROM clientes WHERE id = ?", (transporte['cliente_id'],))
            cliente_row = cursor.fetchone()
            conn.close()
            discord_id = int(cliente_row['discord_id']) if cliente_row else transporte['cliente_id']
        except:
            discord_id = transporte['cliente_id']
        
        # Atualiza status para ENTREGUE
        db.update_transporte_status(transporte['id'], STATUS["ENTREGUE"])
        
        # Envia para cliente confirmar retirada
        embed_retirada = discord.Embed(
            title="📦 ITEMS ENTREGUES EM CAERLEON!",
            description="Seus items chegaram com segurança",
            color=0x2ECC71
        )
        embed_retirada.add_field(
            name="🎯 Próximo Passo:",
            value="1️⃣ Vá até Caerleon\n2️⃣ Retire todos os items\n3️⃣ Clique em 'Confirmar Retirada'",
            inline=False
        )
        embed_retirada.set_footer(text="🎯 WHADAWEL™ | Transporte Concluído")
        
        # View com botão final
        view_retirada = discord.ui.View(timeout=None)
        
        btn_retirada = discord.ui.Button(
            label="✅ Confirmar Retirada",
            style=discord.ButtonStyle.success,
            custom_id=f"confirmar_retirada_{transporte['id']}"
        )
        
        async def retirada_callback(ret_inter):
            await self._confirmar_retirada(ret_inter, transporte, numero_ticket)
        
        btn_retirada.callback = retirada_callback
        view_retirada.add_item(btn_retirada)
        
        # Envia para cliente
        if canal_ticket:
            await canal_ticket.send(
                content=f"<@{discord_id}>",
                embed=embed_retirada,
                view=view_retirada
            )
        
        # Confirma para staff
        embed_conf = discord.Embed(
            title="✅ Transporte Confirmado",
            description="Cliente foi notificado para retirar items",
            color=0x2ECC71
        )
        
        await interaction.followup.send(embed=embed_conf, ephemeral=True)
        print(f"   ✅ Transporte confirmado\n")
    
    async def _confirmar_retirada(self, interaction, transporte, numero_ticket):
        """Cliente confirma retirada - FIM DO FLUXO"""
        
        print(f"\n🎉 [CONFIRMAR_RETIRADA] Ticket-{numero_ticket} - FLUXO FINALIZADO")
        
        await interaction.response.defer()
        
        # Atualiza status final
        db.update_transporte_status(transporte['id'], STATUS["CONCLUIDO"])
        
        # Mensagem final
        embed_final = discord.Embed(
            title="🎉 TRANSPORTE CONCLUÍDO!",
            description="Obrigado por usar T.A.S Mania",
            color=0x2ECC71
        )
        embed_final.add_field(
            name="✨ Sucesso!",
            value="Seus items foram entregues com segurança\n\n**WHADAWEL garante qualidade! 💙**",
            inline=False
        )
        embed_final.add_field(
            name="📊 Estatísticas",
            value=f"Ticket: #{numero_ticket:04d}\nValor: R$ {float(transporte['taxa_final']):.2f}\nStatus: ✅ CONCLUÍDO",
            inline=False
        )
        embed_final.set_footer(text="🎯 WHADAWEL™ | Transportes Seguros desde 2024")
        
        # Busca canal
        guild = self.bot.get_guild(self.guild_id)
        canal_ticket = None
        for ch in guild.channels:
            if ch.name == f"ticket-{numero_ticket}":
                canal_ticket = ch
                break
        
        if canal_ticket:
            await canal_ticket.send(embed=embed_final)
        
        # ===== ENVIAR PARA HISTÓRICO-TAS =====
        print(f"   📝 Enviando para histórico-tas...")
        canal_historico = None
        for ch in guild.channels:
            if ch.name == "historico-tas":
                canal_historico = ch
                break
        
        if canal_historico:
            # Formata: Origem -> Destino ✅
            origem = transporte.get('origem', 'Desconhecida')
            destino = transporte.get('destino', 'Desconhecida')
            
            embed_historico = discord.Embed(
                title="✅ TRANSPORTE CONCLUÍDO",
                description=f"**{origem} → {destino}**",
                color=0x2ECC71
            )
            embed_historico.set_footer(text=f"Ticket #{numero_ticket:04d}")
            
            await canal_historico.send(embed=embed_historico)
            print(f"   ✅ Registrado em histórico-tas")
        
        await interaction.followup.send(
            "✅ Transporte finalizado com sucesso!",
            ephemeral=True
        )
        print(f"✅ [FLUXO COMPLETO] Ticket {numero_ticket} finalizado!\n")
    
    async def _rejeitar_pagamento(self, interaction, numero_ticket, msg_original):
        """Rejeita o pagamento pedindo nova foto"""
        
        print(f"\n❌ [REJEITAR] Pagamento do ticket-{numero_ticket}")
        
        await interaction.response.defer()
        
        # Busca canal do ticket
        guild = self.bot.get_guild(self.guild_id)
        canal_ticket = None
        for ch in guild.channels:
            if ch.name == f"ticket-{numero_ticket}":
                canal_ticket = ch
                break
        
        if canal_ticket:
            embed_rejeitado = discord.Embed(
                title="❌ Comprovante Rejeitado",
                description="O comprovante enviado não foi aceito",
                color=0xE74C3C
            )
            embed_rejeitado.add_field(
                name="🔍 Motivo Comum",
                value="• Imagem ilegível\n• Dados incompletos\n• Transferência não aparece",
                inline=False
            )
            embed_rejeitado.add_field(
                name="📸 Próxima Ação",
                value="Por favor, envie outra foto do comprovante\n✅ Certifique-se de que a imagem está clara e legível",
                inline=False
            )
            
            # Busca user
            user_obj = await self.bot.fetch_user(int(msg_original.author.id))
            
            embed_rejeitado.add_field(
                name="💬 Contato",
                value=f"Se houver dúvidas, abra uma mensagem em <#duvidas>",
                inline=False
            )
            
            await canal_ticket.send(embed=embed_rejeitado)
        
        # Confirma para o staff
        embed_conf = discord.Embed(
            title="❌ Pagamento Rejeitado",
            description=f"Ticket #{numero_ticket} - Cliente pedido para reenviador",
            color=0xE74C3C
        )
        
        await interaction.followup.send(embed=embed_conf, ephemeral=True)
        
        # Edita mensagem original no canal de análise
        try:
            msg_analise = await interaction.channel.fetch_message(
                interaction.message.id
            )
            embed_editado = msg_analise.embeds[0]
            embed_editado.color = 0xE74C3C
            embed_editado.set_footer(text="❌ REJEITADO - Aguardando nova imagem")
            await msg_analise.edit(embed=embed_editado, view=None)
        except:
            pass
        
        print(f"❌ [REJEITAR] Concluído\n")
    
    async def _corrigir_pagamento(self, interaction, numero_ticket, msg_original):
        """Marca para correção (valor diferente)"""
        
        print(f"\n🔧 [CORRIGIR] Pagamento do ticket-{numero_ticket}")
        
        # Modal para o staff inserir o valor correto
        class ModalValorCorreto(discord.ui.Modal):
            def __init__(self):
                super().__init__(title="💰 Valor Recebido", custom_id="modal_valor_corrigido")
                self.valor_input = discord.ui.TextInput(
                    label="Qual foi o valor recebido?",
                    placeholder="Ex: 40.32",
                    required=True
                )
                self.add_item(self.valor_input)
            
            async def on_submit(self, modal_interaction):
                try:
                    valor_recebido = float(self.valor_input.value)
                    
                    # Busca o transporte
                    conn = db.get_connection()
                    conn.row_factory = sqlite3.Row
                    cursor = db.get_wrapped_cursor(conn)
                    cursor.execute("""
                        SELECT * FROM transportes 
                        WHERE numero_ticket = ? 
                        ORDER BY id DESC LIMIT 1
                    """, (numero_ticket,))
                    transporte = cursor.fetchone()
                    conn.close()
                    
                    if not transporte:
                        await modal_interaction.response.send_message(
                            "❌ Transporte não encontrado",
                            ephemeral=True
                        )
                        return
                    
                    valor_esperado = transporte['valor_br']
                    
                    # Busca canal do ticket
                    guild = self.bot.get_guild(self.guild_id)
                    canal_ticket = None
                    for ch in guild.channels:
                        if ch.name == f"ticket-{numero_ticket}":
                            canal_ticket = ch
                            break
                    
                    if canal_ticket:
                        embed_diferenca = discord.Embed(
                            title="⚠️ Valor Diferente Detectado",
                            color=0xF39C12
                        )
                        embed_diferenca.add_field(
                            name="💵 Valor Esperado",
                            value=f"R$ {valor_esperado:.2f}",
                            inline=True
                        )
                        embed_diferenca.add_field(
                            name="💰 Valor Recebido",
                            value=f"R$ {valor_recebido:.2f}",
                            inline=True
                        )
                        embed_diferenca.add_field(
                            name="📊 Diferença",
                            value=f"R$ {abs(valor_esperado - valor_recebido):.2f}",
                            inline=False
                        )
                        
                        if valor_recebido < valor_esperado:
                            embed_diferenca.add_field(
                                name="⚡ Ação Necessária",
                                value=f"Faltam R$ {valor_esperado - valor_recebido:.2f}\nPor favor, envie o valor faltante",
                                inline=False
                            )
                        else:
                            embed_diferenca.add_field(
                                name="✅ Situação",
                                value="Valor acima do esperado! Será confirmado",
                                inline=False
                            )
                            # Aprova se recebeu mais
                            db.update_transporte_status(transporte['id'], STATUS["PAGO"])
                            embed_diferenca.color = 0x2ECC71
                        
                        await canal_ticket.send(embed=embed_diferenca)
                    
                    await modal_interaction.response.send_message(
                        f"✅ Valor registrado: R$ {valor_recebido:.2f}",
                        ephemeral=True
                    )
                    
                except ValueError:
                    await modal_interaction.response.send_message(
                        "❌ Valor inválido. Use formato: 40.32",
                        ephemeral=True
                    )
        
        await interaction.response.send_modal(ModalValorCorreto())
        print(f"🔧 [CORRIGIR] Modal enviado\n")


async def setup(bot):
    await bot.add_cog(PaymentVerification(bot))
    print("✅ Cog Payment Verification carregado")
