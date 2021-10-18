import logging as log
import time
import telegram

telegram_bot_api_key = "API_KEY"
group_chat_id = groupChatId
private_chat_id = privateChatId

bot = telegram.Bot(token=telegram_bot_api_key)


def send_message_to_group(text: str, silent: bool = False):
    try:
        bot.send_message(text=text, chat_id=group_chat_id, disable_notification=silent)
    except Exception as e:
        log.error(e)
        log.error("Try again in 5 seconds")
        time.sleep(5)
        return send_message_to_group(text, silent)


def send_message_to_ferris(text: str, silent: bool = False):
    try:
        bot.send_message(text=text, chat_id=private_chat_id, disable_notification=silent)
    except Exception as e:
        log.error(e)
        log.error("Try again in 5 seconds")
        time.sleep(5)
        return send_message_to_group(text, silent)


def send_database_to_ferris(relative_db_path: str):
    try:
        bot.send_document(chat_id=private_chat_id, document=open(relative_db_path, 'rb'))
    except Exception as e:
        log.error(e)
        log.error("Try again in 5 seconds")
        time.sleep(5)
        return send_message_to_group(text, silent)
