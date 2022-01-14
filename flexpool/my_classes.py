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
    share_delta: ShareStats

    def __init__(self, name: str, shares: ShareStats, delta: ShareStats):
        self.shares = shares
        self.name = name
        self.share_delta = delta


def get_delta_string(number: int) -> str:
    if number > 0:
        return f"+ {number}"
    elif number < 0:
        return f"- {number}"
    else:
        return number.__str__()


class DailyReport:
    workers: list[WorkerStats]
    current_eth: float
    limit_eth: float
    percent: float
    days_left: float

    def __init__(self, workers: list[WorkerStats], current_eth: float, limit_eth: float,
                 days_left: float):
        self.workers = workers
        self.current_eth = current_eth
        self.limit_eth = limit_eth
        self.percent = current_eth / limit_eth
        self.days_left = days_left

    def __str__(self):
        text = f"Daily mining report\n\n"

        if len(self.workers) > 0:
            for d in self.workers:
                text += f"Name: {d.name}\n" \
                        f"Valid shares: {d.shares.valid} ({get_delta_string(d.share_delta.valid)})\n" \
                        f"Stale shares: {d.shares.stale} ({get_delta_string(d.share_delta.stale)})\n" \
                        f"Invalid shares: {d.shares.invalid} ({get_delta_string(d.share_delta.invalid)})\n\n"

        text += f"{'{:.6f}'.format(self.current_eth)} ETH of {'{:.6f}'.format(self.limit_eth)} ETH " \
                f"({'{:.2f}'.format(self.percent * 100)} %)\n"
        text += f"{'{:.1f}'.format(self.days_left)} days left to payout"
        text = text.strip()
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
        limit_eth=limit_eth,
        current_eth=current_eth,
        days_left=18.9
    )
    daily_string = str(daily)
    print(daily_string)
