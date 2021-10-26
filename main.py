import os
import sys
import time
import sched
import logging as log
import logging_module
import flexpool_database_module as flex_db
import flexpool_requests_module as flex_api
import telegram_bot_module as bot
"""
import nanopool_requests_module as nano_api
import nanopool_database_module as nano_db
"""


if not os.environ.__contains__("DEBUG"):
    os.environ["DEBUG"] = "0"  # 0=TRUE, 1=FALSE


logging_module.init_logging()  # setup logging format and file
log.info("Started script")
# nano_db.init_database()  # used to setup a non existing database
flex_db.init()
flex_api.init()
bot.init()

if sys.argv.__contains__("-sendDatabase"):
    if not os.path.exists(flex_db.DATA_PATH):
        log.error("Database file does not exists!")
    else:
        bot.send_database_to_ferris(flex_db.DATA_PATH)
    exit(0)


if sys.argv.__contains__("-sendLog"):
    if not os.path.exists("my_log.log"):
        log.error("Log file does not exists!")
    else:
        bot.send_log_to_ferris("my_log.log")
    exit(0)


s = sched.scheduler(time.time, time.sleep)
bot.send_message_to_ferris("Script started", silent=True)


def monitor_flexpool():
    worker_data = flex_api.get_data_of_workers()
    flex_db.insert_worker_values(worker_data)

    payout_data = flex_api.get_payment_data()
    if payout_data is None:
        log.debug("No payouts yet")
    else:
        flex_db.insert_payouts(payout_data)

    log.info("Restart in 3600 seconds\n")
    s.enter(3600, 1, monitor_flexpool)


"""
def monitor_nanopool():
    worker_data = nano_api.get_data_of_workers()  # sample: [(worker, rating),(worker, rating)...]
    nano_db.insert_worker_values(worker_data)

    payout_data = nano_api.get_payment_data()
    nano_db.insert_payouts(payout_data)

"""


s.enter(0, 1, monitor_flexpool)
s.run()
