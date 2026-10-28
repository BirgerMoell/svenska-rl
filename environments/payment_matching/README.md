# Matcha inbetalningar mot kundfakturor

Typed answer (`mapping`, partial reward per payment). Open invoices with OCR references and the day's bank payments. Rules: an exact valid OCR reference wins (part payments too); otherwise payer + exact amount + uniqueness; otherwise `omatchad`. Distractors: references with swapped digits (fail the Luhn check), two identical invoices for the same customer, unknown payers.

Independent test: re-applies the rules to the tables parsed from the prompt, with its own Luhn check.

Run `python3 -m svrl.cli demo payment_matching` and `python3 -m svrl.cli check payment_matching`. Contract v0.2 (docs/environment-contract.md); data from the shared generator in `svrl.kontoret`. Synthetic, Apache-2.0.
