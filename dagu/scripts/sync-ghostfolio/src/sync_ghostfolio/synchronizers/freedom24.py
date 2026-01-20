import logging
from datetime import date, timedelta
from functools import cached_property
from typing import final, override

from ghostfolio import Ghostfolio  # pyright: ignore[reportMissingTypeStubs]
from tradernet import Tradernet

from ._base import PlatformSynchronizer
from ._models import GhostfolioActivity

logger = logging.getLogger(__name__)


@final
class Freedom24Synchronizer(PlatformSynchronizer):
    _ID_COMMENT_PREFIX = "ID: "
    _IGNORE_INSTRUMENTS = ("USD/EUR",)
    _BUY_TRADE_TYPE = 1
    _MAIN_CASH_ACCOUNT_CURRENCY = "EUR"

    def __init__(
        self,
        ghostfolio_client: Ghostfolio,
        ghostfolio_account_id: str,
        freedom24_public_key: str,
        freedom24_private_key: str,
        *,
        ntfy_topic: str | None = None,
    ) -> None:
        super().__init__(
            ghostfolio_client, ghostfolio_account_id, ntfy_topic=ntfy_topic
        )
        self._tradernet = Tradernet(freedom24_public_key, freedom24_private_key)

    @cached_property
    def _sync_from(self) -> date:
        max_datetime = self._get_max_account_datetime()
        return date(
            max_datetime.year, max_datetime.month, max_datetime.day
        ) + timedelta(days=1)

    @staticmethod
    def _convert_symbol_to_yahoo(symbol: str) -> str:
        if symbol.endswith(".US"):
            return symbol.removesuffix(".US")
        elif symbol.endswith(".EU"):
            return symbol.replace(".EU", ".DE")

        return symbol

    def _get_trades(self) -> list[GhostfolioActivity]:
        logger.info("Retrieving trades from %s onwards", self._sync_from.isoformat())
        trades = self._tradernet.get_trades_history(  # pyright: ignore[reportAny]
            start=self._sync_from, end=(date.today() - timedelta(days=1))
        )["trades"]["trade"]

        return [
            {
                "accountId": self._ghostfolio_account_id,
                "comment": self._ID_COMMENT_PREFIX + str(trade["id"]),  # pyright: ignore[reportAny]
                "currency": trade["curr_c"],
                "dataSource": "YAHOO",
                "date": trade["date"] + "Z",
                "fee": float(trade["commission"]),  # pyright: ignore[reportAny]
                "quantity": float(trade["q"]),  # pyright: ignore[reportAny]
                "symbol": self._convert_symbol_to_yahoo(trade["instr_nm"]),  # pyright: ignore[reportAny]
                "type": "BUY" if int(trade["type"]) == self._BUY_TRADE_TYPE else "SELL",  # pyright: ignore[reportAny]
                "unitPrice": float(trade["p"]),  # pyright: ignore[reportAny]
            }
            for trade in trades  # pyright: ignore[reportAny]
            if trade["instr_nm"] not in self._IGNORE_INSTRUMENTS
        ]

    @override
    def _get_new_activities(self) -> list[GhostfolioActivity]:
        return self._get_trades()

    @override
    def _get_cash_balance(self) -> float:
        logger.info("Retrieving main account cash balance")
        accounts = self._tradernet.get_user_data()["OPQ"]["ps"]["acc"]  # pyright: ignore[reportAny]
        return next(  # pyright: ignore[reportAny]
            acc["s"]
            for acc in accounts  # pyright: ignore[reportAny]
            if acc["curr"] == self._MAIN_CASH_ACCOUNT_CURRENCY
        )
