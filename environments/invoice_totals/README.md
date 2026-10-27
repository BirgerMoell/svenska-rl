# Fakturans totalsumma

Swedish arithmetic over three synthetic invoice lines with 6%, 12% or 25% VAT.
Prices use integer öre and whole kronor before VAT. Exactly one of four displayed
totals is correct. Distractors include omitted VAT and arithmetic errors.

Run `python3 -m svrl.cli demo invoice_totals` and `python3 -m svrl.cli smoke invoice_totals`.
Independent tests parse the displayed lines and reconstruct the sum and VAT.
No real invoices or FinQA questions are used. Own synthetic generator: Apache-2.0.
Limitation: single-turn, one currency, no discounts or mixed VAT rates.
