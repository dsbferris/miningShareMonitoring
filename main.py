import os
import sys
import time
import sched
import logging as log
import logging_module
import flexpool_database_module as db
import flexpool_requests_module as api
import telegram_bot_module as bot

s = sched.scheduler(time.time, time.sleep)


def init():
    global s
    if not os.environ.__contains__("PRODUCTION"):
        os.environ["PRODUCTION"] = "0"  # 0=DEBUG 1=PRODUCTION

    logging_module.init_logging()
    log.info("Started script")
    db.init()
    api.init()
    bot.init()

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

    bot.send_message_to_ferris("Script started", silent=True)


init()

db.get_all_workers_shares()


def monitor_shares():
    worker_data = api.get_data_of_workers()
    db.insert_worker_values(worker_data)


def monitor_payouts():
    payout_data = api.get_payment_data()
    if payout_data is None:
        log.debug("No payouts yet")
    else:
        db.insert_payouts(payout_data)


def monitor_flexpool():
    monitor_shares()
    monitor_payouts()
    log.info("See you in 24 hours\n")
    s.enter(24 * 3600, 1, monitor_flexpool)


s.enter(0, 1, monitor_flexpool)
s.run()
