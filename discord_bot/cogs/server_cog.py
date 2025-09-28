import discord
from discord.ext import commands

from data_class import ProfileData, ProfileDataBase
from data_control import ServerControl

ANNOUNCE_CHANNEL_ID = 1321307574242377769


class ServerControlCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.announcement_texts = {
            "start": "<@&1358390418613469355>\nСервер запущен",
            "stop": "<@&1358390418613469355>\nСервер оффлаин",
        }

    def _get_admin_profile(self, discord_id: int) -> dict | None:
        profile = ProfileDataBase.get_profile_by_discord(str(discord_id))
        if not profile:
            return None

        data = profile.get("data", ProfileData())
        if not isinstance(data, ProfileData):
            return None

        return profile if data.access.get("server_control", False) else None

    async def _do_action(self, ctx: commands.Context, action: str) -> None:
        profile = self._get_admin_profile(ctx.author.id)

        if profile is None:
            await ctx.reply(f"Ошибка доступа к команде, {ctx.author.id}")
            return

        if action == "start":
            ServerControl.perform_action("start")
            await ctx.reply("Сервер запущен")

        elif action == "stop":
            ServerControl.perform_action("stop")
            await ctx.reply("Сервер остановлен")

        else:
            await ctx.reply("Неверный параметр\n`!server start`\n`!server stop`")
            return

        channel = self.bot.get_channel(ANNOUNCE_CHANNEL_ID)
        if channel:
            text = self.announcement_texts.get(action)
            if text and isinstance(channel, discord.TextChannel):
                try:
                    await channel.send(text)

                except Exception as e:
                    await ctx.reply(f"Не удалось отправить уведомление: {e}")

    @commands.command(name="server")
    async def server_cmd(self, ctx: commands.Context, action: str):
        await self._do_action(ctx, action.lower())
