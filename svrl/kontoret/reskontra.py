"""Accounts-receivable rules shared by the payment environments (matching payments to invoices)."""
from svrl.kontoret import ids


def corrupt_reference(reference, rng):
    """Swap two adjacent different digits so the Luhn check fails (adjacent swaps are always detected except
    0-9 / 9-0, which are avoided)."""
    digits = list(reference)
    for _ in range(50):
        i = rng.randrange(len(digits) - 1)
        a, b = digits[i], digits[i + 1]
        if a != b and {a, b} != {"0", "9"}:
            swapped = digits[:i] + [b, a] + digits[i + 2:]
            out = "".join(swapped)
            if not ids.luhn_valid(out):
                return out
    return reference[:-1] + str((int(reference[-1]) + 1) % 10)


def match_payment(invoices, payer, amount, reference):
    """1) exact, valid OCR -> that invoice (any amount); 2) else payer is the customer AND amount equals the total
    AND exactly one such invoice; 3) else "omatchad"."""
    by_ocr = [i for i in invoices if i.ocr == reference]
    if by_ocr and ids.ocr_valid(reference):
        return by_ocr[0].number
    candidates = [i for i in invoices if i.customer.name == payer and i.total() == amount]
    return candidates[0].number if len(candidates) == 1 else "omatchad"
