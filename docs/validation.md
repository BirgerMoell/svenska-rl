# Validation protocol v0.2

Reports describe runs, not trusted badges. Independent workers must reproduce evidence at an exact source digest
before future catalogue promotion. Finite tests cannot prove that an environment has no bugs.

## Contract (CI, CPU, standard library)

`python3 -m svrl.cli check ENV_ID` (see `docs/environment-contract.md`): determinism, task diversity, disjoint
splits, the reference answer or action list earns 1.0 on every seed, shortcut probes earn at most 0.3 mean
reward, malformed actions are handled, step limits are enforced. Plus independent domain tests that re-solve
tasks from the public prompt. CI runs this for every environment on every pull request.

## L1: model baseline

`python3 -m svrl.cli rollout ENV_ID --base-url URL --model NAME --count 64 --out runs/ENV-MODEL.jsonl` with a
pinned model (Hugging Face commit or GGUF digest), greedy decoding, on the eval split. Report mean reward, solved
share and the per-level breakdown. A useful training environment leaves room: roughly 10–90 % for the target model.
An environment that every model solves, or none does, still passes the contract but teaches little.

## L2: real RL training

Require the contract and L1, a pinned >=100M-parameter causal LM, >=2 optimizer steps, finite loss and gradient
curves, nonzero gradients, changed weights, a checkpoint digest, source digest, library versions, seed and
configuration. `python3 -m svrl.cli train` runs a small GRPO (typed environments); larger runs export data
with `svrl.cli export` to an external RLVR trainer and report the same fields. Policy-gradient loss can rise,
fall or be negative; decreasing loss is not an acceptance criterion.

## L3: held-out improvement

Evaluate greedily before and after on identical >=32 eval seeds with the same inference budget
(`svrl.cli compare before.jsonl after.jsonl`, or the before/after inside a `train` report). Predeclare training
length and hyperparameters; do not select checkpoints on eval. Require >=0.05 absolute mean reward improvement
and a strictly positive lower bound of a paired 95 % bootstrap interval (2,000 resamples). Report all cases.
Otherwise keep L2 and mark L3 inconclusive. Improvement is specific to that experiment.

Tune on dev. Repeated final experiments need fresh preregistered eval suites; report failures as well as
successes. Independent replication and evaluator-owned cases are required for future trusted L3 badges.

## Integrity

Contributor-edited manifests never confer trusted status. Bind results to source, model, data and protocol
versions. Keep credentials out of reports. Separate publication from executing submitted code. Disposable L2/L3
workers have no repository write credentials. CI must never check out a PR in a privileged job.
