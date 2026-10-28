"""Beställningsförslag för lagret: hur många enheter av varje artikel ska beställas?

Replaces the v0.1 single-article multiple-choice `inventory_order`. A stock list of 3-6 articles with stock on
hand, reserved units, incoming deliveries (only those arriving before a stated date count), a minimum level and a
pack size. Rule: order the smallest number of whole packs so that available stock (on hand - reserved + counted
incoming) reaches at least the minimum level; 0 if it already does. Answer: JSON article number -> units.
Partial reward per article.
"""
import datetime as dt

from svrl.contract import TypedEnvironment, TypedTask
from svrl.kontoret.world import World

ARTICLES = ["Kopieringspapper A4", "Toner svart", "Pärmar", "Kaffebönor 1 kg", "Engångsmuggar", "Pennor blå",
            "Post-it-lappar", "Batterier AA", "Handsprit", "Kuvert C5", "Whiteboardpennor", "Häftklamrar"]


class InventoryReorder(TypedEnvironment):
    id = "inventory_reorder"
    partial_reward = True

    def generate(self, rng):
        world = World(rng)
        cutoff = world.today + dt.timedelta(days=rng.choice([3, 5, 7]))
        items, expected = [], {}
        for name in rng.sample(ARTICLES, rng.randint(3, 6)):
            number = f"A{rng.randint(1000, 9999)}"
            stock = rng.randint(0, 200)
            reserved = rng.randint(0, stock)
            minimum = rng.randint(10, 250)
            pack = rng.choice([1, 5, 6, 10, 12, 20, 25, 50])
            incoming = []
            for _ in range(rng.choice([0, 0, 1, 2])):
                incoming.append((rng.randint(5, 60), world.today + dt.timedelta(days=rng.randint(1, 14))))
            counted = sum(q for q, d in incoming if d <= cutoff)
            deficit = max(0, minimum - (stock - reserved + counted))
            expected[number] = -(-deficit // pack) * pack
            items.append((number, name, stock, reserved, incoming, minimum, pack))
        rows = []
        for number, name, stock, reserved, incoming, minimum, pack in items:
            inc = ", ".join(f"{q} st {d.isoformat()}" for q, d in incoming) or "–"
            rows.append(f"| {number} | {name} | {stock} | {reserved} | {inc} | {minimum} | {pack} |")
        instruction = (
            f"Du ansvarar för förrådet på {world.org.name}. Dagens datum är {world.today.isoformat()}. Ta fram "
            "ett beställningsförslag.\n\n"
            "| Artikelnr | Artikel | I lager | Reserverat | Inkommande leveranser | Miniminivå | Förpackning (st) |\n"
            "|---|---|---|---|---|---|---|\n" + "\n".join(rows) + "\n\n"
            f"Regler: tillgängligt = i lager − reserverat + inkommande leveranser som kommer senast "
            f"{cutoff.isoformat()} (senare leveranser räknas inte). Beställ det minsta antalet hela förpackningar "
            "så att tillgängligt blir minst miniminivån; beställ 0 om nivån redan nås. Svara med ett JSON-objekt "
            "där varje artikelnummer pekar på antalet enheter (inte förpackningar) att beställa.")
        return TypedTask(instruction, {"type": "mapping", "value": expected}, "mapping",
                         {"articles": len(items), "zero_orders": sum(v == 0 for v in expected.values())})


def create():
    return InventoryReorder()
