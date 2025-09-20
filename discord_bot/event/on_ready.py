from discord_bot.main_obj import bot


@bot.event
async def on_ready():
    print(f"Discord bot logged in as {bot.user}")
    channel = bot.get_channel(1321317710222721054)
    if channel:
        await channel.send("Setup done")
