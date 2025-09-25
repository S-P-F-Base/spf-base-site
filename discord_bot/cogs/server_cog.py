from discord.ext import commands

from data_class import ProfileData, ProfileDataBase
from data_control import ServerControl


class ServerControlCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    def _get_admin_profile(self, discord_id: int) -> dict | None:
        profile = ProfileDataBase.get_profile_by_discord(str(discord_id))
        if not profile:
            return None
        data = profile.get("data")
        if not isinstance(data, ProfileData):
            return None
        return profile if data.is_admin else None

    async def _do_action(self, ctx: commands.Context, action: str) -> None:
        user_id = ctx.author.id
        profile = await ctx.bot.loop.run_in_executor(
            None, self._get_admin_profile, user_id
        )

        if not profile:
            await ctx.reply("Отказано в доступе")
            return

        if action == "start":
            ServerControl.perform_action("start")
            await ctx.reply("Сервер запущен.")

        elif action == "stop":
            ServerControl.perform_action("stop")
            await ctx.reply("Сервер остановлен.")

        else:
            await ctx.reply(
                "Неверный параметр. Используй `!server start` или `!server stop`."
            )

    @commands.command(name="server")
    async def server_cmd(self, ctx: commands.Context, action: str):
        await self._do_action(ctx, action.lower())
