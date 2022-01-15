import datetime
from zoneinfo import ZoneInfo
import sqlite3
import logging as log
import os

import telegram_bot_module
import telegram_bot_module as bot
from flexpool import my_classes as mc

DATA_DIR = "database"
DATA_NAME = "flexpool_mining.db"
DATA_PATH = os.path.join(DATA_DIR, DATA_NAME)

con: sqlite3.Connection = None

de_timezone = ZoneInfo("Europe/Berlin")

payout_limit_wei: int

if not os.path.exists(DATA_DIR):
    os.mkdir(DATA_DIR)


def get_con_cursor() -> sqlite3.Cursor:
    global con
    if con is None:
        db_path = os.path.join(os.getcwd(), DATA_PATH)
        log.debug(f"Try setting con for {db_path}")
        con = sqlite3.connect(db_path)
        log.debug("Setup sqlite con")
        return con.cursor()
    else:
        try:
            c = con.cursor()
            return c
        except:
            con = None
            return get_con_cursor()


def init(payoutLimit: int):
    global payout_limit_wei
    payout_limit_wei = payoutLimit
    cursor = get_con_cursor()
    CREATE_TABLE_SHARES = '''CREATE TABLE IF NOT EXISTS shares(
                                name TEXT PRIMARY KEY,
                                validShares INTEGER NOT NULL,
                                staleShares INTEGER NOT NULL,
                                invalidShares INTEGER NOT NULL,
                                timestamp TIMESTAMP);'''
    cursor.execute(CREATE_TABLE_SHARES)
    log.debug("Created Table Shares")

    CREATE_TABLE_SHARES_AT_PAYOUT = '''CREATE TABLE IF NOT EXISTS shares_per_payout(
                                id INTEGER PRIMARY KEY AUTOINCREMENT,
                                name TEXT,
                                validShares INTEGER,
                                staleShares INTEGER,
                                invalidShares INTEGER,
                                hash TEXT,
                                timestamp TIMESTAMP,
                                FOREIGN KEY (hash) REFERENCES payouts(hash));'''
    cursor.execute(CREATE_TABLE_SHARES_AT_PAYOUT)
    log.debug("Created Table Shares at Payout")

    CREATE_TABLE_PAYOUTS = '''CREATE TABLE IF NOT EXISTS payouts(
                                timestamp TIMESTAMP,
                                value REAL,
                                fee REAL,
                                feePercent REAL,
                                feePrice INTEGER,
                                duration INTEGER,
                                confirmed BOOLEAN,
                                confirmedTimestamp TIMESTAMP,
                                hash TEXT PRIMARY KEY);'''
    cursor.execute(CREATE_TABLE_PAYOUTS)
    log.debug("Created Table Payouts")
    con.commit()
    log.debug("Committed changes to db")


# region Worker

def get_latest_share_datetime():
    TIMESTAMP_COUNT = '''SELECT COUNT(timestamp) FROM shares;'''
    GET_TIMESTAMP = '''SELECT timestamp FROM shares;'''
    cursor = get_con_cursor()
    count = cursor.execute(TIMESTAMP_COUNT).fetchone()[0]
    if count <= 0:
        return None
    else:
        fetched = cursor.execute(GET_TIMESTAMP).fetchone()[0]
        date_time_string_format = '%Y-%m-%d %H:%M:%S.%f%z'
        fixed_date_string = fetched.removesuffix(":00") + "00"
        s_datetime = datetime.datetime.strptime(fixed_date_string, date_time_string_format)
        return s_datetime


def get_all_workers_shares():
    GET_ALL_WORKERS = '''SELECT * from shares'''
    cursor = get_con_cursor()
    fetched = cursor.execute(GET_ALL_WORKERS).fetchall()
    return fetched


