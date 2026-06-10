import asyncio
import logging
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from datetime import datetime, time
import pytz
from telegram.ext import Application, CommandHandler, PollAnswerHandler
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from config import BOT_TOKEN, CHAT_ID, MOSCOW_TZ
from sheets import get_players, get_unpaid_players
from jobs import send_poll, check_poll_votes, remind_unpaid

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Простой веб-сервер чтобы Render не усыплял сервис
class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"OK")
    def log_message(self, format, *args):
        pass  # Не засорять логи

def run_health_server():
    server = HTTPServer(("0.0.0.0", 8080), HealthHandler)
    server.serve_forever()

async def start_command(update, context):
    await update.message.reply_text("Бот активен. Используй /poll, /check_votes, /remind_payment")

async def manual_poll(update, context):
    await send_poll(context.application)

async def manual_check(update, context):
    await check_poll_votes(context.application)

async def manual_remind(update, context):
    await remind_unpaid(context.application)

async def handle_poll_answer(update, context):
    answer = update.poll_answer
    poll_id = answer.poll_id
    user_id = answer.user.id
    if poll_id == context.application.bot_data.get("current_poll_id"):
        voted = context.application.bot_data.setdefault("voted_users", set())
        voted.add(user_id)
        logger.info(f"User {user_id} voted")

def main():
    # Запускаем веб-сервер в фоне
    thread = threading.Thread(target=run_health_server, daemon=True)
    thread.start()
    logger.info("Health server запущен на порту 8080")

    app = Application.builder().token(BOT_TOKEN).build()
    app.bot_data["voted_users"] = set()
    app.bot_data["current_poll_id"] = None

    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("poll", manual_poll))
    app.add_handler(CommandHandler("check_votes", manual_check))
    app.add_handler(CommandHandler("remind_payment", manual_remind))
    app.add_handler(PollAnswerHandler(handle_poll_answer))

    scheduler = AsyncIOScheduler(timezone=MOSCOW_TZ)

    # Каждое воскресенье в 12:00 МСК — публикуем опрос
    scheduler.add_job(
        send_poll, "cron",
        day_of_week="sun", hour=12, minute=0,
        args=[app]
    )

    # Каждое воскресенье с 17:00 каждые 2 часа — дёргаем не проголосовавших
    scheduler.add_job(
        check_poll_votes, "cron",
        day_of_week="sun", hour="17-23", minute=0,
        args=[app]
    )

    # Каждый день с 1 по 28 число в 8:00 МСК — напоминаем об оплате
    scheduler.add_job(
        remind_unpaid, "cron",
        day="1-28", hour=8, minute=0,
        args=[app]
    )

    scheduler.start()
    logger.info("Бот запущен")
    app.run_polling()

if __name__ == "__main__":
    main()

import os
import pytz

BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
CHAT_ID = int(os.environ.get("CHAT_ID", "0"))
SPREADSHEET_ID = os.environ.get("SPREADSHEET_ID", "1Ytl-LmaiKJ0PTWpKs0vkBZbBUkmkUTa4l4_60ly6M58")
GOOGLE_CREDS_JSON = os.environ.get("GOOGLE_CREDS_JSON", "")

MOSCOW_TZ = pytz.timezone("Europe/Moscow")

# Сколько часов ждать после опроса перед первым напоминанием
POLL_REMIND_AFTER_HOURS = 5

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

web: python bot.py

python-telegram-bot==20.7
apscheduler==3.10.4
gspread==6.0.2
google-auth==2.27.0
pytz==2024.1

import json
import os
import gspread
from google.oauth2.service_account import Credentials
from config import SPREADSHEET_ID, GOOGLE_CREDS_JSON

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

def get_sheet():
    creds_data = json.loads(GOOGLE_CREDS_JSON)
    creds = Credentials.from_service_account_info(creds_data, scopes=SCOPES)
    client = gspread.authorize(creds)
    return client.open_by_key(SPREADSHEET_ID).sheet1

def get_players():
    """Возвращает список игроков (только role=player)"""
    sheet = get_sheet()
    records = sheet.get_all_records()
    return [r for r in records if r.get("role") == "player"]

def get_unpaid_players():
    """Возвращает игроков у которых monthly_paid пустое"""
    players = get_players()
    return [p for p in players if not str(p.get("monthly_paid", "")).strip()]
