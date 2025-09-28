from discord.ext import commands


class FunCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(name="dban")
    async def dban(self, ctx: commands.Context):
        await ctx.send("Недостаточно прав")

    @commands.command(name="sudo_dban")
    async def sudo_dban(self, ctx: commands.Context):
        await ctx.send("Хорошая попытка, но нет")
