import logging
from enum import IntEnum

import discord
from discord.ext import commands

from data_class import ProfileData, ProfileDataBase

from .etc import build_limits_embeds


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

APPEAL_STR = (
    "Для апелляции или уточнения создайте тикет: "
    "https://discord.com/channels/1321306723423883284/1358046882059780136/1408426647820046378."
)


class ForumControlCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(name="cleanup_ankets")
    @commands.has_permissions(manage_threads=True)
    async def purge_bad_forms(self, ctx: commands.Context):
        forum_id = ForumsID.CharacterQuestionnaires
        target_tag_id = 1355814835169919052
        if ctx.guild is None:
            print("???")
            return

        forum = ctx.guild.get_channel(forum_id)
        if not isinstance(forum, discord.ForumChannel):
            await ctx.send("Форум не найден или указан неверный ID.")
            return

        deleted = 0
        failed = 0

        target_tag = forum.get_tag(target_tag_id)
        if not target_tag:
            await ctx.send("Тег не найден.")
            return

        async with ctx.typing():
            for thread in forum.threads:
                try:
                    if target_tag in thread.applied_tags:
                        await thread.delete(
                            reason=f"Удаление анкет с тегом 'отклонено' юзером {ctx.author.id}"
                        )
                        deleted += 1

                except discord.Forbidden:
                    logging.warning(f"Нет прав на удаление темы {thread.id}")
                    failed += 1

                except discord.HTTPException as e:
                    logging.error(f"Ошибка при удалении темы {thread.id}: {e}")
                    failed += 1

            async for thread in forum.archived_threads(limit=None):
                try:
                    if target_tag in thread.applied_tags:
                        await thread.delete(
                            reason=f"Удаление анкет с тегом 'отклонено' юзером {ctx.author.id}"
                        )
                        deleted += 1

                except discord.Forbidden:
                    logging.warning(f"Нет прав на удаление архивного треда {thread.id}")
                    failed += 1

                except discord.HTTPException as e:
                    logging.error(
                        f"Ошибка при удалении архивного треда {thread.id}: {e}"
                    )
                    failed += 1

        await ctx.send(f"Удалено {deleted} тредов, не удалось удалить {failed}.")

    @commands.Cog.listener()
    async def on_thread_create(self, thread: discord.Thread):
        tr_parent = thread.parent
        if (
            not tr_parent
            or not isinstance(tr_parent, discord.ForumChannel)
            or tr_parent.id not in WATCHED_FORUM_IDS
        ):
            return

        await thread.send("<@&1355456288716488854>")

        author_id = thread.owner_id
        if not author_id:
            return

        profile = ProfileDataBase.get_profile_by_discord(str(author_id))
        if not profile:
            return

        data: ProfileData = profile.get("data", ProfileData())

        async def send_dm_and_delete(reason: str):
            user = self.bot.get_user(author_id) or await self.bot.fetch_user(author_id)
            if user:
                try:
                    await user.send(
                        f"Ваша анкета была удалена.\nПричина: {reason}\n{APPEAL_STR}"
                    )

                except discord.Forbidden:
                    pass

            try:
                await thread.delete(reason=reason)

            except discord.Forbidden:
                logging.error(f"Нет прав на удаление темы {thread.id}")

            except discord.HTTPException as e:
                logging.error(f"Ошибка при удалении темы {thread.id}: {e}")

        # Проверка на блок для заявок в админы
        if tr_parent.id == ForumsID.ApplicationsAdministration and data.blacklist.get(
            "admin", False
        ):
            await send_dm_and_delete("ЧС администрации с БД spf-base.ru")
            return

        # Для анкет персонажей
        is_lore = False
        try:
            lore_tag = tr_parent.get_tag(1404795974706135152)
            if lore_tag and lore_tag in thread.applied_tags:
                is_lore = True

        except Exception:
            logging.warning("Не найден или не прочитан тег лорного персонажа")

        if tr_parent.id == ForumsID.CharacterQuestionnaires:
            if is_lore:
                if data.blacklist.get("lore_chars", False):
                    await send_dm_and_delete("ЧС лорных персонажей с БД spf-base.ru")
                    return

            else:
                if data.blacklist.get("chars", False):
                    await send_dm_and_delete("ЧС обычных персонажей с БД spf-base.ru")
                    return

        # Лимит онли в чар запросах
        if tr_parent.id != ForumsID.CharacterQuestionnaires:
            return

        await thread.send(embeds=build_limits_embeds(data))
