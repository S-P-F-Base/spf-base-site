import re

import discord
from discord import Colour, Embed
from discord.ext import commands

import utils.steam
from data_class import ProfileData, ProfileDataBase
from routers.api.yoomoney.notification import revalidate

from .etc import build_limits_embeds

ALLOWED_ROLES = {
    1361481568404766780,  # Сержант
    1322091700813955084,  # Ст. админ
    1414370801318105188,  # Ст. модер
    1321537454645448716,  # Гл. спф
    1353426520915579060,  # Расист
    1402602828387844177,  # .
    1355456288716488854,  # Бот
}

TEAM_ROLES = {
    "0": 1430944877721423916,
    "1": 1430944267492393123,
    "2": 1430944532475805746,
    "3": 1430944606324916334,
    "4": 1430944655561723944,
    "5": 1430944692018610207,
}


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
            await ctx.message.add_reaction("\u274c")
            return

        profile = ProfileDataBase.get_profile_by_discord(str(author_id))
        if not profile:
            await ctx.message.add_reaction("\u274c")
            return

        data = profile.get("data", ProfileData())
        if not isinstance(data, ProfileData):
            await ctx.message.add_reaction("\u274c")
            return

        if not data.has_access("edit_payments"):
            await ctx.message.add_reaction("\u274c")
            return

        try:
            result = revalidate(uuid, True)
        except Exception as exc:
            await ctx.author.send(f"Ошибка при обновлении платежа:\n{exc}")
            await ctx.message.add_reaction("\u274c")
            return

        await ctx.author.send(f"Результат проверки платежа `{uuid}`:\n```{result}```")

        await ctx.message.add_reaction("\u2705")

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

        team_embed = Embed(title="Команды для сержантов", colour=Colour.yellow())
        team_embed.add_field(
            name="",
            value="\n".join(
                [
                    "`!team <user> <0|1|2|3|4|5|remove>` - Добавить или удалить из отряда человека",
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

        await ctx.send(embeds=[user_embed, team_embed, admin_embed])

    @commands.command(name="team")
    async def team_cmd(
        self,
        ctx: commands.Context,
        member: discord.Member,
        value: str,
    ):
        guild = ctx.guild
        if guild is None:
            await ctx.send("Эта команда доступна только на сервере.")
            return

        author: discord.Member = ctx.author  # type: ignore[assignment]

        author_roles = {r.id for r in author.roles}
        if not (author_roles & ALLOWED_ROLES):
            await ctx.message.add_reaction("\u274c")
            return

        value = value.lower().strip()
        if value == "remove":
            changed = False
            for rid in TEAM_ROLES.values():
                role = guild.get_role(rid)
                if role and role in member.roles:
                    await member.remove_roles(role, reason=f"team remove by {author}")
                    changed = True

            await ctx.message.add_reaction("\u2705" if changed else "\u274c")
            return

        if value not in TEAM_ROLES:
            await ctx.send("Неверный аргумент. Используйте 0–5 или remove.")
            return

        target_role = guild.get_role(TEAM_ROLES[value])
        if target_role is None:
            await ctx.send("Целевая роль не найдена на сервере.")
            return

        for rid in TEAM_ROLES.values():
            role = guild.get_role(rid)
            if role and role in member.roles and role.id != target_role.id:
                await member.remove_roles(role, reason=f"team switch by {author}")

        await member.add_roles(target_role, reason=f"team set {value} by {author}")
        await ctx.message.add_reaction("\u2705")
