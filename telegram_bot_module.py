import os
from datetime import datetime, timedelta
import logging as log
import time
from zoneinfo import ZoneInfo
from telegram import Bot
from flexpool import my_classes as pc

telegram_bot_api_key: str
group_chat_id: int
private_chat_id: int
de_timezone: ZoneInfo
bot: Bot
next_send_time: datetime


def init(api_key: str, groud_id, private_id):
    global telegram_bot_api_key, group_chat_id, private_chat_id, de_timezone, bot, next_send_time
    telegram_bot_api_key = api_key
    group_chat_id = groud_id
    private_chat_id = private_id

    # telegram_bot_api_key = "API_KEY"
    # group_chat_id = groupChatId
    # private_chat_id = privateChatId
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


def daily_report(daily_data):
    text = f"Daily report\n\n"
    if len(daily_data) > 0:
        for d in daily_data:
            text += f"Name: {d[0]}\n" \
                    f"Valid shares: {d[1]}\n" \
                    f"Stale shares: {d[2]}\n" \
                    f"Invalid shares: {d[3]}\n\n"
        text = text.strip()
        if os.environ["PRODUCTION"] != "1":
            send_message_to_ferris(text, True)
        else:
            send_message_to_group(text, True)


def payout_update(p: pc.Payout, counter_value):
    text = f"!!! PAYOUT DATA UPDATED !!!\n" \
           f"Current ETH-EUR: {counter_value}€\n" \
           f"Amount: {'{:.6f}'.format(p.value)} ({'{:.2f}'.format(p.value * counter_value)}€)\n" \
           f"Fee: {'{:.6f}'.format(p.fee)} ({'{:.2f}'.format(p.fee * counter_value)}€)\n" \
           f"Gas Price: {p.feePrice} Gwei\n" \
           f"Confirmed: {p.confirmed}\n" \
           f"Check on https://etherscan.io/tx/{p.txHash}"
    if os.environ["PRODUCTION"] != "1":
        send_message_to_ferris(text, True)
    else:
        send_message_to_group(text)


def payout_new(p: pc.Payout, counter_value):
    text = f"!!! NEW PAYOUT !!!\n" \
           f"Current ETH-EUR: {counter_value}€\n" \
           f"Amount: {'{:.6f}'.format(p.value)} ({'{:.2f}'.format(p.value * counter_value)}€)\n" \
           f"Fee: {'{:.6f}'.format(p.fee)} ({'{:.2f}'.format(p.fee * counter_value)}€)\n" \
           f"Gas Price: {p.feePrice} Gwei\n" \
           f"Confirmed: {p.confirmed}\n" \
           f"Check on https://etherscan.io/tx/{p.txHash}"
    if os.environ["PRODUCTION"] != "1":
        send_message_to_ferris(text, True)
    else:
        send_message_to_group(text)


def worker_stats_per_payout(worker_stats: list, p: pc.Payout, counter_value: float):
    total_shares = 0
    for worker in worker_stats:
        total_shares += worker[2]
    text = "Worker statistics for this payout:\n" \
           f"Countervalue of eth-eur: {counter_value}€\n\n"
    for worker in worker_stats:
        valid_percent = worker[2] / total_shares
        text += f"{worker[1]} has {worker[2]} valid shares.\n"
        text += f"This equals to {'{:2.2f}'.format(valid_percent*100)}% "
        text += f"and about {'{:.2f}'.format(p.value * counter_value * valid_percent)}€\n\n"
    if os.environ["PRODUCTION"] != "1":
        send_message_to_ferris(text, True)
    else:
        send_message_to_group(text)


# unused

def ripped_from_main_init(sys, db, bot):
    if sys.argv.__contains__("-sendDatabase"):
        if not os.path.exists(db.DATA_PATH):
            log.error("Database file does not exists!")
        else:
            bot.send_database_to_ferris(db.DATA_PATH)
        exit(0)

    if sys.argv.__contains__("-sendLog"):
        if not os.path.exists("my_log.log"):
            log.error("Log file does not exists!")
        else:
            bot.send_log_to_ferris("my_log.log")
        exit(0)


def send_database_to_ferris(relative_db_path: str):
    bot.send_document(chat_id=private_chat_id, document=open(relative_db_path, 'rb'))


def send_log_to_ferris(relative_log_path: str):
    bot.send_document(chat_id=private_chat_id, document=open(relative_log_path, 'rb'))

