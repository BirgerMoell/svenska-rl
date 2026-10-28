"""Synthetic Swedish identifiers with correct check digits (Luhn / modulus 10).

Everything is generated from an RNG; nothing refers to real people or companies. Personal identity numbers use
day numbers 61-91 ("samordningsnummer" form) so they can never collide with a real personnummer's birth date
encoding, and organisation numbers use the 55xxxx-xxxx (aktiebolag) shape with a valid check digit.
"""
from __future__ import annotations


def luhn_digit(digits: str) -> str:
    """Check digit for `digits` with the Luhn algorithm (weights 2,1,2,1,... from the right of the payload)."""
    total = 0
    for i, ch in enumerate(reversed(digits)):
        d = int(ch) * (2 if i % 2 == 0 else 1)
        total += d - 9 if d > 9 else d
    return str((10 - total % 10) % 10)


def luhn_valid(number: str) -> bool:
    digits = "".join(ch for ch in number if ch.isdigit())
    return len(digits) >= 2 and luhn_digit(digits[:-1]) == digits[-1]


def samordningsnummer(rng, year_from: int = 1950, year_to: int = 2004) -> str:
    """YYMMDD-NNNC with day + 60, i.e. a coordination-number form that is not a real birth date."""
    year = rng.randint(year_from, year_to)
    month = rng.randint(1, 12)
    day = rng.randint(1, 28) + 60
    serial = rng.randint(100, 999)
    payload = f"{year % 100:02d}{month:02d}{day:02d}{serial:03d}"
    return f"{payload[:6]}-{payload[6:]}{luhn_digit(payload)}"


def organisationsnummer(rng) -> str:
    payload = "55" + "".join(str(rng.randint(0, 9)) for _ in range(7))
    return f"{payload[:6]}-{payload[6:]}{luhn_digit(payload)}"


def bankgiro(rng) -> str:
    payload = "".join(str(rng.randint(0, 9)) for _ in range(6)) if rng.random() < .5 else \
        "".join(str(rng.randint(0, 9)) for _ in range(7))
    payload = str(rng.randint(1, 9)) + payload[1:]
    number = payload + luhn_digit(payload)
    return f"{number[:-4]}-{number[-4:]}"


def ocr(rng, base_length: int = 8) -> str:
    """OCR reference with a length digit and a Luhn check digit (the common Bankgirot 'hard' OCR form)."""
    base = str(rng.randint(1, 9)) + "".join(str(rng.randint(0, 9)) for _ in range(base_length - 1))
    with_length = base + str((len(base) + 2) % 10)
    return with_length + luhn_digit(with_length)


def ocr_valid(reference: str) -> bool:
    digits = "".join(ch for ch in reference if ch.isdigit())
    return (len(digits) >= 3 and digits == reference.strip() and luhn_valid(digits)
            and int(digits[-2]) == len(digits) % 10)
