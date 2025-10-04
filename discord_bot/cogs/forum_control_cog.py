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


class ForumControlCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(name="cleanup_ankets")
    @commands.has_permissions(manage_threads=True)
    async def purge_bad_forms(self, ctx: commands.Context):
        forum_id = 1321317936756953119
        target_tag_id = 1355814835169919052

        forum = ctx.guild.get_channel(forum_id)  # type: ignore
        if not isinstance(forum, discord.ForumChannel):
            await ctx.send("Форум не найден или указан неверный ID.")
            return

        deleted = 0
        failed = 0

        target_tag = forum.get_tag(target_tag_id)
        if not target_tag:
            await ctx.send("Тег не найден.")
            return

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
                logging.error(f"Ошибка при удалении архивного треда {thread.id}: {e}")
                failed += 1

        await ctx.send(f"Удалено {deleted} тредов, не удалось удалить {failed}.")

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
                return
        else:
            if data.blacklist.get("chars", False):
                await send_dm_and_delete("ЧС обычных персонажей с БД spf-base.ru")
                return

        # Если же ничего не нашли просто пишем сколько лимита осталось
        embed = discord.Embed(title="Лимиты", color=discord.Color.orange())

        total_space = data.limits.get("base_limit", 0) + data.limits.get(
            "donate_limit", 0
        )
        used_space = data.limits.get("used", 0)
        free_space = total_space - used_space

        embed.add_field(
            name="Место",
            value=(
                f"Всего: `{total_space}` МБ\n"
                f"Доступно: `{free_space}` МБ\n"
                f"Занято: `{used_space}` МБ"
            ),
            inline=False,
        )

        total_chars = data.limits.get("base_char", 0) + data.limits.get(
            "donate_char", 0
        )
        used_chars = len(data.chars)
        free_chars = total_chars - used_chars

        embed.add_field(
            name="Персонажи",
            value=(
                f"Всего: `{total_chars}` шт.\n"
                f"Доступно: `{free_chars}` шт.\n"
                f"Занято: `{used_chars}` шт."
            ),
            inline=False,
        )

        await thread.send(embed=embed)
