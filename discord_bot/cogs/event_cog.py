import discord
from discord.ext import commands, tasks

from data_class.profile import ProfileData, ProfileDataBase
from data_control import ServerControl

CHANNEL_ID = 1321307463550767154
ON_MEM_ADD_DM = """
Доброго времени суток, {user}!

Всю выжимку полезной информации вы можете найти в канале <#1358046882059780136>.
По вопросом не стесняйтесь обращаться в <#1361032640760905748>.

Немного ссылкок:
В случае если вы хотите связаться по вопросам сотрудничества: https://spf-base.ru/wiki/docs/cooperation
Каналы для анонимных отзывов: https://spf-base.ru/feedback
"""
ON_MEM_REM_DM = """
Нам жаль, что вы покидаете проект, {user}!

Если несложно - оставьте отзыв. Это можно сделать анонимно.
Форма тут: https://spf-base.ru/leave_feedback
"""


class EventCog(commands.Cog):
    def __init__(self, bot):
        self.bot: commands.Bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        if not self.update_status.is_running():
            channel = self.bot.get_channel(1321317710222721054)
            if channel:
                await channel.send(str(self.update_status.is_running()))
            self.update_status.start()
            if channel:
                await channel.send(str(self.update_status.is_running()))

        await self.update_status()

    async def send_to_dm(
        self,
        member: discord.Member,
        text: str,
    ) -> None:
        try:
            await member.send(text.format(user=member.display_name))

        except discord.Forbidden:
            pass

    async def sent_to_newmembers_channel(
        self,
        member: discord.Member,
        title: str,
        description: str,
        color: discord.Color,
    ) -> None:
        channel = self.bot.get_channel(CHANNEL_ID)
        if channel is None or not isinstance(channel, discord.TextChannel):
            return

        embed = discord.Embed(
            title=title,
            description=description,
            color=color,
            timestamp=discord.utils.utcnow(),
        )
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.add_field(name="Имя", value=str(member), inline=True)
        embed.add_field(name="ID", value=str(member.id), inline=True)
        embed.add_field(name="Mention", value=member.mention, inline=True)

        await channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        await self.send_to_dm(member, ON_MEM_ADD_DM)
        await self.sent_to_newmembers_channel(
            member,
            "Боец прибыл на службу!",
            "Добро пожаловать в Ч.В.К. S.P.F.!",
            color=discord.Color.green(),
        )

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        await self.send_to_dm(member, ON_MEM_REM_DM)
        await self.sent_to_newmembers_channel(
            member,
            "Боец покинул ряды",
            "Боец покинул ряды Ч.В.К. S.P.F.",
            color=discord.Color.red(),
        )

    @tasks.loop(minutes=1)
    async def update_status(self):
        channel = self.bot.get_channel(1321317710222721054)

        if channel:
            await channel.send("f")
        status = ServerControl.get_status()
        if status == "Включен":
            activity = discord.Game(name="Garry's mod, server spf-base.ru")
            status = discord.Status.online

        else:
            activity = discord.CustomActivity(name="Кушает RAM сервера...")
            status = discord.Status.idle

        if channel:
            await channel.send(f"fucku: {status}")

        await self.bot.change_presence(activity=activity, status=status)

    def _get_admin_profile(self, discord_id: int) -> dict | None:
        profile = ProfileDataBase.get_profile_by_discord(str(discord_id))
        if not profile:
            return None

        data = profile.get("data", ProfileData())
        if not isinstance(data, ProfileData):
            return None

        return profile if data.has_access("full_access") else None

    @commands.command(name="update_status")
    async def update_status_cmd(self, ctx: commands.Context):
        profile = self._get_admin_profile(ctx.author.id)

        if profile is None:
            await ctx.message.add_reaction("\U0000274c")
            return

        await self.update_status()
        await ctx.message.add_reaction("\U00002705")
