import logging as log


def wei_to_eth(wei: int) -> float:
    return wei / pow(10, 18)


def eth_to_wei(eth: float) -> int:
    return eth * pow(10, 18)


class Payout:
    timestamp: int
    value: float
    fee: float
    feePercent: float
    feePrice: int
    duration: int
    confirmed: bool
    confirmedTimestamp: int
    txHash: str

    def __init__(self, data):
        if isinstance(data, tuple):
            self.init_from_db(data)
        elif isinstance(data, dict):
            self.init_from_request(data)
        else:
            log.critical("UNKNOWN TYPE!!!!")

    def init_from_db(self, data: tuple):
        self.timestamp = data[0]
        self.value = data[1]
        self.fee = data[2]
        self.feePercent = data[3]
        self.feePrice = data[4]
        self.duration = data[5]
        self.confirmed = data[6] == 1
        self.confirmedTimestamp = data[7]
        self.txHash = data[8]

    def init_from_request(self, payout: dict):
        self.timestamp = payout.get("timestamp")
        self.value = wei_to_eth(payout.get("value"))
        self.fee = wei_to_eth(payout.get("fee"))
        self.feePercent = payout.get("feePercent")
        self.feePrice = payout.get("feePrice")
        self.duration = payout.get("duration")
        self.confirmed = payout.get("confirmed")
        self.confirmedTimestamp = payout.get("confirmedTimestamp")
        self.txHash = payout.get("hash")

    def __iter__(self):  # shitty implementation of iter to make "cursor.execute" accept this class
        return [self.timestamp, self.value, self.fee, self.feePercent, self.feePrice, self.duration, self.confirmed,
                self.confirmedTimestamp, self.txHash]

    def __eq__(self, other):
        if isinstance(other, Payout):
            return (self.txHash == other.txHash and self.timestamp == other.timestamp
                    and self.value == other.value and self.fee == other.fee
                    and self.feePercent == other.feePercent and self.feePrice == other.feePrice
                    and self.duration == other.duration and self.confirmed == other.confirmed
                    and self.confirmedTimestamp == other.confirmedTimestamp)
        else:
            return False


class ShareStats:
    valid: int
    stale: int
    invalid: int

    def __init__(self, valid: int, stale: int, invalid: int):
        self.valid = valid
        self.stale = stale
        self.invalid = invalid

    def __eq__(self, other):
        if isinstance(other, ShareStats):
            return self.valid == other.valid and self.stale == other.stale and self.invalid == other.invalid

    def __add__(self, other):
        if isinstance(other, ShareStats):
            return ShareStats(self.valid + other.valid, self.stale + other.stale, self.invalid + other.invalid)


class WorkerStats:
    shares: ShareStats
    name: str
    delta_shares: ShareStats

    def __init__(self, name: str, shares: ShareStats, delta: ShareStats):
        self.shares = shares
        self.name = name
        self.delta_shares = delta


def get_delta_string(number: int) -> str:
    if number > 0:
        return f"+ {number}"
    elif number < 0:
        return f"- {number}"
    else:
        return number.__str__()


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


class DailyReport:
    workers: list[WorkerStats]
    current_wei: int
    limit_wei: int
    avg_eff_hashrate: int
    daily_reward_per_gigahash_sec_wei: int

    def __init__(self, workers: list[WorkerStats],
                 current_wei: int, limit_wei: int,
                 avg_eff_hashrate: int, daily_reward_per_gigahash_sec_wei: int):
        self.workers = workers
        self.current_wei = current_wei
        self.limit_wei = limit_wei
        self.avg_eff_hashrate = avg_eff_hashrate
        self.daily_reward_per_gigahash_sec_wei = daily_reward_per_gigahash_sec_wei

    def __str__(self):
        text = f"Daily mining report\n\n"

        if len(self.workers) > 0:
            for d in self.workers:
                text += f"Name: {d.name}\n" \
                        f"Valid shares: {d.shares.valid} ({get_delta_string(d.delta_shares.valid)})\n" \
                        f"Stale shares: {d.shares.stale} ({get_delta_string(d.delta_shares.stale)})\n" \
                        f"Invalid shares: {d.shares.invalid} ({get_delta_string(d.delta_shares.invalid)})\n\n"

        text += f"{'{:.6f}'.format(wei_to_eth(self.current_wei))} ETH of {'{:.6f}'.format(wei_to_eth(self.limit_wei))} ETH " \
                f"({'{:.2f}'.format((self.current_wei / self.limit_wei) * 100)} %)\n"
        days_left = days_left_for_payout(hashRate=self.avg_eff_hashrate,
                                         payoutLimit_wei=self.limit_wei, currentBalance_wei=self.current_wei,
                                         dailyRewardPerGigaHashSec_wei=self.daily_reward_per_gigahash_sec_wei)
        text += f"{'{:.1f}'.format(days_left)} days left to payout"
        return text


def daily_sample(mc):
    ferris: mc.WorkerStats = mc.WorkerStats(
        name="Ferris",
        shares=mc.ShareStats(valid=12345, stale=10, invalid=0),
        delta=mc.ShareStats(valid=1000, stale=2, invalid=0)
    )
    levin: mc.WorkerStats = mc.WorkerStats(
        name="Levin",
        shares=mc.ShareStats(valid=54321, stale=9, invalid=0),
        delta=mc.ShareStats(valid=999, stale=1, invalid=0)
    )
    worker_list: list[mc.WorkerStats] = [ferris, levin]
    limit_eth = 0.075
    current_eth = 0.05678

    daily: mc.DailyReport = mc.DailyReport(
        workers=worker_list,
        limit_wei=limit_eth,
        current_wei=current_eth,
        days_left=18.9
    )
    daily_string = str(daily)
    print(daily_string)
