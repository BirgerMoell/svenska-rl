# Registrera inbetalningar och påminn om restbelopp

Tool episode. Tools: `lista_inbetalningar`, `lista_obetalda_fakturor`, `hamta_faktura`, `registrera_betalning`, `skicka_mejl`. The model registers payments by the `payment_matching` rules and e-mails the contact of every part-paid invoice with the invoice number and remaining amount. Scored on the end state: wrong registrations and stray e-mails cost reward.

Tests: the reference reaches 1.0; a wrong registration lowers the reward; finishing immediately or only reading earns at most the credit for correctly unregistered payments.

Run `python3 -m svrl.cli demo payment_registration` and `python3 -m svrl.cli check payment_registration`. Contract v0.2 (docs/environment-contract.md); data from the shared generator in `svrl.kontoret`. Synthetic, Apache-2.0.
