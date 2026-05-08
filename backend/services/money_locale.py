"""
Normalize currency + region for localized salary/tuition search and display.

Voice agent sets `currency_code` (ISO 4217) and optional `country_or_region` on the profile.
"""

from __future__ import annotations

_SUPPORTED = frozenset({"USD", "GBP", "EUR", "CAD", "AUD", "INR", "JPY", "CHF", "NZD", "SEK", "NOK"})

# Broad equity benchmark we mention in methodology / index-return queries
_US = "S&P 500"
_UK = "FTSE 100"
_EU = "STOXX Europe 600"


def normalize_currency_code(raw: str | None) -> str:
    c = (raw or "USD").strip().upper()
    return c if c in _SUPPORTED else "USD"


_UK_REGION_HINTS = (
    "uk", "u.k.", "united kingdom", "britain", "great britain",
    "england", "scotland", "wales", "northern ireland",
    "london", "manchester", "birmingham", "edinburgh", "cardiff", "belfast",
)


def coerced_currency_from_region(currency_code: str, country_or_region: str) -> str:
    """
    If the agent left currency as default USD but the region screams UK, assume GBP.
    Does not override an explicit non-USD choice.
    """
    c = normalize_currency_code(currency_code)
    if c != "USD":
        return c
    co = (country_or_region or "").lower()
    if any(h in co for h in _UK_REGION_HINTS):
        return "GBP"
    return c


def money_locale(currency_code: str, country_or_region: str) -> str:
    """
    Bucket for search query wording: US | UK | EU.
    EU is a coarse default for EUR and common EU country hints.
    """
    c = normalize_currency_code(currency_code)
    co = (country_or_region or "").lower()
    uk_hints = _UK_REGION_HINTS
    eu_hints = (
        "eu", "europe", "eurozone", "germany", "france", "spain", "italy",
        "netherlands", "belgium", "austria", "portugal", "ireland", "poland",
    )
    if c == "GBP" or any(h in co for h in uk_hints):
        return "UK"
    if c == "EUR" or any(h in co for h in eu_hints):
        return "EU"
    return "US"


def equity_benchmark_label(locale: str) -> str:
    if locale == "UK":
        return _UK
    if locale == "EU":
        return _EU
    return _US


def currency_symbol(code: str) -> str:
    c = normalize_currency_code(code)
    return {
        "USD": "$",
        "GBP": "£",
        "EUR": "€",
        "CAD": "CA$",
        "AUD": "A$",
        "INR": "₹",
        "JPY": "¥",
        "CHF": "CHF ",
        "NZD": "NZ$",
        "SEK": "",
        "NOK": "",
    }.get(c, "")


def grad_timeline(graduation_year: int, current_year: int) -> tuple[int, int | None]:
    """
    For alumni vs current/prospective students.

    Returns:
        compound_years: years for tuition-vs-index growth math (illustrative 4y if not graduated).
        years_since_graduation: None if unknown grad year or graduation is still in the future.
    """
    if graduation_year <= 0 or graduation_year < 1950 or graduation_year > current_year:
        return 4, None
    elapsed = max(1, current_year - graduation_year)
    return elapsed, elapsed


def index_anchor_year(graduation_year: int, current_year: int) -> int:
    """Calendar year for S&P/FTSE fallback table when grad year is missing or in the future."""
    if graduation_year <= 0 or graduation_year > current_year:
        return current_year
    return graduation_year


def format_money_int(amount: int | None, currency_code: str) -> str:
    """Plain text for LLM profile line (no locale-specific grouping rules)."""
    if amount is None:
        return "not provided"
    c = normalize_currency_code(currency_code)
    sym = currency_symbol(c)
    if c in ("SEK", "NOK", "CHF"):
        return f"{amount:,} {c}"
    if sym:
        return f"{sym}{amount:,}"
    return f"{amount:,} {c}"
