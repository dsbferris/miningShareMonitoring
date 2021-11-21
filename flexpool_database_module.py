import datetime
import functools
from zoneinfo import ZoneInfo
import sqlite3
import logging as log
import os
import telegram_bot_module as bot
import payout_class as pc

DATA_DIR = "database"
DATA_NAME = "flexpool_mining.db"
DATA_PATH = os.path.join(DATA_DIR, DATA_NAME)

con: sqlite3.Connection = None

de_timezone = ZoneInfo("Europe/Berlin")

if not os.path.exists(DATA_DIR):
    os.mkdir(DATA_DIR)


def get_con_cursor() -> sqlite3.Cursor:
    global con
    if con is None:
        con = sqlite3.connect(os.path.join(os.getcwd(), DATA_PATH))
        return con.cursor()
    else:
        try:
            c = con.cursor()
            return c
        except:
            con = None
            return get_con_cursor()


def init():
    cursor = get_con_cursor()
    CREATE_TABLE_SHARES = '''CREATE TABLE IF NOT EXISTS shares(
                                name TEXT PRIMARY KEY,
                                validShares INTEGER NOT NULL,
                                staleShares INTEGER NOT NULL,
                                invalidShares INTEGER NOT NULL,
                                timestamp TIMESTAMP);'''
    cursor.execute(CREATE_TABLE_SHARES)

    CREATE_TABLE_SHARES_AT_PAYOUT = '''CREATE TABLE IF NOT EXISTS shares_per_payout(
                                id INTEGER PRIMARY KEY AUTOINCREMENT,
                                name TEXT,
                                validShares INTEGER,
                                staleShares INTEGER,
                                invalidShares INTEGER,
                                hash TEXT,
                                FOREIGN KEY (hash) REFERENCES payouts(hash));'''
    cursor.execute(CREATE_TABLE_SHARES_AT_PAYOUT)

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
    con.commit()


# region Worker

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


def insert_worker_values(worker_data: list[dict]):
    JUST_INSERT_SHARES = '''INSERT INTO shares (name, validShares, staleShares, invalidShares, timestamp)
                            VALUES (?, ?, ?, ?, ?);'''
    ADD_UP_SHARES = '''UPDATE shares SET 
                        validShares=?, staleShares=?, invalidShares=?, timestamp=? 
                        WHERE name=?'''

    cursor = get_con_cursor()
    timestamp = datetime.datetime.now(de_timezone)
    for worker in worker_data:
        name = worker.get("name")
        valid = worker.get("validShares")
        stale = worker.get("staleShares")
        invalid = worker.get("invalidShares")

        previous = get_last_shares_of_worker(name)
        actual = [valid, stale, invalid]
        if previous is None:
            VALUES = [name] + actual + [timestamp]
            cursor.execute(JUST_INSERT_SHARES, VALUES)
        else:
            new_actual = []
            for i in range(0, len(previous)):
                new_actual += [actual[i] + previous[i]]
            VALUES = new_actual + [timestamp, name]
            cursor.execute(ADD_UP_SHARES, VALUES)
        log.info(f"Inserted worker values: {VALUES}")
    con.commit()

    GET_ALL_WORKER_CURRENT_VALUES = '''SELECT * from shares;'''
    daily_data: list[tuple] = cursor.execute(GET_ALL_WORKER_CURRENT_VALUES).fetchall()
    bot.daily_report(daily_data)

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
    fetched = cursor.execute(GET_WORKERS_SHARES_FOR_PAYOUT, [txHash])
    return fetched


def insert_worker_values_at_payout(p: pc.Payout, counter_value):
    INSERT_WORKER_DATA_AT_PAYOUT = '''INSERT INTO shares_per_payout
                                        (name, validShares, staleShares, invalidShares, hash) 
                                        VALUES (?,?,?,?,?);'''
    cursor = get_con_cursor()
    workers_shares = get_all_workers_shares()
    for worker in workers_shares:
        name = worker[0]
        valid = worker[1]
        stale = worker[2]
        invalid = worker[3]
        VALUES = [name, valid, stale, invalid, p.txHash]
        cursor.execute(INSERT_WORKER_DATA_AT_PAYOUT, VALUES)
        delete_worker(name)
    stats = get_workers_shares_for_payout(p.txHash)
    # TODO CONTINUE HERE!
    pass
    pass


# endregion

# region Payouts


def get_payouts() -> list[pc.Payout]:
    GET_PAYOUTS = '''SELECT * from payouts;'''
    cursor = get_con_cursor()
    fetched = cursor.execute(GET_PAYOUTS).fetchall()
    print(fetched)
    return fetched


def insert_payouts(payout_data: dict):
    '''INSERT_PAYOUTS = INSERT INTO payouts
                        (hash, timestamp, value, fee, feePercent, feePrice, duration, confirmed, confirmedTimestamp) 
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?) 
                        ON CONFLICT (hash) DO UPDATE SET 
                            timestamp=excluded.timestamp,
                            value=excluded.value,
                            fee=excluded.fee,
                            feePercent=excluded.feePercent,
                            feePrice=excluded.feePrice,
                            duration=excluded.duration,
                            confirmed=excluded.confirmed,
                            confirmedTimestamp=excluded.confirmedTimestamp
                        WHERE confirmed != excluded.confirmed
                        OR confirmedTimestamp != excluded.confirmedTimestamp;'''
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

    request_payouts: list[pc.Payout] = []
    for payout in data:
        request_payouts.append(pc.Payout(payout))

    db_hashset: list[str] = []
    db_payouts: list[pc.Payout] = []
    tuple_list = get_payouts()
    for t in tuple_list:
        p = pc.Payout(t)
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
                pass
                cursor.execute(UPDATE_PAYOUT, p.__iter__())
                bot.payout_update(p, counter_value)
            else:
                cursor.execute(JUST_INSERT_PAYOUT, p.__iter__())
                bot.payout_new(p, counter_value)
                if os.environ["PRODUCTION"] == 1:
                    insert_worker_values_at_payout(p, counter_value)

        con.commit()
    else:
        log.info("No new payouts")
    con.close()

# endregion
