import datetime
import time
from zoneinfo import ZoneInfo
import logging as log
import logging_module
import nanopool_requests_module as nano_api
import nanopool_database_module as nano_db
import flexpool_database_module as flex_db
import flexpool_requests_module as flex_api
import telegram_bot_module as bot

logging_module.init_logging()  # setup logging format and file
log.info("Started script")

de_timezone = ZoneInfo("Europe/Berlin")
nano_db.init_database()  # used to setup a non existing database

bot.send_message_to_ferris("Script started", silent=True)


def wei_to_eth(wei: int) -> float:
    giga_giga = pow(10, 18)
    return wei / giga_giga


def monitor_nanopool():
    worker_data = nano_api.get_data_of_workers()  # sample: [(worker, rating),(worker, rating)...]
    nano_db.insert_worker_values(worker_data)

    payout_data = nano_api.get_payment_data()
    nano_db.insert_payouts(payout_data)


def monitor_flexpool():
    worker_data = flex_api.get_data_of_workers()
    flex_db.insert_worker_values(worker_data)

    payout_data = flex_api.get_payment_data()
    flex_db.insert_payouts(payout_data)


while True:
    monitor_nanopool()
    log.info("Restart in 3600 seconds\n")
    time.sleep(3600)
