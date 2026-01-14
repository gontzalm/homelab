import logging
from abc import ABC, abstractmethod

from ghostfolio import Ghostfolio  # pyright: ignore[reportMissingTypeStubs]

from ..models import GhostfolioActivity

logger = logging.getLogger(__name__)


class PlatformSynchronizer(ABC):
    def __init__(
        self,
        ghostfolio_client: Ghostfolio,
        ghostfolio_account_id: str,
    ) -> None:
        self._ghostfolio: Ghostfolio = ghostfolio_client
        self._ghostfolio_account_id: str = ghostfolio_account_id

    @abstractmethod
    def _get_new_activities(self) -> list[GhostfolioActivity]:
        raise NotImplementedError

    def sync(self) -> None:
        new_activities = self._get_new_activities()
        logger.info(
            "Synchronizing %s activities to Ghostfolio account ID '%s'",
            len(new_activities),
            self._ghostfolio_account_id,
        )
        self._ghostfolio.import_transactions({"activities": new_activities})
