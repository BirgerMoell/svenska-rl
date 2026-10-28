# Kontoret: the shared simulated organisation

`svrl.kontoret` generates one consistent synthetic Swedish workplace from a seed, so environments in different
areas share entities and conventions instead of each inventing their own.

| Module | Contents |
|---|---|
| `world.py` | `World(rng)`: the organisation, staff (`Person`: name, department, e-mail, mobile, identity number), customers (`Company`: org number, bankgiro, contact), invoices (`Invoice`, `InvoiceLine` with VAT 25/12/6 % and discounts), payments; `round_half_up` |
| `ids.py` | Luhn check digits; synthetic identity numbers (coordination-number form, day + 60, so never a real birth date), organisation numbers (55xxxx), bankgiro numbers, OCR references with length and check digit |
| `kalender.py` | Swedish public holidays incl. Easter-dependent days, midsommar, alla helgons dag and the non-working eves; working-day arithmetic; `first_common_slot` scheduling |
| `fmt.py` | Swedish money and date formatting and tolerant parsing (integer öre internally); locale table for later translation |
| `reskontra.py` | Accounts-receivable rules: OCR-first payment matching with a unique-amount fallback; corrupted references for distractors |

Conventions: money is integer öre; rounding is half-up and always stated in the prompt; dates are ISO in answers;
everything is synthetic (`exempel.se` addresses, invented company names).

## Roadmap

Next systems, each with read/write tools so tool episodes can cross systems:

1. Ledger with the BAS chart of accounts (verifications, VAT reporting, period close).
2. Accounts payable (supplier invoices, attestation, payment files).
3. HR and payroll (employment terms, leave and holiday pay, sick pay, time reports).
4. Case management for public administration (registration, deadlines, confidentiality review, decisions).
5. CRM and support tickets (customer records, SLA, escalations).
6. Document archive (versions, templates, retention).

Each system should come with a generator, tool functions, and at least one typed and one tool environment.
