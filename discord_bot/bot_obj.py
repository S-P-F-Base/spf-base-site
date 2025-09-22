import discord
from discord.ext import commands

from data_control import Config

from .cogs import EventCog

intents = discord.Intents.all()

bot = commands.Bot(command_prefix="!", intents=intents)


async def start():
    await bot.add_cog(EventCog(bot))
    await bot.start(Config.discord_bot())


async def stop():
    await bot.close()
