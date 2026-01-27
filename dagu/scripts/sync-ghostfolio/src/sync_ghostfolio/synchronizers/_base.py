import logging
from abc import ABC, abstractmethod
from datetime import datetime
from functools import cached_property

import httpx
from ghostfolio import Ghostfolio  # pyright: ignore[reportMissingTypeStubs]

from ._models import ActivityType, GhostfolioAccount, GhostfolioActivity
from ._notifications import NOTIFICATION_TEMPLATE

logger = logging.getLogger(__name__)


class PlatformSynchronizer(ABC):
    _ID_COMMENT_PREFIX: str = "ID: "

    def __init__(
        self,
        ghostfolio_client: Ghostfolio,
        ghostfolio_account_id: str,
        *,
        ntfy_topic: str | None = None,
    ) -> None:
        self._ghostfolio: Ghostfolio = ghostfolio_client
        self._ghostfolio_account_id: str = ghostfolio_account_id
        self.ntfy_topic: str | None = ntfy_topic

    @cached_property
    def _existing_ids(self) -> set[str]:
        activities: list[GhostfolioActivity] = self._ghostfolio.orders(  # pyright: ignore[reportAny]
            account_id=self._ghostfolio_account_id
        )["activities"]

        return set(
            activity["comment"].removeprefix(self._ID_COMMENT_PREFIX)  # pyright: ignore[reportTypedDictNotRequiredAccess]
            for activity in activities
        )

    @cached_property
    def _account(self) -> GhostfolioAccount:
        try:
            return next(
                acc
                for acc in self._ghostfolio.accounts()["accounts"]  # pyright: ignore[reportAny]
                if acc["id"] == self._ghostfolio_account_id
            )
        except StopIteration:
            raise ValueError(
                f"Ghostfolio account with ID '{self._ghostfolio_account_id}' does not exist"
            )

    def _activity_exists(self, activity_comment: str) -> bool:
        return (
            activity_comment.removeprefix(self._ID_COMMENT_PREFIX) in self._existing_ids
        )

    @abstractmethod
    def _get_new_activities(self) -> list[GhostfolioActivity]:
        raise NotImplementedError

    @abstractmethod
    def _get_cash_balance(self) -> float | None:
        raise NotImplementedError

    def _get_max_account_datetime(self) -> datetime:
        activities: list[GhostfolioActivity] = self._ghostfolio.orders(  # pyright: ignore[reportAny]
            account_id=self._ghostfolio_account_id
        )["activities"]

        if not activities:
            return datetime(1970, 1, 1)

        return max(datetime.fromisoformat(activity["date"]) for activity in activities)

    def _notify_activities(self, activities: list[GhostfolioActivity]) -> None:
        if self.ntfy_topic is None:
            return

        with httpx.Client() as http:
            for activity in activities:
                r = http.post(
                    self.ntfy_topic,
                    headers={
                        "Title": f"New Ghostfolio Activity in {self._account['name']}",
                        "Tags": "chart",
                    },
                    content=NOTIFICATION_TEMPLATE[ActivityType(activity["type"])]
                    .substitute(activity)
                    .encode(),
                )
                _ = r.raise_for_status()

    def _sync_activities(self) -> None:
        new_activities = self._get_new_activities()
        logger.info(
            "Synchronizing %s activities to Ghostfolio account ID '%s'",
            len(new_activities),
            self._ghostfolio_account_id,
        )
        self._ghostfolio.import_transactions({"activities": new_activities})
        self._notify_activities(new_activities)

    def _sync_cash_balance(self) -> None:
        balance = self._get_cash_balance()

        if balance is None:
            return

        logger.info(
            "Synchronizing cash balance to Ghostfolio account ID '%s'",
            self._ghostfolio_account_id,
        )

        _ = self._ghostfolio.put(
            "account",
            object_id=self._ghostfolio_account_id,
            data={
                "id": self._account["id"],
                "name": self._account["name"],
                "currency": self._account["currency"],
                "platformId": self._account["platformId"],
                "balance": balance,
            },
        )

    def sync(self) -> None:
        self._sync_activities()
        self._sync_cash_balance()
