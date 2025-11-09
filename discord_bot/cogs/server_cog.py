from datetime import datetime, time
from zoneinfo import ZoneInfo

import discord
from discord.ext import commands, tasks

from data_class import ProfileData, ProfileDataBase
from data_control import ServerControl

ANNOUNCE_CHANNEL_ID = 1321307574242377769


class ServerControlCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.announcement_texts = {
            "start": "<@&1358390418613469355>\nСервер запущен",
            "stop": "<@&1358390418613469355>\nСервер оффлаин",
            "6_am": "<@&1358390418613469355>\nЯ отправила сервер спатки",
        }

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
            await ctx.message.add_reaction("\U0000274c")
            return

        server_stat = ServerControl.get_status()
        if (server_stat == "Включен" and action == "start") or (
            server_stat == "Выключен" and action == "stop"
        ):
            await ctx.message.add_reaction("\U0000274c")
            await ctx.reply(
                f"Нельзя запустить `{action}` если сервер уже `{server_stat}`"
            )
            return

        if action == "start":
            ServerControl.perform_action("start")
            await ctx.message.add_reaction("\U00002705")

        elif action == "stop":
            ServerControl.perform_action("stop")
            await ctx.message.add_reaction("\U00002705")

        else:
            await ctx.message.add_reaction("\U0000274c")
            await ctx.reply("Неверный параметр\n`!server start`\n`!server stop`")

        channel = self.bot.get_channel(ANNOUNCE_CHANNEL_ID)
        if channel:
            text = self.announcement_texts.get(action)
            if text and isinstance(channel, discord.TextChannel):
                try:
                    await channel.send(text)

                except Exception as e:
                    await ctx.reply(f"Не удалось отправить уведомление: {e}")

    @tasks.loop(minutes=1)
    async def autostop_task(self):
        now = datetime.now(ZoneInfo("Europe/Moscow")).time()
        target = time(6, 0)

        if now.hour == target.hour and now.minute == target.minute:
            ServerControl.perform_action("stop")

            channel = self.bot.get_channel(ANNOUNCE_CHANNEL_ID)
            if channel and isinstance(channel, discord.TextChannel):
                await channel.send(self.announcement_texts["6_am"])

    @commands.command(name="server")
    async def server_cmd(self, ctx: commands.Context, action: str | None = None):
        profile = self._get_admin_profile(ctx.author.id)

        if profile is None:
            await ctx.message.add_reaction("\U0000274c")
            return

        if action is None:
            await ctx.message.add_reaction("\U0000274c")
            await ctx.reply(
                "Нужно указать действие: `!server start`, `!server stop` или `!server status`"
            )
            return

        action = action.lower()

        ACTIONS = {
            "start": {"type": "action"},
            "stop": {"type": "action"},
            "status": {"type": "status"},
        }

        if action not in ACTIONS:
            await ctx.message.add_reaction("\U0000274c")
            await ctx.reply(
                "Неизвестная команда.\n"
                "`!server start`\n"
                "`!server stop`\n"
                "`!server status`"
            )
            return

        kind = ACTIONS[action]["type"]

        if kind == "status":
            status = ServerControl.get_status()
            await ctx.message.add_reaction("\U00002705")
            await ctx.reply(f"Текущее состояние сервера: `{status}`")
            return

        await self._do_action(ctx, action)
