from typing import Any, Literal, TypedDict


class GhostfolioWeights(TypedDict):
    name: str
    weight: float


class GhostfolioHolding(TypedDict):
    allocationInPercentage: float
    assetClass: Literal["EQUITY", "CRYPTO", "CASH", "LIABILITY", "COMMODITY"]
    assetSubClass: str  # e.g., "MUTUALFUND", "ETF", "CRYPTOCURRENCY"
    countries: list[GhostfolioWeights]
    currency: str
    dataSource: Literal["YAHOO", "COINGECKO", "MANUAL", "GHOSTFOLIO"]
    dateOfFirstActivity: str  # ISO 8601 Date String
    dividend: float
    grossPerformance: float
    grossPerformancePercent: float
    grossPerformancePercentWithCurrencyEffect: float
    grossPerformanceWithCurrencyEffect: float
    holdings: list[dict[str, Any]]  # pyright: ignore[reportExplicitAny]
    investment: float
    marketPrice: float
    name: str
    netPerformance: float
    netPerformancePercent: float
    netPerformancePercentWithCurrencyEffect: float
    netPerformanceWithCurrencyEffect: float
    quantity: float
    sectors: list[GhostfolioWeights]
    symbol: str
    tags: list[str]
    transactionCount: int
    url: str | None
    valueInBaseCurrency: float


class PrivateGhostfolioHolding(TypedDict):
    """
    A privacy-safe subset of holding data for LLM analysis.
    Contains NO absolute values (prices, totals, quantities).
    """

    # IDENTITY
    symbol: str
    name: str

    # CLASSIFICATION (Crucial for risk analysis)
    assetClass: Literal["EQUITY", "CRYPTO", "CASH", "LIABILITY", "COMMODITY"]
    assetSubClass: str  # e.g. "ETF", "MUTUALFUND"
    currency: str

    # ALLOCATION (The most important field for the LLM)
    # This sums up to 100% (or 1.0) across the portfolio
    allocationInPercentage: float

    # PERFORMANCE (Relative only)
    # We use percent so the LLM sees the trend (e.g. +15%)
    # without knowing the amount (e.g. +€5,000)
    grossPerformancePercent: float

    # RISK & EXPOSURE METADATA
    sectors: list[GhostfolioWeights]
    countries: list[GhostfolioWeights]
    tags: list[str]

    # TIME CONTEXT
    # Useful for the LLM to know if this is a long-term hold or a trade
    dateOfFirstActivity: str


from typing import List, Optional, TypedDict


class GhostfolioPlatform(TypedDict):
    id: str
    name: str
    url: str


class GhostfolioAccount(TypedDict):
    id: str
    name: str
    currency: str
    comment: str | None
    platformId: str | None
    isExcluded: bool
    balance: float
    value: float
    balanceInBaseCurrency: float
    valueInBaseCurrency: float
    dividendInBaseCurrency: float
    interestInBaseCurrency: float
    allocationInPercentage: float
    transactionCount: int
    createdAt: str
    updatedAt: str
    userId: str
    platform: GhostfolioPlatform


class PrivateGhostfolioAccount(TypedDict):
    """
    Anonymized version for LLM processing.
    Focuses on portfolio distribution and metadata without absolute wealth figures.
    """

    name: str
    currency: str
    isExcluded: bool
    allocationInPercentage: float
    transactionCount: int
    updatedAt: str
    platform: GhostfolioPlatform
