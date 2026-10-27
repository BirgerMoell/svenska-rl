# Validation protocol v0.1

Reports describe runs, not trusted badges. Independent workers must reproduce
evidence at an exact source digest before future catalogue promotion. Finite tests
cannot prove that an environment has no bugs.

## L1: runnable

Require contract tests across 100 seeds per split, independent domain tests,
determinism, diverse prompts, correct termination, no observed split overlap,
zero rewards for malformed/incorrect actions, and eight tiny-policy episodes.
The bundled policy is an 8,356-parameter randomly initialized neural network, not
a pretrained language model. It establishes model-to-environment execution, not
learning. Reference success is 1.0; uniform random expected reward is 0.25.

## L2: real RL training

Require L1, a pinned >=100M-parameter causal LM, >=2 optimizer steps, batch >=2,
finite loss/gradient curves, nonzero gradients, changed weights, a checkpoint
digest, source digest, model revision, library versions, seed and configuration.
The trainer uses REINFORCE over A/B/C/D with a fixed 0.25 baseline. Full-parameter
training can require substantial memory. Loss can rise, fall or be negative;
decreasing policy-gradient loss is not an acceptance criterion.

## L3: held-out improvement

Evaluate greedily before/after on identical >=32 held-out cases and inference
budgets. Predeclare training length and hyperparameters; do not select checkpoints
on eval. Require >=0.05 absolute mean reward improvement and a strictly positive
lower bound of a paired 95% bootstrap interval (2,000 resamples). Report all cases.
Otherwise preserve L2 and mark L3 inconclusive. Improvement is specific to that
experiment, not proof of general usefulness.

Tune on dev. Repeated final experiments need fresh preregistered eval suites;
report failures as well as successes. Independent replication and evaluator-owned
cases are required for future trusted L3 badges.

## Integrity

Contributor-edited manifests never confer trusted status. Bind results to source,
model, data and protocol versions. Keep credentials out of reports. Separate
publication from executing submitted code. Disposable L2/L3 workers have no
repository write credentials. CI must never checkout a PR in a privileged job.
