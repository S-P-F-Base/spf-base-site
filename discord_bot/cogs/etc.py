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
            f"Всего: `{total_chars}`\n"
            f"Доступно: `{free_chars}`\n"
            f"Занято: `{used_chars}`"
        ),
        inline=False,
    )

    return storage, chars
