from typing import Final

import discord


def build_limits_embeds(data) -> tuple[discord.Embed, discord.Embed]:
    total_space = data.limits.get("base_limit", 0) + data.limits.get("donate_limit", 0)
    used_space = data.limits.get("used", 0)
    free_space = total_space - used_space

    storage = discord.Embed(title="Лимиты - хранилище", color=discord.Color.orange())
    storage.add_field(
        name="Объём",
        value=(
            f"Всего: `{total_space:.2f}` МБ\n"
            f"Доступно: `{free_space:.2f}` МБ\n"
            f"Занято: `{used_space:.2f}` МБ"
        ),
        inline=False,
    )

    total_chars = data.limits.get("base_char", 0) + data.limits.get("donate_char", 0)
    used_chars = len(data.chars)
    free_chars = total_chars - used_chars

    chars = discord.Embed(title="Лимиты - персонажи", color=discord.Color.orange())
    chars.add_field(
        name="Слоты",
        value=(
            f"Всего: `{total_chars}`\nДоступно: `{free_chars}`\nЗанято: `{used_chars}`"
        ),
        inline=False,
    )

    return storage, chars


async def add_nope(message: discord.Message):
    await message.add_reaction("\u274c")


async def add_yep(message: discord.Message):
    await message.add_reaction("\u2705")


NEW_MEMBER_CHANNEL_ID: Final = 1321307463550767154
BOT_CHANNEL_ID: Final = 1466667684849520864
CAIN_ID: Final = 456381306553499649
