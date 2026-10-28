# Maskera personuppgifter inför utlämnande

Typed answer (`strings`, multiset F1 partial reward). A case message mixes private persons' identity numbers, mobile numbers, private e-mail, home addresses and names with information that stays (switchboard, functional mailbox, organisation number, case number, the official). Three policies decide which classes to mask.

Independent test: every target occurs in the text; organisation data and the official's contact data are never targets; every identity number is.

Run `python3 -m svrl.cli demo document_redaction` and `python3 -m svrl.cli check document_redaction`. Contract v0.2 (docs/environment-contract.md); data from the shared generator in `svrl.kontoret`. Synthetic, Apache-2.0.
