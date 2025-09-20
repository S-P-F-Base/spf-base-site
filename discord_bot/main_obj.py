import discord
from discord.ext import commands

intents = discord.Intents.all()

bot = commands.Bot(command_prefix="!", intents=intents)


@bot.event
async def on_ready():
    print(f"Discord bot logged in as {bot.user}")
    channel = bot.get_channel(1321317710222721054)
    if channel:
        await channel.send("Setup done")


@bot.command()
async def ping(ctx):
    await ctx.send("Pong!")