def get_last_shares_of_worker(worker: str) -> list:  # (valid, stale, invalid)
    cursor = get_con_cursor()
    GET_SHARES = '''SELECT validShares, staleShares, invalidShares FROM shares WHERE name=? ORDER BY timestamp DESC;'''

    GET_COUNT_OF_VALID_SHARES = '''SELECT COUNT(validShares) FROM shares WHERE name=?;'''

    log.debug(f"Try reading previous valid shares of {worker}")
    valid_shares = None
    count = cursor.execute(GET_COUNT_OF_VALID_SHARES, [worker]).fetchone()[0]
    if count > 0:
        valid_shares = cursor.execute(GET_SHARES, [worker]).fetchone()  # needs array, else error...
        valid_shares = list(valid_shares)
        log.debug(f"Fetched previous valid shares: {valid_shares}")
    else:
        log.debug("Worker had no previous valid shares")
    return valid_shares


# Hashrate in H/s, payout_limit and currentBalance in wei, not ETH, dailyRewardPerGigaHashSec in wei/ GH/s
def days_left_for_payout(hashRate: int, dailyRewardPerGigaHashSec_wei: int,
                         payoutLimit_wei: int, currentBalance_wei: int) -> float:
    # payout in x days (payout limit - <miner/balance>) / daily eth (using <miner/stats> hashrate and
    # <pool/dailyRewardPerGigaHashSec>) = eth left for payout / daily eth mined by current hashrate = eth left for
    # payout / current hashrate * dailyRewardPerGigaHashSec

    # dailyRewardPerGigaHashSec = 16617213256156008 wei / 1 GH/s = wei / 1 * 10^9 H/s
    # miner/stats/currentEffectiveHashrate = 80000000 = 80MH/s
    # miner/stats/averageEffectiveHashrate = 57361110.791666664 = 57,4MH/s = 57,4 * 10^6 H/s
    left_for_payout = payoutLimit_wei - currentBalance_wei
    # pow(10,9) to remove the Giga from dailyRewardPerGigaHashSec
    daily_wei = (dailyRewardPerGigaHashSec_wei * hashRate) / pow(10, 9)
    days_left = left_for_payout / daily_wei
    return days_left


def insert_worker_values(worker_data: list[mc.WorkerStats], daily_reward_per_gigahash_sec_wei: int, current_balance_wei: int, avg_hashrate: int):
    JUST_INSERT_SHARES = '''INSERT INTO shares (name, validShares, staleShares, invalidShares, timestamp)
                            VALUES (?, ?, ?, ?, ?);'''
    ADD_UP_SHARES = '''UPDATE shares SET 
                        validShares=?, staleShares=?, invalidShares=?, timestamp=? 
                        WHERE name=?'''

    cursor = get_con_cursor()
    timestamp = datetime.datetime.now(de_timezone)
    for worker in worker_data:
        previous = get_last_shares_of_worker(worker.name)
        actual = [worker.share_delta.valid, worker.share_delta.stale, worker.share_delta.invalid]
        if previous is None:
            VALUES = [worker.name] + actual + [timestamp]
            cursor.execute(JUST_INSERT_SHARES, VALUES)
        else:
            new_actual = []
            for i in range(0, len(previous)):
                new_actual += [actual[i] + previous[i]]
            VALUES = new_actual + [timestamp, worker.name]
            cursor.execute(ADD_UP_SHARES, VALUES)
        log.info(f"Inserted worker values: {VALUES}")
    con.commit()

    GET_ALL_WORKER_CURRENT_VALUES = '''SELECT * from shares;'''
    daily_worker_data: list[tuple] = cursor.execute(GET_ALL_WORKER_CURRENT_VALUES).fetchall()

    days_left = days_left_for_payout(
        hashRate=avg_hashrate,
        payoutLimit_wei=payout_limit_wei,
        currentBalance_wei=current_balance_wei,
        dailyRewardPerGigaHashSec_wei=daily_reward_per_gigahash_sec_wei)

    # TODO Add Payout in X Days into daily report
    # TODO Warn worker if offline for 24 hours (aka +0) for max. three times in row
    daily = mc.DailyReport(limit_eth=mc.wei_to_eth(payout_limit_wei), current_eth=mc.wei_to_eth(current_balance_wei),
                           days_left=days_left, workers=[])
    bot.daily_report(daily)

    con.close()


