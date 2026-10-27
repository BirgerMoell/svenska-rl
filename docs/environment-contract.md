# Environment contract v0.1

This local single-turn contract is inspired by OpenEnv, but is not wire-compatible.
A future adapter must be tested against a pinned OpenEnv version.

Each package exports `create()` from `environment.py`, plus a manifest with an id
matching the directory. `svrl.core.load(id)` discovers it automatically.

- `reset(seed: int, split: train|dev|eval)` returns public observations.
- `public_prompt()` serializes the instruction and four possible actions.
- `step(action)` accepts A/B/C/D, ignoring surrounding whitespace.
- One action terminates the episode. Malformed input terminates with zero reward.
- A second step raises `RuntimeError`; reset starts another episode.
- `reference_action()` is trusted qualification code, never an agent-facing tool.
- Ground truth comes from simulator state, not a model judging its own answer.

Public observations contain only `instruction`, `actions`, `max_steps`. Local
Python callers can inspect internals: this runtime is not an adversarial sandbox.
Production tool environments need an isolated process boundary.

Use integer minor units for money. Define rounding, units, dates, time zones,
boundaries and ambiguity. Exactly one action must be correct; randomize its position.
Train/dev/eval have different deterministic RNG namespaces. Also hold out templates,
entities or compositions where useful. Public evaluation is reproducible, not secret.
Use dev for tuning. Independent tests must reconstruct outcomes from observations,
not merely compare the verifier against its own stored answer.

Multi-turn tools, state mutation, browser interaction, partial rewards and recovery
need tested runtime extensions. Do not flatten these capabilities into trivia.
