import discord
from discord.ext import commands, tasks

from data_control import ServerControl


class EventCog(commands.Cog):
    def __init__(self, bot):
        self.bot: commands.Bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        await self.update_status()

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        try:
            text = (
                "Нам жаль, что вы покидаете проект.\n\n"
                "Если несложно - оставьте отзыв. Это можно сделать анонимно.\n"
                "Форма тут: https://spf-base.ru/leave_feedback"
            )
            await member.send(text)

        except discord.Forbidden:
            pass

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
