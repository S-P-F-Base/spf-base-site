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

        await ctx.send(
            f"""# Лимиты
## Место
Всего: `{data.limits.get("base_limit", 0) + data.limits.get("donate_limit", 0)}` МБ
Доступно: `{data.limits.get("base_limit", 0) + data.limits.get("donate_limit", 0) - data.limits.get("used", 0)}` МБ
Занято: `{data.limits.get("used", 0)}` МБ

## Персонажи
Всего: `{data.limits.get("base_char", 0) + data.limits.get("donate_char", 0)}` шт.
Доступно `{data.limits.get("base_char", 0) + data.limits.get("donate_char", 0) - len(data.chars)}` шт.
Занято `{len(data.chars)}` шт.
"""
        )

    @commands.command(name="help")
    async def help_cmd(self, ctx: commands.Context):
        await ctx.send(HELP_STR)
