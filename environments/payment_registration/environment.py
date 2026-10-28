"""Registrera dagens inbetalningar i kundreskontran och påminn om kvarstående belopp (verktyg, flera steg).

Tools read the open invoices and the bank file, register a payment against an invoice and send e-mail. The
matching rules are those of `payment_matching`. After registering, the customer contact of every invoice that is
part-paid (remaining > 0 after a registered payment) must get one e-mail stating the invoice number and the
remaining amount. Scored on the final state: correct registrations, no wrong registrations, correct reminders
(right recipient, invoice number and remaining amount in the text), no e-mails to anyone else.
Reward = max(0, (correct - wrong) / required); 1.0 only for an exactly right end state.
"""
import datetime as dt
import re
from dataclasses import dataclass, field

from svrl.contract import Tool, ToolEnvironment, ToolError, ToolTask
from svrl.kontoret import fmt, ids
from svrl.kontoret.reskontra import corrupt_reference, match_payment
from svrl.kontoret.world import World


@dataclass
class Ledger:
    invoices: dict                      # number -> {"customer", "contact_email", "total", "ocr", "paid"}
    payments: dict                      # id -> {"date", "payer", "amount", "reference"}
    registered: dict = field(default_factory=dict)   # payment id -> invoice number
    outbox: list = field(default_factory=list)


def list_payments(state):
    return [{"id": pid, **{k: (v if k != "amount" else fmt.money(v)) for k, v in p.items()}}
            for pid, p in state.payments.items() if pid not in state.registered]


def list_invoices(state, kund=None):
    rows = [{"fakturanummer": n, "kund": i["customer"], "belopp": fmt.money(i["total"]), "ocr": i["ocr"],
             "betalt": fmt.money(i["paid"])} for n, i in state.invoices.items() if i["paid"] < i["total"]]
    return [r for r in rows if kund is None or kund.lower() in r["kund"].lower()]


def get_invoice(state, fakturanummer):
    inv = state.invoices.get(fakturanummer)
    if inv is None:
        raise ToolError(f"faktura {fakturanummer} finns inte")
    return {"fakturanummer": fakturanummer, "kund": inv["customer"], "kontakt_epost": inv["contact_email"],
            "belopp": fmt.money(inv["total"]), "betalt": fmt.money(inv["paid"]),
            "kvar_att_betala": fmt.money(inv["total"] - inv["paid"]), "ocr": inv["ocr"]}


def register(state, betalnings_id, fakturanummer):
    if betalnings_id not in state.payments:
        raise ToolError(f"inbetalning {betalnings_id} finns inte")
    if betalnings_id in state.registered:
        raise ToolError(f"inbetalning {betalnings_id} är redan registrerad")
    if fakturanummer not in state.invoices:
        raise ToolError(f"faktura {fakturanummer} finns inte")
    state.registered[betalnings_id] = fakturanummer
    inv = state.invoices[fakturanummer]
    inv["paid"] += state.payments[betalnings_id]["amount"]
    return {"status": "registrerad", "kvar_att_betala": fmt.money(inv["total"] - inv["paid"])}


def send_mail(state, till, amne, text):
    state.outbox.append({"to": till.strip().lower(), "subject": amne, "text": text})
    return {"status": "skickat"}


TOOLS = [
    Tool("lista_inbetalningar", "Listar dagens ännu inte registrerade inbetalningar från banken.",
         {"type": "object", "properties": {}, "required": []}, list_payments),
    Tool("lista_obetalda_fakturor", "Listar obetalda kundfakturor, valfritt filtrerade på kundnamn.",
         {"type": "object", "properties": {"kund": {"type": "string"}}, "required": []}, list_invoices),
    Tool("hamta_faktura", "Hämtar en faktura med kontaktperson och kvarstående belopp.",
         {"type": "object", "properties": {"fakturanummer": {"type": "string"}}, "required": ["fakturanummer"]},
         get_invoice),
    Tool("registrera_betalning", "Registrerar en inbetalning mot en faktura. Kan inte ångras.",
         {"type": "object", "properties": {"betalnings_id": {"type": "string"}, "fakturanummer": {"type": "string"}},
          "required": ["betalnings_id", "fakturanummer"]}, register, mutates=True),
    Tool("skicka_mejl", "Skickar ett e-postmeddelande.",
         {"type": "object", "properties": {"till": {"type": "string"}, "amne": {"type": "string"},
                                           "text": {"type": "string"}}, "required": ["till", "amne", "text"]},
         send_mail, mutates=True),
]