def delete_worker(name: str):
    DELETE_WORKER = '''DELETE FROM shares WHERE name=?'''
    cursor = get_con_cursor()
    cursor.execute(DELETE_WORKER, [name])
    con.commit()


# endregion

# region Shares Per Payout

def get_workers_shares_for_payout(txHash: str):
    GET_WORKERS_SHARES_FOR_PAYOUT = '''SELECT * FROM shares_per_payout WHERE hash=?'''
    cursor = get_con_cursor()
    fetched = cursor.execute(GET_WORKERS_SHARES_FOR_PAYOUT, [txHash]).fetchall()
    return fetched


def insert_worker_values_at_payout(p: mc.Payout, counter_value):
    INSERT_WORKER_DATA_AT_PAYOUT = '''INSERT INTO shares_per_payout
                                        (name, validShares, staleShares, invalidShares, hash, timestamp) 
                                        VALUES (?,?,?,?,?,?);'''
    cursor = get_con_cursor()
    workers_shares = get_all_workers_shares()
    for worker in workers_shares:
        name = worker[0]
        valid = worker[1]
        stale = worker[2]
        invalid = worker[3]
        VALUES = [name, valid, stale, invalid, p.txHash, datetime.datetime.now(de_timezone)]
        cursor.execute(INSERT_WORKER_DATA_AT_PAYOUT, VALUES)
        delete_worker(name)
    con.commit()
    stats = get_workers_shares_for_payout(p.txHash)
    telegram_bot_module.worker_stats_per_payout(stats, p, counter_value)
    # TODO CONTINUE HERE!
    pass
    pass


# endregion

# region Payouts


def get_payouts() -> list[mc.Payout]:
    GET_PAYOUTS = '''SELECT * from payouts;'''
    cursor = get_con_cursor()
    fetched = cursor.execute(GET_PAYOUTS).fetchall()
    print(fetched)
    return fetched


def insert_payouts(payout_data: dict):
    JUST_INSERT_PAYOUT = '''INSERT INTO payouts 
                        (timestamp, value, fee, feePercent, feePrice, duration, confirmed, confirmedTimestamp, hash) 
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);'''

    UPDATE_PAYOUT = '''UPDATE payouts SET
                        timestamp=?,
                        value=?,
                        fee=?,
                        feePercent=?,
                        feePrice=?,
                        duration=?,
                        confirmed=?,
                        confirmedTimestamp=?
                        WHERE hash=?;'''

    cursor = get_con_cursor()
    data: list[dict] = payout_data.get("data")
    counter_value: float = payout_data.get("countervalue")

    request_payouts: list[mc.Payout] = []
    for payout in data:
        request_payouts.append(mc.Payout(payout))

    db_hashset: list[str] = []
    db_payouts: list[mc.Payout] = []
    tuple_list = get_payouts()
    for t in tuple_list:
        p = mc.Payout(t)
        db_payouts.append(p)
        db_hashset.append(p.txHash)

    new_payouts = request_payouts
    for db in db_payouts:
        for req in request_payouts:
            if db == req:
                new_payouts.remove(db)
                break

    if len(new_payouts) > 0:
        for p in new_payouts:
            if db_hashset.__contains__(p.txHash):
                cursor.execute(UPDATE_PAYOUT, p.__iter__())
                bot.payout_update(p, counter_value)
            else:
                cursor.execute(JUST_INSERT_PAYOUT, p.__iter__())
                bot.payout_new(p, counter_value)
                insert_worker_values_at_payout(p, counter_value)

        con.commit()
    else:
        log.info("No new payouts")
    con.close()

# endregion
