import datetime
from zoneinfo import ZoneInfo
import sqlite3
import logging as log
import os
import telegram_bot_module as bot

DATA_DIR = "database"
DATA_NAME = "flexpool_mining.db"
DATA_PATH = os.path.join(DATA_DIR, DATA_NAME)

de_timezone = ZoneInfo("Europe/Berlin")

if not os.path.exists(DATA_DIR):
    os.mkdir(DATA_DIR)


def wei_to_eth(wei: int) -> float:
    giga_giga = pow(10, 18)
    return wei / giga_giga


def get_connection() -> sqlite3.Connection:
    return sqlite3.connect(os.path.join(os.getcwd(), DATA_PATH))


def init():
    connection = get_connection()
    cursor = connection.cursor()
    CREATE_TABLE_SHARES = '''CREATE TABLE IF NOT EXISTS shares(
                                name TEXT PRIMARY KEY,
                                validShares INTEGER NOT NULL,
                                staleShares INTEGER NOT NULL,
                                invalidShares INTEGER NOT NULL,
                                timestamp TIMESTAMP);'''
    cursor.execute(CREATE_TABLE_SHARES)

    CREATE_TABLE_RESETS = '''CREATE TABLE IF NOT EXISTS resets(
                                id INTEGER PRIMARY KEY AUTOINCREMENT,
                                name TEXT,
                                validSharesBefore INTEGER,
                                staleSharesBefore INTEGER,
                                invalidSharesBefore INTEGER,
                                validSharesAfter INTEGER,
                                staleSharesAfter INTEGER,
                                invalidSharesAfter INTEGER,
                                timestamp TIMESTAMP);'''
    cursor.execute(CREATE_TABLE_RESETS)

    CREATE_TABLE_PAYOUTS = '''CREATE TABLE IF NOT EXISTS payouts(
                                hash TEXT PRIMARY KEY,
                                timestamp TIMESTAMP,
                                value INTEGER,
                                fee INTEGER,
                                feePercent REAL,
                                feePrice INTEGER,
                                duration INTEGER,
                                confirmed BOOLEAN,
                                confirmedTimestamp TIMESTAMP);'''
    cursor.execute(CREATE_TABLE_PAYOUTS)
    connection.commit()
    connection.close()


def get_last_shares_of_worker(worker: str, cursor: sqlite3.Cursor) -> tuple:  # (valid, stale, invalid)
    GET_SHARES = '''SELECT validShares, staleShares, invalidShares FROM shares WHERE name=? ORDER BY timestamp DESC;'''

    GET_COUNT_OF_VALID_SHARES = '''SELECT COUNT(validShares) FROM shares WHERE name=?;'''

    log.debug(f"Try reading previous valid shares of {worker}")
    valid_shares = None
    if cursor.execute(GET_COUNT_OF_VALID_SHARES, [worker]).fetchone()[0] > 0:
        valid_shares = cursor.execute(GET_SHARES, [worker]).fetchone()  # needs array, else error...
        log.debug(f"Fetched previous valid shares: {valid_shares}")
    else:
        log.debug("Worker had no previous valid shares")
    return valid_shares


def insert_worker_values(worker_data: list[dict]):
    INSERT_SHARES = '''INSERT INTO shares (name, validShares, staleShares, invalidShares, timestamp)
                            VALUES (?, ?, ?, ?, ?)
                            ON CONFLICT (name) DO UPDATE SET 
                                validShares=excluded.validShares,
                                staleShares=excluded.staleShares,
                                invalidShares=excluded.invalidShares,
                                timestamp=excluded.timestamp
                            WHERE timestamp < excluded.timestamp'''

    con = get_connection()
    cursor = con.cursor()
    timestamp = datetime.datetime.now(de_timezone)
    for worker in worker_data:
        name = worker.get("name")
        valid = worker.get("validShares")
        stale = worker.get("staleShares")
        invalid = worker.get("invalidShares")

        previous = get_last_shares_of_worker(name, cursor)
        actual = (valid, stale, invalid)
        if previous is not None and previous > actual:
            INSERT_RESET = '''INSERT INTO resets 
            (name, 
            validSharesBefore, staleSharesBefore, invalidSharesBefore, 
            validSharesAfter, staleSharesAfter, invalidSharesAfter, 
            timestamp)
                                VALUES (?, ?, ?, ?, ?, ?, ?, ?)'''
            RESET_VALUES = (name, previous[0], previous[1], previous[2], actual[0], actual[1], actual[2], timestamp)
            cursor.execute(INSERT_RESET, RESET_VALUES)
            tuple_string = f"Worker was resettet!\n" \
                           f"Time: {timestamp.strftime('%Y-%m-%d %H:%M:%S')}\n" \
                           f"Worker: {name}\n" \
                           f"Format: (Valid, Stale, Invalid)\n" \
                           f"Previous: {previous}\n" \
                           f"Now: {actual}"
            bot.send_message_to_group(tuple_string)
            log.critical(f"RESET! {RESET_VALUES}")

        VALUES = (name, valid, stale, invalid, timestamp)
        cursor.execute(INSERT_SHARES, VALUES)
        log.info(f"Inserted worker values: {VALUES}")

    con.commit()
    if timestamp.hour == 14:
        GET_ALL_WORKER_CURRENT_VALUES = '''SELECT * from shares;'''
        daily_data: list[tuple] = cursor.execute(GET_ALL_WORKER_CURRENT_VALUES).fetchall()
        text = f"Daily report\n\n"
        for d in daily_data:
            text += f"Name: {d[0]}\n" \
                    f"Valid shares: {d[1]}\n" \
                    f"Stale shares: {d[2]}\n" \
                    f"Invalid shares: {d[3]}\n"
            bot.send_message_to_group(text, True)
    con.close()


def insert_payouts(data: dict):
    INSERT_PAYOUTS = '''INSERT INTO payouts 
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
    con = get_connection()
    cursor = con.cursor()
    payout_data: list[dict] = data.get("data")
    counter_value: float = data.get("countervalue")
    for payout in payout_data:
        txHash: str = payout.get("hash")
        timestamp: int = payout.get("timestamp")
        value: int = payout.get("value")
        fee: int = payout.get("fee")
        feePercent: float = payout.get("feePercent")
        feePrice: int = payout.get("feePrice")
        duration: int = payout.get("duration")
        confirmed: bool = payout.get("confirmed")
        confirmedTimestamp: int = payout.get("confirmedTimestamp")

        payout_tuple = (txHash, timestamp, value, fee, feePercent, feePrice, duration, confirmed, confirmedTimestamp)
        result = cursor.execute(INSERT_PAYOUTS, payout_tuple)

        if result.rowcount == 1:
            value_in_eth = wei_to_eth(value)
            fee_in_eth = wei_to_eth(fee)
            text = f"!!! PAYOUT DATA CHANGED !!!\n" \
                   f"Current ETH-EUR: {counter_value}€\n" \
                   f"Amount: {'{:.6f}'.format(value_in_eth)} ({'{:.2f}'.format(value_in_eth * counter_value)}€)\n" \
                   f"Fee: {'{:.6f}'.format(fee_in_eth)} ({'{:.2f}'.format(fee_in_eth * counter_value)}€)\n" \
                   f"Gas Price: {feePrice} Gwei\n" \
                   f"Confirmed: {confirmed}\n" \
                   f"Check on https://etherscan.io/tx/{txHash}"
            # bot.send_message_to_group(text)
            bot.send_message_to_ferris(text)

    con.commit()
    con.close()
