import logging

import discord
from discord.ext import commands

from data_class import ProfileData, ProfileDataBase

WATCHED_FORUM_IDS = {
    1321317936756953119,  # Анкеты и персонажи
    1398286514571448433,  # Заявки на администрацию
}

APPEAL_STR = (
    "Для апелляции или уточнения создайте тикет: "
    "https://discord.com/channels/1321306723423883284/1358046882059780136/1408426647820046378."
)


class ForumBlockCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_thread_create(self, thread: discord.Thread):
        if (
            not thread.parent
            or not isinstance(thread.parent, discord.ForumChannel)
            or thread.parent.id not in WATCHED_FORUM_IDS
        ):
            return

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
                    logging.warning(f"Не удалось отправить ЛС пользователю {author_id}")

            try:
                await thread.delete(reason=reason)

            except discord.Forbidden:
                logging.error(f"Нет прав на удаление темы {thread.id}")

            except discord.HTTPException as e:
                logging.error(f"Ошибка при удалении темы {thread.id}: {e}")

        # Проверка на блок для заявок в админы
        if thread.parent.id == 1398286514571448433 and data.blacklist.get(
            "admin", False
        ):
            await send_dm_and_delete("ЧС администрации с БД spf-base.ru")
            return

        # Для анкет персонажей
        is_lore = False
        try:
            lore_tag = thread.parent.get_tag(1404795974706135152)
            if lore_tag and lore_tag in thread.applied_tags:
                is_lore = True

        except Exception:
            logging.warning("Не найден или не прочитан тег лорного персонажа")

        if is_lore:
            if data.blacklist.get("lore_chars", False):
                await send_dm_and_delete("ЧС лорных персонажей с БД spf-base.ru")
        else:
            if data.blacklist.get("chars", False):
                await send_dm_and_delete("ЧС обычных персонажей с БД spf-base.ru")
