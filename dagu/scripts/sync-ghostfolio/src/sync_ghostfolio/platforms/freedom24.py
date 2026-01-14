import json
import logging
from datetime import date, datetime, timedelta
from functools import cached_property
from typing import final, override

from ghostfolio import Ghostfolio  # pyright: ignore[reportMissingTypeStubs]
from tradernet import Tradernet

from ..models import GhostfolioActivity
from ._synchronizer import PlatformSynchronizer

logger = logging.getLogger(__name__)


@final
class Freedom24Synchronizer(PlatformSynchronizer):
    _ID_COMMENT_PREFIX = "ID: "
    _IGNORE_INSTRUMENTS = ("USD/EUR",)
    _BUY_OPERATION = 1
    _SELL_OPERATION = 3

    def __init__(
        self,
        ghostfolio_client: Ghostfolio,
        ghostfolio_account_id: str,
        freedom24_public_key: str,
        freedom24_private_key: str,
        sync_from_historical: datetime,
    ) -> None:
        super().__init__(ghostfolio_client, ghostfolio_account_id)
        self._sync_from_historical = sync_from_historical
        self._tradernet = Tradernet(freedom24_public_key, freedom24_private_key)

    @cached_property
    def _sync_from(self) -> datetime:
        activities: list[GhostfolioActivity] = self._ghostfolio.orders(  # pyright: ignore[reportAny]
            account_id=self._ghostfolio_account_id
        )["activities"]

        if not activities:
            return self._sync_from_historical

        return max(datetime.fromisoformat(activity["date"]) for activity in activities)

    @staticmethod
    def _convert_symbol_to_yahoo(symbol: str) -> str:
        if symbol.endswith(".US"):
            return symbol.removesuffix(".US")
        elif symbol.endswith(".EU"):
            return symbol.replace(".EU", ".DE")

        return symbol

    def _get_trades(self) -> list[GhostfolioActivity]:
        logger.info("Retrieving trades from %s onwards", self._sync_from.isoformat())
        orders = self._tradernet.get_historical(start=self._sync_from)["orders"][  # pyright: ignore[reportAny]
            "order"
        ]
        # This step is necessary because the 'start' argument is truncated to the date
        # in the previous retrieval
        orders = [
            order
            for order in orders  # pyright: ignore[reportAny]
            if datetime.fromisoformat(order["date"] + "Z") > self._sync_from  # pyright: ignore[reportAny]
        ]

        return [
            {
                "accountId": self._ghostfolio_account_id,
                "comment": self._ID_COMMENT_PREFIX + str(trade["id"]),  # pyright: ignore[reportAny]
                "currency": order["cur"],
                "dataSource": "YAHOO",
                "date": trade["date"] + "Z",
                "fee": 0,
                "quantity": trade["q"],
                "symbol": self._convert_symbol_to_yahoo(order["instr"]),  # pyright: ignore[reportAny]
                "type": "BUY" if order["oper"] == self._BUY_OPERATION else "SELL",
                "unitPrice": trade["p"],
            }
            for order in orders  # pyright: ignore[reportAny]
            if order["instr"] not in self._IGNORE_INSTRUMENTS and "trade" in order
            for trade in order["trade"]  # pyright: ignore[reportAny]
        ]

    def _get_fees(self) -> list[GhostfolioActivity]:
        logger.info("Retrieving fees")
        raise NotImplementedError

    @override
    def _get_new_activities(self) -> list[GhostfolioActivity]:
        return self._get_trades()
        # return [*self._get_trades(), *self._get_fees()]
