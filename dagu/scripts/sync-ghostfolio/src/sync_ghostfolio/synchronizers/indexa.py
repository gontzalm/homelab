import logging
from typing import final, override

import httpx
from ghostfolio import Ghostfolio  # pyright: ignore[reportMissingTypeStubs]

from ..models import GhostfolioActivity
from ._base import PlatformSynchronizer

logger = logging.getLogger(__name__)


@final
class IndexaCapitalSynchronizer(PlatformSynchronizer):
    BASE_URL = "https://api.indexacapital.com"
    OPERATIONS = {
        "buy": ("ALTA IIC SWITCH", "SUSCRIPCIÓN FONDOS INVERSIÓN"),
        "sell": ("BAJA IIC SWITCH", "REEMBOLSO FONDOS INVERSIÓN"),
        "fee": ("CUSTODIA INVERSIS", "CARGO COMISION GESTION"),
    }

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
            base_url=f"{self.BASE_URL}/accounts/{self._account_number}",
            headers={"X-AUTH-TOKEN": indexa_capital_api_key},
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
                "comment": self._ID_COMMENT_PREFIX + transaction["reference"],
                "currency": transaction["currency"],
                "dataSource": "YAHOO",
                "date": transaction["executed_at"].partition(" ")[0],  # pyright: ignore[reportAny]  # pyright: ignore[reportAny]
                "fee": 0,
                "quantity": transaction["titles"],
                "symbol": transaction["instrument"]["isin_code"],
                "type": "BUY"
                if transaction["operation_type"] in self.OPERATIONS["buy"]
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
                "comment": self._ID_COMMENT_PREFIX + transaction["reference"],
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
            if transaction["operation_type"] in self.OPERATIONS["fee"]
        ]

    @override
    def _get_new_activities(self) -> list[GhostfolioActivity]:
        activities = [*self._get_instrument_transactions(), *self._get_fees()]
        return [a for a in activities if not self._activity_exists(a)]

    @override
    def _get_cash_balance(self) -> float:
        logger.info(
            "Retrieving cash balance for account number '%s'", self._account_number
        )
        r = self._indexa.get("/portfolio")
        _ = r.raise_for_status()

        return r.json()["portfolio"]["cash_amount"]  # pyright: ignore[reportAny]
