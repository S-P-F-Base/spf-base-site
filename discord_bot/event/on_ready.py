from discord_bot.main_obj import bot


@bot.event
async def on_ready():
    print(f"Discord bot logged in as {bot.user}")
