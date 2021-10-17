import logging
import telegram

telegram_bot_api_key = "API_KEY"
group_chat_id = groupChatId
private_chat_id = privateChatId

bot = telegram.Bot(token=telegram_bot_api_key)


def send_message_to_group(text: str, silent: bool = False):
    bot.send_message(text=text, chat_id=group_chat_id, disable_notification=silent)


def send_message_to_ferris(text: str, silent: bool = False):
    bot.send_message(text=text, chat_id=private_chat_id, disable_notification=silent)


def send_database_to_ferris():
    bot.send_document(chat_id=private_chat_id, document=open('database/nanopool_mining.db', 'rb'))
