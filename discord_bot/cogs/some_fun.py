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
    image: Path | None = None


@dataclass
class Level:
    threshold: int
    responses: List[Response] = field(default_factory=list)


class AIManager(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.owner_id = 456381306553499649
        self.images_root = Path("static/images/ashley")

        self.offenses: Dict[int, int] = {}
        self.repeat: set[int] = set()

        self.levels: List[Level] = [
            Level(
                1,
                [
                    Response(
                        "Эй... может, не надо так грубо?",
                        self.images_root / "normal.png",
                    ),
                    Response(
                        "Мм... я делаю вид, что не услышала.",
                        self.images_root / "sili.png",
                    ),
                ],
            ),
            Level(
                2,
                [
                    Response(
                        "Ты правда хочешь продолжать?", self.images_root / "worry.png"
                    ),
                    Response(
                        "Я начинаю сердиться... чуть-чуть.",
                        self.images_root / "normal.png",
                    ),
                ],
            ),
            Level(
                3,
                [
                    Response(
                        "Хватит. Последний раз предупреждаю.",
                        self.images_root / "angry.png",
                    ),
                    Response(
                        "Ты нарываешься на час тишины.", self.images_root / "angry.png"
                    ),
                ],
            ),
        ]

        self.owner_responses: List[Response] = [
            Response(
                "Ну ты же знаешь, что со мной так нельзя...",
                self.images_root / "worry.png",
            ),
        ]
        self.repeat_responses: List[Response] = [
            Response(
                "Мы это уже проходили. Я всё ещё помню тебя.",
                self.images_root / "angry.png",
            ),
            Response("Снова? Хорошо.", self.images_root / "angry.png"),
            Response("Ты явно не учишься. Отдыхай.", self.images_root / "angry.png"),
        ]

        self.cannot_punish: List[Response] = [
            Response(
                "Я не могу его тронуть, а он обижает...",
                self.images_root / "something_wrong.png",
            ),
        ]

        self.ping_responses: List[Response] = [
            Response(
                "Умф... Я не являюсь разумной. Я не смогу поддерживать диалог вне моих рамок. Если сильно хотите помучать меня - спросите у моего Мастера что вас интересует по мне.",
                self.images_root / "not_ai_i.png",
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
        user: discord.Member,
        user_id: int,
    ):
        if user_id == self.owner_id:
            response = self.pick_block(self.owner_responses)
            await self.send_response(message.channel, response)
            return

        if user_id in self.repeat:
            response = self.pick_block(self.repeat_responses)
            await self.send_response(message.channel, response)
            await self.apply_timeout_or_report(user, message.channel)
            return

        count = self.offenses.get(user_id, 0) + 1
        self.offenses[user_id] = count

        level_response = None
        for level in reversed(self.levels):
            if count >= level.threshold:
                level_response = self.pick_block(level.responses)
                break

        if level_response:
            await self.send_response(message.channel, level_response)

        if count >= self.levels[-1].threshold:
            self.repeat.add(user_id)
            await self.apply_timeout_or_report(user, message.channel)

    async def send_response(self, channel: discord.TextChannel, response: Response):
        if response.image:
            await channel.send(response.phrase, file=discord.File(response.image))
        else:
            await channel.send(response.phrase)

    async def apply_timeout_or_report(
        self,
        user: discord.Member,
        channel: discord.TextChannel,
    ):
        try:
            await user.timeout(timedelta(hours=1), reason="Bot insult")

        except Exception:
            owner = self.bot.get_user(self.owner_id)
            if owner:
                response = self.pick_block(self.cannot_punish)
                await self.send_response(owner, response)

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
                await self.send_response(message.channel, response)
