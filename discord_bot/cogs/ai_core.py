import random
import re
from dataclasses import dataclass, field
from datetime import timedelta
from pathlib import Path
from typing import Dict, List

import discord
from discord.ext import commands


@dataclass
class Response:
    phrase: str
    image: str | None = None

    async def send(self, channel: discord.TextChannel | discord.DMChannel) -> None:
        if self.image:
            await channel.send(
                self.phrase,
                file=discord.File(Path("static/images/ashley") / self.image),
            )

        else:
            await channel.send(self.phrase)


@dataclass
class Level:
    threshold: int
    responses: List[Response] = field(default_factory=list)


class AICore(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.owner_id = 456381306553499649

        self.offenses: Dict[int, int] = {}
        self.repeat: set[int] = set()

        self.levels: List[Level] = [
            Level(
                1,
                [
                    Response("Эй... может, не надо так грубо?", "normal.png"),
                    Response("Мм... я делаю вид, что не услышала.", "sili.png"),
                ],
            ),
            Level(
                2,
                [
                    Response("Ты правда хочешь продолжать?", "worry.png"),
                    Response("Я начинаю сердиться... чуть-чуть.", "normal.png"),
                ],
            ),
            Level(
                3,
                [
                    Response("Хватит. Последний раз предупреждаю.", "angry.png"),
                    Response("Ты нарываешься на час тишины.", "angry.png"),
                ],
            ),
        ]

        self.owner_responses: List[Response] = [
            Response("Ну ты же знаешь, что со мной так нельзя...", "worry.png"),
        ]
        self.repeat_responses: List[Response] = [
            Response("Мы это уже проходили. Я всё ещё помню тебя.", "angry.png"),
            Response("Снова? Хорошо.", "angry.png"),
            Response("Ты явно не учишься. Отдыхай.", "angry.png"),
        ]

        self.cannot_punish: List[Response] = [
            Response("Я не могу его тронуть, а он обижает...", "something_wrong.png"),
        ]

        self.ping_responses: List[Response] = [
            Response(
                "Умф... Я не являюсь разумной. Я не смогу поддерживать диалог вне моих рамок. Если сильно хотите помучать меня - спросите у моего Мастера что вас интересует по мне.",
                "not_ai_i.png",
            ),
        ]

        self.insult_pattern = re.compile(
            r"(нах+у+й?|на хуй|иди\s+на\s+хуй|пош[её]л\s+на\s+хуй|"
            r"мразь|сука|сучара|еблан|ебанат|пидор|пидорас|уебок|"
            r"ублюдок|долб[оа]ёб|тварь|гнида|чмо|урод)",
            re.IGNORECASE,
        )

    def is_insult(self, msg: str) -> bool:
        return bool(self.insult_pattern.search(msg))

    def is_ping(self, msg: str) -> bool:
        return not self.insult_pattern.search(msg)

    def pick_block(self, blocks: List[Response]) -> Response:
        return random.choice(blocks)

    async def handle_insult(
        self,
        message: discord.Message,
        user: discord.Member | discord.User,
        user_id: int,
    ):
        channel = message.channel
        if not isinstance(channel, (discord.TextChannel, discord.DMChannel)):
            return

        if user_id == self.owner_id:
            response = self.pick_block(self.owner_responses)
            await response.send(channel)
            return

        if user_id in self.repeat:
            response = self.pick_block(self.repeat_responses)
            await response.send(channel)
            await self.apply_timeout_or_report(user, channel)
            return

        count = self.offenses.get(user_id, 0) + 1
        self.offenses[user_id] = count

        level_response = None
        for level in reversed(self.levels):
            if count >= level.threshold:
                level_response = self.pick_block(level.responses)
                break

        if level_response:
            await level_response.send(channel)

        if count >= self.levels[-1].threshold:
            self.repeat.add(user_id)
            await self.apply_timeout_or_report(user, channel)

    async def apply_timeout_or_report(
        self,
        user: discord.Member | discord.User,
        channel: discord.TextChannel | discord.DMChannel,
    ):
        if isinstance(user, discord.User):
            return

        try:
            await user.timeout(timedelta(hours=1), reason="Bot insult")

        except Exception:
            owner = self.bot.get_user(self.owner_id)
            if owner:
                response = self.pick_block(self.cannot_punish)
                await response.send(owner)

            else:
                await channel.send("Я даже пожаловаться не могу...")

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot:
            return

        user = message.author
        user_id = user.id
        content = message.content

        if f"<@{self.bot.user.id}>" not in content:
            return

        async with message.channel.typing():
            if self.is_insult(content):
                await self.handle_insult(message, user, user_id)

            elif self.is_ping(content):
                response = self.pick_block(self.ping_responses)
                await response.send(message.channel)  # pyright: ignore[reportArgumentType]
