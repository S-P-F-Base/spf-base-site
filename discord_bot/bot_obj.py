import discord
from discord.ext import commands

from data_control import Config

from .cogs import (
    DebugCog,
    EventCog,
    ForumBlockCog,
    ServerControlCog,
    UserControlCog,
)

intents = discord.Intents.all()

bot = commands.Bot(command_prefix="!", intents=intents)


async def start():
    for cls in [
        DebugCog,
        EventCog,
        ForumBlockCog,
        ServerControlCog,
        UserControlCog,
    ]:
        await bot.add_cog(cls(bot))

    await bot.start(Config.discord_bot())


async def stop():
    await bot.close()
