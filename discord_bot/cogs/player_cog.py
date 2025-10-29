import json
import sqlite3
from datetime import datetime
from pathlib import Path

from discord.ext import commands

from data_class import ProfileDataBase
from economy import GameDBProcessor


class PlayerCog(commands.Cog):
    def __init__(self, bot):
        self.bot: commands.Bot = bot

    @commands.command(name="user_time")
    async def user_time(self, ctx: commands.Context):
        author_id = ctx.author.id
        if not author_id:
            return

        profile = ProfileDataBase.get_profile_by_discord(str(author_id))
        if not profile:
            await ctx.message.add_reaction("\U0000274c")
            return

        profile = profile.get("data", None)
        if not profile:
            await ctx.message.add_reaction("\U0000274c")
            return

        if not profile.has_access("edit_profiles"):
            await ctx.message.add_reaction("\U0000274c")
            return

        async with ctx.typing():
            db_path = Path("data/users_time.db")
            GameDBProcessor.download_db(db_path)
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()

            cursor.execute(
                "SELECT name, last_played_at, steamid, id FROM spf2_characters"
            )
            rows = cursor.fetchall()
            conn.close()

            now = datetime.now().timestamp()
            month_ago = now - 30 * 24 * 60 * 60

            inactive = []
            for name, ts, steamid, id in rows:
                try:
                    if steamid == "STORAGE":
                        continue

                    ts = int(ts)
                    if ts and ts < month_ago:
                        inactive.append((name, ts, steamid, id))

                except (ValueError, TypeError):
                    continue

            if not inactive:
                await ctx.send("Нет персонажей, не заходивших более месяца.")
                return

            header = "# Персонажи, не заходившие более месяца:\n"
            message = header
            for name, ts, steamid, id in inactive:
                line = f"`{id}` `{steamid}` `{name}` - <t:{ts}:R> (<t:{ts}:f>)\n"
                if len(message) + len(line) >= 2000:
                    await ctx.send(message)
                    message = line
                else:
                    message += line

            if message:
                await ctx.send(message)

            db_path.unlink(missing_ok=True)

    @commands.command(name="user_inventory")
    async def user_inventory(self, ctx: commands.Context):
        author_id = ctx.author.id
        if not author_id:
            return

        profile = ProfileDataBase.get_profile_by_discord(str(author_id))
        if not profile:
            await ctx.message.add_reaction("\U0000274c")
            return

        profile = profile.get("data", None)
        if not profile:
            await ctx.message.add_reaction("\U0000274c")
            return

        if not profile.has_access("full_access"):
            await ctx.message.add_reaction("\U0000274c")
            return

        async with ctx.typing():
            db_path = Path("data/users_inventory.db")
            GameDBProcessor.download_db(db_path)

            conn = sqlite3.connect(db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            query = """
            SELECT
                cd.char_id,
                ch.name,
                ch.steamid,
                cd.json
            FROM spf2_char_data AS cd
            JOIN spf2_characters AS ch
            ON ch.id = cd.char_id
            WHERE cd.key = 'inventory';
            """

            cursor.execute(query)
            rows = cursor.fetchall()
            conn.close()

            blocks = []
            for row in rows:
                steamid = (row["steamid"] or "").upper()
                if steamid == "STORAGE":
                    continue

                try:
                    inv = json.loads(row["json"] or "{}")

                except (TypeError, json.JSONDecodeError):
                    continue

                items = inv.get("items", []) or []
                if not items:
                    continue

                header = f"ID: `{row['char_id']}` | NAME: `{row['name']}` | STEAM: `{row['steamid']}`\n"
                block = header
                for item in items:
                    item_id = item.get("id")
                    if not item_id:
                        continue
                    count = item.get("count", 1)
                    block += f"  {item_id} x{count}\n"
                block += "\n"
                blocks.append(block)

            if not blocks:
                await ctx.send("Нет персонажей с непустым инвентарём.")
                db_path.unlink(missing_ok=True)
                return

            message = "# Инвентари персонажей:\n"
            for block in blocks:
                if len(message) + len(block) >= 2000:
                    await ctx.send(message)
                    message = block

                else:
                    message += block

            if message:
                await ctx.send(message)

            db_path.unlink(missing_ok=True)
