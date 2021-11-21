import os
from datetime import datetime, timedelta
import logging as log
import time
from zoneinfo import ZoneInfo
from telegram import Bot
import payout_class as pc

telegram_bot_api_key: str
group_chat_id: int
private_chat_id: int
de_timezone: ZoneInfo
bot: Bot
next_send_time: datetime


def init():
    global telegram_bot_api_key, group_chat_id, private_chat_id, de_timezone, bot, next_send_time
    telegram_bot_api_key = "API_KEY"
    group_chat_id = groupChatId
    private_chat_id = privateChatId
    de_timezone = ZoneInfo("Europe/Berlin")
    bot = Bot(token=telegram_bot_api_key)
    next_send_time = datetime.now(de_timezone) - timedelta(seconds=5)


def send_message(text: str, chat_id: int, silent: bool = False):
    global next_send_time
    error_occurred = False
    while datetime.now(de_timezone) < next_send_time:
        time.sleep(1)

    try:
        bot.send_message(text=text, chat_id=chat_id, disable_notification=silent, disable_web_page_preview=False)
    except Exception as e:
        log.error(e)
        error_occurred = True
    finally:
        next_send_time = datetime.now(de_timezone) + timedelta(seconds=5)
        if error_occurred:
            return send_message(text=text, chat_id=chat_id, silent=silent)


def send_message_to_group(text: str, silent: bool = False):
    if os.environ["PRODUCTION"] == "1":
        send_message(text=text, chat_id=group_chat_id, silent=silent)
    else:
        send_message_to_ferris(text, silent)


def send_message_to_ferris(text: str, silent: bool = False):
    send_message(text=text, chat_id=private_chat_id, silent=silent)


def send_database_to_ferris(relative_db_path: str):
    bot.send_document(chat_id=private_chat_id, document=open(relative_db_path, 'rb'))


def send_log_to_ferris(relative_log_path: str):
    bot.send_document(chat_id=private_chat_id, document=open(relative_log_path, 'rb'))


def daily_report(daily_data):
    if os.environ["PRODUCTION"] != 1:
        return
    text = f"Daily report\n\n"
    if len(daily_data) > 0:
        for d in daily_data:
            text += f"Name: {d[0]}\n" \
                    f"Valid shares: {d[1]}\n" \
                    f"Stale shares: {d[2]}\n" \
                    f"Invalid shares: {d[3]}\n\n"
        text = text.strip()
        send_message_to_group(text, True)


def payout_update(p: pc.Payout, counter_value):
    if os.environ["PRODUCTION"] != 1:
        return
    text = f"!!! PAYOUT DATA UPDATED !!!\n" \
           f"Current ETH-EUR: {counter_value}€\n" \
           f"Amount: {'{:.6f}'.format(p.value)} ({'{:.2f}'.format(p.value * counter_value)}€)\n" \
           f"Fee: {'{:.6f}'.format(p.fee)} ({'{:.2f}'.format(p.fee * counter_value)}€)\n" \
           f"Gas Price: {p.feePrice} Gwei\n" \
           f"Confirmed: {p.confirmed}\n" \
           f"Check on https://etherscan.io/tx/{p.txHash}"
    send_message_to_group(text)


def payout_new(p: pc.Payout, counter_value):
    if os.environ["PRODUCTION"] != 1:
        return
    text = f"!!! NEW PAYOUT !!!\n" \
           f"Current ETH-EUR: {counter_value}€\n" \
           f"Amount: {'{:.6f}'.format(p.value)} ({'{:.2f}'.format(p.value * counter_value)}€)\n" \
           f"Fee: {'{:.6f}'.format(p.fee)} ({'{:.2f}'.format(p.fee * counter_value)}€)\n" \
           f"Gas Price: {p.feePrice} Gwei\n" \
           f"Confirmed: {p.confirmed}\n" \
           f"Check on https://etherscan.io/tx/{p.txHash}"
    send_message_to_group(text)
