import logging
from abc import ABC, abstractmethod
from datetime import datetime
from functools import cached_property

from ghostfolio import Ghostfolio  # pyright: ignore[reportMissingTypeStubs]

from ..models import GhostfolioActivity

logger = logging.getLogger(__name__)


class PlatformSynchronizer(ABC):
    _ID_COMMENT_PREFIX: str = "ID: "

    def __init__(
        self,
        ghostfolio_client: Ghostfolio,
        ghostfolio_account_id: str,
    ) -> None:
        self._ghostfolio: Ghostfolio = ghostfolio_client
        self._ghostfolio_account_id: str = ghostfolio_account_id

    @cached_property
    def _existing_ids(self) -> set[str]:
        activities: list[GhostfolioActivity] = self._ghostfolio.orders(  # pyright: ignore[reportAny]
            account_id=self._ghostfolio_account_id
        )["activities"]

        return set(
            activity["comment"].removeprefix(self._ID_COMMENT_PREFIX)  # pyright: ignore[reportTypedDictNotRequiredAccess]
            for activity in activities
        )

    def _activity_exists(self, activity: GhostfolioActivity) -> bool:
        return (
            activity["comment"].removeprefix(self._ID_COMMENT_PREFIX)  # pyright: ignore[reportTypedDictNotRequiredAccess]
            in self._existing_ids
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

    def _sync_activities(self) -> None:
        new_activities = self._get_new_activities()
        logger.info(
            "Synchronizing %s activities to Ghostfolio account ID '%s'",
            len(new_activities),
            self._ghostfolio_account_id,
        )
        self._ghostfolio.import_transactions({"activities": new_activities})

    def _sync_cash_balance(self) -> None:
        balance = self._get_cash_balance()

        if balance is None:
            return

        logger.info(
            "Synchronizing cash balance to Ghostfolio account ID '%s'",
            self._ghostfolio_account_id,
        )
        account = next(  # pyright: ignore[reportAny]
            acc
            for acc in self._ghostfolio.accounts()["accounts"]  # pyright: ignore[reportAny]
            if acc["id"] == self._ghostfolio_account_id
        )

        _ = self._ghostfolio.put(
            "account",
            object_id=self._ghostfolio_account_id,
            data={
                "id": account["id"],
                "name": account["name"],
                "currency": account["currency"],
                "platformId": account["platformId"],
                "balance": balance,
            },
        )

    def sync(self) -> None:
        self._sync_activities()
        self._sync_cash_balance()
