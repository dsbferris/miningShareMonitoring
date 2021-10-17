import logging as log
import requests
import time
import telegram_bot_module as bot

api_url = "https://api.flexpool.io/v2"
miner_address = "0xF105D49D387cb84D06EDC9EAC0785eFbBb5a0c67"

# Payments
"""
{
  "error": "string",
  "result": {
    "countervalue": float,
    "totalItems": int,
    "totalPages": int,
    "data": [
      {
        "hash": "string",
        "timestamp": int,
        "value": int,
        "fee": int,
        "feePercent": float,
        "duration": int,
        "confirmed": bool,
        "confirmedTimestamp": int
      }
    ]
  }
}
"""

# Workers
"""
{
  "error": string,
  "result": [
    {
      "name": string,
      "isOnline": bool,
      "count": int,
      "reportedHashrate": float,
      "currentEffectiveHashrate": float,
      "averageEffectiveHashrate": float,
      "validShares": int,
      "staleShares": int,
      "invalidShares": int,
      "lastSeen": int
    }
  ]
}
"""


def make_request(url: str, params: dict, fail_count=0) -> dict:
    response = requests.get(url=url, params=params)
    json: dict = response.json()
    error = json.get("error")
    if error is not None:
        log.error(error)
        if fail_count % 60 == 0:
            bot.send_message_to_ferris(f"Script failed since {(10*fail_count)/60} minutes!\n\n{error}")
        log.error("Retry in 10 seconds")
        time.sleep(10)
        return make_request(url, params, fail_count+1)
    return json.get("result")


def get_data_of_workers() -> dict:
    url = api_url + "/miner/workers"
    params = dict(coin="eth", address=miner_address)
    return make_request(url, params)


def get_payment_data() -> dict:
    url = api_url + "/miner/payments"
    params = dict(coin="eth", address=miner_address, countervalue="eur", page=0)
    return make_request(url, params)
