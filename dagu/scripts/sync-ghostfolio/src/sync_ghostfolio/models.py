from typing import NotRequired, Protocol, TypedDict


class GhostfolioConfig(TypedDict):
    host: str
    ntfy_topic: NotRequired[str]


class GeneralCryptoConfig(TypedDict):
    proxy_url: NotRequired[str]
    mempool_url: NotRequired[str]
    tx_delay_days: NotRequired[int]


class PlatformConfig(TypedDict):
    ghostfolio_account_id: str


class IndexaCapitalConfig(PlatformConfig):
    account_number: str


class Freedom24Config(PlatformConfig):
    pass


class CryptoConfig(PlatformConfig):
    coins: list[str]


class UserPlatforms(TypedDict):
    indexa_capital: NotRequired[IndexaCapitalConfig]
    freedom24: NotRequired[Freedom24Config]
    crypto: NotRequired[CryptoConfig]


class Config(TypedDict):
    ghostfolio: GhostfolioConfig
    crypto: GeneralCryptoConfig
    users: dict[str, UserPlatforms]


class Synchronizer(Protocol):
    def sync(self) -> None: ...
