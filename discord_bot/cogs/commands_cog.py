import re

from discord import Colour, Embed
from discord.ext import commands

import utils.steam
from data_class import ProfileData, ProfileDataBase

from .etc import build_limits_embeds


class CommandsCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(name="limits")
    async def limits_cmd(self, ctx: commands.Context):
        author_id = ctx.author.id
        if not author_id:
            return

        profile = ProfileDataBase.get_profile_by_discord(str(author_id))
        if not profile:
            await ctx.send(
                "Вы не зарегестрированны в БД! Пройти регистрацию можно [на сайте](https://spf-base.ru/profile)"
            )
            return

        data: ProfileData = profile.get("data", ProfileData())
        await ctx.send(embeds=build_limits_embeds(data))

    @commands.command(name="size")
    async def size_cmd(self, ctx: commands.Context, url: str):
        ids: list[str] = []
        for part in re.split(r"[\s,]+", (url or "").strip()):
            m = re.search(r"[?&]id=(\d+)", part)
            if m:
                ids.append(m.group(1))

        sizes = utils.steam.fetch_workshop_sizes(ids)
        total_size = sum(sizes.values())
        total_mb = round(total_size / 1024 / 1024, 2)
        await ctx.send(f"{total_mb} МБ")

    @commands.command(name="help")
    async def help_cmd(self, ctx: commands.Context):
        user_embed = Embed(title="Команды для игроков", colour=Colour.orange())
        user_embed.add_field(
            name="",
            value="\n".join(
                [
                    "`!help` - Показать справку по командам",
                    "`!limits` - Показать свои лимиты",
                    "`!size <url>` - Показать занимаемое место аддона",
                ]
            ),
            inline=False,
        )

        admin_embed = Embed(title="Команды для администрации", colour=Colour.red())
        admin_embed.add_field(
            name="",
            value="\n".join(
                [
                    "`!server <start|stop>` - Остановить / запустить сервер",
                    "`!update_status` - Обновить статус бота",
                    "`!user_time` - Расстрельный список",
                    "`!cleanup_ankets` - Чистка",
                ]
            ),
            inline=False,
        )

        await ctx.send(embeds=[user_embed, admin_embed])
