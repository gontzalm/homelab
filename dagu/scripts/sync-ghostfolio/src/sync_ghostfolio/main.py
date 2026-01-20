import logging
import sys
import tomllib
from pathlib import Path

from dotenv import dotenv_values
from ghostfolio import Ghostfolio  # pyright: ignore[reportMissingTypeStubs]

from sync_ghostfolio.synchronizers.crypto import (
    BtcSynchronizer,
    EthSynchronizer,
)

from .models import Config
from .synchronizers.freedom24 import Freedom24Synchronizer
from .synchronizers.indexa import IndexaCapitalSynchronizer

logging.basicConfig(level=logging.INFO)
logging.getLogger("httpx").setLevel(logging.WARNING)

env: dict[str, str] = dotenv_values()  # pyright: ignore[reportAssignmentType]


def main() -> None:
    user = sys.argv[1]
    config: Config = tomllib.loads(Path("config.toml").read_text())  # pyright: ignore[reportAssignmentType]
    user_platforms = config["users"][user]

    ghostfolio = Ghostfolio(
        token=env[f"{user.upper()}_GHOSTFOLIO_TOKEN"],
        host=config["ghostfolio"]["host"],
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
                    ntfy_topic=config["ghostfolio"]["ntfy_topic"],
                )

            case "freedom24":
                f24_config = user_platforms["freedom24"]  # pyright: ignore[reportTypedDictNotRequiredAccess]
                synchronizer = Freedom24Synchronizer(
                    ghostfolio,
                    f24_config["ghostfolio_account_id"],
                    env[f"{user.upper()}_FREEDOM24_PUBLIC_KEY"],
                    env[f"{user.upper()}_FREEDOM24_PRIVATE_KEY"],
                    ntfy_topic=config["ghostfolio"]["ntfy_topic"],
                )

            case "crypto":
                crypto_config = user_platforms["crypto"]  # pyright: ignore[reportTypedDictNotRequiredAccess]
                for coin in crypto_config["coins"]:
                    match coin:
                        case "BTC":
                            synchronizer = BtcSynchronizer(
                                ghostfolio,
                                crypto_config["ghostfolio_account_id"],
                                env["COINGECKO_DEMO_API_KEY"],
                                env[f"{user.upper()}_BTC_ZPUB"],
                                provider_url=config["crypto"]["mempool_url"],
                                proxy_url=config["crypto"]["proxy_url"],
                                ntfy_topic=config["ghostfolio"]["ntfy_topic"],
                            )

                        case "ETH":
                            synchronizer = EthSynchronizer(
                                ghostfolio,
                                crypto_config["ghostfolio_account_id"],
                                env["COINGECKO_DEMO_API_KEY"],
                                env[f"{user.upper()}_ETH_ADDRESS"],
                                proxy_url=config["crypto"]["proxy_url"],
                                ntfy_topic=config["ghostfolio"]["ntfy_topic"],
                            )

                        case _:
                            raise ValueError(f"Unsupported coin {coin}")

                    synchronizer.sync()

                continue

            case _:
                raise ValueError(f"Unsupported platform {platform}")

        synchronizer.sync()
