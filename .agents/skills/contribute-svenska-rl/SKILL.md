---
name: contribute-svenska-rl
description: Build Swedish RL environments or contribute reproducible compute experiments to BirgerMoell/svenska-rl. Use when asked to contribute through the project link or work on its claimed tasks.
---

# Contribute to Svenska RL

Repository: https://github.com/BirgerMoell/svenska-rl
Site: https://birgermoell.github.io/svenska-rl/

The person delegates the work to you. Handle selection, implementation, tests,
documentation and submission. Persistent skill installation is optional.

## Start

1. Check `gh auth status` or an available GitHub connector. Clone the repository
   and read `AGENTS.md`, `CONTRIBUTING.md`, `docs/environment-contract.md` and
   `docs/validation.md`.
2. Default to one build task. For compute contributions read `docs/compute.md`.
   Respect the person's budget. Do not provision paid services. A CPU L1 run is
   the default; large model downloads and training require a supplied compute budget.
3. Run `gh issue list --repo BirgerMoell/svenska-rl --state open --limit 100`.
   Choose a bounded owner-authored task with a `svrl-task` marker. Read comments
   and linked PRs; avoid an active lease or completed work. Catalogue entries
   alone are not claims. If none is available, propose a concrete missing capability.
4. Post `/claim`, then wait for the claims workflow reply. Check your GitHub
   account holds the lease. If the workflow fails or you lose the race, do not
   assume ownership; choose another task or report the blocker.

## Build

Use the reference environments as minimal examples. Preserve the intended
capability; do not replace a workflow with unrelated easy multiple-choice trivia.
Multi-turn work may need a separate shared-runtime prerequisite ticket.

Implement a generator or validated data pack, public observations, actions,
authoritative-state verifier, reference solver, independent domain tests and
train/dev/eval splits. Never expose answers or verifier internals as model tools.
Use Swedish instructions and synthetic data by default; record external data
provenance and licenses. Never train on evaluation-only datasets.

The starter runner supports four terminal actions and constrained-action LM RL.
Read the environment contract before extending it.

## Qualify

Regenerate the site catalogue with `python3 scripts/build_site.py` after adding
or modifying environment metadata. Run domain and project tests, `python3 -m svrl.cli check ENV_ID` and
`python3 -m svrl.cli smoke ENV_ID --output runs/ENV_ID-l1.json`.
If necessary, install PyTorch in a local virtual environment from an established
registry when permitted. A reference solver alone is not L1.

L2 requires real reward-based training of a 100M+ model, finite losses/gradients
and changed weights. L3 also requires paired held-out improvement. Follow
`docs/compute.md`. If resources are insufficient, submit L1 with L2/L3 pending.

## Submit

Fork and push a branch with the person's account. Open a PR against main, link
the issue and include evidence and limitations. Wait for CI and fix failures.
Renew the claim if needed. Stop after three failed repair cycles and report the
remaining failure; do not repeatedly spend compute without a new diagnosis.

Do not weaken shared acceptance checks, merge your own work or approve your own
evidence. Shared changes need separate PRs. Report the PR URL, actual levels and
outstanding gates. No manual implementation or review is required from the person.
