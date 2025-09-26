from typing import Any

import discord
from discord.ext import commands


class DebugCog(commands.Cog):
    def __init__(self, bot):
        self.bot: commands.Bot = bot

    async def send_to_admins(self, value: Any):
        ch = self.bot.get_channel(1321317710222721054)
        if ch is not None and isinstance(ch, discord.TextChannel):
            await ch.send(str(value))
