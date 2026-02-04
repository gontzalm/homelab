import logging
from typing import Literal, final, override

import httpx
from ghostfolio import Ghostfolio

from ._base import PlatformSynchronizer
from ._models import (
    ActivityType,
    DataSource,
    GhostfolioActivity,
    IndexaFee,
    IndexaPensionFund,
)

logger = logging.getLogger(__name__)


@final
class IndexaCapitalSynchronizer(PlatformSynchronizer):
    BASE_URL = "https://api.indexacapital.com"
    OPERATIONS = {
        "buy": (
            "ALTA IIC SWITCH",
            "SUSCRIPCIÓN FONDOS INVERSIÓN",
            "APORTACION A PLAN DE PENSIONES",
        ),
        "sell": ("BAJA IIC SWITCH", "REEMBOLSO FONDOS INVERSIÓN"),
        "fee": ("CUSTODIA INVERSIS", "CARGO COMISION GESTION"),
    }

    def __init__(
        self,
        ghostfolio_client: Ghostfolio,
        ghostfolio_account_id: str,
        indexa_capital_api_key: str,
        indexa_capital_account_number: str,
        *,
        account_type: Literal["mutual", "pension"] = "mutual",
        ntfy_topic: str | None = None,
    ) -> None:
        super().__init__(
            ghostfolio_client, ghostfolio_account_id, ntfy_topic=ntfy_topic
        )
        self._account_number = indexa_capital_account_number
        self._indexa = httpx.Client(
            base_url=f"{self.BASE_URL}/accounts/{self._account_number}",
            headers={"X-AUTH-TOKEN": indexa_capital_api_key},
        )
        self.account_type = account_type

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
                "dataSource": DataSource["YAHOO"]
                if self.account_type == "mutual"
                else DataSource["MANUAL"],
                "date": transaction["executed_at"].partition(" ")[0],
                "fee": 0,
                "quantity": transaction["titles"],
                "symbol": transaction["instrument"]["isin_code"]
                if self.account_type == "mutual"
                else IndexaPensionFund(transaction["instrument"]["name"]).name,
                "type": ActivityType["BUY"]
                if transaction["operation_type"] in self.OPERATIONS["buy"]
                else ActivityType["SELL"],
                "unitPrice": transaction["price"],
            }
            for transaction in r.json()
        ]

    def _get_fees(self) -> list[GhostfolioActivity]:
        if self.account_type == "pension":
            return []

        logger.info("Retrieving fees for account number '%s'", self._account_number)
        r = self._indexa.get("/cash-transactions")
        _ = r.raise_for_status()

        return [
            {
                "accountId": self._ghostfolio_account_id,
                "comment": self._ID_COMMENT_PREFIX + transaction["reference"],
                "currency": transaction["currency"],
                "dataSource": DataSource["MANUAL"],
                "date": transaction["date"],
                "fee": abs(transaction["amount"]),
                "quantity": 0,
                "symbol": IndexaFee.GF_INDEXA_CUST_FEE.name
                if "CUSTODIA" in transaction["operation_type"]
                else IndexaFee.GF_INDEXA_MGMT_FEE.name,
                "type": ActivityType["FEE"],
                "unitPrice": 0,
            }
            for transaction in r.json()
            if transaction["operation_type"] in self.OPERATIONS["fee"]
        ]

    @override
    def _post_actions(self) -> None:
        if self.account_type != "pension":
            return

        # Update Pension Funds Net Asset Value (NAV)
        r = self._indexa.get("/portfolio")
        r.raise_for_status()
        positions = r.json()["instrument_accounts"][0]["positions"]

        for position in positions:
            self._ghostfolio.post(
                "market-data",
                object_id=f"MANUAL/{IndexaPensionFund(position['instrument']['name']).name}",
                data={
                    "marketData": [
                        {"date": position["date"], "marketPrice": position["price"]}
                    ]
                },
            )

    @override
    def _get_new_activities(self) -> list[GhostfolioActivity]:
        activities = [*self._get_instrument_transactions(), *self._get_fees()]
        return [a for a in activities if not self._activity_exists(a["comment"])]

    @override
    def _get_cash_balance(self) -> float | None:
        if self.account_type == "pension":
            return None

        logger.info(
            "Retrieving cash balance for account number '%s'", self._account_number
        )
        r = self._indexa.get("/portfolio")
        _ = r.raise_for_status()

        return r.json()["portfolio"]["cash_amount"]
