import io

import discord
from discord.ext import commands

from data_bases import PlayerDB

intents = discord.Intents.all()

bot = commands.Bot(command_prefix="!", intents=intents)


@bot.event
async def on_ready():
    print(f"Discord bot logged in as {bot.user}")
    channel = bot.get_channel(1321317710222721054)
    if channel and isinstance(channel, discord.TextChannel):
        await channel.send("Setup done")


@bot.command()
async def ping(ctx):
    await ctx.send("Pong!")


@bot.command(name="list_users")
async def list_users(ctx):
    if ctx.author.id != 456381306553499649:
        await ctx.send("Nope")
        return

    players = PlayerDB.get_pdata_all()
    if not players:
        await ctx.send("Нет зарегистрированных пользователей.")
        return

    lines = []
    for u_id, discord_id, steam_id, pdata in players:
        lines.append(
            f"ID {u_id} | discord: {discord_id or '-'} | steam: {steam_id or '-'} | name: {pdata.discord_name or '-'}"
        )

    chunk = "\n".join(lines)
    if len(chunk) > 1900:
        buffer = io.BytesIO(chunk.encode("utf-8"))
        buffer.seek(0)
        await ctx.send(file=discord.File(fp=buffer, filename="users.txt"))
    else:
        await ctx.send(f"```\n{chunk}\n```")
