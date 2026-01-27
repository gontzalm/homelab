from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from typing import NotRequired, TypedDict


class DataSource(StrEnum):
    COINGECKO = "COINGECKO"
    GHOSTFOLIO = "GHOSTFOLIO"
    MANUAL = "MANUAL"
    YAHOO = "YAHOO"


class ActivityType(StrEnum):
    BUY = "BUY"
    SELL = "SELL"
    DIVIDEND = "DIVIDEND"
    FEE = "FEE"
    INTEREST = "INTEREST"
    LIABILITY = "LIABILITY"


# See https://github.com/ghostfolio/ghostfolio?tab=readme-ov-file#import-activities
class GhostfolioActivity(TypedDict):
    accountId: NotRequired[str]  # Id of the account
    comment: NotRequired[str]  # Comment of the activity
    currency: str
    dataSource: DataSource
    date: str
    fee: float
    quantity: float
    symbol: str  # Symbol of the activity (suitable for `dataSource`)
    type: ActivityType
    unitPrice: float


class GhostfolioPlatform(TypedDict):
    id: str
    name: str
    url: str | None


class GhostfolioAccount(TypedDict):
    balance: float
    comment: str | None
    createdAt: str
    currency: str
    id: str
    isExcluded: bool
    name: str
    platformId: str
    updatedAt: str
    userId: str
    platform: GhostfolioPlatform
    dividendInBaseCurrency: float
    interestInBaseCurrency: float
    transactionCount: int
    valueInBaseCurrency: float
    allocationInPercentage: float
    balanceInBaseCurrency: float
    value: float


class CryptoTx(TypedDict):
    id: str
    value: Decimal
    fee: Decimal
    executed_at: datetime


class BtcTx(CryptoTx):
    address: str


class EthTx(CryptoTx):
    block: int
