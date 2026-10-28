"""Swedish formatting and parsing of money, dates and times. Money is always integer öre internally.

Formatting is locale-driven so a later translation only adds a locale entry; parsing is deliberately tolerant
(the model may write "1 234,50 kr", "1234.50", "1 234:50 SEK") because the checked skill is the amount, not the
typography.
"""
from __future__ import annotations

import datetime as dt
import re

LOCALES = {
    "sv": {"thousands": " ", "decimal": ",", "currency": "kr",
           "weekdays": ["måndag", "tisdag", "onsdag", "torsdag", "fredag", "lördag", "söndag"],
           "months": ["januari", "februari", "mars", "april", "maj", "juni", "juli", "augusti", "september",
                      "oktober", "november", "december"]},
}


def money(ore: int, lang: str = "sv", currency: bool = True) -> str:
    loc = LOCALES[lang]
    sign = "-" if ore < 0 else ""
    kr, rest = divmod(abs(ore), 100)
    groups = f"{kr:,}".replace(",", loc["thousands"])
    text = f"{sign}{groups}{loc['decimal']}{rest:02d}"
    return f"{text} {loc['currency']}" if currency else text


_MONEY = re.compile(r"-?\d{1,3}(?:[   .]\d{3})+(?:[,.:]\d{1,2})?|-?\d+(?:[,.:]\d{1,2})?")


def parse_money(text: str) -> int | None:
    """Parse one amount to öre; returns None unless exactly one amount is present (no hedging with lists)."""
    if text is None:
        return None
    cleaned = re.sub(r"(?i)\b(kr|kronor|sek|:-)\b|:-", " ", text).strip()
    found = _MONEY.findall(cleaned)
    if len(found) != 1:
        return None
    token = found[0]
    negative = token.startswith("-")
    token = token.lstrip("-")
    m = re.fullmatch(r"(\d{1,3}(?:[   .]\d{3})+|\d+)(?:[,.:](\d{1,2}))?", token)
    if not m:
        return None
    whole, frac = m.group(1), m.group(2) or "0"
    # A separator followed by exactly three digits is a thousands separator ("1.234" = 1 234 kr); decimals have
    # at most two digits, which is all öre amounts need.
    whole = re.sub(r"[   .]", "", whole)
    value = int(whole) * 100 + int(frac.ljust(2, "0"))
    return -value if negative else value


def date(d: dt.date) -> str:
    return d.isoformat()


def long_date(d: dt.date, lang: str = "sv") -> str:
    loc = LOCALES[lang]
    return f"{loc['weekdays'][d.weekday()]} {d.day} {loc['months'][d.month - 1]} {d.year}"


def parse_date(text: str) -> dt.date | None:
    if text is None:
        return None
    found = re.findall(r"\b(\d{4})-(\d{2})-(\d{2})\b", text)
    if len(found) != 1:
        return None
    try:
        return dt.date(*map(int, found[0]))
    except ValueError:
        return None


def parse_time(text: str) -> str | None:
    if text is None:
        return None
    found = re.findall(r"\b([01]?\d|2[0-3])[:.]([0-5]\d)\b", text)
    if len(found) != 1:
        return None
    return f"{int(found[0][0]):02d}:{found[0][1]}"
