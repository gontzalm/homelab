import logging
from functools import cached_property
from typing import final, override

import httpx
from ghostfolio import Ghostfolio  # pyright: ignore[reportMissingTypeStubs]

from ..models import GhostfolioActivity
from ._synchronizer import PlatformSynchronizer

logger = logging.getLogger(__name__)


@final
class IndexaCapitalSynchronizer(PlatformSynchronizer):
    _BASE_URL = "https://api.indexacapital.com"
    _BUY_OPERATIONS = ("ALTA IIC SWITCH", "SUSCRIPCIÓN FONDOS INVERSIÓN")
    _SELL_OPERATIONS = ("BAJA IIC SWITCH", "REEMBOLSO FONDOS INVERSIÓN")
    _FEE_OPERATIONS = ("CUSTODIA INVERSIS", "CARGO COMISION GESTION")
    _REFERENCE_COMMENT_PREFIX = "Ref: "

    def __init__(
        self,
        ghostfolio_client: Ghostfolio,
        ghostfolio_account_id: str,
        indexa_capital_api_key: str,
        indexa_capital_account_number: str,
    ) -> None:
        super().__init__(ghostfolio_client, ghostfolio_account_id)
        self._account_number = indexa_capital_account_number
        self._indexa = httpx.Client(
            base_url=f"{self._BASE_URL}/accounts/{self._account_number}",
            headers={"X-AUTH-TOKEN": indexa_capital_api_key},
        )

    @cached_property
    def _existing_references(self) -> set[str]:
        activities: list[GhostfolioActivity] = self._ghostfolio.orders(  # pyright: ignore[reportAny]
            account_id=self._ghostfolio_account_id
        )["activities"]

        return set(
            activity["comment"].removeprefix(self._REFERENCE_COMMENT_PREFIX)  # pyright: ignore[reportTypedDictNotRequiredAccess]
            for activity in activities
        )

    def _get_instrument_transactions(self) -> list[GhostfolioActivity]:
        logger.info(
            "Retrieving instrument transactions for account number '%s'",
            self._account_number,
        )
        r = self._indexa.get("/instrument-transactions")
        _ = r.raise_for_status()

        return [
            {
                "accountId": self._ghostfolio_account_id,
                "comment": self._REFERENCE_COMMENT_PREFIX + transaction["reference"],
                "currency": transaction["currency"],
                "dataSource": "YAHOO",
                "date": transaction["executed_at"].partition(" ")[0],  # pyright: ignore[reportAny]  # pyright: ignore[reportAny]
                "fee": 0,
                "quantity": transaction["titles"],
                "symbol": transaction["instrument"]["isin_code"],
                "type": "BUY"
                if transaction["operation_type"] in self._BUY_OPERATIONS
                else "SELL",
                "unitPrice": transaction["price"],
            }
            for transaction in r.json()  # pyright: ignore[reportAny]
        ]

    def _get_fees(self) -> list[GhostfolioActivity]:
        logger.info("Retrieving fees for account number '%s'", self._account_number)
        r = self._indexa.get("/cash-transactions")
        _ = r.raise_for_status()

        return [
            {
                "accountId": self._ghostfolio_account_id,
                "comment": self._REFERENCE_COMMENT_PREFIX + transaction["reference"],
                "currency": transaction["currency"],
                "dataSource": "MANUAL",
                "date": transaction["date"],
                "fee": abs(transaction["amount"]),  # pyright: ignore[reportAny]
                "quantity": 0,
                "symbol": "INDEXA_CUST_FEE"
                if "CUSTODIA" in transaction["operation_type"]
                else "INDEXA_MGMT_FEE",
                "type": "FEE",
                "unitPrice": 0,
            }
            for transaction in r.json()  # pyright: ignore[reportAny]
            if transaction["operation_type"] in self._FEE_OPERATIONS
        ]

    @override
    def _get_new_activities(self) -> list[GhostfolioActivity]:
        activities = [*self._get_instrument_transactions(), *self._get_fees()]
        return [
            activity
            for activity in activities
            if activity["comment"].removeprefix(self._REFERENCE_COMMENT_PREFIX)  # pyright: ignore[reportTypedDictNotRequiredAccess]
            not in self._existing_references
        ]
