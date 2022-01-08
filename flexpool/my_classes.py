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


class WorkerStats:
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