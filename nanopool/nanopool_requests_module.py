import logging
import requests
import time
import telegram_bot_module


def get_api_data(url: str, fail_count=0) -> list[dict]:
    logging.debug(f"Try fetching: {url}")
    try:
        data = requests.get(url).json().get("data")
        if data is None:
            raise Exception("Data was None!")
        else:
            logging.debug("Fetched data")
            return data
    except Exception as e:
        logging.error("Error fetching data!")
        logging.error(e)
        fail_count += 1
        if fail_count > 60:
            telegram_bot_module.send_message_to_ferris(f"Failed {fail_count} times to fetch data!")
            fail_count = 0
        logging.error("Retry in 10 seconds")
        time.sleep(10)
        return get_api_data(url, fail_count)


def get_data_of_workers() -> list[dict]:
    nanopool_api_workers = "https://api.nanopool.org/v1/eth/workers/YOURWALLET"
    return get_api_data(nanopool_api_workers)


def get_payment_data() -> list[dict]:
    nanopool_api_payments = "https://api.nanopool.org/v1/eth/payments/YOURWALLET"
    return get_api_data(nanopool_api_payments)
