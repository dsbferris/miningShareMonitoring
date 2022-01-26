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
        log.debug(f"Try setting db_connection for {db_path}")
        con = sqlite3.connect(db_path)
        log.debug("Setup sqlite db_connection")
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
    log.debug("Committed changes to db_connection")


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


def get_last_shares_of_worker(worker: str) -> mc.ShareStats:  # (valid, stale, invalid)
    cursor = get_con_cursor()
    GET_SHARES = '''SELECT validShares, staleShares, invalidShares FROM shares WHERE name=? ORDER BY timestamp DESC;'''

    GET_COUNT_OF_VALID_SHARES = '''SELECT COUNT(validShares) FROM shares WHERE name=?;'''

    log.debug(f"Try reading previous listing of {worker}")
    count = cursor.execute(GET_COUNT_OF_VALID_SHARES, [worker]).fetchone()[0]
    if count > 0:
        shares = cursor.execute(GET_SHARES, [worker]).fetchone()  # needs array, else error...
        # shares = list(shares)
        log.debug(f"Fetched previous valid shares: {shares}")
        shares: mc.ShareStats = mc.ShareStats(shares[0], shares[1], shares[2])
    else:
        shares: mc.ShareStats = mc.ShareStats(0, 0, 0)
        log.debug(f"{worker} is not listed. Returning (0, 0, 0)")
    return shares


def insert_worker_values(daily: mc.DailyReport):
    JUST_INSERT_SHARES = '''REPLACE INTO shares (name, validShares, staleShares, invalidShares, timestamp)
                            VALUES (?, ?, ?, ?, ?);'''
    ADD_UP_SHARES = '''UPDATE shares SET 
                        validShares=?, staleShares=?, invalidShares=?, timestamp=? 
                        WHERE name=?'''

    cursor = get_con_cursor()
    timestamp = datetime.datetime.now(de_timezone)
    for worker in daily.workers:
        previous = get_last_shares_of_worker(worker.name)
        worker.shares = worker.delta_shares + previous
        VALUES = [worker.name] + [worker.delta_shares.valid, worker.delta_shares.stale, worker.delta_shares.invalid] + [
            timestamp]
        # VALUES = [worker.shares.valid, worker.shares.stale, worker.shares.invalid] + [timestamp, worker.name]
        cursor.execute(JUST_INSERT_SHARES, VALUES)
        log.info(f"Inserted worker values: {VALUES}")
    con.commit()

    bot.daily_report(daily)


def insert_worker_values_old(worker_data: list[mc.WorkerStats], daily_reward_per_gigahash_sec_wei: int,
                             current_balance_wei: int, avg_hashrate: int):
    JUST_INSERT_SHARES = '''INSERT INTO shares (name, validShares, staleShares, invalidShares, timestamp)
                            VALUES (?, ?, ?, ?, ?);'''
    ADD_UP_SHARES = '''UPDATE shares SET 
                        validShares=?, staleShares=?, invalidShares=?, timestamp=? 
                        WHERE name=?'''

    cursor = get_con_cursor()
    timestamp = datetime.datetime.now(de_timezone)
    for worker in worker_data:
        previous = get_last_shares_of_worker(worker.name)
        actual = [worker.delta_shares.valid, worker.delta_shares.stale, worker.delta_shares.invalid]
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
    daily = mc.DailyReport(limit_wei=mc.wei_to_eth(payout_limit_wei), current_wei=mc.wei_to_eth(current_balance_wei),
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

# endregion

# region Payouts


def get_payouts() -> list[mc.Payout]:
    GET_PAYOUTS = '''SELECT * from payouts;'''
    cursor = get_con_cursor()
    log.debug("Fetching previous PAYOUTS")
    fetched = cursor.execute(GET_PAYOUTS).fetchall()
    return fetched


def insert_payouts(payout_data: dict):
    INSERT_OR_REPLACE_PAYOUT = '''REPLACE INTO payouts 
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

    # create payout class out of json dict
    api_payouts: list[mc.Payout] = []
    for payout in data:
        api_payouts.append(mc.Payout(payout))

    # get payouts from db
    recorded_payouts = get_payouts()
    # create list that contains already known payouts
    matched_payouts_both_contain: list[mc.Payout] = []
    for api_payout in api_payouts:
        for db_payout in recorded_payouts:
            if api_payout.txHash == db_payout.txHash:
                if api_payout.__eq__(db_payout):
                    matched_payouts_both_contain.append(api_payout)
                    break

    for matched_payout in matched_payouts_both_contain:
        api_payouts.remove(matched_payout)
    # TODO SHIT IS NOT WRITING PAYOUTS INTO DATABASE. CHECK ON THIS!
    if len(api_payouts) > 0:
        for api_payout in api_payouts:
            cursor.execute(INSERT_OR_REPLACE_PAYOUT, api_payout.__iter__())
            con.commit()
            bot.payout_new(api_payout, counter_value)
            insert_worker_values_at_payout(api_payout, counter_value)
            log.debug("NEW PAYOUT")
    else:
        log.debug("No new Payout.")
    # BELOW HERE IS OLD CODE

# endregion
