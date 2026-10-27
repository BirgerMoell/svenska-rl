# Tidigaste gemensamma möte

Find the earliest free 30-minute interval for three fictional participants within
08:00–16:00 on a common day. Busy slots are explicit and at least one solution
exists. The verifier accepts only the earliest shared slot among the four actions.

Run `python3 -m svrl.cli demo calendar_booking` and `python3 -m svrl.cli smoke calendar_booking`.
Independent tests enumerate free slots from the displayed schedules.
Own synthetic generator: Apache-2.0. No external calendars or personal data.
Limitation: no date changes, time zones, booking mutations or variable durations.
