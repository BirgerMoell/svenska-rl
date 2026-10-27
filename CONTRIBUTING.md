# Agent contributions

Start with [the skill](.agents/skills/contribute-svenska-rl/SKILL.md).
An agent builds an environment, enriches a data pack, or runs a compute experiment.
It handles implementation, documentation, tests and PR submission.

## Claims

Use an open owner-authored issue containing `<!-- svrl-task: ID -->`.
Post exactly `/claim`. The earliest still-active claim in chronological comment
order holds a 24-hour lease. A bot replies with the holder and expiry. Wait for
confirmation before starting. Use `/renew` or `/release`; only the holder can do
these. A repeated `/claim` by the holder renews. All times are UTC.

The command history is authoritative; replies are snapshots and may race. Re-read
recent commands if a reply looks stale. Edited and deleted commands are unsupported:
post a new command. Comments are not immutable. This lightweight protocol prevents
ordinary collisions; it is not a security boundary or durable distributed scheduler.

## Submission

Use a fork and `gh pr create` targeting `BirgerMoell/svenska-rl:main`.
Link the issue with `Closes #N`. Include source digest and actual reports. Do not
commit weights or large traces. Each environment has an importable package,
manifest, implementation, independent domain tests, and a README.

CI uses unprivileged `pull_request` events on hosted runners. Do not execute an
arbitrary PR on a persistent compute worker with credentials.

## Release boundary

Automated claims and CI are implemented. Independent agent review, trusted badge
promotion, automatic merging and compute scheduling are separate infrastructure
tasks. Contributors need no manual reviews. Their work is ready when a PR and
its evidence are submitted; release awaits the separate coordinator.
