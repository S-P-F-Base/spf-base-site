import re
from pathlib import Path

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
    1402602828387844177,  # Тех админ
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
                    "`!size <url> (url) (...)` - Показать занимаемое место аддона/аддонов",
                ]
            ),
            inline=False,
        )

        team_embed = Embed(title="Команды для сержантов", colour=Colour.yellow())
        team_embed.add_field(
            name="",
            value="\n".join(
                [
                    "`!team <user> <0|1|2|3|4|5> [add|remove]`",
                    "Добавить или убрать пользователя из отряда.",
                    "",
                    "**Примеры:**",
                    "`!team @User 3` — добавить в отряд 3",
                    "`!team @User 3 remove` — убрать из отряда 3",
                ]
            ),
            inline=False,
        )

        admin_embed = Embed(title="Команды для администрации", colour=Colour.red())
        admin_embed.add_field(
            name="",
            value="\n".join(
                [
                    "`!server <start|stop|restart|status>` - Управление сервером",
                    "`!user <time|inventory>` - Немного магии с пользователями",
                    "`!update_status` - Прижать Эшли к полу и проверить статус сервера",
                    "`!cleanup_ankets` - Чистка мусора с анкет",
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
        team: str,
        action: str = "add",
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

        team = team.lower().strip()
        action = action.lower().strip()

        if team not in TEAM_ROLES:
            await ctx.message.add_reaction("\u274c")
            await ctx.send("Неверный номер отряда. Используйте 0–5.")
            return

        if action not in ("add", "remove"):
            await ctx.message.add_reaction("\u274c")
            await ctx.send("Неверное действие. Используйте add или remove.")
            return

        target_role = guild.get_role(TEAM_ROLES[team])
        if target_role is None:
            await ctx.message.add_reaction("\u274c")
            await ctx.send("Роль отряда не найдена на сервере.")
            return

        if action == "remove":
            if target_role not in member.roles:
                await ctx.message.add_reaction("\u274c")
                return

            await member.remove_roles(
                target_role,
                reason=f"team remove {team} by {author}",
            )
            await ctx.message.add_reaction("\u2705")
            return

        # add
        if target_role in member.roles:
            await ctx.message.add_reaction("\u274c")
            return

        await member.add_roles(
            target_role,
            reason=f"team add {team} by {author}",
        )
        await ctx.message.add_reaction("\u2705")

    @commands.command(name="сука")
    async def fuck_cmd(self, ctx: commands.Context, userid: str):
        author_id = ctx.author.id
        if author_id != 456381306553499649:
            await ctx.message.add_reaction("\u274c")
            return

        await ctx.send(
            f"Здравствуйте, <@{userid}>!\n"
            f"Вы недавно задали вопрос, на который уже есть готовый ответ - вот здесь: https://discord.com/channels/1321306723423883284/1358046882059780136/1377966195159994458 или в канале <#1427916856903209000>.\n"
            "Чтобы мой хозяин не говорил вам это лично и... слишком эмоционально, он поручил мне передать: перед тем как спрашивать, заглядывайте в уже существующие ответы. Экономит время и нервы всем - особенно ему."
        )

        await ctx.message.delete()

    @commands.command(name="give")
    async def owo_cmd(self, ctx: commands.Context):
        author_id = ctx.author.id
        if author_id != 456381306553499649:
            await ctx.message.add_reaction("\u274c")
            return

        txt = "Умф... Хозяин сказал что разработка моих алгоритмов не в приоритете.\n Так же он просил напомнить что есть [донат](https://spf-base.ru/donate) если кто-то хочет поддержать проект.\n\n||А ещё он вредный и не хочет печеньками делиться!||"

        channel = self.bot.get_channel(1321307574242377769)
        if channel and isinstance(channel, discord.TextChannel):
            await channel.send(
                txt,
                file=discord.File(Path("static/images/ashley/happy.png")),
            )
