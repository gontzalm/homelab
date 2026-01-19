from datetime import datetime
from decimal import Decimal
from typing import TypedDict


class CryptoTx(TypedDict):
    id: str
    value: Decimal
    fee: Decimal
    executed_at: datetime


class BtcTx(CryptoTx):
    address: str


class EthTx(CryptoTx):
    block: int
