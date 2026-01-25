import logging
import os
from pathlib import Path

from dotenv import load_dotenv
from ghostfolio import Ghostfolio  # pyright: ignore[reportMissingTypeStubs]

from analyze_ghostfolio.analyzer import GhostfolioAnalyzer

logging.basicConfig(level=logging.INFO)

_ = load_dotenv()


def main() -> None:
    ghostfolio = Ghostfolio(
        os.environ["GHOSTFOLIO_TOKEN"],
        host="http://ghostfolio:3333",
    )

    analyzer = GhostfolioAnalyzer(
        ghostfolio,
        "gemini/gemini-flash-latest",
        Path("profile.toml"),
        "http://ntfy/dagu",
    )

    analyzer.analyze_portfolio()
