import datetime
import os
import sys
import time
import sched
import logging as log
import logging_module
from flexpool import flexpool_database_module as db, flexpool_requests_module as api
import telegram_bot_module as bot
from flexpool import my_classes as mc

s = sched.scheduler(time.time, time.sleep)
payout_limit_in_wei: int



def init():
    global s, payout_limit_in_wei

    if not os.environ.__contains__("PRODUCTION"):
        os.environ["PRODUCTION"] = "0"  # 0=DEBUG 1=PRODUCTION

    logging_module.init_logging()
    log.info("Started script")
    db.init()
    api.init()
    bot.init()

    # bot.send_message_to_ferris("Script started", silent=True)
    payout_limit_in_eth = 0.075
    payout_limit_in_wei = mc.eth_to_wei(payout_limit_in_eth)


init()


def monitor_shares():

    worker_data = api.miner_workers()
    db.insert_worker_values(worker_data)


def monitor_payouts():
    payout_data = api.miner_payments()
    if payout_data is None:
        log.debug("No payouts yet")
    else:
        db.insert_payouts(payout_data)


def monitor_flexpool():
    monitor_shares()
    monitor_payouts()
    log.info("See you in 24 hours\n")
    s.enter(datetime.timedelta(days=1).total_seconds(), 1, monitor_flexpool)


last_time_running = db.get_latest_share_datetime()
if last_time_running is not None:
    time_diff = datetime.datetime.now(db.de_timezone) - last_time_running
    one_day_seconds = datetime.timedelta(days=1)
    wait_diff = one_day_seconds - time_diff
    wait_seconds = wait_diff.total_seconds()
    if wait_seconds < 0:
        s.enter(0, 1, monitor_flexpool)
    else:
        print(f"Fetched last values at {last_time_running}.\nWaiting {wait_diff}")
        s.enter(wait_seconds, 1, monitor_flexpool)
else:
    s.enter(0, 1, monitor_flexpool)
s.run()
