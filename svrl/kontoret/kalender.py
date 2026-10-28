"""Swedish public holidays ("röda dagar") and working-day arithmetic, computed (no data files)."""
from __future__ import annotations

import datetime as dt


def easter(year: int) -> dt.date:
    """Gregorian Easter Sunday (anonymous Gregorian algorithm)."""
    a, b, c = year % 19, year // 100, year % 100
    d, e = b // 4, b % 4
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i, k = c // 4, c % 4
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    month = (h + l - 7 * m + 114) // 31
    day = (h + l - 7 * m + 114) % 31 + 1
    return dt.date(year, month, day)


def _saturday_between(start: dt.date, end: dt.date) -> dt.date:
    d = start
    while d.weekday() != 5:
        d += dt.timedelta(days=1)
    assert d <= end
    return d


def holidays(year: int) -> dict[dt.date, str]:
    """Swedish public holidays plus the de facto non-working eves (midsommarafton, julafton, nyårsafton)."""
    e = easter(year)
    midsummer_day = _saturday_between(dt.date(year, 6, 20), dt.date(year, 6, 26))
    all_saints = _saturday_between(dt.date(year, 10, 31), dt.date(year, 11, 6))
    days = {
        dt.date(year, 1, 1): "nyårsdagen", dt.date(year, 1, 6): "trettondedag jul",
        e - dt.timedelta(days=2): "långfredagen", e: "påskdagen", e + dt.timedelta(days=1): "annandag påsk",
        dt.date(year, 5, 1): "första maj", e + dt.timedelta(days=39): "Kristi himmelsfärdsdag",
        e + dt.timedelta(days=49): "pingstdagen", dt.date(year, 6, 6): "Sveriges nationaldag",
        midsummer_day - dt.timedelta(days=1): "midsommarafton", midsummer_day: "midsommardagen",
        all_saints: "alla helgons dag", dt.date(year, 12, 24): "julafton", dt.date(year, 12, 25): "juldagen",
        dt.date(year, 12, 26): "annandag jul", dt.date(year, 12, 31): "nyårsafton",
    }
    return days


def is_working_day(d: dt.date) -> bool:
    return d.weekday() < 5 and d not in holidays(d.year)


def add_working_days(d: dt.date, n: int) -> dt.date:
    step = 1 if n >= 0 else -1
    remaining = abs(n)
    while remaining:
        d += dt.timedelta(days=step)
        if is_working_day(d):
            remaining -= 1
    return d


DAY_START, DAY_END, LUNCH = 8 * 60, 17 * 60, (12 * 60, 13 * 60)


def hm(minutes: int) -> str:
    return f"{minutes // 60:02d}:{minutes % 60:02d}"


def first_common_slot(days, busy, length: int, buffer: bool = False):
    """Earliest (date, start minute) on a working day, on a half hour, 08:00-17:00, not overlapping lunch
    12:00-13:00, where no block in `busy` (iterable of lists of (date, start, end) minutes) overlaps; with
    `buffer`, no block may end exactly at the start. None when no slot exists."""
    for d in days:
        if not is_working_day(d):
            continue
        for s in range(DAY_START, DAY_END - length + 1, 30):
            e = s + length
            if s < LUNCH[1] and e > LUNCH[0]:
                continue
            if all(not (bd == d and (bs < e and be > s or (buffer and be == s)))
                   for blocks in busy for bd, bs, be in blocks):
                return d, s
    return None
