import os
import datetime
from zoneinfo import ZoneInfo
import sqlite3
import logging as log
import os
import telegram_bot_module as bot


DATA_PATH = "database"
DATA_NAME = "flexpool_mining.db"

de_timezone = ZoneInfo("Europe/Berlin")

if not os.path.exists(DATA_PATH):
    os.mkdir(DATA_PATH)


def get_connection() -> sqlite3.Connection:
    return sqlite3.connect(os.path.join(os.path.join(os.getcwd(), DATA_PATH), DATA_NAME))


def init_database():
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


def get_last_shares_of_worker(worker: str, cursor: sqlite3.Cursor) -> tuple:
    GET_RATING = '''SELECT validShares, staleShares, invalidShares FROM shares WHERE name=? ORDER BY timestamp DESC;'''

    GET_COUNT_OF_RATINGS = '''SELECT COUNT(validShares) FROM shares WHERE name=?;'''

    log.debug(f"Try reading previous rating of '{worker}'")
    rating = None
    if cursor.execute(GET_COUNT_OF_RATINGS, [worker]).fetchone()[0] > 0:
        rating = cursor.execute(GET_RATING, [worker]).fetchone()[0]  # needs array, else error...
        log.debug(f"Fetched previous rating: {rating}")
    else:
        log.debug("Worker had no previous rating")
    return rating


def insert_worker_values(worker_data: dict):
    pass


def insert_payouts(payout_data: dict):
    pass
