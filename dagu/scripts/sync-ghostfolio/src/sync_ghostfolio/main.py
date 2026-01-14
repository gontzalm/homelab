import logging
import sys
import tomllib
from pathlib import Path

from dotenv import dotenv_values
from ghostfolio import Ghostfolio  # pyright: ignore[reportMissingTypeStubs]

from .models import Config
from .platforms.freedom24 import Freedom24Synchronizer
from .platforms.indexa import IndexaCapitalSynchronizer

logging.basicConfig(level=logging.INFO)

env: dict[str, str] = dotenv_values()  # pyright: ignore[reportAssignmentType]


def main() -> None:
    user = sys.argv[1]
    config: Config = tomllib.loads(Path("config.toml").read_text())  # pyright: ignore[reportAssignmentType]
    user_platforms = config["users"][user]

    ghostfolio = Ghostfolio(
        token=env["GHOSTFOLIO_TOKEN"], host="http://ghostfolio:3333"
    )

    for platform in user_platforms:
        match platform:
            case "indexa_capital":
                indexa_config = user_platforms["indexa_capital"]  # pyright: ignore[reportTypedDictNotRequiredAccess]
                synchronizer = IndexaCapitalSynchronizer(
                    ghostfolio,
                    indexa_config["ghostfolio_account_id"],
                    env[f"{user.upper()}_INDEXA_CAPITAL_API_KEY"],
                    indexa_config["account_number"],
                )

            case "freedom24":
                f24_config = user_platforms["freedom24"]  # pyright: ignore[reportTypedDictNotRequiredAccess]
                synchronizer = Freedom24Synchronizer(
                    ghostfolio,
                    f24_config["ghostfolio_account_id"],
                    env[f"{user.upper()}_FREEDOM24_PUBLIC_KEY"],
                    env[f"{user.upper()}_FREEDOM24_PRIVATE_KEY"],
                    f24_config["sync_from_historical"],
                )

            case _:
                raise ValueError(f"Unsupported platform {platform}")

        synchronizer.sync()
