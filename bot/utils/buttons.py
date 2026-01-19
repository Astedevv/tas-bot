"""
Utilitários para criar componentes de botões e selects
"""
import discord
from config import ORIGENS

class BotaoOrigem(discord.ui.Select):
    """Select para escolher origem"""
    def __init__(self, callback_func):
        options = [
            discord.SelectOption(label=origem, value=origem)
            for origem in ORIGENS
        ]
        super().__init__(
            placeholder="Escolha a origem...",
            min_values=1,
            max_values=1,
            options=options,
            custom_id="select_origem"
        )
        self.callback_func = callback_func
    
    async def callback(self, interaction: discord.Interaction):
        await self.callback_func(interaction, self.values[0])

class BotaoPrioridade(discord.ui.View):
    """Botões para escolher prioridade"""
    def __init__(self, callback_func):
        super().__init__()
        self.callback_func = callback_func
    
    @discord.ui.button(label="🕒 Normal", style=discord.ButtonStyle.gray, custom_id="btn_normal")
    async def normal(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.callback_func(interaction, "NORMAL")
    
    @discord.ui.button(label="⚡ Alta (+20%)", style=discord.ButtonStyle.danger, custom_id="btn_alta")
    async def alta(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.callback_func(interaction, "ALTA")

class ModalValor(discord.ui.Modal):
    """Modal para inserir valor estimado"""
    def __init__(self, callback_func):
        super().__init__(title="Valor da Carga", custom_id="modal_valor")
        self.callback_func = callback_func
        self.valor = discord.ui.TextInput(
            label="Valor em prata (ex: 18500000)",
            placeholder="Apenas números",
            required=True,
            min_length=2,
            max_length=20
        )
        self.add_item(self.valor)
    
    async def on_submit(self, interaction: discord.Interaction):
        valor_text = self.valor.value.replace(".", "").replace(",", "")
        try:
            valor = int(valor_text)
            await self.callback_func(interaction, valor)
        except ValueError:
            await interaction.response.send_message(
                "❌ Valor inválido! Use apenas números.",
                ephemeral=True
            )

class ModalObservacoes(discord.ui.Modal):
    """Modal para observações opcionais"""
    def __init__(self, callback_func):
        super().__init__(title="Observações (Opcional)", custom_id="modal_obs")
        self.callback_func = callback_func
        self.obs = discord.ui.TextInput(
            label="Observações",
            placeholder="Ex: Peso alto, itens refinados...",
            required=False,
            max_length=500,
            style=discord.TextStyle.paragraph
        )
        self.add_item(self.obs)
    
    async def on_submit(self, interaction: discord.Interaction):
        await self.callback_func(interaction, self.obs.value or "Nenhuma")

class ViewConfirmarDeposito(discord.ui.View):
    """View com botão de confirmação de depósito"""
    def __init__(self, callback_func):
        super().__init__()
        self.callback_func = callback_func
    
    @discord.ui.button(label="✅ Confirmei Depósito", style=discord.ButtonStyle.success, custom_id="btn_confirmar_dep")
    async def confirmar(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.callback_func(interaction, True)
    
    @discord.ui.button(label="❌ Cancelar", style=discord.ButtonStyle.danger, custom_id="btn_cancelar_dep")
    async def cancelar(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.callback_func(interaction, False)

class ModalConfirmarDeposito(discord.ui.Modal):
    """Modal de confirmação de depósito"""
    def __init__(self, callback_func):
        super().__init__(title="Confirmar Depósito", custom_id="modal_confirmar_dep")
        self.callback_func = callback_func
        self.comprovante = discord.ui.TextInput(
            label="Cole o link da imagem ou descrição",
            placeholder="Envie uma imagem neste canal ou cole o link",
            required=True,
            max_length=500,
            style=discord.TextStyle.paragraph
        )
        self.add_item(self.comprovante)
        self.confirmacao = discord.ui.TextInput(
            label="Digite 'SIM' para confirmar",
            placeholder="SIM",
            required=True,
            max_length=3
        )
        self.add_item(self.confirmacao)
    
    async def on_submit(self, interaction: discord.Interaction):
        if self.confirmacao.value.upper() == "SIM":
            await self.callback_func(interaction, True)
        else:
            await interaction.response.send_message(
                "❌ Digite exatamente 'SIM' para confirmar!",
                ephemeral=True
            )

class ViewControleStaff(discord.ui.View):
    """View com botões de controle para staff"""
    def __init__(self, callback_validar, callback_rejeitar):
        super().__init__()
        self.callback_validar = callback_validar
        self.callback_rejeitar = callback_rejeitar
    
    @discord.ui.button(label="✅ Validar Pagamento", style=discord.ButtonStyle.success, custom_id="btn_validar_pag")
    async def validar(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.callback_validar(interaction)
    
    @discord.ui.button(label="❌ Rejeitar Pagamento", style=discord.ButtonStyle.danger, custom_id="btn_rejeitar_pag")
    async def rejeitar(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.callback_rejeitar(interaction)

class ViewControleTransporte(discord.ui.View):
    """View com botões para controlar transporte"""
    def __init__(self, callback_iniciar, callback_confirmar):
        super().__init__()
        self.callback_iniciar = callback_iniciar
        self.callback_confirmar = callback_confirmar
    
    @discord.ui.button(label="🚀 Iniciar Transporte", style=discord.ButtonStyle.primary, custom_id="btn_iniciar_trans")
    async def iniciar(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.callback_iniciar(interaction)
    
    @discord.ui.button(label="📸 Confirmar Entrega", style=discord.ButtonStyle.success, custom_id="btn_confirmar_trans")
    async def confirmar(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.callback_confirmar(interaction)

class ViewConfirmarEntrega(discord.ui.View):
    """View para cliente confirmar entrega"""
    def __init__(self, callback_func):
        super().__init__()
        self.callback_func = callback_func
    
    @discord.ui.button(label="✅ Confirmei Retirada", style=discord.ButtonStyle.success, custom_id="btn_confirmar_ret")
    async def confirmar(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.callback_func(interaction, True)
