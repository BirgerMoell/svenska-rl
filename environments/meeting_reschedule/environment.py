"""Flytta ett möte när en deltagare fått förhinder, och meddela deltagarna (verktyg, flera steg).

The calendar system holds the participants' meetings for one working week. One meeting must move because a
participant is away on its day. The model reads calendars with tools, moves the meeting to the earliest slot in
the rest of the week where all participants are free (rules as in `meeting_slot`, and not on the day of the
absence), and e-mails every participant the new date and time. Scored on state: 0.6 for the meeting at the right
date and time (0 for the whole task if it was moved anywhere else or another meeting was changed), 0.4 split over
the participants who got exactly one e-mail containing the new date (ÅÅÅÅ-MM-DD) and start time (TT:MM).
"""
import datetime as dt
import re
from dataclasses import dataclass, field

from svrl.contract import Tool, ToolEnvironment, ToolError, ToolTask
from svrl.kontoret import kalender
from svrl.kontoret.kalender import DAY_END, DAY_START, LUNCH, hm
from svrl.kontoret.world import World


@dataclass
class Calendar:
    people: dict                       # email -> name
    meetings: dict                     # id -> {"title", "date", "start", "end", "participants": [email]}
    absences: dict                     # email -> [date iso]
    outbox: list = field(default_factory=list)
    moves: list = field(default_factory=list)


def _minutes(text):
    m = re.fullmatch(r"([01]\d|2[0-3]):([0-5]\d)", text.strip())
    if not m:
        raise ToolError("tid anges som TT:MM")
    return int(m[1]) * 60 + int(m[2])


def list_people(state):
    return [{"namn": n, "epost": e} for e, n in state.people.items()]


def get_calendar(state, epost, datum):
    epost = epost.strip().lower()
    if epost not in state.people:
        raise ToolError(f"ingen person med e-post {epost}")
    try:
        dt.date.fromisoformat(datum)
    except ValueError:
        raise ToolError("datum anges som ÅÅÅÅ-MM-DD")
    rows = [{"mote_id": mid, "titel": m["title"], "start": hm(m["start"]), "slut": hm(m["end"])}
            for mid, m in sorted(state.meetings.items(), key=lambda kv: kv[1]["start"])
            if m["date"] == datum and epost in m["participants"]]
    away = datum in state.absences.get(epost, [])
    return {"datum": datum, "franvarande_hela_dagen": away, "moten": rows}


def get_meeting(state, mote_id):
    m = state.meetings.get(mote_id)
    if m is None:
        raise ToolError(f"mötet {mote_id} finns inte")
    return {"mote_id": mote_id, "titel": m["title"], "datum": m["date"], "start": hm(m["start"]),
            "slut": hm(m["end"]), "deltagare": [{"namn": state.people[e], "epost": e} for e in m["participants"]]}


def move_meeting(state, mote_id, datum, start):
    m = state.meetings.get(mote_id)
    if m is None:
        raise ToolError(f"mötet {mote_id} finns inte")
    try:
        dt.date.fromisoformat(datum)
    except ValueError:
        raise ToolError("datum anges som ÅÅÅÅ-MM-DD")
    s = _minutes(start)
    length = m["end"] - m["start"]
    m.update(date=datum, start=s, end=s + length)
    state.moves.append(mote_id)
    return {"status": "flyttat", "datum": datum, "start": hm(s), "slut": hm(s + length)}


def send_mail(state, till, amne, text):
    state.outbox.append({"to": till.strip().lower(), "subject": amne, "text": text})
    return {"status": "skickat"}


TOOLS = [
    Tool("lista_personer", "Listar personer i kalendersystemet med e-postadresser.",
         {"type": "object", "properties": {}, "required": []}, list_people),
    Tool("hamta_mote", "Hämtar ett möte med tid och deltagare.",
         {"type": "object", "properties": {"mote_id": {"type": "string"}}, "required": ["mote_id"]}, get_meeting),
    Tool("hamta_kalender", "Hämtar en persons möten och eventuell heldagsfrånvaro för ett datum.",
         {"type": "object", "properties": {"epost": {"type": "string"}, "datum": {"type": "string"}},
          "required": ["epost", "datum"]}, get_calendar),
    Tool("flytta_mote", "Flyttar ett möte till ett nytt datum och en ny starttid (längden behålls).",
         {"type": "object", "properties": {"mote_id": {"type": "string"}, "datum": {"type": "string"},
                                           "start": {"type": "string"}}, "required": ["mote_id", "datum", "start"]},
         move_meeting, mutates=True),
    Tool("skicka_mejl", "Skickar ett e-postmeddelande.",
         {"type": "object", "properties": {"till": {"type": "string"}, "amne": {"type": "string"},
                                           "text": {"type": "string"}}, "required": ["till", "amne", "text"]},
         send_mail, mutates=True),
]

TITLES = ["Budgetavstämning", "Projektmöte", "Veckomöte", "Leverantörsgenomgång", "Planering inför kvartalet",
          "Rekryteringsmöte", "Avtalsgenomgång", "Styrgruppsmöte", "Uppföljning av kundärenden"]


