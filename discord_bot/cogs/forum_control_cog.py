import asyncio
import logging
from enum import IntEnum

import discord
from discord.ext import commands
from discord.utils import utcnow

from data_class import ProfileData, ProfileDataBase

from .etc import build_limits_embeds

NOTIFY_ROLE_ID = 1355456288716488854

APPEAL_STR = (
    "Для апелляции или уточнения создайте тикет: "
    "https://discord.com/channels/1321306723423883284/1358046882059780136/1408426647820046378."
)


class ForumsID(IntEnum):
    BugReports = 1355066916326215690  # баг-репорты
    SuggestionsIdeas = 1359870657185185792  # предложения-и-идеи
    CharacterQuestionnaires = 1321317936756953119  # анкеты-персонажи
    ApplicationsAdministration = 1398286514571448433  # заявки-на-администрацию


WATCHED_FORUM_IDS = frozenset(
    {
        ForumsID.BugReports.value,
        ForumsID.SuggestionsIdeas.value,
        ForumsID.CharacterQuestionnaires.value,
        ForumsID.ApplicationsAdministration.value,
    }
)

LORE_TAG_ID = 1404795974706135152


class ForumControlCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._processed_threads: set[int] = set()
        self._start_time = utcnow()

    async def _iter_forum_threads(self, forum: discord.ForumChannel):
        for th in forum.threads:
            yield th

        async for th in forum.archived_threads(limit=None):
            yield th

    async def _safe_delete_thread(self, thread: discord.Thread, reason: str):
        try:
            await thread.delete(reason=reason)

        except discord.Forbidden:
            logging.error(f"Нет прав на удаление темы {thread.id}")

        except discord.HTTPException as e:
            logging.error(f"Ошибка при удалении темы {thread.id}: {e}")

    async def _send_dm_and_delete(
        self,
        author_id: int,
        thread: discord.Thread,
        reason: str,
    ):
        user = self.bot.get_user(author_id) or await self.bot.fetch_user(author_id)
        if user:
            try:
                await user.send(
                    f"Ваша анкета была удалена.\nПричина: {reason}\n{APPEAL_STR}"
                )

            except discord.Forbidden:
                pass

        await self._safe_delete_thread(thread, reason)

    async def get_thread_owner(self, thread: discord.Thread) -> discord.Member | None:
        if thread.owner:
            return thread.owner

        starter = getattr(thread, "starter_message", None)
        if isinstance(starter, discord.Message):
            if isinstance(starter.author, discord.Member):
                return starter.author

            if thread.guild:
                mem = thread.guild.get_member(starter.author.id)
                if mem:
                    return mem

        if isinstance(thread.parent, discord.TextChannel):
            try:
                msg = await thread.parent.fetch_message(thread.id)
                if isinstance(msg.author, discord.Member):
                    return msg.author

                if thread.guild:
                    mem = thread.guild.get_member(msg.author.id)
                    if mem:
                        return mem

            except discord.NotFound:
                pass

            except discord.HTTPException:
                pass

        try:
            await thread.join()

        except (discord.Forbidden, discord.HTTPException):
            pass

        for attempt in range(6):
            try:
                async for m in thread.history(limit=1, oldest_first=True):
                    if isinstance(m.author, discord.Member):
                        return m.author

                    if thread.guild:
                        mem = thread.guild.get_member(m.author.id)
                        if mem:
                            return mem

                    return None

            except discord.HTTPException:
                pass

            await asyncio.sleep(min(0.5 * (2**attempt), 4.0))

        return None

    async def _process_new_forum_thread(
        self,
        thread: discord.Thread,
        parent: discord.ForumChannel,
    ):
        try:
            await thread.send(f"<@&{NOTIFY_ROLE_ID}>")
        except discord.HTTPException:
            pass

        author = await self.get_thread_owner(thread)
        if not author:
            return

        author_id = author.id

        profile = ProfileDataBase.get_profile_by_discord(str(author_id))
        if not profile:
            return

        data: ProfileData = profile.get("data", ProfileData())

        blacklist_key: str | None = None

        if parent.id == ForumsID.ApplicationsAdministration.value:
            blacklist_key = "admin"

        elif parent.id == ForumsID.CharacterQuestionnaires.value:
            is_lore = False
            try:
                lore_tag = parent.get_tag(LORE_TAG_ID)
                if lore_tag and lore_tag in getattr(thread, "applied_tags", ()):
                    is_lore = True

            except Exception:
                logging.warning("Не найден или не прочитан тег лорного персонажа")

            blacklist_key = "lore_chars" if is_lore else "chars"

        if blacklist_key and data.blacklist.get(blacklist_key, False):
            reason_map = {
                "admin": "ЧС администрации с БД spf-base.ru",
                "lore_chars": "ЧС лорных персонажей с БД spf-base.ru",
                "chars": "ЧС обычных персонажей с БД spf-base.ru",
            }
            await self._send_dm_and_delete(
                author_id,
                thread,
                reason_map[blacklist_key],
            )
            return

        if parent.id == ForumsID.CharacterQuestionnaires.value:
            try:
                await thread.send(embeds=build_limits_embeds(data))

            except discord.HTTPException:
                pass

    @commands.command(name="cleanup")
    @commands.has_permissions(manage_threads=True)
    async def purge_bad_forms(self, ctx: commands.Context):
        if ctx.guild is None:
            await ctx.send("Гильдия не определена.")
            return

        target_tags_id = [
            1355814835169919052,  # 'отклонено'
            1404794315707781160,  # 'выведен из рп'
            1410589109214515281,  # 'принято (для предложений и идей)'
            1410589140831043594,  # 'отклонено (для предложений и идей)'
        ]

        for fid in [
            ForumsID.CharacterQuestionnaires.value,
            ForumsID.SuggestionsIdeas.value,
        ]:
            forum = ctx.guild.get_channel(fid)
            if not isinstance(forum, discord.ForumChannel):
                await ctx.send("Форум не найден или указан неверный ID.")
                return

            target_tags = [forum.get_tag(tag_id) for tag_id in target_tags_id]
            target_tags = [t for t in target_tags if t is not None]

            if not target_tags:
                await ctx.send("Теги не найдены.")
                return

            deleted = 0
            failed = 0

            async with ctx.typing():
                async for thread in self._iter_forum_threads(forum):
                    try:
                        applied_tags = getattr(thread, "applied_tags", ())
                        if any(tag in applied_tags for tag in target_tags):
                            await thread.delete(
                                reason=f"Удаление юзером {ctx.author.id}"
                            )
                            deleted += 1

                    except discord.Forbidden:
                        logging.warning(f"Нет прав на удаление темы {thread.id}")
                        failed += 1

                    except discord.HTTPException as e:
                        logging.error(f"Ошибка при удалении темы {thread.id}: {e}")
                        failed += 1

            await ctx.send(f"Удалено {deleted} форумов\nФорум: <#{fid}>")

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot:
            return

        thread = message.channel
        if not isinstance(thread, discord.Thread):
            return

        parent = thread.parent
        if not parent or not isinstance(parent, discord.ForumChannel):
            return

        if parent.id not in WATCHED_FORUM_IDS:
            return

        if thread.created_at and thread.created_at < self._start_time:
            return

        if thread.id in self._processed_threads:
            return

        self._processed_threads.add(thread.id)

        await self._process_new_forum_thread(thread, parent)
