import logging
from abc import ABC, abstractmethod
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from functools import cache, cached_property
from typing import Any, ClassVar, Generic, Protocol, TypeVar, final, override

import httpx
from bip_utils import (  # pyright: ignore[reportMissingTypeStubs]
    Bip44Changes,
    Bip84,
    Bip84Coins,
)
from bip_utils.bip.bip84.bip84 import (  # pyright: ignore[reportMissingTypeStubs]
    Bip44Base,
)
from ghostfolio import Ghostfolio  # pyright: ignore[reportMissingTypeStubs]

from ._base import PlatformSynchronizer
from ._models import (
    ActivityType,
    BtcTx,
    CryptoTx,
    DataSource,
    EthTx,
    GhostfolioActivity,
)

logger = logging.getLogger(__name__)


T = TypeVar("T", bound=CryptoTx)


class CryptoConfig(Protocol):
    _DEFAULT_PROVIDER_URL: ClassVar[str]
    COINGECKO_COIN_ID: ClassVar[str]
    PROVIDER_API_PATH: ClassVar[str]
    provider_url: str
    proxy_url: str | None
    tx_delay_days: int | None

    @property
    def coingecko_api_key(self) -> str: ...


class CryptoSynchronizer(PlatformSynchronizer, CryptoConfig, ABC, Generic[T]):
    @cached_property
    def _http(self) -> httpx.Client:
        return httpx.Client(
            base_url=self.provider_url.removesuffix("/") + self.PROVIDER_API_PATH,
            proxy=self.proxy_url,
        )

    @cached_property
    def _coingecko(self) -> httpx.Client:
        return httpx.Client(
            base_url="https://api.coingecko.com/api/v3",
            params={"x_cg_demo_api_key": self.coingecko_api_key},
        )

    @cache
    def _get_coin_price(self, date: date) -> float:
        logger.info(
            "Getting '%s' price for %s", self.COINGECKO_COIN_ID, date.isoformat()
        )
        r = self._coingecko.get(
            f"/coins/{self.COINGECKO_COIN_ID}/history",
            params={"date": date.isoformat(), "localization": False},
        )
        _ = r.raise_for_status()
        return r.json()["market_data"]["current_price"]["usd"]  # pyright: ignore[reportAny]

    @abstractmethod
    def _get_transactions(self) -> list[T]:
        raise NotImplementedError

    @override
    def _get_new_activities(self) -> list[GhostfolioActivity]:
        return [
            {
                "accountId": self._ghostfolio_account_id,
                "comment": self._ID_COMMENT_PREFIX + tx["id"],
                "currency": "USD",
                "dataSource": DataSource["COINGECKO"],
                "date": tx["executed_at"].isoformat(),
                "fee": float(tx["fee"])
                * self._get_coin_price(
                    tx["executed_at"].date() - timedelta(days=self.tx_delay_days or 0)
                ),
                "quantity": float(abs(tx["value"])),
                "symbol": self.COINGECKO_COIN_ID,
                "type": ActivityType["BUY"]
                if tx["value"] > 0
                else ActivityType["SELL"],
                "unitPrice": self._get_coin_price(
                    tx["executed_at"].date() - timedelta(days=self.tx_delay_days or 0)
                ),
            }
            for tx in self._get_transactions()
            if not self._activity_exists(self._ID_COMMENT_PREFIX + tx["id"])
        ]

    @override
    def _get_cash_balance(self) -> None:
        return None


