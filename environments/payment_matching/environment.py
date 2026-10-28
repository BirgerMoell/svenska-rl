"""Matcha inbetalningar mot kundfakturor (kundreskontra) enligt uttryckliga regler.

The model gets the open invoices and the day's bank payments and returns a JSON object payment id -> invoice
number or "omatchad". Rules in the prompt: (1) a payment whose reference equals an invoice's OCR number matches
that invoice, even when the amount differs (part payment); (2) a reference that is not a valid OCR number (check
digit fails), or no reference, falls back to: payer equals the invoice's customer AND amount equals the invoice's
total AND exactly one such invoice exists; (3) otherwise "omatchad". Distractors: transposed OCR digits (fail the
check digit), two invoices of the same customer and amount (ambiguous fallback), payments from unknown payers.
Per-payment partial reward; extra keys cost credit.
"""
import datetime as dt

from svrl.contract import TypedEnvironment, TypedTask
from svrl.kontoret import fmt, ids
from svrl.kontoret.reskontra import corrupt_reference, match_payment
from svrl.kontoret.world import World


class PaymentMatching(TypedEnvironment):
    id = "payment_matching"
    partial_reward = True

    def generate(self, rng):
        world = World(rng, n_customers=rng.randint(4, 7))
        invoices = [world.invoice(n_lines=(1, 2)) for _ in range(rng.randint(4, 8))]
        if rng.random() < .5:  # an ambiguous pair for the fallback rule
            twin = world.invoice(customer=invoices[0].customer, n_lines=(1, 1))
            twin.lines = [type(line)(**vars(line)) for line in invoices[0].lines]
            invoices.append(twin)
        rng.shuffle(invoices)
        payments, expected = [], {}
        n = rng.randint(3, min(7, len(invoices) + 1))
        for k, kind in enumerate(rng.choices(["ocr", "ocr_part", "bad_ocr", "no_ref", "unknown"],
                                             weights=[4, 2, 2, 2, 1], k=n)):
            pid = f"B{k + 1:02d}"
            inv = rng.choice(invoices)
            payer, amount, reference = inv.customer.name, inv.total(), inv.ocr
            if kind == "ocr_part":
                amount = inv.total() * rng.choice([25, 40, 50]) // 100
            elif kind == "bad_ocr":
                reference = corrupt_reference(inv.ocr, rng)
            elif kind == "no_ref":
                reference = rng.choice(["", f"Faktura {inv.number}"[: rng.choice([0, 7])], "Betalning"]).strip()
            elif kind == "unknown":
                payer, reference = world.person().name, ids.ocr(rng)
                amount = rng.randint(200, 20000) * 100
            match = match_payment(invoices, payer, amount, reference)
            payments.append((pid, world.today - dt.timedelta(days=rng.randint(0, 2)), payer, amount, reference))
            expected[pid] = match
        lines = [f"Du arbetar med kundreskontran hos {world.org.name}. Matcha dagens inbetalningar mot obetalda "
                 "kundfakturor.", "", "Obetalda fakturor:", "| Fakturanummer | Kund | Belopp inkl. moms | OCR-nummer |",
                 "|---|---|---|---|"]
        lines += [f"| {i.number} | {i.customer.name} | {fmt.money(i.total())} | {i.ocr} |" for i in invoices]
        lines += ["", "Inbetalningar:", "| Id | Datum | Betalare | Belopp | Referens |", "|---|---|---|---|---|"]
        lines += [f"| {p} | {d.isoformat()} | {payer} | {fmt.money(a)} | {r or '–'} |" for p, d, payer, a, r in payments]
        lines += ["", "Regler:",
                  "1. Om referensen är exakt samma som en fakturas OCR-nummer hör betalningen till den fakturan, även "
                  "om beloppet avviker (delbetalning).",
                  "2. Om referensen saknas eller inte är ett giltigt OCR-nummer (kontrollsiffran enligt "
                  "Luhn-algoritmen stämmer inte, eller numret finns inte bland fakturorna): matcha bara om betalaren "
                  "är fakturans kund, beloppet är exakt fakturans belopp och det finns exakt en sådan faktura.",
                  "3. Annars är betalningen omatchad.",
                  "Svara med ett JSON-objekt där varje inbetalnings-id pekar på ett fakturanummer eller på \"omatchad\"."]
        return TypedTask("\n".join(lines), {"type": "mapping", "value": expected}, "mapping",
                         {"payments": len(payments), "invoices": len(invoices)})


def create():
    return PaymentMatching()
