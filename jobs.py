import logging
from datetime import datetime
from telegram import Bot
from config import CHAT_ID, MOSCOW_TZ
from sheets import get_players, get_unpaid_players

logger = logging.getLogger(__name__)

async def send_poll(app):
    """Публикует опрос в воскресенье в 12:00"""
    try:
        # Сбрасываем данные предыдущего опроса
        app.bot_data["voted_users"] = set()
        app.bot_data["poll_sent_at"] = datetime.now(MOSCOW_TZ)

        message = await app.bot.send_poll(
            chat_id=CHAT_ID,
            question="⚽️ Играешь в футбол во вторник?",
            options=["✅ Да, буду", "❌ Нет, не смогу"],
            is_anonymous=False
        )
        app.bot_data["current_poll_id"] = message.poll.id
        app.bot_data["poll_message_id"] = message.message_id
        logger.info("Опрос опубликован")
    except Exception as e:
        logger.error(f"Ошибка при публикации опроса: {e}")

async def check_poll_votes(app):
    """Тегает тех кто не проголосовал — каждые 2 часа после 17:00"""
    try:
        poll_id = app.bot_data.get("current_poll_id")
        if not poll_id:
            return

        voted_ids = app.bot_data.get("voted_users", set())
        players = get_players()

        # Получаем участников чата через get_chat_members не работает в обычных группах
        # Поэтому дёргаем всех игроков из таблицы у кого нет голоса по username
        # Для тега используем username из таблицы
        not_voted_mentions = []
        for player in players:
            username = str(player.get("username", "")).strip()
            if not username:
                continue
            # Добавляем @ если нет
            if not username.startswith("@"):
                username = "@" + username
            not_voted_mentions.append(username)

        if not not_voted_mentions:
            return

        # Формируем сообщение
        mentions = " ".join(not_voted_mentions)
        text = (
            f"🔔 Эй, {mentions}\n\n"
            f"Проголосуйте в опросе выше — играете во вторник или нет?\n"
            f"Не молчите, нам важно знать состав! ⚽️"
        )
        await app.bot.send_message(chat_id=CHAT_ID, text=text)
        logger.info(f"Напомнили {len(not_voted_mentions)} игрокам")
    except Exception as e:
        logger.error(f"Ошибка при проверке голосов: {e}")

async def remind_unpaid(app):
    """Напоминает неоплатившим каждый день с 1-го числа в 8:00"""
    try:
        unpaid = get_unpaid_players()
        if not unpaid:
            logger.info("Все оплатили — напоминать некому")
            return

        mentions = []
        for player in unpaid:
            username = str(player.get("username", "")).strip()
            if not username:
                continue
            if not username.startswith("@"):
                username = "@" + username
            mentions.append(username)

        if not mentions:
            return

        text = (
            f"💰 {' '.join(mentions)}\n\n"
            f"Напоминаю об оплате за поле в этом месяце.\n"
            f"Скиньте деньги как можно скорее 🙏"
        )
        await app.bot.send_message(chat_id=CHAT_ID, text=text)
        logger.info(f"Напомнили об оплате: {mentions}")
    except Exception as e:
        logger.error(f"Ошибка при напоминании об оплате: {e}")
