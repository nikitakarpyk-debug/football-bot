import asyncio
import logging
from datetime import datetime, time
import pytz
from telegram.ext import Application, CommandHandler, PollAnswerHandler
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from config import BOT_TOKEN, CHAT_ID, MOSCOW_TZ
from sheets import get_players, get_unpaid_players
from jobs import send_poll, check_poll_votes, remind_unpaid

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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
