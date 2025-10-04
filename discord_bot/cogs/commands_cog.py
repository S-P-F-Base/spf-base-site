import re

import discord
from discord.ext import commands

import utils.steam
from data_class import ProfileData, ProfileDataBase

HELP_STR: str = """
Список доступных команд:
- `!help` - Показать справку по командам
- `!limits` - Показать свои лимиты
- `!size <url>` - Показать занимаемое место аддона
"""


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

        embed = discord.Embed(title="Лимиты", color=discord.Color.orange())

        total_space = data.limits.get("base_limit", 0) + data.limits.get(
            "donate_limit", 0
        )
        used_space = data.limits.get("used", 0)
        free_space = total_space - used_space

        embed.add_field(
            name="Место",
            value=(
                f"Всего: `{total_space}` МБ\n"
                f"Доступно: `{free_space}` МБ\n"
                f"Занято: `{used_space}` МБ"
            ),
            inline=False,
        )

        total_chars = data.limits.get("base_char", 0) + data.limits.get(
            "donate_char", 0
        )
        used_chars = len(data.chars)
        free_chars = total_chars - used_chars

        embed.add_field(
            name="Персонажи",
            value=(
                f"Всего: `{total_chars}` шт.\n"
                f"Доступно: `{free_chars}` шт.\n"
                f"Занято: `{used_chars}` шт."
            ),
            inline=False,
        )

        await ctx.send(embed=embed)

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
        await ctx.send(HELP_STR)
