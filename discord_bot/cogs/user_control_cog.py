import asyncio
import time
from collections import deque
from typing import Optional

from discord.ext import commands

from data_control import Config

ROLE_VALUES: dict[int, tuple[int, int]] = {
    1389261673726218260: (75, 3),  # Первопроходец
}
DEFAULT_VALUE: tuple[int, int] = (50, 2)


class UserControlCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

        self._user_cache: dict[int, tuple[float, dict]] = {}
        self._cache_ttl = 3 * 60 * 60  # 3 часа

        self._rl_lock = asyncio.Lock()
        self._rl_calls = deque()  # timestamps
        self._rl_per = 45  # запросов
        self._rl_window = 60.0  # секунд

    # ---------------- internal helpers ----------------
    def _cache_get(self, user_id: int) -> Optional[dict]:
        rec = self._user_cache.get(user_id)
        if not rec:
            return None
        exp, data = rec
        if exp > time.monotonic():
            return data
        self._user_cache.pop(user_id, None)
        return None

    def _cache_set(self, user_id: int, data: dict) -> None:
        self._user_cache[user_id] = (time.monotonic() + self._cache_ttl, data)

    async def _rate_limit(self) -> None:
        async with self._rl_lock:
            now = time.monotonic()
            while self._rl_calls and now - self._rl_calls[0] > self._rl_window:
                self._rl_calls.popleft()
            if len(self._rl_calls) >= self._rl_per:
                await asyncio.sleep(self._rl_window - (now - self._rl_calls[0]))
            self._rl_calls.append(time.monotonic())

    # ---------------- public API ----------------
    async def get_user_info(
        self, user_id: int, *, cache_only: bool = False
    ) -> Optional[dict]:
        cached = self._cache_get(user_id)
        if cached is not None:
            return cached

        guild = self.bot.get_guild(int(Config.discord_guild_id()))
        data: Optional[dict] = None

        if guild:
            member = guild.get_member(user_id)
            if member:
                data = {
                    "username": member.display_name or member.name,
                    "avatar_url": member.display_avatar.url
                    if member.display_avatar
                    else "",
                }

        if data is not None:
            self._cache_set(user_id, data)
            return data

        if cache_only:
            return None

        await self._rate_limit()
        try:
            u = await self.bot.fetch_user(user_id)
            data = {
                "username": u.name,
                "avatar_url": u.display_avatar.url if u.display_avatar else "",
            }

        except Exception:
            data = None

        if data is not None:
            self._cache_set(user_id, data)

        return data

    async def get_role_value(self, user_id: int) -> tuple[int, int]:
        guild = self.bot.get_guild(int(Config.discord_guild_id()))
        if not guild:
            raise RuntimeError("Guild not found or bot missing intents.members")

        member = guild.get_member(user_id)
        if member is None:
            await self._rate_limit()
            try:
                member = await guild.fetch_member(user_id)

            except Exception:
                return DEFAULT_VALUE

        if member is None:
            return DEFAULT_VALUE

        max_value = DEFAULT_VALUE
        for role in member.roles:
            value = ROLE_VALUES.get(role.id)
            if value and value > max_value:
                max_value = value

        return max_value
