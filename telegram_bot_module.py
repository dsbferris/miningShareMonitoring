import os
from datetime import datetime, timedelta
import logging as log
import time
from zoneinfo import ZoneInfo
import telegram


telegram_bot_api_key: str
group_chat_id: int
private_chat_id: int
de_timezone: ZoneInfo
bot: telegram.Bot
next_send_time: datetime


def init():
    global telegram_bot_api_key, group_chat_id, private_chat_id, de_timezone, bot, next_send_time
    telegram_bot_api_key = "API_KEY"
    group_chat_id = groupChatId
    private_chat_id = privateChatId
    de_timezone = ZoneInfo("Europe/Berlin")
    bot = telegram.Bot(token=telegram_bot_api_key)
    next_send_time = datetime.now(de_timezone) - timedelta(seconds=5)


def send_message(text: str, chat_id: int, silent: bool = False):
    global next_send_time
    error_occurred = False
    while datetime.now(de_timezone) < next_send_time:
        time.sleep(1)

    try:
        bot.send_message(text=text, chat_id=chat_id, disable_notification=silent, disable_web_page_preview=True)
    except Exception as e:
        log.error(e)
        error_occurred = True
    finally:
        next_send_time = datetime.now(de_timezone) + timedelta(seconds=5)
        if error_occurred:
            return send_message(text=text, chat_id=chat_id, silent=silent)


def send_message_to_group(text: str, silent: bool = False):
    if os.environ["DEBUG"] == "1":
        send_message(text=text, chat_id=private_chat_id, silent=silent)
    else:
        send_message_to_ferris(text, silent)


def send_message_to_ferris(text: str, silent: bool = False):
    send_message(text=text, chat_id=private_chat_id, silent=silent)


def send_database_to_ferris(relative_db_path: str):
    bot.send_document(chat_id=private_chat_id, document=open(relative_db_path, 'rb'))
    return send_database_to_ferris(relative_db_path)
