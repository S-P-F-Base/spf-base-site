from datetime import datetime
from functools import wraps
from zoneinfo import ZoneInfo

import discord
from discord.ext import commands, tasks

from data_class import ProfileData, ProfileDataBase
from data_control import ServerControl, ServerStatus

ANNOUNCE_CHANNEL_ID = 1321307574242377769


def server_admin_only(func):
    @wraps(func)
    async def wrapper(self, ctx: commands.Context, *args, **kwargs):
        profile = ProfileDataBase.get_profile_by_discord(str(ctx.author.id))
        data = profile.get("data") if profile else None
        if not isinstance(data, ProfileData) or not data.has_access("server_control"):
            await ctx.message.add_reaction("\u274c")
            return

        return await func(self, ctx, *args, **kwargs)

    return wrapper


class ServerControlCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.announcement_texts = {
            "start": "<@&1358390418613469355>\nЯ лапками запустила сервер",
            "stop": "<@&1358390418613469355>\nЯ лапками выключила сервер",
            "6_am": "<@&1358390418613469355>\nЯ отправила сервер спатки",
        }
        if not self.autostop_task.is_running():
            self.autostop_task.start()

    async def _announce(self, action: str):
        channel = self.bot.get_channel(ANNOUNCE_CHANNEL_ID)
        if channel and isinstance(channel, discord.TextChannel):
            text = self.announcement_texts.get(action)
            if text:
                try:
                    await channel.send(text)

                except Exception as e:
                    return f"Не удалось отправить уведомление: {e}"

        return None

    def _can_perform(self, action: str) -> bool:
        status = ServerControl.get_status()

        match action:
            case "start":
                return status not in [ServerStatus.RUNNING, ServerStatus.START]

            case "stop":
                return status not in [ServerStatus.STOP, ServerStatus.DEAD]

            case "restart":
                return status not in [ServerStatus.STOP, ServerStatus.DEAD]

        return False

    async def _perform_action(self, ctx: commands.Context, action: str):
        status = ServerControl.get_status()

        if status in [ServerStatus.FAILED, ServerStatus.UNKNOWN]:
            await ctx.message.add_reaction("\u274c")
            await ctx.reply(
                "Сервер сложил лапки намертво, или ведёт себя странно. Я не буду выполнять вашу команду. Свяжитесь с Кайном"
            )
            return

        if not self._can_perform(action):
            await ctx.message.add_reaction("\u274c")
            st = {
                ServerStatus.DEAD: "остановлен",
                ServerStatus.STOP: "останавливается",
                ServerStatus.START: "запускается",
                ServerStatus.RUNNING: "запущен",
            }.get(status, "Неизвестно")
            await ctx.reply(f"Нельзя выполнить `{action}` если сервер {st}")
            return

        ServerControl.perform_action(action)  # pyright: ignore[reportArgumentType]
        await ctx.message.add_reaction("\u2705")

        announce_key = "start" if action in ["start", "restart"] else action
        await self._announce(announce_key)

    @tasks.loop(minutes=1)
    async def autostop_task(self):
        now = datetime.now(ZoneInfo("Europe/Moscow")).time()
        if (
            ServerControl.get_status() is ServerStatus.RUNNING
            and now.hour == 6
            and now.minute == 0
        ):
            ServerControl.perform_action("stop")
            await self._announce("6_am")

    @commands.group(name="server", invoke_without_command=True)
    @server_admin_only
    async def server(self, ctx: commands.Context):
        await ctx.send("Используй подкоманду: `start`, `stop`, `restart` или `status`")

    @server.command(name="start")
    @server_admin_only
    async def start(self, ctx: commands.Context):
        await self._perform_action(ctx, "start")

    @server.command(name="stop")
    @server_admin_only
    async def stop(self, ctx: commands.Context):
        await self._perform_action(ctx, "stop")

    @server.command(name="restart")
    @server_admin_only
    async def restart(self, ctx: commands.Context):
        await self._perform_action(ctx, "restart")

    @server.command(name="status")
    @server_admin_only
    async def status(self, ctx: commands.Context):
        status = ServerControl.get_status()
        await ctx.message.add_reaction("\u2705")
        await ctx.reply(f"Текущее состояние сервера: `{status.value}`")
