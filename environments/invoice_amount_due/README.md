# Belopp att betala på en faktura

Typed answer (`money`). Invoice lines with quantities and prices in öre, VAT 25/12/6 % per line, line discounts, an earlier part payment, a credit note and rounding to whole kronor across four levels. About 12 % of tasks hide a price the calculation needs; then the correct answer is `INFORMATION SAKNAS`. All rounding rules are in the prompt.

Independent test: re-parses the invoice table from the prompt and recomputes the amount with its own half-up rounding.

Run `python3 -m svrl.cli demo invoice_amount_due` and `python3 -m svrl.cli check invoice_amount_due`. Contract v0.2 (docs/environment-contract-v0.2.md); data from the shared generator in `svrl.kontoret`. Synthetic, Apache-2.0.
