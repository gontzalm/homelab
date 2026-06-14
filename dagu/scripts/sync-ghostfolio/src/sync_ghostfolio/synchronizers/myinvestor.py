import logging
from datetime import date, timedelta
from functools import cached_property
from typing import final, override

import httpx
from ghostfolio import Ghostfolio

from ._base import PlatformSynchronizer
from ._models import ActivityType, DataSource, GhostfolioActivity
from ._utils import isin_to_yahoo

logger = logging.getLogger(__name__)


@final
class MyInvestorSynchronizer(PlatformSynchronizer):
    BASE_URL = "https://api.myinvestor.es"
    OPERATIONS = {
        ActivityType.BUY: ("INVESTMENT_FUNDS_SUBSCRIPTION",),
    }

    def __init__(
        self,
        ghostfolio_client: Ghostfolio,
        ghostfolio_account_id: str,
        customer_id: str,
        password: str,
        *,
        ntfy_topic: str | None = None,
    ) -> None:
        super().__init__(
            ghostfolio_client, ghostfolio_account_id, ntfy_topic=ntfy_topic
        )
        self._http = httpx.Client(base_url=self.BASE_URL)
        self._login(customer_id, password)

    def _login(self, customer_id: str, password: str) -> None:
        logger.info("Authenticating with MyInvestor")
        r = self._http.post(
            "/login/api/v2/auth/token",
            json={"customerId": customer_id, "password": password},
        )
        r.raise_for_status()
        token = r.json()["payload"]["data"]["accessToken"]
        self._http.headers["Authorization"] = f"Bearer {token}"

    @cached_property
    def _account_id(self) -> str:
        logger.info("Discovering MyInvestor securities account")
        r = self._http.get(
            "/cperf-server/api/v2/securities-accounts/self-basic"
        )
        r.raise_for_status()
        return r.json()["payload"]["data"][0]["accountId"]

    @cached_property
    def _cash_account_id(self) -> str:
        logger.info("Discovering MyInvestor cash account")
        r = self._http.get(
            "/cperf-server/api/v2/securities-accounts/self-basic"
        )
        r.raise_for_status()
        return r.json()["payload"]["data"][0]["cashAccountId"]

    @override
    def _get_new_activities(self) -> list[GhostfolioActivity]:
        date_from = date.today() - timedelta(days=180)
        logger.info(
            "Retrieving MyInvestor orders from %s onwards",
            date_from.isoformat(),
        )
        r = self._http.get(
            f"/cperf-server/api/v3/securities-accounts/{self._account_id}/orders",
            params={
                "status": "COMPLETE",
                "dateFrom": date_from.isoformat(),
            },
        )
        r.raise_for_status()
        orders = r.json()["payload"]["data"]

        activities: list[GhostfolioActivity] = []
        for order in orders:
            op_type = next(
                (t for t, ops in self.OPERATIONS.items() if order["operationType"] in ops),
                None,
            )
            if op_type is None:
                logger.warning(
                    "Unknown operation type '%s' for order '%s', skipping",
                    order["operationType"],
                    order["reference"],
                )
                continue

            shares = float(order["shares"])
            if shares == 0:
                logger.warning(
                    "Order '%s' has zero shares, skipping",
                    order["reference"],
                )
                continue

            activities.append(
                {
                    "accountId": self._ghostfolio_account_id,
                    "comment": self._ID_COMMENT_PREFIX + order["reference"],
                    "currency": order["currency"],
                    "dataSource": DataSource.YAHOO,
                    "date": order["orderDate"].partition("T")[0],
                    "fee": 0,
                    "quantity": shares,
                    "symbol": isin_to_yahoo(order["isin"]),
                    "type": op_type,
                    "unitPrice": float(order["cash"]) / shares,
                }
            )

        return [a for a in activities if not self._activity_exists(a["comment"])]

    @override
    def _get_cash_balance(self) -> float | None:
        logger.info("Retrieving MyInvestor cash balance")
        r = self._http.get("/cperf-server/api/v2/cash-accounts/self")
        r.raise_for_status()
        accounts = r.json()["payload"]["data"]
        for account in accounts:
            if account["accountId"] == self._cash_account_id:
                return float(account["enabledBalance"])

        logger.warning(
            "Cash account '%s' not found in cash accounts response",
            self._cash_account_id,
        )
        return None
