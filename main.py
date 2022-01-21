import datetime
import os
import time
import sched
import logging as log
import logging_module
from flexpool import flexpool_database_module as db, flexpool_requests_module as api, my_classes as mc
import telegram_bot_module as bot


# TODO WRITE TESTS!!! ONLY WAY TO VERIFY PRODUCTION BUILD ARE REALLY WORKING CORRECT!


s = sched.scheduler(time.time, time.sleep)
logging_module.init_logging()


def init():
    if not os.environ.__contains__("PRODUCTION"):
        os.environ["PRODUCTION"] = "0"  # 0=DEBUG 1=PRODUCTION

    api_key: str = ""
    if os.environ.__contains__("API_KEY"):
        api_key = os.environ["API_KEY"]

    private_chat_id: int = 0
    if os.environ.__contains__("PRIVATE_CHAT_ID"):
        private_chat_id = int(os.environ["PRIVATE_CHAT_ID"])

    group_chat_id: int = 0
    if os.environ.__contains__("GROUP_CHAT_ID"):
        group_chat_id = int(os.environ["GROUP_CHAT_ID"])

    miner_address: str = ""
    if os.environ.__contains__("MINER_ADDRESS"):
        miner_address = os.environ["MINER_ADDRESS"]

    payout_limit_eth: float = 0
    if os.environ.__contains__("PAYOUT_LIMIT_ETH"):
        payout_limit_eth = float(os.environ["PAYOUT_LIMIT_ETH"])

    if api_key == "" or private_chat_id == 0 or group_chat_id == 0 or miner_address == "" or payout_limit_eth == 0:
        log.error("Some environment variable was not given!\nExiting")
        exit(-1)

    log.debug("Fetched all environment variables")
    payout_limit_wei = mc.eth_to_wei(payout_limit_eth)
    db.init(payoutLimit=payout_limit_wei)
    api.init(address=miner_address)
    bot.init(api_key=api_key, private_id=private_chat_id, group_id=group_chat_id)


init()


def monitor_shares():
    worker_data = api.miner_workers()

    daily_reward_per_gigahash_sec_wei = api.pool_daily_reward_per_gigahash_sec()
    current_balance_wei = api.miner_balance_wei()
    avg_eff_hash = int(api.miner_average_effective_hashrate())

    daily: mc.DailyReport = mc.DailyReport(
        workers=worker_data,
        current_wei=current_balance_wei,
        limit_wei=db.payout_limit_wei,
        avg_eff_hashrate=avg_eff_hash,
        daily_reward_per_gigahash_sec_wei=daily_reward_per_gigahash_sec_wei
    )

    db.insert_worker_values(daily)


def monitor_payouts():
    payout_data = api.miner_payments()
    if payout_data is None:
        log.debug("No payouts yet")
    else:
        db.insert_payouts(payout_data=payout_data)


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
        log.debug(f"Fetched last values at {last_time_running}.")
        log.debug(f"Waiting {wait_diff}")
        s.enter(wait_seconds, 1, monitor_flexpool)
else:
    s.enter(0, 1, monitor_flexpool)

s.run()
