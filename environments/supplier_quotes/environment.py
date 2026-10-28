"""Välj leverantör utifrån offerter: total kostnad, kapacitet, leveranstid och budget, eller avstå.

Ported from the v0.1 multiple-choice contribution (PR #22) to contract v0.2: the model now states the supplier
AND the total cost (JSON), or declines, so guessing among the suppliers earns nothing. Rules (in the prompt):
the whole need from one supplier; prices excl. VAT, VAT not added; shipping once per order; capacity must
cover the need; delivery at the latest on the deadline day; total cost within budget (inclusive); lowest total
cost wins, ties by shortest delivery time, then supplier name alphabetically; decline if no quote qualifies.
Generation modes: ordinary (usually something qualifies), all late (decline), inclusive boundaries, tied
totals; 3-5 suppliers. Declining is correct in roughly a quarter of tasks, so always declining does not pay.
"""
from svrl.contract import TypedEnvironment, TypedTask
from svrl.kontoret import fmt
from svrl.kontoret.world import World

NAMES = ("Alfa", "Beta", "Gamma", "Delta", "Epsilon")


def select(quotes, quantity, budget, deadline):
    feasible = [q for q in quotes if q["capacity"] >= quantity and q["days"] <= deadline
                and q["price"] * quantity + q["shipping"] <= budget]
    if not feasible:
        return None
    best = min(feasible, key=lambda q: (q["price"] * quantity + q["shipping"], q["days"], q["name"]))
    return best["name"], best["price"] * quantity + best["shipping"]


class SupplierQuotes(TypedEnvironment):
    id = "supplier_quotes"

    def generate(self, rng):
        world = World(rng, n_customers=5)
        names = [f"{n} – {c.name}" for n, c in zip(NAMES, world.customers)][:rng.randint(3, 5)]
        quantity, deadline = rng.randint(5, 100), rng.randint(2, 14)
        quotes = [{"name": n, "price": rng.randint(100, 25000), "shipping": rng.randint(0, 30000),
                   "days": rng.randint(1, 18), "capacity": rng.randint(1, 150)} for n in names]
        budget = rng.randint(100, 25000) * quantity + rng.randint(0, 30000)
        mode = rng.randrange(5)
        if mode >= 3 and rng.random() < .85:  # ordinary: usually one or more offers qualify
            for q in rng.sample(quotes, rng.randint(1, len(quotes))):
                q.update(capacity=max(q["capacity"], quantity + rng.randint(0, 30)), days=rng.randint(1, deadline))
            cheapest = min(q["price"] * quantity + q["shipping"] for q in quotes
                           if q["capacity"] >= quantity and q["days"] <= deadline)
            budget = max(budget, cheapest + rng.randint(0, 50000))
        if mode == 0:  # every offer too late: decline
            for q in quotes:
                q["days"] = deadline + rng.randint(1, 5)
        elif mode == 1:  # inclusive price, delivery and capacity boundaries; one öre of shipping decides
            price, shipping = rng.randint(100, 20000), rng.randint(0, 10000)
            budget = price * quantity + shipping
            winner = rng.choice(names)
            for q in quotes:
                q.update(price=price, shipping=shipping if q["name"] == winner else shipping + 1,
                         days=deadline, capacity=quantity)
        elif mode == 2:  # identical totals: delivery time and then the name decide
            price, shipping = rng.randint(100, 20000), rng.randint(0, 10000)
            budget = price * quantity + shipping + rng.randint(0, 10000)
            for q in quotes:
                q.update(price=price, shipping=shipping, days=rng.randint(1, deadline),
                         capacity=quantity + rng.randint(0, 20))
        rng.shuffle(quotes)
        winner = select(quotes, quantity, budget, deadline)
        rows = "\n".join(f"| {q['name']} | {fmt.money(q['price'])} | {fmt.money(q['shipping'])} | {q['days']} | "
                         f"{q['capacity']} |" for q in quotes)
        instruction = (
            f"Du arbetar med inköp på {world.org.name}. Behov: {quantity} enheter. Budget: {fmt.money(budget)}. "
            f"Leverans senast inom {deadline} dagar.\n\n"
            "Regler: beställ hela behovet från en enda leverantör. Priser är exklusive moms; lägg inte till moms. "
            "Frakten betalas en gång per beställning. Kapaciteten måste räcka, leveransen får ske senast på sista "
            "dagen och totalkostnaden (antal × styckpris + frakt) får inte överstiga budgeten. Välj lägsta "
            "totalkostnad bland godkända offerter. Vid samma totalkostnad väljer du kortast leveranstid, därefter "
            "leverantörens namn i alfabetisk ordning.\n\n"
            "| Leverantör | Styckpris | Frakt | Leveranstid (dagar) | Kapacitet (enheter) |\n|---|---|---|---|---|\n"
            f"{rows}\n\n"
            "Svara med ett JSON-objekt: {\"leverantor\": <leverantörens namn som i tabellen>, \"totalkostnad\": "
            "<belopp i kronor>}. Om ingen offert uppfyller kraven: {\"leverantor\": \"avstå\"}.")
        if winner is None:
            spec = {"type": "mapping", "value": {"leverantor": "avstå"}}
        else:
            spec = {"type": "mapping", "value": {"leverantor": winner[0], "totalkostnad": {"money": winner[1]}}}
        return TypedTask(instruction, spec, "mapping", {"mode": mode, "suppliers": len(quotes),
                                                        "declined": winner is None})


def create():
    return SupplierQuotes()
