import os
import pytz

BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
CHAT_ID = int(os.environ.get("CHAT_ID", "0"))
SPREADSHEET_ID = os.environ.get("SPREADSHEET_ID", "1Ytl-LmaiKJ0PTWpKs0vkBZbBUkmkUTa4l4_60ly6M58")
GOOGLE_CREDS_JSON = os.environ.get("GOOGLE_CREDS_JSON", "")

MOSCOW_TZ = pytz.timezone("Europe/Moscow")

# Сколько часов ждать после опроса перед первым напоминанием
POLL_REMIND_AFTER_HOURS = 5
