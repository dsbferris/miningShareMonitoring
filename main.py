import time
import logging as log
import logging_module
import nanopool_requests_module as nano_api
import nanopool_database_module as nano_db
import flexpool_database_module as flex_db
import flexpool_requests_module as flex_api
import telegram_bot_module as bot

logging_module.init_logging()  # setup logging format and file
log.info("Started script")

# nano_db.init_database()  # used to setup a non existing database

flex_db.init_database()
# bot.send_message_to_ferris("Script started", silent=True)


def monitor_flexpool():
    worker_data = flex_api.get_data_of_workers()
    flex_db.insert_worker_values(worker_data)

    payout_data = flex_api.get_payment_data()
    if payout_data is None:
        log.debug("No payouts yet")
    else:
        flex_db.insert_payouts(payout_data)


def monitor_nanopool():
    worker_data = nano_api.get_data_of_workers()  # sample: [(worker, rating),(worker, rating)...]
    nano_db.insert_worker_values(worker_data)

    payout_data = nano_api.get_payment_data()
    nano_db.insert_payouts(payout_data)


def test():
    error = False
    try:
        print("Hello")
        print(1/0)
    except:
        error = True
        print("error")
        time.sleep(5)
    finally:
        print("finally")
        print(error)


while True:
    # monitor_nanopool()
    monitor_flexpool()
    log.info("Restart in 3600 seconds\n")
    time.sleep(3600)
