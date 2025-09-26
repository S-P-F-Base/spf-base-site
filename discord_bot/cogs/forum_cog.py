import logging

import discord
from discord.ext import commands

from data_class import ProfileData, ProfileDataBase

WATCHED_FORUM_IDS = {
    1321317936756953119,  # Анкеты и персонажи
    1398286514571448433,  # Заявки на администрацию
}

APPEAL_STR = "Для апелляции или уточнения создайте тикет: https://discord.com/channels/1321306723423883284/1358046882059780136/1408426647820046378."


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

        # Проверка на блок администрации
        if thread.parent.id == 1398286514571448433 and data.blacklist.get(
            "admin", False
        ):
            no_tag = thread.parent.get_tag(1410593837189038091)
            if not no_tag:
                logging.error("Проёбан айди тега отказа для анкет на администрацию")
                return

            await thread.send(
                f"<@{author_id}>, вы находитесь в чёрном списке для подачи на пост администратора. {APPEAL_STR}"
            )
            await thread.edit(
                reason="ЧС администрации с БД spf-base.ru",
                applied_tags=[no_tag],
                locked=True,
            )

        else:
            lore_tag = thread.parent.get_tag(1404795974706135152)
            if not lore_tag:
                logging.error(
                    "Проёбан айди тега лорового персонажа для анкет персонажа"
                )
                return

            no_tag = thread.parent.get_tag(1355814835169919052)
            if not no_tag:
                logging.error("Проёбан айди тега отказа для анкет персонажа")
                return

            if lore_tag in thread.applied_tags:  # На лорного персонажа
                if data.blacklist.get("lore_chars", False):
                    await thread.send(
                        f"<@{author_id}>, вы находитесь в чёрном списке для подачи на лорного персонажа. {APPEAL_STR}"
                    )
                    await thread.edit(
                        reason="ЧС лорных с БД spf-base.ru",
                        applied_tags=[no_tag],
                        locked=True,
                    )

            else:  # На обычного персонажа
                if data.blacklist.get("chars", False):
                    await thread.send(
                        f"<@{author_id}>, вы находитесь в чёрном списке для подачи обычных персонажей. {APPEAL_STR}"
                    )
                    await thread.edit(
                        reason="ЧС обычных с БД spf-base.ru",
                        applied_tags=[no_tag],
                        locked=True,
                    )
