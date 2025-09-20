from discord_bot.main_obj import bot


@bot.command()
async def ping(ctx):
    await ctx.send("Pong!")
