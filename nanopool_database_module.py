import os
import datetime
from zoneinfo import ZoneInfo
import sqlite3
import logging
import os
import telegram_bot_module


DATA_PATH = "database"
DATA_NAME = "nanopool_mining.db"

de_timezone = ZoneInfo("Europe/Berlin")

if not os.path.exists(DATA_PATH):
    os.mkdir(DATA_PATH)


def get_database_path() -> str:
    return os.path.join(os.getcwd(), os.path.join(DATA_PATH, DATA_NAME))


def get_connection() -> sqlite3.Connection:
    return sqlite3.connect(os.path.join(os.path.join(os.getcwd(), DATA_PATH), DATA_NAME))


def init_database():
    logging.debug(f"DBPATH: {os.path.join(os.path.join(os.getcwd(), DATA_PATH), DATA_NAME)}")
    connection = get_connection()
    cursor = connection.cursor()
    logging.debug("Initializing Connection")

    # region RATINGS
    CREATE_TABLE_RATINGS = '''CREATE TABLE ratings(
                                uid INTEGER PRIMARY KEY,
                                workerName TEXT,
                                rating INTEGER,
                                zeitstempel TIMESTAMP);'''
    IS_RATINGS_EXISTING = '''SELECT name FROM sqlite_master WHERE type='table' AND name='ratings';'''
    if cursor.execute(IS_RATINGS_EXISTING).fetchone() is None:
        cursor.execute(CREATE_TABLE_RATINGS)
        logging.debug("Created table ratings")
    else:
        logging.debug("Table ratings already exists")
    # endregion

    # region RESETS
    CREATE_TABLE_RESETS = '''CREATE TABLE resets(
                                workerName TEXT PRIMARY KEY, 
                                rating_before INTEGER NOT NULL, 
                                rating_after INTEGER NOT NULL,
                                zeitstempel TIMESTAMP);'''
    IS_RESETS_EXISTING = '''SELECT name FROM sqlite_master WHERE type='table' AND name='resets';'''
    if cursor.execute(IS_RESETS_EXISTING).fetchone() is None:
        cursor.execute(CREATE_TABLE_RESETS)
        logging.debug("Created table resets")
    else:
        logging.debug("Table resets already exists")
    # endregion

    # region PAYOUTS
    CREATE_TABLE_PAYOUTS = '''CREATE TABLE payouts(
                            zeitstempel TIMESTAMP,
                            txHash TEXT PRIMARY KEY,
                            amount REAL NOT NULL,
                            confirmed BOOLEAN NOT NULL);'''
    IS_PAYOUTS_EXISTING = '''SELECT name FROM sqlite_master WHERE type='table' AND name='payouts';'''
    if cursor.execute(IS_PAYOUTS_EXISTING).fetchone() is None:
        cursor.execute(CREATE_TABLE_PAYOUTS)
        logging.debug("Created table payouts")
    else:
        logging.debug("Table payouts already exists")
    # endregion

    connection.commit()
    connection.close()
    logging.debug("Closed Connection")


def get_last_rating_of_worker(worker: str, cursor) -> int:
    GET_RATING = '''SELECT rating FROM ratings WHERE workerName=? ORDER BY zeitstempel DESC LIMIT 1;'''

    GET_COUNT_OF_RATINGS = '''SELECT COUNT(rating) FROM ratings WHERE workerName=?;'''

    logging.debug(f"Try reading previous rating of '{worker}'")
    rating = None
    if cursor.execute(GET_COUNT_OF_RATINGS, [worker]).fetchone()[0] > 0:
        rating = cursor.execute(GET_RATING, [worker]).fetchone()[0]  # needs array, else error...
        logging.debug(f"Fetched previous rating: {rating}")
    else:
        logging.debug("Worker had no previous rating")
    return rating


def insert_worker_values(worker_data: list[dict]):
    INSERT_RATING = '''INSERT INTO ratings (uid, workerName, rating, zeitstempel)
                        VALUES (?, ?, ?, ?)
                        ON CONFLICT(uid) DO UPDATE SET
                            rating=excluded.rating,
                            zeitstempel=excluded.zeitstempel
                        WHERE zeitstempel < excluded.zeitstempel
                        AND uid == excluded.uid;'''

    connection = get_connection()
    cursor = connection.cursor()
    logging.debug("Initializing Connection")

    timestamp = datetime.datetime.now(de_timezone)
    for worker in worker_data:
        uid = worker.get('uid')
        worker_name = worker.get("id")
        rating = worker.get("rating")
        previous_rating = get_last_rating_of_worker(worker_name, cursor)
        if previous_rating is not None and previous_rating > rating:
            INSERT_RESET = '''  INSERT INTO resets 
                                (zeitstempel, workerName, rating_before, rating_after) 
                                VALUES (?, ?, ?, ?);'''
            reset_data_tuple = (timestamp, worker_name, previous_rating, rating)
            cursor.execute(INSERT_RESET, reset_data_tuple)
            tuple_string = f"Rating was resettet!\n" \
                           f"Time: {timestamp.strftime('%Y-%m-%d %H:%M:%S')}\n" \
                           f"Worker: {worker_name}\n" \
                           f"Previous rating: {previous_rating}\n" \
                           f"Rating now: {rating}"
            logging.critical(reset_data_tuple)
            telegram_bot_module.send_message_to_group(tuple_string)

        rating_data_tuple = (uid, worker_name, rating, timestamp)
        cursor.execute(INSERT_RATING, rating_data_tuple)

    connection.commit()
    logging.debug("Written Values into Database")
    connection.close()
    logging.debug("Closed Connection")

    # DAILY REPORT
    if datetime.datetime.now(de_timezone).hour == 14:
        text = "Daily rating report:\n"
        for worker in worker_data:
            worker_name = worker.get("id")
            rating = worker.get("rating")
            text += f"{worker_name}: {rating}\n"
        telegram_bot_module.send_message_to_group(text=text, silent=True)


def insert_payouts(payout_data: list[dict]):
    INSERT_PAYOUTS = '''INSERT INTO payouts (zeitstempel, txHash, amount, confirmed)
                        VALUES (?, ?, ?, ?)
                        ON CONFLICT(txHash) DO UPDATE SET
                            confirmed=excluded.confirmed,
                            amount=excluded.amount,
                            zeitstempel=excluded.zeitstempel,
                            txHash=excluded.txHash
                        WHERE confirmed != excluded.confirmed
                        OR amount != excluded.amount
                        OR zeitstempel != excluded.zeitstempel;'''
    connection = get_connection()
    cursor = connection.cursor()
    logging.debug("Initializing Connection")
    for payout in payout_data:
        zeitstempel = payout.get("date")
        txHash = payout.get("txHash")
        amount = payout.get("amount")
        confirmed = payout.get("confirmed")
        payout_data_tuple = (zeitstempel, txHash, amount, confirmed)
        result = cursor.execute(INSERT_PAYOUTS, payout_data_tuple)
        if result.rowcount == 1:
            text = f"!!! PAYOUT DATA CHANGED !!!\n" \
                   f"Amount: {amount}\n" \
                   f"Confirmed: {confirmed}\n" \
                   f"Check on https://etherscan.io/tx/{txHash}"
            telegram_bot_module.send_message_to_group(text)

    connection.commit()
    logging.debug("Written Values into Database")
    connection.close()
    logging.debug("Closed Connection")
