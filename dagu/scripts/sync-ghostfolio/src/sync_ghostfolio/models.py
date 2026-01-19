from typing import NotRequired, TypedDict


class GhostfolioConfig(TypedDict):
    host: str


class GeneralCryptoConfig(TypedDict):
    proxy_url: str
    mempool_url: str


class PlatformConfig(TypedDict):
    ghostfolio_account_id: str


class IndexaCapitalConfig(PlatformConfig):
    account_number: str


class Freedom24Config(PlatformConfig):
    pass


class CryptoConfig(PlatformConfig):
    proxy_url: str
    coins: list[str]


class UserPlatforms(TypedDict):
    indexa_capital: NotRequired[IndexaCapitalConfig]
    freedom24: NotRequired[Freedom24Config]
    crypto: NotRequired[CryptoConfig]


class Config(TypedDict):
    ghostfolio: GhostfolioConfig
    crypto: GeneralCryptoConfig
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
