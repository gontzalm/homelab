import json
import logging
import tomllib
from datetime import date
from functools import cached_property
from pathlib import Path
from string import Template
from typing import Any, TypeVar, final

import httpx
import litellm
from ghostfolio import Ghostfolio  # pyright: ignore[reportMissingTypeStubs]

from .models import (
    PrivateGhostfolioAccount,
    PrivateGhostfolioHolding,
)

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=dict[str, Any])  # pyright: ignore[reportExplicitAny]


@final
class GhostfolioAnalyzer:
    _TEMPlATES_DIR = Path(__file__).parent / "prompt-templates"

    def __init__(
        self,
        ghostfolio_client: Ghostfolio,
        model: str,
        user_profile: Path,
        ntfy_topic: str,
    ):
        self._ghostfolio = ghostfolio_client
        self._model = model
        self._user_profile = user_profile
        self._ntfy_topic = ntfy_topic

    def _get_private_info(self, info: str, private_fields: type[T]) -> list[T]:
        logger.info("Retrieving ghostfolio info '%s'", info)

        data = getattr(self._ghostfolio, info)()[info]  # pyright: ignore[reportAny]
        return [  # pyright: ignore[reportReturnType, reportUnknownVariableType]
            {k: element[k] for k in private_fields.__required_keys__}  # pyright: ignore[reportUnknownMemberType, reportAttributeAccessIssue, reportUnknownVariableType]
            for element in data  # pyright: ignore[reportAny]
        ]

    @cached_property
    def holdings(self) -> list[PrivateGhostfolioHolding]:
        return self._get_private_info("holdings", PrivateGhostfolioHolding)  # pyright: ignore[reportUnknownVariableType, reportArgumentType]

    @cached_property
    def accounts(self) -> list[PrivateGhostfolioAccount]:
        return self._get_private_info(  # pyright: ignore[reportUnknownVariableType]
            "accounts",
            PrivateGhostfolioAccount,  # pyright: ignore[reportArgumentType]
        )

    def analyze_portfolio(self) -> None:
        logger.info("Starting portfolio analysis")

        prompt_template = Template(
            (self._TEMPlATES_DIR / "instructions.md").read_text()
        )
        prompt = prompt_template.substitute(
            user_profile=json.dumps(
                tomllib.loads(self._user_profile.read_text()), indent=2
            ),
            accounts=json.dumps(self.accounts, indent=2),
            holdings=json.dumps(self.holdings, indent=2),
            output_template=(self._TEMPlATES_DIR / "output.md").read_text(),
        )
        print(prompt)

        logger.info("Requesting analysis from LLM (%s)...", self._model)
        response = litellm.completion(  # pyright: ignore[reportUnknownMemberType]
            self._model, messages=[{"role": "user", "content": prompt}]
        )
        analysis: str = response.choices[0].message.content  # pyright: ignore[reportUnknownMemberType, reportAttributeAccessIssue, reportUnknownVariableType, reportAssignmentType]

        logger.info("Sending analysis to ntfy topic '%s'", self._ntfy_topic)
        with httpx.Client() as http:
            r = http.put(
                self._ntfy_topic,
                headers={
                    "Title": "Ghostfolio Portfolio Analysis",
                    "Tags": "chart_with_upwards_trend",
                    "File": f"analysis-{date.today()}.md",
                },
                content=analysis.encode(),
            )
            _ = r.raise_for_status()
