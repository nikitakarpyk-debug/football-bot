import asyncio
import logging
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
import pytz
from telegram.ext import Application, CommandHandler, PollAnswerHandler
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from config import BOT_TOKEN, CHAT_ID, MOSCOW_TZ
from sheets import get_players, get_unpaid_players
from jobs import send_poll, check_poll_votes, remind_unpaid

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

ADMIN_ID = 937117147

class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"OK")
    def log_message(self, format, *args):
        pass

def run_health_server():
    server = HTTPServer(("0.0.0.0", 8080), HealthHandler)
    server.serve_forever()

async def start_command(update, context):
    if update.effective_user.id != ADMIN_ID:
        return
    await update.message.reply_text("Бот активен. Используй /poll, /check_votes, /remind_payment")

async def manual_poll(update, context):
    if update.effective_user.id != ADMIN_ID:
        return
    await send_poll(context.application)

async def manual_check(update, context):
    if update.effective_user.id != ADMIN_ID:
        return
    await check_poll_votes(context.application)

async def manual_remind(update, context):
    if update.effective_user.id != ADMIN_ID:
        return
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
    thread = threading.Thread(target=run_health_server, daemon=True)
    thread.start()
    logger.info("Health server запущен на порту 8080")

    app = Application.builder().token(BOT_TOKEN).build()
    app.bot_data["voted_users"] = set()
    app.bot_data["current_poll_id"] = None

    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("opros", manual_poll))
app.add_handler(CommandHandler("golosyem", manual_check))
app.add_handler(CommandHandler("sday_babki", manual_remind))
    app.add_handler(PollAnswerHandler(handle_poll_answer))

    scheduler = AsyncIOScheduler(timezone=MOSCOW_TZ)

    scheduler.add_job(
        send_poll, "cron",
        day_of_week="sun", hour=12, minute=0,
        args=[app]
    )

    scheduler.add_job(
        check_poll_votes, "cron",
        day_of_week="sun", hour="17-23", minute=0,
        args=[app]
    )

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
