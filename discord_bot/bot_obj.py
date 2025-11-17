import discord
from discord.ext import commands

from data_control import Config

from .cogs import (
    CommandsCog,
    EventCog,
    ForumControlCog,
    PlayerCog,
    ServerControlCog,
    UserControlCog,
    AIManager
)

intents = discord.Intents.all()

bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)


async def start():
    for cls in [
        CommandsCog,
        EventCog,
        ForumControlCog,
        PlayerCog,
        ServerControlCog,
        UserControlCog,
        AIManager
    ]:
        await bot.add_cog(cls(bot))

    await bot.start(Config.discord_bot())


async def stop():
    await bot.close()