class PaymentRegistration(ToolEnvironment):
    id = "payment_registration"

    def generate(self, rng):
        world = World(rng, n_customers=rng.randint(3, 6))
        invoices = [world.invoice(n_lines=(1, 2)) for _ in range(rng.randint(3, 6))]
        payments, plan = {}, []
        for k, kind in enumerate(rng.choices(["ocr", "ocr_part", "bad_ocr", "no_ref", "unknown"],
                                             weights=[4, 3, 2, 2, 1], k=rng.randint(2, 5))):
            inv = rng.choice(invoices)
            payer, amount, reference = inv.customer.name, inv.total(), inv.ocr
            if kind == "ocr_part":
                amount = inv.total() * rng.choice([25, 40, 50]) // 100
            elif kind == "bad_ocr":
                reference = corrupt_reference(inv.ocr, rng)
            elif kind == "no_ref":
                reference = ""
            elif kind == "unknown":
                payer, reference, amount = world.person().name, ids.ocr(rng), rng.randint(200, 20000) * 100
            pid = f"B{k + 1:02d}"
            payments[pid] = {"date": (world.today - dt.timedelta(days=rng.randint(0, 2))).isoformat(),
                             "payer": payer, "amount": amount, "reference": reference}
        # Expected end state: apply the rules in payment order against the invoices' totals.
        expected, paid = {}, {i.number: 0 for i in invoices}
        for pid, p in payments.items():
            match = match_payment(invoices, p["payer"], p["amount"], p["reference"])
            if match != "omatchad":
                expected[pid] = match
                paid[match] += p["amount"]
        by_number = {i.number: i for i in invoices}
        reminders = {n: by_number[n].total() - paid[n] for n in set(expected.values())
                     if 0 < paid[n] < by_number[n].total()}
        contacts = {n: by_number[n].customer.contact.email for n in by_number}
        state = Ledger({i.number: {"customer": i.customer.name, "contact_email": i.customer.contact.email,
                                   "total": i.total(), "ocr": i.ocr, "paid": 0} for i in invoices}, payments)
        reference = [{"tool": "lista_inbetalningar", "arguments": {}},
                     {"tool": "lista_obetalda_fakturor", "arguments": {}}]
        reference += [{"tool": "registrera_betalning", "arguments": {"betalnings_id": p, "fakturanummer": n}}
                      for p, n in expected.items()]
        reference += [{"tool": "skicka_mejl", "arguments": {
            "till": contacts[n], "amne": f"Kvarstående belopp på faktura {n}",
            "text": f"Hej! Vi har tagit emot en delbetalning på faktura {n}. Kvar att betala: {fmt.money(rest)}."}}
            for n, rest in sorted(reminders.items())]
        reference.append({"final": "Klart: inbetalningarna är registrerade och påminnelser skickade."})

        def check(st, final):
            required = len(expected) + len(reminders) + sum(1 for p in payments if p not in expected)
            correct = sum(st.registered.get(p) == n for p, n in expected.items())
            correct += sum(1 for p in payments if p not in expected and p not in st.registered)
            wrong = sum(1 for p, n in st.registered.items() if expected.get(p) != n)
            sent_ok = set()
            for mail in st.outbox:
                hit = None
                for n, rest in reminders.items():
                    amounts = {fmt.parse_money(m) for m in re.findall(r"\d[\d  .]*,\d{2}", mail["text"])}
                    if mail["to"] == contacts[n] and n in mail["text"] + mail["subject"] and rest in amounts:
                        hit = n
                if hit and hit not in sent_ok:
                    sent_ok.add(hit)
                else:
                    wrong += 1  # e-mail to the wrong person, a duplicate, or without the right content
            correct += len(sent_ok)
            score = max(0.0, (correct - wrong) / required)
            return {"reward": score, "score": score, "correct": correct, "wrong": wrong, "required": required}

        instruction = (
            f"Du arbetar med kundreskontran hos {world.org.name} och har tillgång till ekonomisystemets verktyg. "
            "Registrera dagens inbetalningar mot rätt fakturor enligt reglerna nedan. Registrera inte "
            "inbetalningar som inte kan matchas. När du är klar ska kontaktpersonen för varje faktura som efter "
            "registreringen är delbetald (något betalt men inte allt) få ett mejl med fakturanumret och det "
            "kvarstående beloppet i kronor. Skicka inga andra mejl. Avsluta med ett kort meddelande utan "
            "verktygsanrop när allt är klart.\n\nRegler:\n"
            "1. Om referensen är exakt samma som en fakturas OCR-nummer hör betalningen till den fakturan, även om "
            "beloppet avviker.\n"
            "2. Om referensen saknas eller inte är ett giltigt OCR-nummer: matcha bara om betalaren är fakturans "
            "kund, beloppet är exakt fakturans belopp och det finns exakt en sådan faktura.\n"
            "3. Annars ska inbetalningen lämnas oregistrerad.")
        return ToolTask(instruction, state, TOOLS, check, reference, max_steps=8 + 2 * len(payments) + len(reminders),
                        meta={"payments": len(payments), "matches": len(expected), "reminders": len(reminders)})


def create():
    return PaymentRegistration()
