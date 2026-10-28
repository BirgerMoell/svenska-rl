"""Kontoret: one consistent synthetic Swedish organisation that environments draw tasks from.

A `World` is generated from an RNG: the organisation, its staff, customers and suppliers, products, invoices and
bank payments. Environments take the parts they need, so tasks across areas share the same entities, identifiers
and conventions (integer öre, VAT 25/12/6 %, OCR references, Swedish working days). All data is synthetic.
"""
from __future__ import annotations

import datetime as dt
from dataclasses import dataclass, field

from svrl.kontoret import ids, kalender

FIRST_NAMES = ["Anna", "Erik", "Maria", "Lars", "Karin", "Johan", "Sara", "Anders", "Emma", "Mikael", "Elin",
               "Fredrik", "Linnea", "Oskar", "Ida", "Nils", "Hanna", "Ahmed", "Fatima", "Mehmet", "Leyla", "Jonas",
               "Sofia", "Per", "Malin", "Ali", "Amina", "Gustav", "Ebba", "Viktor", "Tove", "Daniel", "Yasmin",
               "Kristina", "Mohammed", "Agnes", "Hugo", "Alva", "Ville", "Saga"]
LAST_NAMES = ["Andersson", "Johansson", "Karlsson", "Nilsson", "Eriksson", "Larsson", "Olsson", "Persson",
              "Svensson", "Gustafsson", "Pettersson", "Jonsson", "Jansson", "Hansson", "Bengtsson", "Lindberg",
              "Lindqvist", "Berg", "Holm", "Sandberg", "Ali", "Mohammadi", "Yilmaz", "Nyström", "Lundgren",
              "Hedlund", "Ekström", "Sjöberg", "Wallin", "Engström"]
COMPANY_STEMS = ["Norrsken", "Fjällbacka", "Älvdal", "Granskog", "Kustlinje", "Solvik", "Ekbacken", "Stenhamra",
                 "Björkudden", "Lövånger", "Sjöglimt", "Tallmon", "Vinterviken", "Havsbris", "Mälarvy", "Ängsgård",
                 "Klippan", "Furulund", "Strandvik", "Hagaberg", "Rönnskär", "Ljungby", "Myrbacka", "Skärgårds"]
COMPANY_KINDS = ["Bygg", "Konsult", "Data", "Städ", "Transport", "Café", "Tryckeri", "El", "Måleri", "Revision",
                 "Trädgård", "Fastighet", "Media", "Teknik", "Kontorsservice"]
DEPARTMENTS = ["Ekonomi", "HR", "Inköp", "Försäljning", "IT", "Kundtjänst", "Kommunikation", "Ledning"]
PRODUCTS = [("Konsulttimme", 25, (650, 1450)), ("Licens, månadsvis", 25, (120, 900)),
            ("Kontorsmaterial", 25, (40, 400)), ("Utbildningsdag", 25, (2500, 9000)),
            ("Livsmedel till personalfest", 12, (80, 600)), ("Hotellnatt", 12, (900, 2100)),
            ("Facklitteratur", 6, (180, 650)), ("Persontransport", 6, (90, 900)),
            ("Serviceavtal, kvartal", 25, (1500, 12000)), ("Frakt", 25, (99, 450))]


@dataclass
class Person:
    first: str
    last: str
    department: str
    email: str
    phone: str
    id_number: str

    @property
    def name(self) -> str:
        return f"{self.first} {self.last}"


@dataclass
class Company:
    name: str
    org_number: str
    bankgiro: str
    contact: Person
    city: str


@dataclass
class InvoiceLine:
    description: str
    quantity: int
    unit_price: int  # öre, excluding VAT
    vat_percent: int
    discount_percent: int = 0

    def net(self) -> int:
        gross = self.quantity * self.unit_price
        return gross - round_half_up(gross * self.discount_percent, 100)

    def vat(self) -> int:
        return round_half_up(self.net() * self.vat_percent, 100)


