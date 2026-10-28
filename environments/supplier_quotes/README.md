# Välj leverantör utifrån offerter

Typed answer (`mapping`, all-or-nothing). 3-5 supplier quotes with unit price, shipping, delivery time and capacity; the whole need from one supplier within budget and deadline (both inclusive); lowest total cost, ties by delivery time and then name; decline when nothing qualifies. The model gives the supplier and the total cost, so guessing a supplier earns nothing. Modes: ordinary, all late, inclusive boundaries decided by one öre, tied totals.

Ported to contract v0.2 from the multiple-choice contribution in PR #22 (same rules and generation modes).
Independent test: re-applies the rules to the quote table parsed from the prompt.

Run `python3 -m svrl.cli demo supplier_quotes` and `python3 -m svrl.cli check supplier_quotes`. Synthetic, Apache-2.0.
