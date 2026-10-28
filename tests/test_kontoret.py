import datetime as dt
import random
import unittest

from svrl.kontoret import fmt, ids, kalender
from svrl.kontoret.world import World, round_half_up


class IdentifierTests(unittest.TestCase):
    def test_luhn_known_values(self):
        # Skatteverket's published example personnummer 811218-9876 and Bankgirot's OCR example.
        self.assertTrue(ids.luhn_valid("811218-9876"))
        self.assertFalse(ids.luhn_valid("811218-9877"))
        self.assertEqual(ids.luhn_digit("811218987"), "6")

    def test_generated_identifiers_are_valid(self):
        rng = random.Random(1)
        for _ in range(500):
            pnr = ids.samordningsnummer(rng)
            self.assertTrue(ids.luhn_valid(pnr))
            self.assertGreaterEqual(int(pnr[4:6]), 61)  # coordination-number day: never a real birth date
            self.assertTrue(ids.luhn_valid(ids.organisationsnummer(rng)))
            self.assertTrue(ids.luhn_valid(ids.bankgiro(rng)))
            ref = ids.ocr(rng)
            self.assertTrue(ids.ocr_valid(ref))
            self.assertFalse(ids.ocr_valid(ref[:-1] + str((int(ref[-1]) + 1) % 10)))


class CalendarTests(unittest.TestCase):
    def test_known_holidays(self):
        self.assertEqual(kalender.easter(2026), dt.date(2026, 4, 5))
        self.assertEqual(kalender.easter(2027), dt.date(2027, 3, 28))
        h = kalender.holidays(2026)
        self.assertEqual(h[dt.date(2026, 6, 19)], "midsommarafton")
        self.assertEqual(h[dt.date(2026, 5, 14)], "Kristi himmelsfärdsdag")
        self.assertEqual(h[dt.date(2026, 10, 31)], "alla helgons dag")
        self.assertFalse(kalender.is_working_day(dt.date(2026, 4, 3)))  # långfredagen
        self.assertTrue(kalender.is_working_day(dt.date(2026, 4, 7)))

    def test_add_working_days_skips_easter(self):
        self.assertEqual(kalender.add_working_days(dt.date(2026, 4, 2), 1), dt.date(2026, 4, 7))


class MoneyTests(unittest.TestCase):
    def test_format_and_parse_round_trip(self):
        for ore in (0, 5, 99, 100, 123456, 100000000, -2550):
            self.assertEqual(fmt.parse_money(fmt.money(ore)), ore)

    def test_tolerant_parsing(self):
        for text, ore in (("1 234,50 kr", 123450), ("1234.50", 123450), ("1 234:50 SEK", 123450),
                          ("12 345 kr", 1234500), ("1.234,5 kr", 123450), ("17,00", 1700)):
            self.assertEqual(fmt.parse_money(text), ore, text)

    def test_hedged_answers_do_not_parse(self):
        for text in ("100 kr eller 200 kr", "", "ungefär", "1 234,50 kr (moms 246,90 kr)"):
            self.assertIsNone(fmt.parse_money(text), text)

    def test_round_half_up(self):
        self.assertEqual(round_half_up(250, 100), 3)
        self.assertEqual(round_half_up(249, 100), 2)
        self.assertEqual(round_half_up(-250, 100), -3)


class WorldTests(unittest.TestCase):
    def test_world_is_deterministic_and_consistent(self):
        a, b = World(random.Random(7)), World(random.Random(7))
        self.assertEqual(a.org.name, b.org.name)
        self.assertTrue(kalender.is_working_day(a.today))
        invoice = a.invoice(discounts=True)
        self.assertEqual(invoice.total(), invoice.net() + invoice.vat())
        self.assertTrue(ids.ocr_valid(invoice.ocr))


if __name__ == "__main__":
    unittest.main()
