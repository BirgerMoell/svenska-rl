from svrl.core import Environment, multiple_choice


def money(cents):
    return f"{cents // 100},{cents % 100:02d} kr"


class InvoiceTotals(Environment):
    id = "invoice_totals"

    def generate(self, rng):
        rows = [(rng.randint(1, 9), rng.randint(10, 300) * 100) for _ in range(3)]
        subtotal = sum(quantity * price for quantity, price in rows)
        vat = rng.choice([6, 12, 25])
        total = subtotal * (100 + vat) // 100
        lines = [f"Rad {i + 1}: {q} st à {money(p)} exklusive moms."
                 for i, (q, p) in enumerate(rows)]
        instruction = "Beräkna fakturans totalsumma inklusive moms.\n" + "\n".join(lines)
        instruction += f"\nMomsen är {vat} procent på samtliga rader. Inga andra avgifter."
        wrong = [subtotal, total + 100, total - 100, total + 1000, total + rows[0][1]]
        return multiple_choice(rng, instruction, money(total), [money(x) for x in wrong])


def create():
    return InvoiceTotals()
