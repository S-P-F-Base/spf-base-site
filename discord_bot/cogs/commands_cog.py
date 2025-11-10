import re

from discord import Colour, Embed
from discord.ext import commands

import utils.steam
from data_class import ProfileData, ProfileDataBase

from ...routers.api.yoomoney.notification import revalidate
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

    @commands.command(name="update_payment")
    async def update_payment_cmd(self, ctx: commands.Context, uuid: str):
        author_id = ctx.author.id

        if not uuid:
            await ctx.message.add_reaction("\U0000274c")
            return

        profile = ProfileDataBase.get_profile_by_discord(str(author_id))
        if not profile:
            await ctx.message.add_reaction("\U0000274c")
            return

        data = profile.get("data", ProfileData())
        if not isinstance(data, ProfileData):
            await ctx.message.add_reaction("\U0000274c")
            return

        if not data.has_access("edit_payments"):
            await ctx.message.add_reaction("\U0000274c")
            return

        try:
            result = revalidate(uuid, True)
        except Exception as exc:
            await ctx.author.send(f"Ошибка при обновлении платежа:\n{exc}")
            await ctx.message.add_reaction("\U0000274c")
            return

        await ctx.author.send(f"Результат проверки платежа `{uuid}`:\n```{result}```")

        await ctx.message.add_reaction("\U00002705")

    @commands.command(name="size")
    async def size_cmd(self, ctx: commands.Context, *args: str):
        async with ctx.typing():
            ids: list[str] = []
            for part in args:
                m = re.search(r"[?&]id=(\d+)", part)
                if m:
                    ids.append(m.group(1))
                elif part.isdigit():
                    ids.append(part)

            if not ids:
                await ctx.send("Не найдено ни одного ID.")
                return

            sizes: dict[str, int] = {}

            for wid in ids:
                result = utils.steam.fetch_workshop_sizes([wid])
                if isinstance(result, dict):
                    sizes.update(result)

                elif isinstance(result, (int, float)):
                    sizes[wid] = result

            if not sizes:
                await ctx.send("Не удалось получить размеры указанных аддонов.")
                return

            total_size = sum(sizes.values())
            lines = [f"Всего: {total_size / 1024 / 1024:.2f} МБ"]

            for wid, size in sizes.items():
                mb = size / 1024 / 1024
                lines.append(f"- `{wid}`: `{mb:.2f}` МБ")

            await ctx.send("\n".join(lines))

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
                    "`!user_inventory` - Получить рейтлимит от дискорда",
                ]
            ),
            inline=False,
        )

        await ctx.send(embeds=[user_embed, admin_embed])
