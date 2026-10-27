from svrl.core import Environment, multiple_choice


def clock(slot):
    return f"{8 + slot // 2:02d}:{30 * (slot % 2):02d}"


class CalendarBooking(Environment):
    id = "calendar_booking"

    def generate(self, rng):
        slots = list(range(16))
        guaranteed = rng.choice(slots)
        names = ["Alex", "Kim", "Robin"]
        busy = [set(rng.sample([s for s in slots if s != guaranteed], rng.randint(3, 9)))
                for _ in names]
        free = [s for s in slots if all(s not in b for b in busy)]
        instruction = ("Boka dagens tidigaste gemensamma möte på 30 minuter. "
                       "Arbetsdagen är 08:00–16:00. Varje upptagen starttid nedan "
                       "blockerar exakt 30 minuter. Alla tider gäller samma dag.\n")
        instruction += "\n".join(f"{name} är upptagen: " + ", ".join(clock(s) for s in sorted(b))
                                  for name, b in zip(names, busy))
        return multiple_choice(rng, instruction, clock(free[0]),
                               [clock(s) for s in slots if s != free[0]])


def create():
    return CalendarBooking()
