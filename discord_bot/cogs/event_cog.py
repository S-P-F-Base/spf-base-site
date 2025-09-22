import discord
from discord.ext import commands, tasks

from data_control import ServerControl


class EventCog(commands.Cog):
    def __init__(self, bot):
        self.bot: commands.Bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        await self.update_status()

        channel = self.bot.get_channel(1321317710222721054)
        if channel and isinstance(channel, discord.TextChannel):
            await channel.send("Setup done")

    @tasks.loop(minutes=5)
    async def update_status(self):
        status = ServerControl.get_status()
        if status == "Включён":
            activity = discord.Game(name="Garry's mod, server spf-base.ru")
            status = discord.Status.online

        else:
            activity = discord.CustomActivity(name="Кушает RAM сервера...")
            status = discord.Status.idle

        await self.bot.change_presence(activity=activity, status=status)
