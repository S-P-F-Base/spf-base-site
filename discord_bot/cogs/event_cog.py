import discord
from discord.ext import commands, tasks

from data_class.profile import ProfileData, ProfileDataBase
from data_control import ServerControl, ServerStatus

from .etc import NEW_MEMBER_CHANNEL_ID, add_nope, add_yep

ON_MEM_ADD_DM = """
Доброго времени суток, {user}!

Всю выжимку полезной информации вы можете найти в канале <#1358046882059780136>.
По вопросом не стесняйтесь обращаться в <#1361032640760905748>.

Немного ссылкок:
Часто задаваемые вопросы: <#1427916856903209000>
В случае если вы хотите связаться по вопросам сотрудничества: https://spf-base.ru/wiki/docs/cooperation
Каналы для анонимных отзывов: https://spf-base.ru/feedback
"""


class EventCog(commands.Cog):
    def __init__(self, bot):
        self.bot: commands.Bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        if not self.update_status.is_running():
            self.update_status.start()

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
        channel = self.bot.get_channel(NEW_MEMBER_CHANNEL_ID)
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
        await self.sent_to_newmembers_channel(
            member,
            "Боец покинул ряды",
            "Боец покинул ряды Ч.В.К. S.P.F.",
            color=discord.Color.red(),
        )

    @tasks.loop(minutes=5)
    async def update_status(self):
        service_status = ServerControl.get_status()

        match service_status:
            case ServerStatus.RUNNING:
                activity = discord.Game(name="Garry's Mod, server spf-base.ru")
                discord_status = discord.Status.online

            case ServerStatus.DEAD:
                activity = discord.CustomActivity(name="Кушает RAM...")
                discord_status = discord.Status.idle

            case ServerStatus.FAILED:
                activity = discord.CustomActivity(name="Уронила сервер насмерть!")
                discord_status = discord.Status.dnd

            case ServerStatus.START:
                activity = discord.CustomActivity(
                    name="Прикладывает лапки к запуску сервера..."
                )
                discord_status = discord.Status.idle

            case ServerStatus.STOP:
                activity = discord.CustomActivity(
                    name="Прикладывает лапки к остановке сервера..."
                )
                discord_status = discord.Status.idle

            case _:
                activity = discord.CustomActivity(
                    name="Не может понять что с сервером.... Сообщите Кайну"
                )
                discord_status = discord.Status.dnd

        await self.bot.change_presence(activity=activity, status=discord_status)

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
            await add_nope(ctx.message)
            return

        await self.update_status()
        await add_yep(ctx.message)