@dataclass
class Invoice:
    number: str
    customer: Company
    issued: dt.date
    due: dt.date
    ocr: str
    lines: list = field(default_factory=list)
    paid: int = 0  # öre registered so far

    def net(self) -> int:
        return sum(line.net() for line in self.lines)

    def vat(self) -> int:
        return sum(line.vat() for line in self.lines)

    def total(self) -> int:
        return self.net() + self.vat()

    def remaining(self) -> int:
        return self.total() - self.paid


@dataclass
class Payment:
    id: str
    date: dt.date
    amount: int  # öre
    payer: str
    reference: str  # OCR or free-text message from the payer


def round_half_up(numerator: int, denominator: int) -> int:
    """Integer division rounding halves away from zero (the rule stated in every task that rounds)."""
    q, r = divmod(abs(numerator), denominator)
    q += 2 * r >= denominator
    return q if numerator >= 0 else -q


CITIES = ["Stockholm", "Göteborg", "Malmö", "Uppsala", "Umeå", "Luleå", "Örebro", "Linköping", "Jönköping",
          "Sundsvall", "Gävle", "Karlstad", "Växjö", "Visby", "Östersund", "Kiruna"]


class World:
    def __init__(self, rng, today: dt.date | None = None, n_staff: int = 12, n_customers: int = 8):
        self.rng = rng
        self.today = today or self._working_day(dt.date(2026, 1, 1) + dt.timedelta(days=rng.randint(0, 700)))
        self.org = self._company(own=True)
        self.staff = [self.person() for _ in range(n_staff)]
        used = {self.org.name}
        self.customers = []
        while len(self.customers) < n_customers:
            c = self._company()
            if c.name not in used:
                used.add(c.name)
                self.customers.append(c)
        self._invoice_seq = rng.randint(1000, 8000)

    def _working_day(self, d: dt.date) -> dt.date:
        while not kalender.is_working_day(d):
            d += dt.timedelta(days=1)
        return d

    def person(self, department: str | None = None) -> Person:
        rng = self.rng
        first, last = rng.choice(FIRST_NAMES), rng.choice(LAST_NAMES)
        email = f"{first}.{last}@exempel.se".lower().translate(str.maketrans("åäöé", "aaoe"))
        phone = f"07{rng.choice([0, 2, 3, 6, 9])}-{rng.randint(100, 999)} {rng.randint(10, 99)} {rng.randint(10, 99)}"
        return Person(first, last, department or rng.choice(DEPARTMENTS), email, phone, ids.samordningsnummer(rng))

    def _company(self, own: bool = False) -> Company:
        rng = self.rng
        name = f"{rng.choice(COMPANY_STEMS)} {rng.choice(COMPANY_KINDS)} AB"
        return Company(name, ids.organisationsnummer(rng), ids.bankgiro(rng), self.person(), rng.choice(CITIES))

    def invoice(self, customer: Company | None = None, n_lines: tuple = (1, 4), discounts: bool = False,
                vat_rates: tuple | None = None) -> Invoice:
        rng = self.rng
        self._invoice_seq += rng.randint(1, 7)
        issued = self.today - dt.timedelta(days=rng.randint(5, 60))
        lines = []
        for _ in range(rng.randint(*n_lines)):
            desc, vat, (lo, hi) = rng.choice(PRODUCTS)
            if vat_rates:
                vat = rng.choice(vat_rates)
            price = rng.randint(lo, hi) * 100 + rng.choice([0, 0, 0, 50, rng.randint(1, 99)])
            discount = rng.choice([0, 0, 5, 10, 15, 20]) if discounts else 0
            lines.append(InvoiceLine(desc, rng.randint(1, 12), price, vat, discount))
        return Invoice(str(self._invoice_seq), customer or rng.choice(self.customers), issued,
                       issued + dt.timedelta(days=rng.choice([10, 15, 20, 30])), ids.ocr(rng), lines)
