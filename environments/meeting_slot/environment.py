"""Hitta första gemensamma mötestid över flera dagar, med arbetstid, lunch, röda dagar och möteslängd.

Calendars cover 3-5 consecutive calendar days (they may include weekends and Swedish public holidays). Levels:
1 the holidays in the window are named in the prompt; 2 they are not named ("röda dagar är lediga" must be
known: Swedish office knowledge, computed exactly by svrl.kontoret.kalender); 3 adds a buffer rule (no meeting
may start directly after another meeting of the same person). Answer: `SVAR: ÅÅÅÅ-MM-DD TT:MM`.
"""
import datetime as dt

from svrl.contract import TypedEnvironment, TypedTask
from svrl.kontoret import kalender
from svrl.kontoret.kalender import DAY_END, DAY_START, hm
from svrl.kontoret.world import World

class MeetingSlot(TypedEnvironment):
    id = "meeting_slot"

    def generate(self, rng):
        world = World(rng)
        level = rng.choice([1, 2, 3])
        # Bias the window towards holiday-rich periods so the rule matters.
        year = world.today.year
        anchors = list(kalender.holidays(year)) + [world.today]
        start = rng.choice(anchors) - dt.timedelta(days=rng.randint(0, 2))
        days = [start + dt.timedelta(days=i) for i in range(rng.randint(3, 5))]
        length = rng.choice([30, 60, 90])
        people = rng.sample(world.staff, rng.randint(2, 4))
        busy = {p.name: [] for p in people}
        for p in people:
            for d in days:
                if not kalender.is_working_day(d):
                    continue
                for _ in range(rng.randint(1, 5)):
                    s = rng.randrange(DAY_START, DAY_END - 30, 30)
                    busy[p.name].append((d, s, min(DAY_END, s + rng.choice([30, 60, 90, 120]))))
        answer = kalender.first_common_slot(days, busy.values(), length, buffer=level == 3)
        lines = [f"Du är assistent på {world.org.name} och ska boka ett möte på {length} minuter med "
                 + ", ".join(p.name for p in people) + ".",
                 f"Mötet ska ligga mellan {days[0].isoformat()} och {days[-1].isoformat()} (båda dagarna inräknade) "
                 "och börja på hel- eller halvtimme.",
                 "Arbetstiden är 08:00–17:00 måndag till fredag; lunch 12:00–13:00 är alltid blockerad och mötet "
                 "måste sluta senast 17:00. Röda dagar och helgaftnar som midsommarafton, julafton och nyårsafton är "
                 "lediga.",
                 "Boka den tidigaste tid då alla är lediga under hela mötet."]
        if level == 3:
            lines.append("Ingen deltagare får ha ett annat möte som slutar exakt när det nya mötet börjar.")
        if level == 1:
            named = [f"{d.isoformat()} är {kalender.holidays(d.year)[d]}" for d in days if d in kalender.holidays(d.year)]
            if named:
                lines.append("Observera: " + "; ".join(named) + ".")
        lines.append("")
        lines.append("Upptagna tider:")
        for name, blocks in busy.items():
            items = [f"{d.isoformat()} {hm(s)}–{hm(e)}" for d, s, e in sorted(blocks)]
            lines.append(f"- {name}: " + (", ".join(items) if items else "inga möten"))
        lines.append("Om ingen tid fungerar, svara `SVAR: INGEN TID`.")
        # The prompt asks for a date and time in both cases, so the format hint does not reveal a missing slot.
        if answer is None:
            return TypedTask("\n".join(lines), {"type": "text", "value": "INGEN TID"}, "datetime",
                             {"level": level, "no_slot": True})
        return TypedTask("\n".join(lines), {"type": "datetime", "date": answer[0].isoformat(), "time": hm(answer[1])},
                         "datetime", {"level": level, "days": len(days), "people": len(people)})


def create():
    return MeetingSlot()
