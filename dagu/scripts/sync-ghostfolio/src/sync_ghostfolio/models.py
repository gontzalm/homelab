from datetime import datetime
from typing import NotRequired, TypedDict


class PlatformConfig(TypedDict):
    ghostfolio_account_id: str


class IndexaCapitalConfig(PlatformConfig):
    account_number: str


class Freedom24Config(PlatformConfig):
    sync_from_historical: datetime


class UserPlatforms(TypedDict):
    indexa_capital: NotRequired[IndexaCapitalConfig]
    freedom24: NotRequired[Freedom24Config]


class Config(TypedDict):
    users: dict[str, UserPlatforms]


# See https://github.com/ghostfolio/ghostfolio?tab=readme-ov-file#import-activities
class GhostfolioActivity(TypedDict):
    accountId: NotRequired[str]  # Id of the account
    comment: NotRequired[str]  # Comment of the activity
    currency: str
    dataSource: str  # COINGECKO | GHOSTFOLIO 1 | MANUAL | YAHOO
    date: str
    fee: float
    quantity: float
    symbol: str  # Symbol of the activity (suitable for `dataSource`)
    type: str  # BUY | DIVIDEND | FEE | INTEREST | LIABILITY | SELL
    unitPrice: float
