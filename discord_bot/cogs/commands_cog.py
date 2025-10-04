import discord
from discord.ext import commands

from data_class import ProfileData, ProfileDataBase

HELP_STR: str = """
Список доступных команд:
- `!help` - Показать справку по командам
- `!limits` - Показать свои лимиты
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

    @commands.command(name="help")
    async def help_cmd(self, ctx: commands.Context):
        await ctx.send(HELP_STR)
