"""Belopp att betala på en faktura: rader, blandad moms, radrabatter, tidigare delbetalning, öresavrundning.

Levels (meta.level): 1 one VAT rate; 2 mixed VAT per line; 3 + line discounts and an earlier part payment;
4 + a credit line and rounding of the amount due to whole kronor. About 12 % of tasks leave out a price the
calculation needs; then the only correct answer is INFORMATION SAKNAS.
"""
from svrl.contract import TypedEnvironment, TypedTask
from svrl.kontoret import fmt
from svrl.kontoret.world import World, round_half_up

RULES = ("Regler: radbelopp = antal × à-pris. Rabatt i procent dras från radbeloppet före moms. Moms beräknas per "
         "rad på beloppet efter rabatt. Rabatt och moms avrundas per rad till hela ören, och exakt ett halvt öre "
         "avrundas uppåt.")


class InvoiceAmountDue(TypedEnvironment):
    id = "invoice_amount_due"
    abstention = True

    def generate(self, rng):
        world = World(rng, n_customers=3)
        level = rng.choice([1, 2, 3, 4])
        invoice = world.invoice(n_lines=(2, 3 + level), discounts=level >= 3,
                                vat_rates=None if level >= 2 else (rng.choice([25, 12, 6]),))
        if level == 1:
            for line in invoice.lines:
                line.vat_percent = invoice.lines[0].vat_percent
        credit = 0
        if level == 4:
            credit = rng.randint(5, 40) * 1000  # credit note excl. VAT, 25 % VAT
        total = invoice.total()
        credit_total = credit + round_half_up(credit * 25, 100)
        paid = round_half_up(total * rng.choice([20, 25, 30, 40, 50]), 100) if level >= 3 and rng.random() < .6 else 0
        due = total - credit_total - paid
        rounded = level == 4
        if rounded:
            due = round_half_up(due, 100) * 100
        missing = rng.random() < .12
        rows = []
        hidden = rng.randrange(len(invoice.lines)) if missing else None
        for i, line in enumerate(invoice.lines):
            price = "enligt separat offert" if i == hidden else fmt.money(line.unit_price)
            discount = f", rabatt {line.discount_percent} %" if line.discount_percent else ""
            rows.append(f"| {i + 1} | {line.description} | {line.quantity} | {price} | {line.vat_percent} %{discount} |")
        text = [f"Du arbetar på ekonomiavdelningen hos {world.org.name}. Beräkna hur mycket kunden "
                f"{invoice.customer.name} ska betala på faktura {invoice.number} (fakturadatum "
                f"{invoice.issued.isoformat()}).", "",
                "| Rad | Beskrivning | Antal | À-pris exkl. moms | Moms, rabatt |", "|---|---|---|---|---|", *rows, "",
                RULES]
        if credit:
            text.append(f"En kreditnota på {fmt.money(credit)} exklusive moms (25 % moms) ska dras av från fakturan.")
        if paid:
            text.append(f"Kunden har redan betalat {fmt.money(paid)} på fakturan.")
        if rounded:
            text.append("Beloppet att betala avrundas till hela kronor; 50 öre avrundas uppåt.")
        text.append("Vilket belopp, inklusive moms, återstår att betala?")
        spec = {"type": "abstain"} if missing else {"type": "money", "value": due}
        return TypedTask("\n".join(text), spec, "money",
                         {"level": level, "unanswerable": missing, "lines": len(invoice.lines)})


def create():
    return InvoiceAmountDue()
