import logging
import sys
import tomllib
from pathlib import Path

from dotenv import dotenv_values
from ghostfolio import Ghostfolio

from sync_ghostfolio.synchronizers.crypto import (
    BtcSynchronizer,
    EthSynchronizer,
)

from .models import Config, Synchronizer
from .synchronizers.freedom24 import Freedom24Synchronizer
from .synchronizers.indexa import IndexaCapitalSynchronizer

logging.basicConfig(level=logging.INFO)
logging.getLogger("httpx").setLevel(logging.WARNING)

env: dict[str, str] = dotenv_values()  # ty:ignore[invalid-assignment]


def gather_synchronizers(
    user: str, config: Config, ghostfolio: Ghostfolio
) -> list[Synchronizer]:
    synchronizers: list[Synchronizer] = []
    platforms = config["users"][user]

    for platform in platforms:
        match platform:
            case "indexa_capital":
                platform_cfg = platforms["indexa_capital"]
                synchronizers.append(
                    IndexaCapitalSynchronizer(
                        ghostfolio,
                        platform_cfg["ghostfolio_account_id"],
                        env[f"{user.upper()}_INDEXA_CAPITAL_API_KEY"],
                        platform_cfg["account_number"],
                        ntfy_topic=config["ghostfolio"].get("ntfy_topic"),
                    )
                )

            case "indexa_capital_pension":
                platform_cfg = platforms["indexa_capital_pension"]
                synchronizers.append(
                    IndexaCapitalSynchronizer(
                        ghostfolio,
                        platform_cfg["ghostfolio_account_id"],
                        env[f"{user.upper()}_INDEXA_CAPITAL_API_KEY"],
                        platform_cfg["account_number"],
                        account_type="pension",
                        ntfy_topic=config["ghostfolio"].get("ntfy_topic"),
                    )
                )

            case "freedom24":
                platform_cfg = platforms["freedom24"]
                synchronizers.append(
                    Freedom24Synchronizer(
                        ghostfolio,
                        platform_cfg["ghostfolio_account_id"],
                        env[f"{user.upper()}_FREEDOM24_PUBLIC_KEY"],
                        env[f"{user.upper()}_FREEDOM24_PRIVATE_KEY"],
                        ntfy_topic=config["ghostfolio"].get("ntfy_topic"),
                    )
                )

            case "crypto":
                crypto_config = platforms["crypto"]
                for coin in crypto_config["coins"]:
                    match coin:
                        case "BTC":
                            synchronizers.append(
                                BtcSynchronizer(
                                    ghostfolio,
                                    crypto_config["ghostfolio_account_id"],
                                    env["COINGECKO_DEMO_API_KEY"],
                                    env[f"{user.upper()}_BTC_ZPUB"],
                                    provider_url=config["crypto"].get("mempool_url"),
                                    proxy_url=config["crypto"].get("proxy_url"),
                                    ntfy_topic=config["ghostfolio"].get("ntfy_topic"),
                                    tx_delay_days=config["crypto"].get("tx_delay_days"),
                                )
                            )

                        case "ETH":
                            synchronizers.append(
                                EthSynchronizer(
                                    ghostfolio,
                                    crypto_config["ghostfolio_account_id"],
                                    env["COINGECKO_DEMO_API_KEY"],
                                    env[f"{user.upper()}_ETH_ADDRESS"],
                                    proxy_url=config["crypto"].get("proxy_url"),
                                    ntfy_topic=config["ghostfolio"].get("ntfy_topic"),
                                    tx_delay_days=config["crypto"].get("tx_delay_days"),
                                )
                            )

                        case _:
                            raise ValueError(f"Unsupported coin {coin}")

            case _:
                raise ValueError(f"Unsupported platform {platform}")

    return synchronizers


def main() -> None:
    user = sys.argv[1]
    config: Config = tomllib.loads(Path("config.toml").read_text())  # ty:ignore[invalid-assignment]

    ghostfolio = Ghostfolio(
        token=env[f"{user.upper()}_GHOSTFOLIO_TOKEN"],
        host=config["ghostfolio"]["host"],
    )

    for synchronizer in gather_synchronizers(user, config, ghostfolio):
        synchronizer.sync()
