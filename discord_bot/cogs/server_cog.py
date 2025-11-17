from datetime import datetime, time
from zoneinfo import ZoneInfo

import discord
from discord.ext import commands, tasks

from data_class import ProfileData, ProfileDataBase
from data_control import ServerControl, ServerStatus

ANNOUNCE_CHANNEL_ID = 1321307574242377769


class ServerControlCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.announcement_texts = {
            "start": "<@&1358390418613469355>\nСервер запущен",
            "stop": "<@&1358390418613469355>\nСервер оффлаин",
            "6_am": "<@&1358390418613469355>\nЯ отправила сервер спатки",
        }
        if not self.autostop_task.is_running():
            self.autostop_task.start()

    def _get_admin_profile(self, discord_id: int) -> dict | None:
        profile = ProfileDataBase.get_profile_by_discord(str(discord_id))
        if not profile:
            return None

        data = profile.get("data", ProfileData())
        if not isinstance(data, ProfileData):
            return None

        return profile if data.has_access("server_control") else None

    async def _do_action(self, ctx: commands.Context, action: str) -> None:
        profile = self._get_admin_profile(ctx.author.id)
        if profile is None:
            await ctx.message.add_reaction("\u274c")
            return

        server_stat = ServerControl.get_status()
        if server_stat in [ServerStatus.FAILED, ServerStatus.UNKNOWN]:
            await ctx.message.add_reaction("\u274c")
            await ctx.reply(
                "Серверу что-то не хорошо. Трогать в таком состоянии я его не буду. Сообщите Кайну о проблеме"
            )
            return

        if (
            server_stat in [ServerStatus.RUNNING, ServerStatus.START]
            and action == "start"
        ) or (
            server_stat in [ServerStatus.STOP, ServerStatus.DEAD] and action == "stop"
        ):
            await ctx.message.add_reaction("\u274c")
            await ctx.reply(
                f"Нельзя выполнить `{action}`, сервер уже `{server_stat.value}`"
            )
            return

        if action in ["start", "stop", "restart"]:
            ServerControl.perform_action(action)  # pyright: ignore[reportArgumentType]
            await ctx.message.add_reaction("\u2705")

        else:
            await ctx.message.add_reaction("\u274c")
            await ctx.reply("Неверный параметр\n`!server <start|stop|restart>`")

        channel = self.bot.get_channel(ANNOUNCE_CHANNEL_ID)
        if channel and isinstance(channel, discord.TextChannel):
            text = self.announcement_texts.get(action)
            if text:
                try:
                    await channel.send(text)

                except Exception as e:
                    await ctx.reply(f"Не удалось отправить уведомление: {e}")

    @tasks.loop(minutes=1)
    async def autostop_task(self):
        now = datetime.now(ZoneInfo("Europe/Moscow")).time()
        target = time(6, 0)
        if now.hour == target.hour and now.minute == target.minute:
            if ServerControl.get_status() is ServerStatus.RUNNING:
                ServerControl.perform_action("stop")
                channel = self.bot.get_channel(ANNOUNCE_CHANNEL_ID)
                if channel and isinstance(channel, discord.TextChannel):
                    await channel.send(self.announcement_texts["6_am"])

    @commands.command(name="server")
    async def server_cmd(self, ctx: commands.Context, action: str | None = None):
        profile = self._get_admin_profile(ctx.author.id)
        if profile is None:
            await ctx.message.add_reaction("\u274c")
            return

        if action is None:
            await ctx.message.add_reaction("\u274c")
            await ctx.reply(
                "Нужно указать действие: `!server start`, `!server stop` или `!server status`"
            )
            return

        action = action.lower()
        if action == "status":
            status = ServerControl.get_status()
            await ctx.message.add_reaction("\u2705")
            await ctx.reply(f"Текущее состояние сервера: `{status.value}`")
            return

        await self._do_action(ctx, action)