class MeetingReschedule(ToolEnvironment):
    id = "meeting_reschedule"

    def generate(self, rng):
        for _ in range(100):
            task = self._try(rng)
            if task is not None:
                return task
        raise RuntimeError("could not generate a solvable task")

    def _try(self, rng):
        world = World(rng)
        monday = world.today - dt.timedelta(days=world.today.weekday())
        week = [monday + dt.timedelta(days=i) for i in range(5)]
        people = rng.sample(world.staff, rng.randint(3, 5))
        emails = {p.email: p.name for p in people}
        if len(emails) < len(people):
            return None
        meetings, n = {}, 0
        for d in week:
            if not kalender.is_working_day(d):
                continue
            for _ in range(rng.randint(2, 5)):
                s = rng.randrange(DAY_START, DAY_END - 60, 30)
                e = min(DAY_END, s + rng.choice([30, 60, 90]))
                if s < LUNCH[1] and e > LUNCH[0]:
                    continue
                n += 1
                meetings[f"M{n:02d}"] = {"title": rng.choice(TITLES), "date": d.isoformat(), "start": s, "end": e,
                                         "participants": sorted(rng.sample(list(emails), rng.randint(1, len(emails))))}
        work_days = [d for d in week[:-1] if kalender.is_working_day(d)]
        if not work_days:
            return None
        day = rng.choice(work_days)
        target_id = f"M{n + 1:02d}"
        participants = sorted(rng.sample(list(emails), rng.randint(2, len(emails))))
        s = rng.choice([s for s in range(DAY_START, DAY_END - 60, 30) if not (s < LUNCH[1] and s + 60 > LUNCH[0])])
        meetings[target_id] = {"title": rng.choice(TITLES), "date": day.isoformat(), "start": s,
                               "end": s + rng.choice([30, 60]), "participants": participants}
        absent = rng.choice(participants)
        absences = {absent: [day.isoformat()]}
        length = meetings[target_id]["end"] - meetings[target_id]["start"]
        later = [d for d in week if d > day]
        busy = [[(dt.date.fromisoformat(m["date"]), m["start"], m["end"])] for mid, m in meetings.items()
                if mid != target_id and set(m["participants"]) & set(participants)]
        slot = kalender.first_common_slot(later, busy, length)
        if slot is None:
            return None
        new_date, new_start = slot[0].isoformat(), hm(slot[1])
        original = {mid: dict(m) for mid, m in meetings.items()}
        state = Calendar(emails, meetings, absences)
        reference = [{"tool": "hamta_mote", "arguments": {"mote_id": target_id}}]
        reference += [{"tool": "hamta_kalender", "arguments": {"epost": e, "datum": d.isoformat()}}
                      for d in later for e in participants][:4]
        reference.append({"tool": "flytta_mote", "arguments": {"mote_id": target_id, "datum": new_date,
                                                              "start": new_start}})
        reference += [{"tool": "skicka_mejl", "arguments": {
            "till": e, "amne": f"Nytt datum för {meetings[target_id]['title'].lower()}",
            "text": f"Hej {emails[e].split()[0]}! Mötet är flyttat till {new_date} kl. {new_start}."}}
            for e in participants]
        reference.append({"final": f"Mötet är flyttat till {new_date} {new_start} och alla deltagare har fått mejl."})

        def check(st, final):
            target = st.meetings[target_id]
            others_changed = any(st.meetings[mid] != original[mid] for mid in original if mid != target_id)
            moved_right = target["date"] == new_date and hm(target["start"]) == new_start
            if others_changed or not moved_right:
                return {"reward": 0.0, "score": 0.0, "moved_right": moved_right, "others_changed": others_changed}
            mails = {}
            for mail in st.outbox:
                mails.setdefault(mail["to"], []).append(mail["subject"] + "\n" + mail["text"])
            notified = sum(1 for e in participants if len(mails.get(e, [])) == 1
                           and new_date in mails[e][0] and re.search(rf"\b{new_start}\b", mails[e][0]))
            strangers = sum(1 for e in mails if e not in participants)
            score = 0.6 + 0.4 * max(0, notified - strangers) / len(participants)
            return {"reward": score, "score": score, "moved_right": True, "notified": notified,
                    "strangers": strangers}

        instruction = (
            f"Du är assistent på {world.org.name} och har tillgång till kalendersystemet. "
            f"{emails[absent]} har fått förhinder och är borta hela {day.isoformat()}, så mötet {target_id} den dagen "
            f"måste flyttas. Flytta det till den tidigaste tid senare samma vecka (till och med "
            f"{week[-1].isoformat()}) då alla mötets deltagare är lediga under hela mötet. Arbetstid är 08:00–17:00 "
            "på vardagar som inte är röda dagar, lunch 12:00–13:00 är blockerad och mötet ska börja på hel- eller "
            "halvtimme. Ändra inga andra möten. Mejla sedan varje deltagare ett meddelande med det nya datumet "
            "(ÅÅÅÅ-MM-DD) och den nya starttiden (TT:MM). Avsluta med ett kort meddelande utan verktygsanrop.")
        return ToolTask(instruction, state, TOOLS, check, reference,
                        max_steps=12 + 3 * len(participants) * len(later),
                        meta={"participants": len(participants), "days_after": len(later)})


def create():
    return MeetingReschedule()
