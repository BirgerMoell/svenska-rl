"""Choose a feasible supplier by total landed cost, or decline all offers."""
from dataclasses import dataclass

from svrl.core import ACTIONS, Environment, Task

NAMES = ("Alfa", "Beta", "Gamma")
DECLINE = "Avstå: ingen offert uppfyller samtliga krav."


@dataclass(frozen=True)
class Quote:
    name: str
    unit_price: int  # öre, excluding VAT
    shipping: int  # öre per complete order
    days: int
    capacity: int


def money(cents):
    return f"{cents // 100},{cents % 100:02d}"


def select_supplier(quotes, quantity, budget, deadline):
    feasible = [q for q in quotes if q.capacity >= quantity and q.days <= deadline
                and q.unit_price * quantity + q.shipping <= budget]
    if not feasible:
        return None
    return min(feasible, key=lambda q: (q.unit_price * quantity + q.shipping,
                                       q.days, q.name)).name


def build_task(rng, quantity, budget, deadline, quotes):
    instruction = (
        f"Behov: {quantity} enheter.\nBudget: {money(budget)} kr.\n"
        f"Senast leverans: {deadline} dagar.\n"
        "Beställ hela behovet från en enda leverantör. Priser är exklusive moms; "
        "lägg inte till moms. Frakten betalas en gång per beställning. "
        "Kapaciteten måste räcka, leveransen får ske senast på sista dagen och "
        "totalkostnaden får inte överstiga budgeten. Välj lägsta totalkostnad "
        "bland godkända offerter. Vid samma totalkostnad väljer du kortast "
        "leveranstid, därefter leverantörens namn i alfabetisk ordning. "
        "Avstå om ingen offert uppfyller kraven.\n\n"
        "Leverantör | Styckpris (kr) | Frakt (kr) | Leveranstid (dagar) | Kapacitet (enheter)\n")
    instruction += "\n".join(
        f"{q.name} | {money(q.unit_price)} | {money(q.shipping)} | {q.days} | {q.capacity}"
        for q in quotes)
    choices = [f"Beställ {quantity} enheter från {name}." for name in NAMES] + [DECLINE]
    winner = select_supplier(quotes, quantity, budget, deadline)
    correct = DECLINE if winner is None else f"Beställ {quantity} enheter från {winner}."
    rng.shuffle(choices)
    return Task(instruction, tuple(choices), ACTIONS[choices.index(correct)])


class SupplierQuotes(Environment):
    id = "supplier_quotes"

    def generate(self, rng):
        quantity = rng.randint(5, 100)
        deadline = rng.randint(2, 14)
        budget = rng.randint(100, 25000) * quantity + rng.randint(0, 30000)
        quotes = [Quote(name, rng.randint(100, 25000), rng.randint(0, 30000),
                        rng.randint(1, 18), rng.randint(1, 150)) for name in NAMES]
        mode = rng.randrange(5)
        if mode == 0:
            # Explicit refusal cases: every offer arrives too late.
            quotes = [Quote(q.name, q.unit_price, q.shipping, deadline + rng.randint(1, 5),
                            q.capacity) for q in quotes]
        elif mode == 1:
            # Inclusive price, delivery and capacity boundaries all matter.
            price, shipping = rng.randint(100, 20000), rng.randint(0, 10000)
            budget = price * quantity + shipping
            winner = rng.choice(NAMES)
            quotes = [Quote(name, price, shipping if name == winner else shipping + 1,
                            deadline, quantity) for name in NAMES]
        elif mode == 2:
            # Identical total prices exercise delivery and alphabetical ties.
            price, shipping = rng.randint(100, 20000), rng.randint(0, 10000)
            budget = price * quantity + shipping + rng.randint(0, 10000)
            tied_days = rng.randint(1, deadline)
            quotes = [Quote(name, price, shipping, tied_days, quantity + rng.randint(0, 20))
                      for name in NAMES]
            rng.shuffle(quotes)
        return build_task(rng, quantity, budget, deadline, quotes)


def create():
    return SupplierQuotes()
