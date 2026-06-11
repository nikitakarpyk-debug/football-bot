import logging
from datetime import datetime
from config import CHAT_ID, MOSCOW_TZ
from sheets import get_players, get_unpaid_players

logger = logging.getLogger(__name__)

async def send_poll(app):
    try:
        app.bot_data["voted_users"] = set()
        app.bot_data["poll_sent_at"] = datetime.now(MOSCOW_TZ)
        message = await app.bot.send_poll(
            chat_id=CHAT_ID,
            question="⚽️ Эй, тушки! Вторник не отменили, поле забронировано. Голосуйте кто придёт.",
            options=["✅ Да, буду", "❌ Нет, не смогу"],
            is_anonymous=False
        )
        app.bot_data["current_poll_id"] = message.poll.id
        app.bot_data["poll_message_id"] = message.message_id
        logger.info("Опрос опубликован")
    except Exception as e:
        logger.error(f"Ошибка при публикации опроса: {e}", exc_info=True)

async def check_poll_votes(app):
    try:
        poll_id = app.bot_data.get("current_poll_id")
        if not poll_id:
            return
        players = get_players()
        not_voted_mentions = []
        for player in players:
            username = str(player.get("username", "")).strip()
            if not username:
                continue
            if not username.startswith("@"):
                username = "@" + username
            not_voted_mentions.append(username)
        if not not_voted_mentions:
            return
        mentions = " ".join(not_voted_mentions)
        text = f"🔔 {mentions} Игрочишки, ну вы серьёзно? Весь чат проголосовал, а вы как немые."
        )
        await app.bot.send_message(chat_id=CHAT_ID, text=text)
        logger.info(f"Напомнили {len(not_voted_mentions)} игрокам")
    except Exception as e:
        logger.error(f"Ошибка при проверке голосов: {e}", exc_info=True)

async def remind_unpaid(app):
    try:
        logger.info("Запуск remind_unpaid")
        unpaid = get_unpaid_players()
        logger.info(f"Неоплатившие: {unpaid}")
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
            logger.info("Нет юзернеймов для упоминания")
            return
        text = (
    f"⚽️ {' '.join(mentions)}\n\n"
    f"Поле не благотворительность. Вы не Месси чтобы играть бесплатно. Скидывайте бабки."
)
        )
        await app.bot.send_message(chat_id=CHAT_ID, text=text)
        logger.info(f"Напомнили об оплате: {mentions}")
    except Exception as e:
        logger.error(f"Ошибка при напоминании об оплате: {e}", exc_info=True)
        
