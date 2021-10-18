import os
import logging as log
import requests
import time
import telegram_bot_module as bot


api_url: str
miner_address: str


def init():
    global api_url, miner_address
    api_url = "https://api.flexpool.io/v2"
    miner_address = "wallet"

    if os.environ["DEBUG"] == "1":
        miner_address = "0xF105D49D387cb84D06EDC9EAC0785eFbBb5a0c67"


def request_error(url: str, params: dict, fail_count: int, e):
    if e is not None and e == "Page out of range":  # No payments jet
        return None
    log.error(e)
    if fail_count % 60 == 0:
        bot.send_message_to_ferris(f"Script failed since {(10*fail_count)/60} minutes!\n{e}")
    log.error("Retry in 10 seconds")
    time.sleep(10)
    return make_request(url, params, fail_count + 1)


def make_request(url: str, params: dict, fail_count=0):
    try:
        response = requests.get(url=url, params=params)
    except ConnectionError as e:
        return request_error(url, params, fail_count+1, e)
    except Exception as e:
        return request_error(url, params, fail_count+1, e)
    json: dict = response.json()
    error = json.get("error")
    if error is not None:
        return request_error(url, params, fail_count + 1, error)
    return json.get("result")


def get_data_of_workers() -> list[dict]:
    url = api_url + "/miner/workers"
    params = dict(coin="eth", address=miner_address)
    return make_request(url, params)


def get_payment_data() -> dict:
    url = api_url + "/miner/payments"
    params = dict(coin="eth", address=miner_address, countervalue="eur", page=0)
    return make_request(url, params)