@final
class BtcSynchronizer(CryptoSynchronizer[BtcTx]):
    _GAP_LIMIT = 20
    _DEFAULT_PROVIDER_URL = "https://mempool.space/api"
    PROVIDER_API_PATH = "/api"
    COINGECKO_COIN_ID = "bitcoin"

    def __init__(
        self,
        ghostfolio_client: Ghostfolio,
        ghostfolio_account_id: str,
        coingecko_api_key: str,
        zpub: str,
        *,
        ntfy_topic: str | None = None,
        provider_url: str | None = None,
        proxy_url: str | None = None,
        tx_delay_days: int | None = None,
    ) -> None:
        super().__init__(
            ghostfolio_client, ghostfolio_account_id, ntfy_topic=ntfy_topic
        )
        self._coingecko_api_key = coingecko_api_key
        self._zpub = zpub
        self.provider_url = provider_url or self._DEFAULT_PROVIDER_URL
        self.proxy_url = proxy_url
        self.tx_delay_days = tx_delay_days

    @property
    @override
    def coingecko_api_key(self) -> str:
        return self._coingecko_api_key

    @cached_property
    def _derivation_ctx(self) -> Bip44Base:
        return Bip84.FromExtendedKey(self._zpub, Bip84Coins.BITCOIN)

    @staticmethod
    def _sats_to_btc(sats: int) -> Decimal:
        return Decimal(sats) / 100_000_000

    def _derive_address(self, change_type: Bip44Changes, index: int) -> str:
        logger.info("Deriving %s address at index %s", change_type.name, index)
        return (
            self._derivation_ctx.Change(change_type)
            .AddressIndex(index)
            .PublicKey()
            .ToAddress()
        )

    def _compute_tx_net_sats_value(self, tx: dict[str, Any], addr: str) -> int:  # pyright: ignore[reportExplicitAny]
        value = 0

        for vout in tx["vout"]:  # pyright: ignore[reportAny]
            if vout["scriptpubkey_address"] == addr:
                value += vout["value"]  # pyright: ignore[reportAny]

        for vin in tx["vin"]:  # pyright: ignore[reportAny]
            if vin["prevout"]["scriptpubkey_address"] == addr:
                value -= vin["prevout"]["value"]  # pyright: ignore[reportAny]

        return value

    def _get_transactions_for_change_type(
        self, change_type: Bip44Changes
    ) -> list[BtcTx]:
        logger.info("Retrieving BTC transactions for %s", change_type.name)
        consecutive_empty = 0
        idx = 0

        transactions: list[BtcTx] = []
        while consecutive_empty < self._GAP_LIMIT:
            addr = self._derive_address(change_type, idx)
            r = self._http.get(f"/address/{addr}/txs/chain")
            _ = r.raise_for_status()

            txs = r.json()  # pyright: ignore[reportAny]

            if txs:
                consecutive_empty = 0
                for tx in txs:  # pyright: ignore[reportAny]
                    transactions.append(
                        {
                            "id": tx["txid"],
                            "value": self._sats_to_btc(
                                self._compute_tx_net_sats_value(tx, addr)  # pyright: ignore[reportAny]
                            ),
                            "fee": Decimal(0),
                            "executed_at": datetime.fromtimestamp(
                                tx["status"]["block_time"],  # pyright: ignore[reportAny]
                                tz=UTC,
                            ),
                            "address": addr,
                        }
                    )
            else:
                consecutive_empty += 1

            idx += 1

        return transactions

    @override
    def _get_transactions(self) -> list[BtcTx]:
        aggregated_txs: dict[str, BtcTx] = {}

        for type_ in Bip44Changes:
            found_txs = self._get_transactions_for_change_type(type_)

            for tx in found_txs:
                id_ = tx["id"]
                try:
                    logger.debug("Merging fragmented transaction '%s'", id_)
                    aggregated_txs[id_]["value"] += tx["value"]
                except KeyError:
                    aggregated_txs[id_] = tx

        return [tx for tx in aggregated_txs.values() if tx["value"]]


@final
class EthSynchronizer(CryptoSynchronizer[EthTx]):
    _DEFAULT_PROVIDER_URL = "https://eth.blockscout.com"
    PROVIDER_API_PATH = "/api/v2"
    COINGECKO_COIN_ID = "ethereum"

    def __init__(
        self,
        ghostfolio_client: Ghostfolio,
        ghostfolio_account_id: str,
        coingecko_api_key: str,
        address: str,
        *,
        ntfy_topic: str | None = None,
        provider_url: str | None = None,
        proxy_url: str | None = None,
        tx_delay_days: int | None = None,
    ) -> None:
        super().__init__(
            ghostfolio_client, ghostfolio_account_id, ntfy_topic=ntfy_topic
        )
        self._coingecko_api_key = coingecko_api_key
        self._address = address
        self.provider_url = provider_url or self._DEFAULT_PROVIDER_URL
        self.proxy_url = proxy_url
        self.tx_delay_days = tx_delay_days

    @property
    @override
    def coingecko_api_key(self) -> str:
        return self._coingecko_api_key

    @staticmethod
    def _wei_to_eth(wei: int) -> Decimal:
        return Decimal(wei) / 1_000_000_000_000_000_000

    @override
    def _get_transactions(self) -> list[EthTx]:
        logger.info("Retrieving ETH transactions")
        txs: list[dict[str, Any]] = []  # pyright: ignore[reportExplicitAny]
        next_page_params = None

        while True:
            r = self._http.get(
                f"/addresses/{self._address}/transactions", params=next_page_params
            )
            _ = r.raise_for_status()

            data = r.json()  # pyright: ignore[reportAny]
            txs.extend(data["items"])  # pyright: ignore[reportAny]
            next_page_params = data["next_page_params"]  # pyright: ignore[reportAny]
            if next_page_params is None:
                break

        return [
            {
                "id": tx["hash"],
                "value": self._wei_to_eth(int(tx["value"]))  # pyright: ignore[reportAny]
                * (-1 if tx["from"]["hash"] == self._address else 1),
                "fee": self._wei_to_eth(tx["fee"]["value"]),  # pyright: ignore[reportAny]
                "executed_at": datetime.fromisoformat(tx["timestamp"]),  # pyright: ignore[reportAny]
                "block": tx["block_number"],
            }
            for tx in txs
            if tx["status"] == "ok"
        ]
