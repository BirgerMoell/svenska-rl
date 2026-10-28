# Första gemensamma mötestid

Typed answer (`datetime`, or `INGEN TID`). Calendars over 3-5 days that may include weekends and Swedish public holidays; working hours 08-17, lunch 12-13, meeting length 30-90 minutes. Level 1 names the holidays in the window, level 2 relies on knowing them, level 3 adds a buffer rule.

Independent test: brute-forces the earliest slot from the busy times parsed from the prompt.

Run `python3 -m svrl.cli demo meeting_slot` and `python3 -m svrl.cli check meeting_slot`. Contract v0.2 (docs/environment-contract.md); data from the shared generator in `svrl.kontoret`. Synthetic, Apache-2.0.
