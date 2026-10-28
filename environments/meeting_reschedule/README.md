# Flytta ett möte och meddela deltagarna

Tool episode. Tools: `lista_personer`, `hamta_mote`, `hamta_kalender`, `flytta_mote`, `skicka_mejl`. A participant is away for the meeting's day; the model finds the earliest common slot later that week (holidays, lunch, working hours), moves only that meeting and e-mails every participant the new date and time. 0.6 for the right move, 0.4 for the notifications; a wrong move or a changed other meeting scores 0.

Tests: the reference reaches 1.0; moving to a wrong time scores 0.

Run `python3 -m svrl.cli demo meeting_reschedule` and `python3 -m svrl.cli check meeting_reschedule`. Contract v0.2 (docs/environment-contract-v0.2.md); data from the shared generator in `svrl.kontoret`. Synthetic, Apache-2.0.
