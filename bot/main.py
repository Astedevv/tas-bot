"""
Main - Bot T.A.S Mania
"""
import discord
from discord.ext import commands
import os
from dotenv import load_dotenv
import asyncio

load_dotenv()

# Configurações
BOT_TOKEN = os.getenv("BOT_TOKEN")
GUILD_ID = int(os.getenv("GUILD_ID", 0))

# Intents
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

# Bot
bot = commands.Bot(command_prefix="/", intents=intents)

@bot.event
async def on_ready():
    """Evento quando o bot conecta"""
    print(f"\n{'='*50}")
    print(f"✅ Bot conectado como: {bot.user}")
    print(f"   ID: {bot.user.id}")
    print(f"   Guild: {GUILD_ID}")
    print(f"{'='*50}\n")
    
    # Sincroniza comandos slash
    try:
        synced = await bot.tree.sync()
        print(f"✅ {len(synced)} comandos sincronizados")
    except Exception as e:
        print(f"❌ Erro ao sincronizar: {e}")

@bot.event
async def on_guild_join(guild):
    """Evento quando bot entra em um servidor"""
    print(f"📩 Bot adicionado ao servidor: {guild.name}")

@bot.event
async def on_interaction(interaction: discord.Interaction):
    """Evento de interação (botões, select, modais)"""
    # Emit custom event para cogs
    if interaction.type == discord.InteractionType.component:
        bot.dispatch("button_click", interaction)

async def load_cogs():
    """Carrega todos os cogs"""
    base_dir = os.path.dirname(__file__)
    cogs_dir = os.path.join(base_dir, "cogs")

    # Determine package prefix (ex: 'bot') to import extensions reliably
    package_prefix = os.path.basename(base_dir) or None

    for filename in os.listdir(cogs_dir):
        if filename.endswith(".py") and not filename.startswith("__"):
            cog_name = filename[:-3]
            try:
                if package_prefix:
                    await bot.load_extension(f"{package_prefix}.cogs.{cog_name}")
                else:
                    await bot.load_extension(f"cogs.{cog_name}")
                print(f"✅ Cog carregado: {cog_name}")
            except Exception as e:
                print(f"❌ Erro ao carregar {cog_name}: {e}")

async def main():
    """Função principal"""
    async with bot:
        # Carrega cogs
        await load_cogs()
        
        # Conecta ao Discord
        await bot.start(BOT_TOKEN)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Bot desconectando...")
    except Exception as e:
        print(f"\n❌ Erro fatal: {e}")
