import random
import re
from datetime import timedelta
from pathlib import Path

import discord
from discord.ext import commands


class AIManager(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.owner_id = 456381306553499649
        self.images_root = Path("static/images/ashley")

        self.offenses = {}
        self.repeat = set()

        self.levels = {
            1: [
                ("Эй... может, не надо так грубо?", "normal.png"),
                ("Мм... я делаю вид, что не услышала.", "sili.png"),
            ],
            2: [
                ("Ты правда хочешь продолжать?", "worry.png"),
                ("Я начинаю сердиться... чуть-чуть.", "normal.png"),
            ],
            3: [
                ("Хватит. Последний раз предупреждаю.", "angry.png"),
                ("Ты нарываешься на час тишины.", "angry.png"),
            ],
        }

        self.owner_responses = [
            ("Ну ты же знаешь, что со мной так нельзя...", "worry.png"),
        ]

        self.cannot_punish = [
            ("Я не могу его тронуть...", "something_wrong.png"),
        ]

        self.repeat_responses = [
            ("Мы это уже проходили. Я всё ещё помню тебя.", "angry.png"),
            ("Снова? Хорошо.", "angry.png"),
            ("Ты явно не учишься. Отдыхай.", "angry.png"),
        ]

        self.insult_pattern = re.compile(
            r"(нах+у+й?|на хуй|иди\s+на\s+хуй|пош[её]л\s+на\s+хуй|"
            r"мразь|сука|сучара|еблан|ебанат|пидор|пидорас|уебок|"
            r"ублюдок|долб[оа]ёб|тварь|гнида|чмо|урод)",
            re.IGNORECASE,
        )

    def is_insult(self, msg: str) -> bool:
        return bool(self.insult_pattern.search(msg))

    def pick_block(self, blocks):
        phrase, filename = random.choice(blocks)
        return phrase, self.images_root / filename

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot:
            return

        content = message.content
        if not self.is_insult(content):
            return

        user = message.author
        user_id = user.id

        if user_id == self.owner_id:
            phrase, img = self.pick_block(self.owner_responses)
            await message.channel.send(phrase, file=discord.File(img))
            return

        if user_id in self.repeat:
            phrase, img = self.pick_block(self.repeat_responses)
            await message.channel.send(phrase, file=discord.File(img))
            await self.apply_timeout_or_report(user, message.channel)
            return

        count = self.offenses.get(user_id, 0) + 1
        self.offenses[user_id] = count

        level = min(count, 3)
        phrase, img = self.pick_block(self.levels[level])
        await message.channel.send(phrase, file=discord.File(img))

        if count >= 3:
            self.repeat.add(user_id)
            await self.apply_timeout_or_report(user, message.channel)

    async def apply_timeout_or_report(
        self, user: discord.Member, channel: discord.TextChannel
    ):
        try:
            await user.timeout(timedelta(hours=1), reason="Bot insult")

        except Exception:
            owner = self.bot.get_user(self.owner_id)
            if owner:
                phrase, img = self.pick_block(self.cannot_punish)
                await owner.send(f"{phrase} {user.mention}", file=discord.File(img))

            else:
                await channel.send("Я даже пожаловаться не могу...")
