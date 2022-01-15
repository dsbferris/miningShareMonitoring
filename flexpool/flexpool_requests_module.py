import os
import logging as log
import requests
import time
import telegram_bot_module as bot
from flexpool import my_classes as mc

api_url: str
miner_address: str


def init(address: str):
    global api_url, miner_address
    api_url = "https://api.flexpool.io/v2"
    miner_address = address


def _request_error(url: str, params: dict, fail_count: int, e):
    if e is not None and e == "Page out of range":  # No payments jet
        return None
    log.error(e)
    if fail_count % 60 == 0:
        bot.send_message_to_ferris(f"Script failed since {(10 * fail_count) / 60} minutes!\n{e}")
    log.error("Retry in 10 seconds")
    time.sleep(10)
    return _make_request(url, params, fail_count + 1)


def _make_request(url: str, params: dict, fail_count=0):
    try:
        response = requests.get(url=url, params=params)
    except ConnectionError as e:
        return _request_error(url, params, fail_count + 1, e)
    except Exception as e:
        return _request_error(url, params, fail_count + 1, e)
    json: dict = response.json()
    error = json.get("error")
    if error is not None:
        return _request_error(url, params, fail_count + 1, error)
    return json.get("result")


def miner_workers() -> list[mc.WorkerStats]:
    # "result": [
    #   {
    #   "name": "Ferris_Phoenix",
    #   "isOnline": true,
    #   "count": 1,
    #   "reportedHashrate": 55381483,
    #   "currentEffectiveHashrate": 73333333,
    #   "averageEffectiveHashrate": 56712962.63888889,
    #   "validShares": 1225,
    #   "staleShares": 68,
    #   "invalidShares": 0,
    #   "lastSeen": 1641658314
    #   },
    # ]
    url = api_url + "/miner/workers"
    params = dict(coin="eth", address=miner_address)
    response = _make_request(url, params)
    workers_stats: list[mc.WorkerStats] = []
    for r in response:
        w = mc.WorkerStats(name=r["name"], delta=mc.ShareStats(
                            valid=r["validShares"],
                            stale=r["staleShares"],
                            invalid=r["invalidShares"]),
                           shares=None)
        workers_stats.append(w)

    return workers_stats


def miner_payments() -> dict:
    # "countervalue": 2912.23,
    #     "data": [
    #       {
    #         "hash": "***REMOVED***",
    #         "timestamp": 1638897913,
    #         "value": 48193333093397850,
    #         "fee": 1838904407907000,
    #         "feePercent": 0.036754390763735906,
    #         "feePrice": 87,
    #         "duration": 2138789,
    #         "confirmed": true,
    #         "confirmedTimestamp": 1638897956,
    #         "network": "mainnet"
    #       },
    #       {
    #         "hash": "***REMOVED***",
    #         "timestamp": 1636759124,
    #         "value": 53158198134477620,
    #         "fee": 1811723853282000,
    #         "feePercent": 0.03295845778506697,
    #         "feePrice": 86,
    #         "duration": 2204924,
    #         "confirmed": true,
    #         "confirmedTimestamp": 1636760934,
    #         "network": "mainnet"
    #       }
    #     ],
    #     "totalItems": 2,
    #     "totalPages": 1

    url = api_url + "/miner/payments"
    params = dict(coin="eth", address=miner_address, countervalue="eur", page=0)
    data: list[dict] = []
    response = _make_request(url, params)
    totalPages = response["totalPages"]
    if totalPages > 1:
        data += response["data"]
        for i in range(1, totalPages + 1):
            params["page"] = i
            resp = _make_request(url, params)
            if resp is not None:
                data.append(resp["data"])
        response["data"] = data
    return response


def miner_average_effective_hashrate() -> int:
    # "averageEffectiveHashrate": 145925925.0625,
    # "currentEffectiveHashrate": 153333332,
    # "invalidShares": 0,
    # "reportedHashrate": 179703474,
    # "staleShares": 47,
    # "validShares": 3152
    url = api_url + "/miner/stats"
    params = dict(coin="eth", address=miner_address)
    response = _make_request(url, params)
    return response["averageEffectiveHashrate"]


def miner_balance_wei():
    # "balance": 68736199578713790,
    # "balanceCountervalue": 200.18,
    # "price": 2912.23
    url = api_url + "/miner/balance"
    params = dict(coin="eth", address=miner_address, countervalue="eur")
    response = _make_request(url, params)
    return response["balance"]


def pool_daily_reward_per_gigahash_sec() -> int:
    # "result": 16617213256156008
    url = api_url + "/pool/dailyRewardPerGigahashSec"
    params = dict(coin="eth")
    response: int = _make_request(url, params)
    return response
