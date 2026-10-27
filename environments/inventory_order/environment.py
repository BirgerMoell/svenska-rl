from svrl.core import Environment, multiple_choice


class InventoryOrder(Environment):
    id = "inventory_order"

    def generate(self, rng):
        stock = rng.randint(0, 80)
        reserved = rng.randint(0, stock)
        target = rng.randint(20, 120)
        pack = rng.choice([5, 10, 12, 20])
        deficit = max(0, target - (stock - reserved))
        order = ((deficit + pack - 1) // pack) * pack
        instruction = (f"Lagret innehåller {stock} enheter, varav {reserved} är reserverade. "
                       f"Efter beställning ska minst {target} enheter vara tillgängliga "
                       f"utöver de reserverade. Varorna säljs i hela förpackningar om {pack}. "
                       "Hur många enheter ska du minst beställa? Beställ noll om lagret räcker.")
        wrong = [order + pack, order + 2 * pack, order + 3 * pack, max(0, order - pack)]
        return multiple_choice(rng, instruction, f"{order} enheter", [f"{x} enheter" for x in wrong])


def create():
    return InventoryOrder()
