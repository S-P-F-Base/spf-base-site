import discord
from discord.ext import commands

from data_control import Config

ROLE_VALUES: dict[int, tuple[int, int]] = {
    1389261673726218260: (75, 3),  # Первопроходец
}
DEFAULT_VALUE = (50, 2)


class UserControlCog(commands.Cog):
    def __init__(self, bot):
        self.bot: commands.Bot = bot

    async def get_user_info(self, user_id: int) -> dict:
        user = await self.bot.fetch_user(user_id)
        return {
            "username": user.name,
            "avatar_url": user.display_avatar.url,
        }

    async def get_role_value(self, user_id: int) -> tuple[int, int]:
        guild: discord.Guild = self.bot.get_guild(int(Config.discord_guild_id()))  # type: ignore
        if not guild:
            raise RuntimeError("Guild error")

        member = guild.get_member(user_id)
        if member is None:
            member = await guild.fetch_member(user_id)
        if member is None:
            return DEFAULT_VALUE

        max_value = DEFAULT_VALUE
        for role in member.roles:
            value = ROLE_VALUES.get(role.id)
            if value and value > max_value:
                max_value = value

        return max_value

    @commands.command(name="userinfo")
    async def userinfo(self, ctx: commands.Context, user_id: int):
        data = await self.get_user_info(user_id)
        await ctx.send(str(data))
